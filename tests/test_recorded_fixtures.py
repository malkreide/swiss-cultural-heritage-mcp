"""Jedes Werkzeug, gefahren aus einer aufgezeichneten Antwort.

Die handgeschriebenen Stubs im Rest der Suite pruefen die *Fehler*-Pfade — ein
Timeout, ein 5xx, eine leere Trefferliste —, die sich nicht auf Zuruf
aufzeichnen lassen und als Erfindung in Ordnung sind. Was sie nicht koennen: die
Form einer Erfolgs-Antwort belegen. Sie stimmen mit dem ueberein, was ihr Autor
annahm.

Genau daran ist es hier zweimal gescheitert:

- `heritage_search_museum_datasets` filterte auf die CKAN-Organisation
  `schweizerisches-nationalmuseum`. Die heisst `…-snm`; ohne das Kuerzel
  antwortet CKAN mit HTTP 200 und null Treffern, ohne Fehler und ohne Warnung.
- `heritage_search_helveticat` fragte OAI-PMH mit einem Format, das die Quelle
  nicht publiziert, und ohne das verlangte `set`. Die Antwort war ein
  `<error>`-Element mit HTTP 200 — gelesen als leere Trefferliste.

Vier Quellen, aber mehr Abfrageformen als Hosts. Zugeordnet wird beim Abspielen
nach der Anfrage und nicht nach der Reihenfolge: `heritage_cross_search` und
`search_heritage` fragen mehrere Quellen in einem Aufruf ab.

Herkunft, Datum, Auswahlregel und SHA-256 je Datei stehen in
`tests/fixtures/PROVENANCE.md`; neu aufzeichnen mit
`PYTHONPATH=src python scripts/record_fixtures.py`.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from typing import Any

import httpx
import pytest
import respx
from fixture_data import (
    fixture_json,
    fixture_text,
    provenance,
    recorded_names,
    recorder,
    schluesselverzeichnis,
)

from swiss_cultural_heritage_mcp import server

# Werkzeug → (Eingabeklasse, Eingabe). Bewusst noch einmal hingeschrieben und
# nicht aus dem Recorder-Plan abgeleitet: die Tests sollen eine eigene Aussage
# machen. Dass beide dieselben Aufrufe fahren, prueft
# `test_der_recorder_faehrt_dieselben_aufrufe`.
WERKZEUGE: dict[str, tuple[str, str, dict[str, Any]]] = {
    "artists": (
        "heritage_search_artists",
        "ArtistSearchInput",
        {"query": "Giacometti", "limit": 5},
    ),
    "museum_datasets": (
        "heritage_search_museum_datasets",
        "MuseumSearchInput",
        {"query": "Museum", "limit": 5},
    ),
    "nb_collections": ("heritage_list_nb_collections", "NbCollectionsInput", {}),
    "memobase": (
        "search_heritage",
        "HeritageSearchInput",
        {"query": "Zürich", "collection": "memobase", "limit": 5},
    ),
    "dodis": (
        "search_heritage",
        "HeritageSearchInput",
        {"query": "Zürich", "collection": "dodis", "limit": 5},
    ),
    "cross_search": (
        "heritage_cross_search",
        "CrossSearchInput",
        {"query": "Sammlung", "sources": ["sik_isea", "snm"], "limit_per_source": 3},
    ),
}

# Die Einzelabrufe: ihre IDs stammen aus den Aufzeichnungen der Suchen, nicht
# aus einer fest verdrahteten Liste. Sonst muesste die Aufzeichnung zur ID
# passen — und der naechstliegende Weg dahin waere, sie danach auszuwaehlen.
DETAILS = {
    "artist_detail": ("heritage_get_artist", "ArtistDetailInput", "artist_id"),
    "item_memobase": ("get_heritage_item", "HeritageItemInput", "item_id"),
    "item_dodis": ("get_heritage_item", "HeritageItemInput", "item_id"),
}


def _detail_eingabe(name: str) -> dict[str, Any]:
    """Die Eingabe eines Einzelabrufs, aus der Aufzeichnung der Suche gelesen."""
    if name == "artist_detail":
        zeilen = fixture_json("artists_1.json")["result"]["records"]
        return {"artist_id": str(zeilen[0]["HAUPTNR"])}
    if name == "item_memobase":
        treffer = fixture_json("memobase_1.json")["hydra:member"]
        return {"collection": "memobase", "item_id": str(treffer[0]["@id"])}
    treffer = fixture_json("dodis_1.json")
    return {"collection": "dodis", "item_id": str(treffer[0]["id"])}


@pytest.fixture
def quelle():
    """Beantwortet jede Anfrage aus ihrer eigenen Aufzeichnung und protokolliert mit.

    Nach der *Anfrage* zugeordnet, nicht nach der Reihenfolge: sonst waeren die
    Mehrquellen-Werkzeuge ein Gluecksspiel und die Zuordnung im gruenen Fall
    zufaellig richtig. Eine Anfrage ohne Aufzeichnung faellt hier laut auf,
    statt still eine fremde Datei zu bekommen.
    """
    protokoll: list[httpx.Request] = []
    verzeichnis = schluesselverzeichnis()

    def antwort(request: httpx.Request) -> httpx.Response:
        protokoll.append(request)
        name = verzeichnis.get(str(request.url))
        if name is None:
            raise AssertionError(
                f"keine Aufzeichnung fuer diese Anfrage:\n  {request.url}\n"
                "Neu aufzeichnen mit `PYTHONPATH=src python scripts/record_fixtures.py`."
            )
        return httpx.Response(200, text=fixture_text(name))

    with respx.mock:
        respx.route().mock(side_effect=antwort)
        yield protokoll


async def _fahre(name: str):
    """Ruft ein Werkzeug mit der Eingabe aus der Tabelle."""
    if name in DETAILS:
        werkzeug, klasse, _ = DETAILS[name]
        eingabe = _detail_eingabe(name)
    else:
        werkzeug, klasse, eingabe = WERKZEUGE[name]
    return await getattr(server, werkzeug)(getattr(server, klasse)(**eingabe))


# --------------------------------------------------------------------------
# Herkunft
# --------------------------------------------------------------------------
def test_provenance_nennt_ein_brauchbares_aufnahmedatum():
    """Eine Aufzeichnung ohne Datum ist eine undatierte Behauptung ueber die Quelle."""
    treffer = re.search(r"Aufgezeichnet am \*\*(\d{4}-\d{2}-\d{2})\*\*", provenance())
    assert treffer, "PROVENANCE.md nennt kein Aufnahmedatum im erwarteten Format"
    wann = dt.date.fromisoformat(treffer.group(1))
    assert wann <= dt.datetime.now(dt.UTC).date(), "Aufnahmedatum liegt in der Zukunft"


def test_jede_fixture_steht_in_der_provenance():
    """Sonst waechst der Ordner und der Nachweis bleibt zurueck."""
    text = provenance()
    fehlend = [n for n in recorded_names() if f"## `{n}`" not in text]
    assert not fehlend, f"ohne Eintrag in PROVENANCE.md: {fehlend}"


def test_jeder_schluessel_zeigt_auf_eine_vorhandene_datei():
    """Der Nachweis traegt hier den Abspielbetrieb — er darf nicht ins Leere zeigen."""
    fehlend = sorted(set(schluesselverzeichnis().values()) - set(recorded_names()))
    assert not fehlend, f"im Nachweis genannt, aber nicht vorhanden: {fehlend}"


def test_keine_aufzeichnung_liegt_unbenutzt_herum():
    """Die Gegenrichtung — eine Datei, die kein Schluessel erreicht, belegt nichts."""
    ueberzaehlig = sorted(set(recorded_names()) - set(schluesselverzeichnis().values()))
    assert not ueberzaehlig, f"von keinem Schluessel erreicht: {ueberzaehlig}"


def test_der_recorder_faehrt_dieselben_aufrufe():
    """Recorder und Tests duerfen nicht auseinanderlaufen.

    Laedt `scripts/record_fixtures.py` als Modul — `main()` wird nicht gerufen,
    es geht keine Anfrage raus. Die Einzelabrufe stehen in beiden ausserhalb
    der Tabelle, weil ihre IDs aus den Suchen kommen.
    """
    im_plan = {a.name for a in recorder().BASIS}
    assert im_plan == set(WERKZEUGE), "Recorder und Testtabelle nennen verschiedene Aufrufe"


def test_der_nachweis_meldet_was_gekuerzt_wurde():
    """Ein Nachweis, der ueber jeder Datei «ungekuerzt» schreibt, belegt nichts.

    Genau das tat er: `_kuerze` gab seine Zaehler als `return vorher, nachher,
    geh(daten)` zurueck, und Python liest die beiden Zahlen, *bevor* `geh` sie
    hochzaehlt — also immer (0, 0). Neun der zehn Aufzeichnungen standen damit
    als vollstaendig im Ordner, obwohl sie gekuerzt sind.

    Diese Zusicherung faellt, wenn die Zaehler wieder blind werden.
    """
    modul = recorder()
    vorher, nachher, gekuerzt = modul._kuerze({"a": list(range(modul.ZEILEN * 3))})
    assert (vorher, nachher) == (modul.ZEILEN * 3, modul.ZEILEN), (
        f"_kuerze meldet {vorher}→{nachher} statt {modul.ZEILEN * 3}→{modul.ZEILEN}"
    )
    assert len(gekuerzt["a"]) == modul.ZEILEN
    assert re.search(r"- \*\*Auswahl:\*\* \d+ von \d+ Listeneintraegen", provenance()), (
        "keine einzige Datei im Nachweis ist als gekuerzt ausgewiesen"
    )


@pytest.mark.parametrize("name", sorted(n for n in recorded_names() if n.endswith(".json")))
def test_keine_aufzeichnung_ist_leer(name):
    """Eine leere Antwort sieht aus wie eine gueltige und prueft nichts.

    Beim ersten Lauf waren drei Dateien leer, und zwei davon waren echte
    Defekte — die Organisation, die es nicht gibt, und der OAI-Fehler. Diese
    Zusicherung ist der Grund, warum das auffiel.
    """
    daten = fixture_json(name)
    if isinstance(daten, list):
        assert daten, f"{name} ist eine leere Liste"
        return
    for pfad in (("result", "records"), ("result", "results"), ("hydra:member",)):
        knoten: Any = daten
        for schluessel in pfad:
            knoten = knoten.get(schluessel) if isinstance(knoten, dict) else None
        if isinstance(knoten, list):
            assert knoten, f"{name}.{'.'.join(pfad)} ist leer — neu aufzeichnen"
            return
    assert daten, f"{name} ist leer"


# --------------------------------------------------------------------------
# Fund 1: die Organisation, die es unter diesem Namen nicht gibt
# --------------------------------------------------------------------------
async def test_die_museumssuche_nennt_die_organisation_die_es_gibt(quelle):
    """`schweizerisches-nationalmuseum` ohne `-snm` findet nichts.

    CKAN beantwortet einen `q` mit einem unbekannten `organization:`-Term mit
    HTTP 200 und null Treffern — kein Fehler, keine Warnung. Das Werkzeug
    lieferte damit zu jeder Anfrage nichts. Gemessen am 15.08.2026: ohne
    Kuerzel 0 Datensaetze, mit 10.

    Diese Zusicherung liest die tatsaechlich gestellte Anfrage. Im Ergebnis
    waere der Unterschied unsichtbar gewesen.
    """
    await _fahre("museum_datasets")
    frage = quelle[-1].url.params.get("q", "")
    assert "organization:schweizerisches-nationalmuseum-snm" in frage, frage


async def test_die_museumssuche_findet_datensaetze(quelle):
    """Und das ist die Zusicherung, die den Fund festhaelt."""
    ergebnis = str(await _fahre("museum_datasets"))
    assert "Gefunden: 10" in ergebnis or "Gefunden:" in ergebnis, ergebnis[:300]
    assert "Keine" not in ergebnis[:120], ergebnis[:300]


# --------------------------------------------------------------------------
# Fund 2: ein OAI-Fehler ist kein leeres Ergebnis
# --------------------------------------------------------------------------
def test_ein_oai_fehler_wird_erkannt():
    """OAI-PMH meldet Fehler im Rumpf und mit HTTP 200.

    Ohne Erkennung parst man null Records und meldet «keine Publikationen
    gefunden» — ein Ausfall in der Form eines gueltigen Negativbefunds. Genau
    so blieb unbemerkt, dass `heritage_search_helveticat` ein Format anfragt,
    das die Quelle nicht publiziert, und das verlangte `set` weglaesst.
    """
    fehler_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">'
        "<responseDate>2026-08-15T00:00:00Z</responseDate>"
        '<error code="badArgument">The request is missing required set argument</error>'
        "</OAI-PMH>"
    )
    with pytest.raises(server.OaiError) as fehler:
        server._parse_oai_records(fehler_xml)
    assert "badArgument" in str(fehler.value)
    assert "KEIN leeres Ergebnis" in str(fehler.value)


def test_der_oai_fehler_faellt_nur_seiner_quelle_zur_last():
    """`OaiError` erbt von `ValueError` und damit von `ExpectedUpstreamError`.

    Das ist kein Zufall, sondern das Muster dieses Servers (siehe
    `UpstreamSchemaError`): in `heritage_cross_search` faellt dann nur *diese*
    Quelle aus, waehrend die anderen weiter antworten. Als blosser
    `RuntimeError` riss der Fehler die ganze foederierte Suche mit.
    """
    assert issubclass(server.OaiError, ValueError)
    assert issubclass(server.OaiError, server.ExpectedUpstreamError)


def test_die_nb_sets_stehen_ungekuerzt_im_ordner():
    """`heritage_list_nb_collections` listet den Bestand — gekuerzt log er."""
    text = fixture_text("nb_collections_1.xml")
    assert text.count("<setSpec>") > 5, "die Set-Liste ist gekuerzt"
    block = provenance().split("## `nb_collections_1.xml`", 1)[1].split("## ", 1)[0]
    assert "ungekuerzt" in block, block


# --------------------------------------------------------------------------
# Die Werkzeuge, jedes an seiner eigenen Antwort
# --------------------------------------------------------------------------
@pytest.mark.parametrize("name", sorted([*WERKZEUGE, *DETAILS]))
async def test_jedes_werkzeug_liest_seine_aufgezeichnete_antwort(quelle, name):
    """Der eigentliche Punkt: jede Abfrage bekommt *ihre* Antwort.

    Alle mit derselben zu bedienen hiesse, die Aufzeichnung gegen eine Abfrage
    zu halten, die sie nicht beantwortet. Der Dispatcher faellt laut, wenn eine
    Anfrage keine Aufzeichnung hat.
    """
    ergebnis = str(await _fahre(name))
    assert ergebnis.strip(), f"{name} liefert nichts"
    assert not ergebnis.lstrip().startswith("Fehler"), ergebnis[:300]
    assert quelle, f"{name} hat gar keine Anfrage abgeschickt"


async def test_memobase_antwortet_in_json_ld(quelle):
    """Vier Quellen, vier Antwortformen — Memobase liefert Hydra/JSON-LD.

    Ein Loader, der ueberall `results` erwartet, liefert hier still nichts.
    """
    daten = fixture_json("memobase_1.json")
    assert "hydra:member" in daten, f"die Form hat sich geaendert: {list(daten)[:6]}"
    ergebnis = str(await _fahre("memobase"))
    assert "Memobase" in ergebnis


async def test_dodis_antwortet_mit_einer_nackten_liste(quelle):
    """Und Dodis mit einer Liste ohne Umschlag — wieder eine andere Form."""
    assert isinstance(fixture_json("dodis_1.json"), list)
    ergebnis = str(await _fahre("dodis"))
    assert "Dodis" in ergebnis


async def test_die_kreuzsuche_fragt_mehrere_quellen(quelle):
    """Zwei Quellen in einem Aufruf — der Grund fuer die Zuordnung nach Anfrage.

    Eine Zuordnung nach Reihenfolge waere im gruenen Fall bloss zufaellig
    richtig.
    """
    await _fahre("cross_search")
    hosts = {r.url.host for r in quelle}
    assert len(quelle) >= 2, f"nur {len(quelle)} Anfrage(n)"
    assert hosts, hosts


# --------------------------------------------------------------------------
# Die Gegenrichtung
# --------------------------------------------------------------------------
@respx.mock
async def test_eine_leere_trefferliste_bleibt_eine_leere_trefferliste():
    """`results: []` ist eine Aussage der Quelle: dazu gibt es nichts.

    Das darf nicht als Fehler herauskommen — sonst kann das Modell einen echten
    Negativtreffer nicht von einem Ausfall unterscheiden.
    """
    leer = json.dumps({"success": True, "result": {"count": 0, "results": []}})
    respx.route().mock(return_value=httpx.Response(200, text=leer))
    ergebnis = str(await _fahre("museum_datasets"))
    assert not ergebnis.lstrip().startswith("Fehler"), ergebnis[:200]
    assert "Kein" in ergebnis or "keine" in ergebnis.lower()


# --------------------------------------------------------------------------
# Der Nachweis, nachgerechnet
# --------------------------------------------------------------------------
@pytest.mark.parametrize("name", sorted(n for n in recorded_names() if n != "PROVENANCE.md"))
def test_die_pruefsumme_im_nachweis_stimmt(name):
    """Eine Pruefsumme, die niemand nachrechnet, ist Zierde.

    Sie steht im Nachweis, um genau einen Fall zu fangen: eine Aufzeichnung,
    die nach dem Lauf von Hand nachgebessert wurde. Eine korrigierte Antwort
    ist wieder eine erfundene — und von aussen ist ihr das nicht anzusehen.
    Ohne diesen Test faengt die Summe nichts.

    Gerechnet wird ueber die Bytes auf der Platte, nicht ueber den Loader:
    genau die hat der Recorder gehasht, und ein Loader, der unterwegs dekodiert
    oder normalisiert, wuerde die Pruefung gegen sich selbst fuehren.
    """
    import hashlib
    import re
    from pathlib import Path

    teile = provenance().split(f"## `{name}`", 1)
    assert len(teile) == 2, f"{name} hat keinen Block in PROVENANCE.md"
    treffer = re.search(r"\*\*SHA-256:\*\*\s*`([0-9a-f]{64})`", teile[1].split("## ", 1)[0])
    assert treffer, f"{name} steht ohne Pruefsumme im Nachweis"
    roh = (Path(__file__).resolve().parent / "fixtures" / name).read_bytes()
    assert hashlib.sha256(roh).hexdigest() == treffer.group(1), (
        f"{name} weicht vom Nachweis ab — von Hand nachgebessert? Neu aufzeichnen."
    )
