#!/usr/bin/env python3
"""Zeichnet je eine echte Antwort pro Abfrage auf.

Warum nicht von Hand geschrieben: eine handgeschriebene Erfolgs-Antwort stimmt
mit dem ueberein, was ihr Autor annahm, und kann die Quelle deshalb nicht
widerlegen. Aufgezeichnet wird darum an demselben Ort, an dem der Server die
Antwort entgegennimmt — ueber einen httpx-Response-Hook auf dem geteilten
Client aus `server._get_http_client()`. Damit tragen Aufzeichnung und Betrieb
denselben User-Agent, dasselbe Timeout und dieselbe Egress-Allow-List; eine
nachgebaute Anfrage taete das nicht.

Vier Quellen — SIKART/CKAN, Memobase, Dodis, die Nationalbibliothek — und mehr
Abfrageformen als Hosts: `datastore_search` je Ressource, `package_search`,
Memobase-Suche und -Einzelabruf, Dodis-Solr-Query und -Volltext, OAI-PMH. Die
Portfolio-Regel «eine Antwort je externem Endpunkt» waere mit vier Dateien
erfuellt und truege fast nichts.

Zugeordnet wird beim Abspielen nach der Anfrage und nicht nach der Reihenfolge:
`heritage_cross_search` und `search_heritage` fragen mehrere Quellen in einem
Aufruf ab, und eine Zuordnung nach Reihenfolge waere im gruenen Fall bloss
zufaellig richtig.

Nicht jede Quelle antwortet mit JSON: die Nationalbibliothek liefert OAI-PMH
als XML. Solche Dateien heissen `.xml` — eine Datei `.json` zu nennen waere
eine Behauptung ueber ihren Inhalt, die nicht stimmt.

## Was hier fehlt, und warum

`heritage_search_helveticat` und `heritage_get_publication` haben keine
Aufzeichnung. Sie fragen OAI-PMH mit `metadataPrefix=oai_dc`; die Schnittstelle
publiziert dieses Format nicht (`ListMetadataFormats` nennt mods, oai_dc,
oai_qdc, marc21, etdms — Records liefert nur `marc21`), und ohne `set` fehlt
zudem ein Pflichtargument. Beide Werkzeuge haben nie einen Datensatz geliefert
und meldeten das als «keine Publikationen gefunden». Seit `_raise_if_oai_error`
sagen sie stattdessen, dass die Quelle die Anfrage abgelehnt hat. Eine
Erfolgs-Aufzeichnung gibt es erst, wenn der Parser MARC21 lesen kann — das ist
ein eigener Schritt und keine Zeile.

## Aufruf

    PYTHONPATH=src python scripts/record_fixtures.py

Schreibt nach `tests/fixtures/` und erzeugt `tests/fixtures/PROVENANCE.md` neu.
Dateien, die kein Plan-Eintrag mehr erzeugt, werden geloescht — sonst waechst
der Ordner und der Nachweis bleibt zurueck.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "src"))

from swiss_cultural_heritage_mcp import server  # noqa: E402

FIXTURES = WURZEL / "tests" / "fixtures"

VERSUCHE = 4

# Wie viele Eintraege einer Trefferliste bleiben. Die Form einer Zeile belegen
# drei genauso gut wie hundert; die Zahl steht je Datei im Nachweis.
ZEILEN = 3


@dataclass(frozen=True)
class Aufruf:
    """Ein Werkzeugaufruf, der Anfragen ausloesen soll."""

    name: str
    werkzeug: str
    klasse: str
    eingabe: dict[str, Any]
    # Kuerzen ist nur dort harmlos, wo der Server die Liste ganz liest. Filtert
    # oder zaehlt er *in* ihr, schneidet ein Schnitt auf die ersten Zeilen
    # womoeglich genau die Zeile weg, die er sucht.
    kuerzen: bool = True
    notiz: str = ""


# `list_heritage_collections` steht bewusst nicht im Plan: es ist ein
# statischer Katalog und schickt keine Anfrage. Was nie ein Netz beruehrt, hat
# hier nichts aufzuzeichnen.
BASIS: list[Aufruf] = [
    Aufruf(
        "artists",
        "heritage_search_artists",
        "ArtistSearchInput",
        {"query": "Giacometti", "limit": 5},
    ),
    Aufruf(
        "museum_datasets",
        "heritage_search_museum_datasets",
        "MuseumSearchInput",
        {"query": "Museum", "limit": 5},
    ),
    Aufruf(
        "nb_collections",
        "heritage_list_nb_collections",
        "NbCollectionsInput",
        {},
        kuerzen=False,
        notiz="Ungekuerzt: das Werkzeug listet die Sets der Nationalbibliothek "
        "vollstaendig. Gekuerzt behauptete es einen kleineren Bestand.",
    ),
    Aufruf(
        "memobase",
        "search_heritage",
        "HeritageSearchInput",
        {"query": "Zürich", "collection": "memobase", "limit": 5},
    ),
    Aufruf(
        "dodis",
        "search_heritage",
        "HeritageSearchInput",
        {"query": "Zürich", "collection": "dodis", "limit": 5},
    ),
    Aufruf(
        "cross_search",
        "heritage_cross_search",
        "CrossSearchInput",
        # «Sammlung» statt «Bern»: beide CKAN-Quellen liefern dazu etwas, und
        # eine Aufzeichnung mit null Treffern belegt keine Form. Ohne die NB —
        # sie lehnt die Anfrage ab (siehe oben), und ein Fehler gehoert nicht
        # in den Fixture-Ordner, sondern zu den handgeschriebenen Stubs.
        {"query": "Sammlung", "sources": ["sik_isea", "snm"], "limit_per_source": 3},
        notiz="Mehrere Quellen in einem Aufruf — der Grund, warum nach Anfrage "
        "und nicht nach Reihenfolge zugeordnet wird.",
    ),
]


def detail_aufrufe(ids: dict[str, str]) -> list[Aufruf]:
    """Die Einzelabrufe, deren IDs aus den Suchen oben stammen.

    Fest verdrahtete IDs waeren beim naechsten Aufzeichnen womoeglich nicht
    mehr im Bestand — und ein 404 sieht hier aus wie ein leeres Ergebnis.
    """
    aufrufe = []
    if ids.get("artist"):
        aufrufe.append(
            Aufruf(
                "artist_detail",
                "heritage_get_artist",
                "ArtistDetailInput",
                {"artist_id": ids["artist"]},
                notiz="Andere Abfrageform als die Suche: `filters` statt `q`.",
            )
        )
    for quelle in ("memobase", "dodis"):
        if ids.get(quelle):
            aufrufe.append(
                Aufruf(
                    f"item_{quelle}",
                    "get_heritage_item",
                    "HeritageItemInput",
                    {"collection": quelle, "item_id": ids[quelle]},
                )
            )
    return aufrufe


@dataclass
class Antwort:
    """Eine gesehene Antwort samt der Anfrage, die sie ausgeloest hat."""

    url: str
    text: str
    werkzeuge: list[str] = field(default_factory=list)
    darf_kuerzen: bool = True
    dateiname: str = ""
    original_bytes: int = 0
    gekuerzt_von: int = 0
    behalten: int = 0
    sha256: str = ""
    bytes: int = 0

    @property
    def schluessel(self) -> str:
        """Woran eine Anfrage beim Abspielen wiedererkannt wird."""
        return self.url


def _endung(text: str) -> str:
    """`.json`, wenn die Antwort JSON ist — sonst `.xml`.

    Die Nationalbibliothek liefert OAI-PMH als XML.
    """
    try:
        json.loads(text)
    except json.JSONDecodeError:
        return ".xml"
    return ".json"


def _hook_fuer(gesehen: list[Antwort]) -> Callable[[httpx.Response], Awaitable[None]]:
    """Baut den Response-Hook fuer einen Versuch.

    Eigene Funktion, damit die Liste als Argument gebunden ist und nicht als
    Schleifenvariable aus dem umgebenden Namensraum (ruff B023).
    """

    async def hook(response: httpx.Response) -> None:
        await response.aread()
        # Redirect-Hops sind Zwischenschritte, keine Antworten auf eine
        # Abfrage — der Server folgt ihnen selbst und prueft dabei jeden Hop.
        if response.is_redirect:
            return
        gesehen.append(Antwort(url=str(response.request.url), text=response.text))

    return hook


async def _fahre(a: Aufruf, client: httpx.AsyncClient) -> list[Antwort]:
    """Ruft ein Werkzeug und gibt die dabei gesehenen Antworten zurueck."""
    fn = getattr(server, a.werkzeug)
    modell = getattr(server, a.klasse)(**a.eingabe)
    letzter: Exception | None = None

    for versuch in range(VERSUCHE):
        if versuch:
            await asyncio.sleep(2**versuch)
        gesehen: list[Antwort] = []
        hook = _hook_fuer(gesehen)
        client.event_hooks.setdefault("response", []).append(hook)
        try:
            ergebnis = await fn(modell)
        except Exception as e:  # noqa: BLE001 — jeder Fehler ist hier ein Retry-Grund
            letzter = e
            continue
        finally:
            client.event_hooks["response"].remove(hook)

        if "Fehler" in str(ergebnis)[:200]:
            letzter = RuntimeError(f"{a.werkzeug} meldet: {str(ergebnis)[:200]}")
            continue
        if not gesehen:
            letzter = RuntimeError(f"{a.werkzeug} hat keine Anfrage abgeschickt")
            continue
        for antwort in gesehen:
            antwort.werkzeuge.append(a.werkzeug)
            antwort.darf_kuerzen = a.kuerzen
        return gesehen

    raise RuntimeError(f"{a.name} nach {VERSUCHE} Versuchen nicht aufgezeichnet: {letzter}")


def _kuerze(daten: Any) -> tuple[int, int, Any]:
    """Kuerzt jede Liste im Baum auf `ZEILEN`; gibt (vorher, nachher, Daten).

    Nur die Zahl der Eintraege, nie ein Feld. Zaehlfelder daneben (`total`,
    `count`, `numFound`) bleiben stehen: die Quelle meint damit die Gesamtzahl
    der Treffer und nicht die Zahl der gelieferten Zeilen, und genau die liest
    der Server aus.
    """
    vorher = nachher = 0

    def geh(knoten: Any) -> Any:
        nonlocal vorher, nachher
        if isinstance(knoten, dict):
            return {k: geh(v) for k, v in knoten.items()}
        if isinstance(knoten, list):
            vorher += len(knoten)
            gekuerzt = knoten[:ZEILEN]
            nachher += len(gekuerzt)
            return [geh(v) for v in gekuerzt]
        return knoten

    return vorher, nachher, geh(daten)


def _ids_aus(nach_schluessel: dict[str, Antwort]) -> dict[str, str]:
    """Zieht je eine ID aus den aufgezeichneten Suchen.

    Aus der Aufzeichnung selbst und nicht aus einem Zwischenspeicher: so
    beschreibt der Einzelabruf garantiert einen Treffer, den die Suche daneben
    auch zeigt, und ein Test kann beide gegeneinander halten.
    """
    ids: dict[str, str] = {}
    for antwort in nach_schluessel.values():
        if antwort.dateiname.startswith("artists_"):
            zeilen = json.loads(antwort.text).get("result", {}).get("records") or []
            if zeilen and zeilen[0].get("HAUPTNR"):
                ids.setdefault("artist", str(zeilen[0]["HAUPTNR"]))
        elif antwort.dateiname.startswith("memobase_"):
            ids.setdefault("memobase", _erste_id(json.loads(antwort.text)))
        elif antwort.dateiname.startswith("dodis_"):
            ids.setdefault("dodis", _erste_id(json.loads(antwort.text)))
    return {k: v for k, v in ids.items() if v}


def _erste_id(daten: Any) -> str:
    """Die ID des ersten Treffers, quer durch die Antwortformen der Quellen."""
    kandidaten: list[Any] = []
    if isinstance(daten, dict):
        for schluessel in ("hydra:member", "member", "docs", "results", "data"):
            wert = daten.get(schluessel)
            if isinstance(wert, list):
                kandidaten = wert
                break
        else:
            antwort = daten.get("response")
            if isinstance(antwort, dict) and isinstance(antwort.get("docs"), list):
                kandidaten = antwort["docs"]
    elif isinstance(daten, list):
        kandidaten = daten
    if not kandidaten or not isinstance(kandidaten[0], dict):
        return ""
    erster = kandidaten[0]
    for feld in ("id", "@id", "identifier", "dodis_id"):
        if erster.get(feld):
            return str(erster[feld])
    return ""


async def main() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    heute = datetime.now(UTC).date().isoformat()
    nach_schluessel: dict[str, Antwort] = {}
    zaehler: dict[str, int] = {}

    client = server._get_http_client()
    try:

        async def nimm_auf(a: Aufruf) -> None:
            print(f"… {a.werkzeug} ({a.name})", file=sys.stderr)
            for antwort in await _fahre(a, client):
                if antwort.schluessel in nach_schluessel:
                    vorhanden = nach_schluessel[antwort.schluessel]
                    if a.werkzeug not in vorhanden.werkzeuge:
                        vorhanden.werkzeuge.append(a.werkzeug)
                    continue
                zaehler[a.name] = zaehler.get(a.name, 0) + 1
                antwort.dateiname = f"{a.name}_{zaehler[a.name]}{_endung(antwort.text)}"
                nach_schluessel[antwort.schluessel] = antwort

        for a in BASIS:
            await nimm_auf(a)

        # Die IDs fuer die Einzelabrufe stehen jetzt in den Aufzeichnungen der
        # Suchen — genommen wird der erste Treffer, nicht ein gemerkter Wert.
        ids = _ids_aus(nach_schluessel)
        print(f"IDs fuer die Einzelabrufe: {ids}", file=sys.stderr)
        for a in detail_aufrufe(ids):
            await nimm_auf(a)
    finally:
        await client.aclose()
        server._http_client = None

    for antwort in nach_schluessel.values():
        antwort.original_bytes = len(antwort.text.encode("utf-8"))
        try:
            daten = json.loads(antwort.text)
        except json.JSONDecodeError:
            (FIXTURES / antwort.dateiname).write_text(antwort.text, encoding="utf-8")
        else:
            if antwort.darf_kuerzen:
                antwort.gekuerzt_von, antwort.behalten, daten = _kuerze(daten)
            # Neu eingerueckt geschrieben: eine Zeile JSON waere kleiner, aber
            # im Diff nicht lesbar, und ein Fixture will gelesen werden.
            (FIXTURES / antwort.dateiname).write_text(
                json.dumps(daten, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
        roh = (FIXTURES / antwort.dateiname).read_bytes()
        antwort.sha256 = hashlib.sha256(roh).hexdigest()
        antwort.bytes = len(roh)

    antworten = sorted(nach_schluessel.values(), key=lambda x: x.dateiname)
    _schreibe_provenance(antworten, heute)

    # Aufraeumen: was kein Plan-Eintrag mehr erzeugt, hat auch keinen Nachweis.
    geschrieben = {a.dateiname for a in antworten} | {"PROVENANCE.md"}
    for pfad in sorted(FIXTURES.iterdir()):
        if pfad.name not in geschrieben:
            print(f"– entferne veraltet: {pfad.name}", file=sys.stderr)
            pfad.unlink()

    print(f"{len(antworten)} Aufzeichnungen in {FIXTURES}", file=sys.stderr)
    return 0


def _schreibe_provenance(antworten: list[Antwort], heute: str) -> None:
    zeilen = [
        "# Herkunft der Fixtures",
        "",
        f"Aufgezeichnet am **{heute}** mit `PYTHONPATH=src python scripts/record_fixtures.py`.",
        "",
        "Eine Antwort je **Abfrage**, nicht je Endpunkt: vier Quellen — SIKART/CKAN,",
        "Memobase, Dodis, Nationalbibliothek —, aber mehr Abfrageformen als Hosts.",
        "Vier Dateien wuerden die Portfolio-Regel erfuellen und fast nichts belegen.",
        "",
        "Der **Schluessel** unten ist die angefragte URL; danach ordnet der Test zu und",
        "nicht nach Reihenfolge. `heritage_cross_search` und `search_heritage` fragen",
        "mehrere Quellen in einem Aufruf ab, und eine Zuordnung nach Reihenfolge waere",
        "im gruenen Fall bloss zufaellig richtig.",
        "",
        "Die Antworten stammen aus dem geteilten Client (gleicher User-Agent, gleiches",
        "Timeout, gleiche Egress-Allow-List wie im Betrieb), abgegriffen ueber einen",
        "httpx-Response-Hook. Ausgeloest hat sie jeweils das Werkzeug selbst — so belegt",
        "die Aufzeichnung auch, dass das Werkzeug genau diese Anfrage schickt.",
        "Redirect-Hops sind nicht aufgezeichnet: sie sind Zwischenschritte, keine",
        "Antworten auf eine Abfrage.",
        "",
        "Neu gesetzt ist die Einrueckung; gekuerzt ist allein die **Zahl** der",
        "Listeneintraege. Kein Feld eines behaltenen Eintrags ist angetastet, und",
        "Zaehlfelder daneben (`total`, `count`, `numFound`) stehen wie geliefert — die",
        "Quelle meint damit die Gesamtzahl der Treffer.",
        "",
        "Die Fehlerpfade — Timeout, 5xx, leere Trefferliste — bleiben handgeschrieben.",
        "Sie lassen sich nicht auf Zuruf aufzeichnen und sind als Erfindung in Ordnung.",
        "",
    ]
    for a in antworten:
        zeilen += [
            f"## `{a.dateiname}`",
            "",
            f"- **Werkzeuge:** {', '.join(f'`{w}`' for w in sorted(a.werkzeuge))}",
            f"- **Schluessel:** `{a.schluessel}`",
        ]
        if a.gekuerzt_von > a.behalten:
            zeilen.append(
                f"- **Auswahl:** {a.behalten} von {a.gekuerzt_von} Listeneintraegen "
                f"(je Liste die ersten {ZEILEN}), aus {a.original_bytes} Bytes Rohantwort"
            )
        elif not a.darf_kuerzen:
            zeilen.append(
                "- **Auswahl:** ungekuerzt — der Server liest diese Liste ganz, "
                "ein Schnitt behauptete einen kleineren Bestand"
            )
        else:
            zeilen.append("- **Auswahl:** ungekuerzt")
        zeilen += [
            f"- **Groesse:** {a.bytes} Bytes",
            f"- **SHA-256:** `{a.sha256}`",
            "",
        ]
    (FIXTURES / "PROVENANCE.md").write_text("\n".join(zeilen), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
