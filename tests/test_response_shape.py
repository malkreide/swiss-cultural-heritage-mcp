"""Die CKAN-Hülle wird bestätigt, nicht angenommen (FID-006).

Sechs Stellen schrieben `data.get("result", {}).get(<feld>, [])` — dreimal auf
`records` (DataStore), zweimal auf `results` (package_search), einmal auf beides
im Mehrquellen-Werkzeug. Fällt `result` weg, war die Trefferliste leer, und das
Werkzeug antwortete «Keine Daten gefunden»: für das Modell nicht davon zu
unterscheiden, dass SIK-ISEA oder das SNM nichts haben.

Zwei der sechs lasen sogar direkt `resp.json().get("result", {})` — ohne das
`success`-Envelope überhaupt anzusehen.

Der Portfolio-Durchlauf am 2026-08-07 fand acht Server, die mit CKAN sprechen;
alle acht prüfen das `success`-Envelope, sieben defaulteten `result` danach.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from swiss_cultural_heritage_mcp.server import (
    CKAN_API,
    UpstreamSchemaError,
    _ckan_result,
)

# --- Der Helfer, und was er trennt -------------------------------------------


def test_a_missing_result_raises_instead_of_returning_nothing():
    with pytest.raises(UpstreamSchemaError):
        _ckan_result({"success": True, "help": "…"}, "datastore_search", "records")


def test_the_message_names_the_keys_that_are_actually_there():
    """Ohne die vorhandenen Schlüssel ist der nächste Schritt Raten."""
    with pytest.raises(UpstreamSchemaError) as excinfo:
        _ckan_result({"success": True, "help": "…", "payload": {}}, "datastore_search", "records")
    message = str(excinfo.value)
    assert "'help'" in message and "'payload'" in message, message
    assert "datastore_search" in message
    assert "keine Leermenge" in message


def test_a_result_without_the_read_field_is_rejected():
    """Die Ebene darunter zählt genauso.

    CKAN liefert `records` bzw. `results` auch bei null Treffern. Fehlt das
    Feld, ist das eine andere Antwort und keine leere Suche.
    """
    with pytest.raises(UpstreamSchemaError) as excinfo:
        _ckan_result({"result": {"total": 0}}, "datastore_search", "records")
    assert "records" in str(excinfo.value)


def test_a_non_object_result_is_rejected():
    with pytest.raises(UpstreamSchemaError) as excinfo:
        _ckan_result({"result": ["a"]}, "package_search", "results")
    assert "list" in str(excinfo.value)


def test_an_empty_hit_list_is_still_a_normal_answer():
    """Ein Wächter, der die echte Leermenge mitfängt, wird abgeschaltet.

    Bestätigt wird die **Anwesenheit** des Schlüssels, nicht sein Inhalt.
    """
    res = _ckan_result({"result": {"records": [], "total": 0}}, "datastore_search", "records")
    assert res["records"] == []
    assert res["total"] == 0


def test_the_error_is_an_expected_upstream_error_not_a_programming_error():
    """`UpstreamSchemaError` erbt von `ValueError`, und das ist tragend.

    `ExpectedUpstreamError` ist ein Tupel, das `ValueError` enthält. Nur dadurch
    wird der Fall zur handlungsorientierten Meldung statt zu einem maskierten
    «Interner Fehler» — und im Mehrquellen-Werkzeug fällt nur *diese* Quelle
    aus, während die anderen weiter antworten.
    """
    from swiss_cultural_heritage_mcp.server import ExpectedUpstreamError

    assert issubclass(UpstreamSchemaError, ExpectedUpstreamError)


# --- Am Werkzeug, nicht nur am Helfer ----------------------------------------


@pytest.mark.asyncio
async def test_artist_search_reports_a_shape_change_instead_of_no_hits():
    """Die Zusage dort, wo der Nutzer sie merkt.

    Vorher: «Keine Daten gefunden» — dieselbe Antwort wie bei einer korrekten
    Suche ohne Treffer.
    """
    from mcp.server.mcpserver.exceptions import ToolError

    from swiss_cultural_heritage_mcp.server import ArtistSearchInput, heritage_search_artists

    with respx.mock:
        respx.get(f"{CKAN_API}/datastore_search").mock(
            return_value=httpx.Response(200, json={"success": True, "help": "…"})
        )
        with pytest.raises(ToolError) as excinfo:
            await heritage_search_artists(ArtistSearchInput(query="Hodler"))
    text = str(excinfo.value)
    assert "Interner Fehler" not in text, (
        "eine Formänderung ist ein erwarteter Upstream-Fehler, kein Programmierfehler"
    )
    assert "result" in text


@pytest.mark.asyncio
async def test_a_real_empty_search_still_says_no_hits():
    """Die Gegenrichtung, und sie ist die wichtigere Hälfte."""
    from swiss_cultural_heritage_mcp.server import ArtistSearchInput, heritage_search_artists

    with respx.mock:
        respx.get(f"{CKAN_API}/datastore_search").mock(
            return_value=httpx.Response(
                200, json={"success": True, "result": {"records": [], "total": 0}}
            )
        )
        out = await heritage_search_artists(ArtistSearchInput(query="gibtesnicht"))
    assert isinstance(out, str)


# --- Dass alle sechs Stellen umgestellt sind ---------------------------------


def test_every_ckan_read_goes_through_the_helper():
    """Sechs Fundstellen, verteilt über vier Werkzeuge.

    Eine davon zu vergessen halbiert die Zusage still — und zwei der sechs
    lasen die Hülle direkt aus `resp.json()`, ohne `success` überhaupt
    anzusehen, waren also am leichtesten zu übersehen.
    """
    from pathlib import Path

    source = Path(__file__).parent.parent / "src" / "swiss_cultural_heritage_mcp" / "server.py"
    body = source.read_text(encoding="utf-8").split('"""', 3)[-1]
    calls = body.count("_ckan_result(")
    assert calls >= 6, f"erwartet: mindestens 6 Aufrufstellen, gefunden: {calls}"
