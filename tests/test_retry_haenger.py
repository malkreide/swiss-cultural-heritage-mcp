"""Eine Anfrage, die hängt, ist kein Fehlschlag — erst die zweite entscheidet.

ANLASS
------
Die geplanten Live-Läufe 184 und 185 (21. und 22.11.2026) fielen je an einem
SIKART-Test, beide Male mit ``httpx.ReadTimeout`` nach 30 s gegen
``datastore_search`` auf opendata.swiss. Nachgemessen am 22.11.2026: gesunde
Antworten kamen in 0,4–3,5 s; einzelne Anfragen hingen über 60 s, und dieselbe
Anfrage direkt danach kam in 1,9 s. Die Quelle war erreichbar, ihr Schema
intakt — sie liess bloss einzelne Anfragen liegen.

Drei Lücken haben daraus einen roten Lauf gemacht, und jede steht hier unter
einem eigenen Test:

1. **Die Werkzeuge für SIKART, Nationalmuseum und Helveticat liefen gar nicht
   über ``_fetch_with_retry``.** Nur Memobase und Dodis taten es. Ein Hänger
   hiess dort 30 s httpx-Timeout und Schluss — länger als das Budget, das der
   Retry dem Client zusagt.
2. **Der erste Versuch bekam das ganze Budget.** Selbst über den Retry hätte
   ein Hänger die 25 s allein verbraucht; die Wiederholung, die ihn gerettet
   hätte, fand nie statt.
3. **Lief das Budget ab, kam ein eingebautes ``TimeoutError``** — nicht in
   ``ExpectedUpstreamError``, also maskiert als «Interner Fehler». Eine
   hängende Quelle sah für das Modell aus wie ein Bug in diesem Server.

Die Uhr hier ist echt und klein, nicht gefälscht: Eine Fake-Uhr, die nur beim
Schlafen vorrückt, kann eine Zusicherung über echte Zeit nicht widerlegen
(`docs/claude/wenn-etwas-rot-ist.md`). Gepatcht wird ``server._http_get``, ein
Name in diesem Modul, nie ``asyncio`` selbst.
"""

from __future__ import annotations

import ast
import asyncio
import time
from pathlib import Path

import httpx
import pytest
from fixture_data import fixture_json
from mcp.server.mcpserver.exceptions import ToolError

from swiss_cultural_heritage_mcp import server
from swiss_cultural_heritage_mcp.server import (
    ArtistSearchInput,
    HeritageItemInput,
    get_heritage_item,
    heritage_search_artists,
)


async def _haengt(*_args, **_kwargs) -> httpx.Response:
    """Antwortet nie. Endet nur, wenn jemand den Versuch abbricht."""
    await asyncio.Event().wait()
    raise AssertionError("unerreichbar")  # pragma: no cover


def _ok(url: str, payload: object) -> httpx.Response:
    return httpx.Response(200, json=payload, request=httpx.Request("GET", url))


@pytest.fixture
def kurze_uhr(monkeypatch):
    """Budget und Versuchsdeckel auf Zehntelsekunden, Backoff auf null."""
    monkeypatch.setattr(server.settings, "retry_total_budget", 3.0)
    monkeypatch.setattr(server.settings, "retry_attempt_timeout", 0.2)
    monkeypatch.setattr(server.settings, "retry_backoff_base", 0.0)


# --- Lücke 2: der Deckel pro Versuch ------------------------------------------


async def test_haengender_versuch_wird_abgebrochen_und_wiederholt(kurze_uhr) -> None:
    aufrufe = 0

    async def erst_haengen_dann_antworten() -> httpx.Response:
        nonlocal aufrufe
        aufrufe += 1
        if aufrufe == 1:
            return await _haengt()
        return _ok("https://example.invalid/", {"ok": True})

    start = time.monotonic()
    resp = await server._fetch_with_retry(erst_haengen_dann_antworten)
    dauer = time.monotonic() - start

    assert resp.json() == {"ok": True}
    assert aufrufe == 2, "der Hänger muss abgebrochen und einmal wiederholt werden"
    # Abgebrochen hat der Versuchsdeckel (0,2 s), nicht das Budget (3 s).
    assert dauer < server.settings.retry_total_budget / 2


# --- Lücke 3: was nach abgelaufenem Budget herauskommt ------------------------


async def test_abgelaufenes_budget_ist_ein_erwarteter_timeout(monkeypatch) -> None:
    # Deckel grösser als das Budget: hier läuft die Gesamtuhr ab, nicht der Versuch.
    monkeypatch.setattr(server.settings, "retry_total_budget", 0.2)
    monkeypatch.setattr(server.settings, "retry_attempt_timeout", 10.0)

    with pytest.raises(server.UpstreamTimeoutError) as info:
        await server._fetch_with_retry(_haengt)

    assert isinstance(info.value, httpx.TimeoutException)
    assert isinstance(info.value, server.ExpectedUpstreamError)
    # Die Quersuche schreibt `str(e)` in ihren Fehlerblock; leer hilft niemandem.
    assert str(info.value)


async def test_haengende_quelle_meldet_zeitueberschreitung(kurze_uhr, monkeypatch) -> None:
    monkeypatch.setattr(server.settings, "retry_total_budget", 0.5)
    monkeypatch.setattr(server, "_http_get", _haengt)

    with pytest.raises(ToolError) as info:
        await get_heritage_item(HeritageItemInput(collection="memobase", item_id="snp-007"))

    meldung = str(info.value)
    assert "Interner Fehler" not in meldung
    assert "Zeitüberschreitung" in meldung


# --- Lücke 1: SIKART läuft über den Retry -------------------------------------


async def test_sikart_suche_uebersteht_einen_haenger(kurze_uhr, monkeypatch) -> None:
    aufgezeichnet = fixture_json("artists_1.json")  # aufgezeichnet 2026-09-20
    aufrufe = 0

    async def erst_haengen_dann_antworten(url, params=None, headers=None):
        nonlocal aufrufe
        aufrufe += 1
        if aufrufe == 1:
            return await _haengt()
        return _ok(url, aufgezeichnet)

    monkeypatch.setattr(server, "_http_get", erst_haengen_dann_antworten)

    # Eigene Schranke: Ohne Retry hinge der Test sonst, statt zu fallen.
    async with asyncio.timeout(5):
        md = await heritage_search_artists(ArtistSearchInput(query="Giacometti", limit=5))

    assert aufrufe == 2
    erster = aufgezeichnet["result"]["records"][0]["HAUPTNR"]
    assert f"`{erster}`" in md


def test_kein_upstream_aufruf_laeuft_am_retry_vorbei() -> None:
    """Jedes ``_http_get``/``_http_post`` steht als Lambda in ``_fetch_with_retry``.

    So waren die drei ältesten Quellen durchgerutscht: Der Retry kam mit den
    Gedächtnisinstitutionen ins Haus und wurde nur dort eingebaut. Ein neues
    Werkzeug, das ``_http_get`` direkt ruft, fällt hier mit Zeilennummer auf.
    """
    quelle = Path(server.__file__).read_text(encoding="utf-8")
    baum = ast.parse(quelle)
    eltern = {kind: knoten for knoten in ast.walk(baum) for kind in ast.iter_child_nodes(knoten)}

    gefunden, roh = 0, []
    for knoten in ast.walk(baum):
        if not (
            isinstance(knoten, ast.Call)
            and isinstance(knoten.func, ast.Name)
            and knoten.func.id in {"_http_get", "_http_post"}
        ):
            continue
        gefunden += 1
        lam = eltern.get(knoten)
        aussen = eltern.get(lam)
        eingehuellt = (
            isinstance(lam, ast.Lambda)
            and lam.body is knoten
            and isinstance(aussen, ast.Call)
            and isinstance(aussen.func, ast.Name)
            and aussen.func.id == "_fetch_with_retry"
            and lam in aussen.args
        )
        if not eingehuellt:
            roh.append(f"Zeile {knoten.lineno}: {ast.unparse(knoten)[:70]}")

    # Positivkontrolle: Ein Test, der keinen Aufruf findet, prüft nichts.
    assert gefunden >= 10, f"nur {gefunden} Upstream-Aufrufe gefunden — Muster veraltet?"
    assert roh == [], "Upstream-Aufrufe ohne Retry und Budget:\n" + "\n".join(roh)
