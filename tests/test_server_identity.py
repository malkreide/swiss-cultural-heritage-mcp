"""Was dieser Server ueber sich selbst sagt — gemessen auf beiden Spec-Aeren.

`MCPServer` nimmt `version`, `title`, `description`, `website_url` und
`instructions` entgegen und setzt fuer nichts davon etwas Eigenes ein. Das
steht so im SDK (`mcp/server/lowlevel/server.py`, `Server.server_info`):

    An unversioned server reports an empty `version`; the SDK never
    substitutes its own.

Dieses Repo uebergab bis zum 18.09.2026 keines der fuenf Felder. Gemessen am
selben Tag gegen den zusammengebauten ASGI-Stack, vor der Aenderung:

    initialize      → serverInfo {"name": "...", "version": ""}
    tools/list      → _meta.serverInfo {"name": "...", "version": ""}
    resources/list  → dasselbe
    prompts/list    → dasselbe
    server/discover → dasselbe, "instructions" fehlte ganz

Der Unterschied zwischen den Aeren ist der Grund, warum das mehr wiegt als
frueher: Unter `initialize` stand `serverInfo` EINMAL je Verbindung. Seit
`2026-07-28` gibt es keinen Handshake mehr, und das SDK stempelt die Identitaet
stattdessen in `_meta` JEDER Antwort. Eine leere Version ist damit kein
einmaliger Schoenheitsfehler, sondern die Auskunft, die der Server bei jedem
Aufruf gibt.

Gemessen statt aus den Konstruktor-Argumenten geschlossen: Ein Argument kann
gesetzt sein und trotzdem nicht auf dem Draht landen — `instructions` etwa
traegt `server/discover`, aber keine der auflistenden Methoden. Deshalb geht
jede Zusicherung hier durch eine echte HTTP-Anfrage.

Gegenprobe gefahren (18.09.2026), je Zusicherung einzeln neutralisiert, indem
das zugehoerige Argument aus dem `MCPServer(...)`-Aufruf entfernt wurde:

    ohne version=      → 6 Faelle rot
    ohne title=        → 6 Faelle rot
    ohne description=  → 6 Faelle rot
    ohne website_url=  → 6 Faelle rot
    ohne instructions= → 2 Faelle rot

Sechs ist die erwartete Zahl und nicht irgendeine: fuenf auflistende Methoden
der modernen Aera plus `initialize`. `instructions` steht nur auf zweien davon
(`server/discover` und `initialize`) — deshalb dort zwei. Keine Zusicherung
blieb bei entfernter Implementierung gruen.
"""

from __future__ import annotations

import json
import pathlib
import re
import tomllib
from typing import Any

import httpx
import pytest
from mcp_types import SERVER_INFO_META_KEY

from swiss_cultural_heritage_mcp import __homepage__, __summary__, __version__
from swiss_cultural_heritage_mcp import server as srv
from swiss_cultural_heritage_mcp.server import build_http_app

_ROOT = pathlib.Path(__file__).resolve().parents[1]

MODERN = "2026-07-28"
HANDSHAKE = "2025-11-25"

# `SERVER_INFO_META_KEY` ist der Schluessel, unter dem das SDK die Identitaet in
# `_meta` stempelt. Aus dem SDK importiert und nicht abgeschrieben: Verschiebt
# eine Spec-Revision den Namen, soll dieser Test mitwandern statt auf einem
# toten Schluessel gruen zu bleiben, weil `.get()` dort `None` faende — und
# `None` ist keine Version.

_BASE_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Host": "127.0.0.1:8000",
}

# Die auflistenden Methoden, die ohne Argumente beantwortbar sind. `tools/call`
# und `resources/read` fehlen bewusst: Sie wuerden eine Quelle abfragen und
# gehoerten damit zu den Live-Tests.
LISTENDE_METHODEN = [
    "tools/list",
    "resources/list",
    "resources/templates/list",
    "prompts/list",
    "server/discover",
]


def _pyproject_version() -> str:
    """Die Version aus `pyproject.toml` — die Quelle, die `check_version_sync.py` haelt."""
    return tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]


def _entpacke(antwort: httpx.Response) -> dict[str, Any]:
    """JSON-RPC-Ergebnis aus der Antwort, SSE-Rahmen abgestreift."""
    koerper = antwort.text
    for zeile in koerper.splitlines():
        if zeile.startswith("data: "):
            koerper = zeile[len("data: ") :]
    geparst = json.loads(koerper)
    assert "error" not in geparst, geparst["error"]
    return geparst["result"]


async def _modern(methode: str) -> dict[str, Any]:
    """Eine Anfrage der Aera 2026-07-28 — Pro-Request-Envelope, kein Handshake."""
    app = build_http_app(None, "127.0.0.1", 8000)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://127.0.0.1:8000"
        ) as client:
            antwort = await client.post(
                "/mcp",
                headers={
                    **_BASE_HEADERS,
                    "MCP-Protocol-Version": MODERN,
                    "Mcp-Method": methode,
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": methode,
                    "params": {
                        "_meta": {
                            "io.modelcontextprotocol/protocolVersion": MODERN,
                            "io.modelcontextprotocol/clientCapabilities": {},
                        }
                    },
                },
            )
    return _entpacke(antwort)


async def _initialize() -> dict[str, Any]:
    """Ein `initialize` der Handshake-Aera durch denselben Stack."""
    app = build_http_app(None, "127.0.0.1", 8000)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://127.0.0.1:8000"
        ) as client:
            antwort = await client.post(
                "/mcp",
                headers=_BASE_HEADERS,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": HANDSHAKE,
                        "capabilities": {},
                        "clientInfo": {"name": "identitaets-test", "version": "1"},
                    },
                },
            )
    return _entpacke(antwort)


# ─────────────────────────── Aera 2026-07-28 ───────────────────────────────────


@pytest.mark.parametrize("methode", LISTENDE_METHODEN)
async def test_jede_moderne_antwort_traegt_die_ausgelieferte_version(methode: str) -> None:
    """Der lasttragende Fall.

    Verglichen wird gegen `pyproject.toml` und nicht gegen `__version__`:
    Beide aus derselben Quelle zu ziehen hiesse, den Wert gegen sich selbst zu
    halten — das bliebe auch dann gruen, wenn ueberhaupt keine Version mehr
    ankaeme, solange nur beide Seiten dasselbe Nichts meldeten.
    """
    stempel = (await _modern(methode)).get("_meta", {}).get(SERVER_INFO_META_KEY, {})
    assert stempel.get("version") == _pyproject_version(), (
        f"{methode} stempelt {stempel.get('version')!r} als Version. Ohne "
        "`version=` meldet das SDK den leeren String und setzt nichts Eigenes "
        "ein. Weicht der Wert ab statt zu fehlen, ist die installierte "
        'Paket-Metadate aelter als pyproject.toml — `pip install -e ".[dev]"`.'
    )


@pytest.mark.parametrize("methode", LISTENDE_METHODEN)
@pytest.mark.parametrize(
    ("feld", "erwartet"),
    [
        ("title", lambda: srv.SERVER_TITLE),
        ("description", lambda: __summary__),
        ("websiteUrl", lambda: __homepage__),
    ],
)
async def test_jede_moderne_antwort_traegt_die_uebrige_identitaet(
    methode: str, feld: str, erwartet
) -> None:
    """`title`, `description` und `websiteUrl` — dieselbe Mechanik, dieselbe Stelle.

    Das SDK laesst jedes dieser Felder weg, wenn es `None` ist
    (`exclude_none=True`), ein fehlendes Argument faellt hier also als
    fehlender Schluessel auf und nicht als leerer Wert.
    """
    stempel = (await _modern(methode)).get("_meta", {}).get(SERVER_INFO_META_KEY, {})
    wert = erwartet()
    assert wert, f"{feld} hat serverseitig keinen Wert — dann prueft dieser Fall nichts"
    assert stempel.get(feld) == wert, (
        f"{methode} stempelt {feld}={stempel.get(feld)!r}, erwartet {wert!r}."
    )


async def test_discover_traegt_die_instructions() -> None:
    """Das einzige Feld, das `server/discover` neben den Capabilities fuehrt.

    Die moderne Aera hat keinen Handshake — ohne dieses Feld erfaehrt ein
    Client nur, WAS es gibt (`tools/list`), nie wofuer dieser Server da ist.
    """
    ergebnis = await _modern("server/discover")
    assert ergebnis.get("instructions") == srv.INSTRUCTIONS
    assert srv.INSTRUCTIONS.strip(), "leere INSTRUCTIONS — dann prueft die Zeile darueber nichts"


async def test_discover_meldet_die_moderne_revision_als_unterstuetzt() -> None:
    """Die Gegenprobe zur Identitaet: Sie wird auf der Aera gemessen, um die es geht.

    Ohne diese Zeile koennte der Stack die Anfrage auf einer aelteren Revision
    beantworten und alles oben bliebe gruen, gemessen an der falschen Aera.
    """
    assert MODERN in (await _modern("server/discover"))["supportedVersions"]


# ─────────────────────────── Handshake-Aera ────────────────────────────────────


async def test_initialize_meldet_dieselbe_identitaet() -> None:
    """Bestehende Clients bekommen denselben Block — die Aenderung ist keine Weiche.

    Ohne diesen Fall waere nicht belegt, dass die Identitaet am Server haengt
    und nicht am modernen Transportpfad.
    """
    ergebnis = await _initialize()
    info = ergebnis["serverInfo"]
    assert info["version"] == _pyproject_version()
    assert info["title"] == srv.SERVER_TITLE
    assert info["description"] == __summary__
    assert info["websiteUrl"] == __homepage__
    assert ergebnis["instructions"] == srv.INSTRUCTIONS


# ─────────────────────────── Die Ableitung selbst ──────────────────────────────


def test_die_identitaet_kommt_aus_den_paket_metadaten() -> None:
    """Kein Literal im Auslieferungspfad — dieselbe Regel wie fuer die Version.

    `scripts/check_version_sync.py` verbietet eine handgepflegte Version in
    `src/`. Beschreibung und Projekt-URL standen unter keinem solchen Verbot;
    die URL stand bis zum 18.09.2026 als Literal im User-Agent, ein zweites Mal
    neben `[project.urls].Homepage`.
    """
    assert __version__ == _pyproject_version()
    assert __homepage__ and __homepage__.startswith("https://")
    assert __homepage__ in srv.USER_AGENT, (
        "der User-Agent nennt die Projekt-URL nicht mehr — Betreiber der "
        "Datenquellen sehen dann keinen Verweis auf das Projekt."
    )
    assert srv.USER_AGENT.startswith(f"swiss-cultural-heritage-mcp/{__version__}")


# ─────────────────── Die Tool-Namen IN den INSTRUCTIONS ────────────────────────
# Was hier steht, hat einen Anlass: Die erste Fassung der INSTRUCTIONS (gemergt
# am 19.09.2026 als PR #90) nannte `search_heritage` als DEN
# quellenuebergreifenden Einstieg, nachdem sie fuenf Quellen aufgezaehlt hatte.
# Dieses Tool erreicht aber nur Memobase und Dodis; fuer SIKART, Nationalmuseum
# und Helveticat gibt es ein zweites, `heritage_cross_search`, das ungenannt
# blieb. Eine Hodler-Frage waere damit auf das Tool geroutet worden, das SIKART
# gar nicht kennt.
#
# Gefunden hat das ein Review, kein Test — und das ist die ehrliche Grenze der
# Pruefung unten: Sie liest keinen Fliesstext. Sie belegt nur, dass jeder
# Tool-Name, den die INSTRUCTIONS in Backticks nennen, auch wirklich ein
# registriertes Tool ist. Das faengt die mechanische Haelfte (umbenannt,
# entfernt, vertippt), nicht die inhaltliche.
#
# Der Marker-Test in `tests/test_registry_manifest.py` faengt beides nicht: Er
# prueft Quellennamen als Teilzeichenketten, und alle drei fehlerhaften Saetze
# kamen dort gruen durch.

_BACKTICK = re.compile(r"`([a-z][a-z0-9_]{4,})`")


def _in_instructions_genannte_bezeichner() -> set[str]:
    """Alle `backtick`-Bezeichner der INSTRUCTIONS in Tool-Namens-Form."""
    return set(_BACKTICK.findall(srv.INSTRUCTIONS))


async def _registrierte_tools() -> set[str]:
    return {tool.name for tool in await srv.mcp.list_tools()}


async def test_jeder_genannte_tool_name_ist_ein_registriertes_tool() -> None:
    """Ein Tool-Name in den INSTRUCTIONS, den es nicht gibt, ist eine Sackgasse.

    Gegen die registrierten Tools geprueft und nicht gegen eine Liste in dieser
    Datei: Wer ein Tool umbenennt, faellt hier auf, ohne dass jemand daran
    gedacht haben muss.

    Nicht jeder Bezeichner in Backticks ist ein Tool — `json`, `markdown`,
    `outputSchema` und `tools/list` stehen dort ebenfalls. Gefiltert wird
    deshalb ueber die Namensform des Repos (`snake_case`, mindestens fuenf
    Zeichen) und danach gegen die tatsaechliche Tool-Liste geschnitten; was
    weder Tool noch Tool-foermig ist, faellt vorher heraus.
    """
    registriert = await _registrierte_tools()
    genannt = _in_instructions_genannte_bezeichner()
    verdaechtig = {n for n in genannt if "_" in n}
    unbekannt = sorted(verdaechtig - registriert)
    assert not unbekannt, (
        f"Die INSTRUCTIONS nennen {unbekannt}, aber der Server registriert diese "
        f"Tools nicht. Registriert sind: {sorted(registriert)}. Entweder ist der "
        "Name veraltet (Tool umbenannt oder entfernt) oder vertippt — in beiden "
        "Faellen schickt der Text jeden Client auf ein Tool, das es nicht gibt."
    )


async def test_die_instructions_nennen_ueberhaupt_tools() -> None:
    """Sichert den Test darueber gegen eine leere Eingabe ab.

    Naehme jemand alle Tool-Namen aus den INSTRUCTIONS, liefe er ueber eine
    leere Menge und bliebe gruen — gruen aus Mangel an Pruefung, und
    ausgerechnet fuer den Text, dessen Zweck das Wegweisen ist.
    """
    registriert = await _registrierte_tools()
    genannt = _in_instructions_genannte_bezeichner() & registriert
    assert len(genannt) >= 2, (
        f"Die INSTRUCTIONS nennen nur {sorted(genannt)}. Der Server hat zwei "
        "quellenuebergreifende Einstiege mit disjunkten Quellen "
        "(`heritage_cross_search` und `search_heritage`); wer nur einen nennt, "
        "verschweigt die Haelfte der Quellen — genau der Befund, der diese "
        "Datei erweitert hat."
    )
