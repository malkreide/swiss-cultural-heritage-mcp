"""Die zwei Zugaenge zur Nationalbibliothek — und die Fallen in beiden.

Am 20.09.2026 lieferten zwei der drei NB-Werkzeuge zu JEDER Eingabe einen
Fehler, und das Dritte nur fuer ein einziges der 68 Sets. Die Quelle war
erreichbar; der `metadataPrefix` war falsch. Aus der Fehlermeldung
(`noRecordsMatch: No Publishing profile exists for given set and
metadataPrefix`) liess sich das nicht lesen — sie klang wie eine Absage der
Quelle und war die Antwort auf eine Anfrage, die es so nicht gibt.

Was die Tests hier festhalten, ist deshalb weniger «der Code tut X» als
«genau diese Verwechslung faellt auf». Vier Klassen davon:

* der Prefix je Set (`marc21`, ausser `RFN`/`RFN2`),
* die Wahl des Zugangs (Suchbegriff → SRU, Sammlung → OAI-PMH),
* die stillen Falschantworten des SRU (unbekannter Index → ganzer Katalog),
* die Ausgabe (Normdaten-Apparat, Listenwerte, Trefferzahl).

Die Gegenprobe steht in `PROBE_REPORT_helveticat.md`: jede Zusicherung wurde
einzeln neutralisiert und faellt dann.
"""

from __future__ import annotations

import httpx
import pytest
import respx
from test_server import (  # type: ignore[import-not-found]
    MOCK_OAI_MARC_RECORDS,
    MOCK_SRU_DIAGNOSE,
    MOCK_SRU_LEER,
    MOCK_SRU_RECORDS,
)

from swiss_cultural_heritage_mcp import server
from swiss_cultural_heritage_mcp.server import (
    NB_OAI_PMH,
    NB_SRU,
    SRU_MAX_RECORDS,
    CrossSearchInput,
    HelvticatSearchInput,
    PublicationDetailInput,
    ResponseFormat,
    ResultEnvelope,
    heritage_cross_search,
    heritage_get_publication,
    heritage_search_helveticat,
)


# --------------------------------------------------------------------------
# Die Profilkarte: welcher metadataPrefix fuer welches Set
# --------------------------------------------------------------------------
class TestProfilkarte:
    def test_marc21_ist_die_vorgabe(self):
        """66 der 68 Sets — gemessen am 20.09.2026 ueber alle Kombinationen."""
        assert server._nb_prefix(None) == "marc21"
        assert server._nb_prefix("helveticat") == "marc21"
        assert server._nb_prefix("swissbook") == "marc21"

    def test_die_zwei_ausnahmen_stehen_drin(self):
        """`RFN` und `RFN2` haben KEIN marc21-Profil, aber je ein anderes.

        Das ist zugleich die Positivkontrolle der Profilkarte: `oai_dc`
        existiert — fuer genau ein Set. Ohne diesen Befund bliebe «oai_dc geht
        nicht» eine Vermutung mit vielen Belegen.
        """
        assert server._nb_prefix("RFN") == "oai_dc"
        assert server._nb_prefix("RFN2") == "oai_qdc"

    @pytest.mark.asyncio
    async def test_die_sammlungssuche_schickt_den_prefix_des_sets(self):
        for set_spec, erwartet in [
            ("swissbook", "marc21"),
            ("RFN", "oai_dc"),
            ("RFN2", "oai_qdc"),
        ]:
            with respx.mock:
                route = respx.get(NB_OAI_PMH).mock(
                    return_value=httpx.Response(200, text=MOCK_OAI_MARC_RECORDS)
                )
                await heritage_search_helveticat(HelvticatSearchInput(set_spec=set_spec))
            frage = str(route.calls[0].request.url)
            assert f"metadataPrefix={erwartet}" in frage, frage

    @pytest.mark.asyncio
    async def test_der_einzelabruf_fragt_marc21(self):
        """Mit `oai_dc` meldete `GetRecord` auf jede gueltige ID `idDoesNotExist`."""
        with respx.mock:
            route = respx.get(NB_OAI_PMH).mock(
                return_value=httpx.Response(200, text=MOCK_OAI_MARC_RECORDS)
            )
            await heritage_get_publication(
                PublicationDetailInput(identifier="oai:helveticat.nb.admin.ch:991005338049703976")
            )
        frage = str(route.calls[0].request.url)
        assert "metadataPrefix=marc21" in frage, frage
        assert "metadataPrefix=oai_dc" not in frage, frage


# --------------------------------------------------------------------------
# MARCXML lesen
# --------------------------------------------------------------------------
class TestMarcParser:
    def test_marc_fuellt_dieselben_schluessel_wie_dublin_core(self):
        """Sonst braeuchte jede Ansicht einen zweiten Renderer."""
        (rec,) = server._parse_oai_records(MOCK_OAI_MARC_RECORDS)
        assert rec["title"] == "Geschichte der Schweizer Volksschule ein Überblick"
        assert rec["creator"] == "Muster, Anna 1961-"
        assert rec["publisher"] == "Zürich WEKA-Verlag"
        assert rec["date"] == "2000-"
        assert rec["subject"] == "Bildungsgeschichte"
        assert rec["language"] == "ger"
        assert rec["oai_identifier"] == "oai:helveticat.nb.admin.ch:991005338049703976"

    def test_die_setzugehoerigkeit_kommt_mit(self):
        (rec,) = server._parse_oai_records(MOCK_OAI_MARC_RECORDS)
        assert rec["sets"] == ["helveticat", "swissbook"]

    def test_dublin_core_liest_sich_weiterhin(self):
        """Der Parser ist formatunabhaengig — `RFN` liefert `oai_dc`.

        Ein auf MARCXML umgestellter Parser, der DC nicht mehr liest, haette
        die zwei Sonderfaelle der Profilkarte lautlos geleert: Records ohne
        ein einziges Feld, sichtbar nur als «Ohne Titel».
        """
        from test_server import MOCK_OAI_RECORDS  # type: ignore[import-not-found]

        records = server._parse_oai_records(MOCK_OAI_RECORDS)
        assert records[0]["title"] == "Geschichte der Schweizer Volksschule"
        assert records[0]["creator"] == "Muster, Anna"


# --------------------------------------------------------------------------
# SRU: der Index ist die gefaehrlichste Stelle
# --------------------------------------------------------------------------
class TestSruIndexSchutz:
    def test_nur_geprüfte_indexe_gehen_hinaus(self):
        """Ein unbekannter Index ergibt HTTP 200 und den GANZEN Katalog.

        Gemessen am 20.09.2026: `alma.unknown_index="x"` → 2'244'233 Treffer,
        kein `diagnostic`. Eine stille Falschantwort in der Form eines sehr
        guten Ergebnisses — deshalb eine Whitelist und keine Durchreiche.
        """
        with pytest.raises(ValueError, match="Unbekannter SRU-Index"):
            server._cql_term("unknown_index", "x")

    def test_der_naheliegende_tippfehler_faellt_auch(self):
        """`dc.title` statt `alma.title` — daneben steht ja `recordSchema=dc`.

        960 Treffer gegen 2'244'233, und nichts an der Antwort sagt es.
        """
        with pytest.raises(ValueError, match="Unbekannter SRU-Index"):
            server._cql_term("dc.title", "Volksschule")

    def test_ein_anfuehrungszeichen_verlaesst_die_abfrage_nicht(self):
        cql = server._cql_term("all_for_ui", 'Keller" or alma.title="x')
        assert cql == 'alma.all_for_ui="Keller\\" or alma.title=\\"x"'

    def test_der_index_steht_immer_unter_alma(self):
        assert server._cql_term("title", "Volksschule") == 'alma.title="Volksschule"'


class TestSruAntwort:
    def test_eine_diagnose_ist_kein_leeres_ergebnis(self):
        """SRU meldet die Absage im Rumpf und mit HTTP 200 — wie OAI-PMH."""
        with pytest.raises(server.SruError) as fehler:
            server._parse_sru_records(MOCK_SRU_DIAGNOSE)
        assert "200812" in str(fehler.value)
        assert "KEIN leeres Ergebnis" in str(fehler.value)

    def test_die_diagnose_faellt_nur_ihrer_quelle_zur_last(self):
        """Sonst reisst ein SRU-Fehler die ganze Quersuche mit."""
        assert issubclass(server.SruError, ValueError)
        assert issubclass(server.SruError, server.ExpectedUpstreamError)

    def test_die_trefferzahl_kommt_aus_der_quelle(self):
        """`numberOfRecords` — die erste ehrliche Gesamtzahl zu dieser Quelle.

        OAI-PMH nennt keine; `total` blieb deshalb immer `None`.
        """
        records, total = server._parse_sru_records(MOCK_SRU_RECORDS)
        assert total == 960
        assert len(records) == 2

    def test_die_bruecke_zum_einzelabruf_haelt(self):
        """SRU gibt eine MMS-ID aus, `heritage_get_publication` will eine OAI-ID.

        Ohne diese Umformung waere jede Ergebniszeile der Suche eine
        Sackgasse — der Identifier daneben passte zu keinem Abruf.
        """
        records, _ = server._parse_sru_records(MOCK_SRU_RECORDS)
        assert records[0]["oai_identifier"] == "oai:helveticat.nb.admin.ch:991016034239703976"
        assert records[0]["mms_id"] == "991016034239703976"

    def test_der_normdaten_apparat_faellt_weg(self):
        """Alma haengt GND-Nummer und Relator-Code an jeden Namen."""
        records, _ = server._parse_sru_records(MOCK_SRU_RECORDS)
        assert records[0]["contributor"] == "Muster, Anna 1961-"
        assert "DE-588" not in str(records[0])
        assert not str(records[0]["contributor"]).endswith("aut")

    def test_ohne_dc_creator_traegt_contributor_den_namen(self):
        """In allen neun geprueften Records war `dc:creator` leer.

        Die Markdown-Ansicht liest `creator`. Ohne diesen Rueckgriff
        verschwiege sie JEDE Autorenangabe, und zwar lautlos.
        """
        records, _ = server._parse_sru_records(MOCK_SRU_RECORDS)
        assert "creator" not in MOCK_SRU_RECORDS.split("</dc:title>")[0]
        assert records[0]["creator"] == "Muster, Anna 1961-"

    def test_ein_name_wird_nie_gekuerzt(self):
        """Der Schnitt trifft nur, was als Apparat erkennbar ist."""
        assert server._ohne_normdaten("Beispiel, Hans") == "Beispiel, Hans"
        assert server._ohne_normdaten("Aut, Maria") == "Aut, Maria"
        assert server._ohne_normdaten("Meyer-Sickendiek, Burkhard") == (
            "Meyer-Sickendiek, Burkhard"
        )


# --------------------------------------------------------------------------
# Welcher Zugang fuer welche Anfrage
# --------------------------------------------------------------------------
class TestZugangswahl:
    @pytest.mark.asyncio
    async def test_ein_suchbegriff_geht_serverseitig_ueber_sru(self):
        """Vorher war das eine Filterung ueber 100 willkuerliche Records."""
        with respx.mock:
            sru = respx.get(NB_SRU).mock(return_value=httpx.Response(200, text=MOCK_SRU_RECORDS))
            oai = respx.get(NB_OAI_PMH).mock(return_value=httpx.Response(200, text=""))
            await heritage_search_helveticat(HelvticatSearchInput(query="Volksschule"))
        assert sru.called
        assert not oai.called, "ein Suchbegriff darf nicht ueber OAI-PMH laufen"
        frage = str(sru.calls[0].request.url)
        assert "operation=searchRetrieve" in frage
        assert "recordSchema=dc" in frage

    @pytest.mark.asyncio
    async def test_eine_sammlung_geht_ueber_oai(self):
        """SRU kennt die OAI-Sets nicht — gemessen: `mms_memberOf` → 0 Treffer."""
        with respx.mock:
            sru = respx.get(NB_SRU).mock(return_value=httpx.Response(200, text=MOCK_SRU_RECORDS))
            oai = respx.get(NB_OAI_PMH).mock(
                return_value=httpx.Response(200, text=MOCK_OAI_MARC_RECORDS)
            )
            await heritage_search_helveticat(HelvticatSearchInput(set_spec="swissbook"))
        assert oai.called
        assert not sru.called

    @pytest.mark.asyncio
    async def test_der_serverseitige_deckel_wird_nicht_ueberschritten(self):
        """`maximumRecords` ist serverseitig bei 50 gedeckelt — lautlos.

        Gemessen: eine Anfrage mit 100 oder 200 liefert 50 Records, ohne
        Warnung und ohne `diagnostic`.

        Geprueft wird `_sru_suche` direkt und NICHT ueber das Werkzeug: dessen
        `limit` ist selbst auf 50 begrenzt, `min(50, 50)` ist 50, und ein Test
        ueber das Werkzeug bliebe deshalb auch ohne den Deckel gruen. Genau so
        stand er hier zuerst — die Gegenprobe hat ihn widerlegt.
        """
        with respx.mock:
            route = respx.get(NB_SRU).mock(return_value=httpx.Response(200, text=MOCK_SRU_RECORDS))
            await server._sru_suche("x", limit=200)
        assert f"maximumRecords={SRU_MAX_RECORDS}" in str(route.calls[0].request.url)
        assert "maximumRecords=200" not in str(route.calls[0].request.url)

    def test_das_limit_des_werkzeugs_passt_zum_deckel_der_quelle(self):
        """Sonst verspricht das Schema mehr, als die Quelle je liefert.

        Ein `limit` ueber 50 wuerde still auf 50 gekuerzt — die Antwort saehe
        aus wie ein vollstaendiges Ergebnis und waere eine Seite davon.
        """
        grenze = HelvticatSearchInput.model_fields["limit"].metadata
        assert any(getattr(m, "le", None) == SRU_MAX_RECORDS for m in grenze), grenze

    @pytest.mark.asyncio
    async def test_ohne_begriff_und_ohne_sammlung_wird_nichts_abgeschickt(self):
        """Die Quelle antwortete darauf mit `badArgument` — das braucht sie nicht."""
        with respx.mock:
            route = respx.get(NB_OAI_PMH).mock(return_value=httpx.Response(200, text=""))
            sru = respx.get(NB_SRU).mock(return_value=httpx.Response(200, text=""))
            ergebnis = await heritage_search_helveticat(
                HelvticatSearchInput(response_format=ResponseFormat.JSON)
            )
        assert not route.called and not sru.called
        assert isinstance(ergebnis, ResultEnvelope)
        assert ergebnis.match_type == "none"

    @pytest.mark.asyncio
    async def test_ein_zeitfenster_ohne_sammlung_wird_erklaert(self):
        """Und zwar mit der spezielleren der beiden Meldungen.

        Eine Anfrage mit nur `from_date` hat weder Begriff noch Sammlung. Steht
        der allgemeine Waechter zuerst, ist diese Auskunft unerreichbar — und
        die Antwort spricht vom Zeitfenster kein Wort.
        """
        with respx.mock:
            respx.get(NB_OAI_PMH).mock(return_value=httpx.Response(200, text=""))
            ergebnis = str(
                await heritage_search_helveticat(HelvticatSearchInput(from_date="2026-09-01"))
            )
        assert "Zeitfenster gibt es nur zusammen mit `set_spec`" in ergebnis, ergebnis
        assert "Änderungsdatum" in ergebnis
        assert "nicht das Erscheinungsjahr" in ergebnis


class TestGelockerteSuche:
    @pytest.mark.asyncio
    async def test_null_treffer_loest_einen_zweiten_anlauf_aus(self):
        """`=` sucht die Wortfolge, `all` alle Woerter irgendwo.

        Gemessen: «Volksschule Zürich» → 4 bzw. 346 Treffer.
        """
        antworten = [
            httpx.Response(200, text=MOCK_SRU_LEER),
            httpx.Response(200, text=MOCK_SRU_RECORDS),
        ]
        with respx.mock:
            route = respx.get(NB_SRU).mock(side_effect=antworten)
            ergebnis = await heritage_search_helveticat(
                HelvticatSearchInput(query="Volksschule Zürich", response_format="json")
            )
        assert len(route.calls) == 2
        assert "all" in str(route.calls[1].request.url)
        assert isinstance(ergebnis, ResultEnvelope)
        assert ergebnis.match_type == "fuzzy"
        assert ergebnis.total == 960

    @pytest.mark.asyncio
    async def test_treffer_beim_ersten_anlauf_bleiben_exact(self):
        with respx.mock:
            route = respx.get(NB_SRU).mock(return_value=httpx.Response(200, text=MOCK_SRU_RECORDS))
            ergebnis = await heritage_search_helveticat(
                HelvticatSearchInput(query="Volksschule", response_format="json")
            )
        assert len(route.calls) == 1
        assert isinstance(ergebnis, ResultEnvelope)
        assert ergebnis.match_type == "exact"


# --------------------------------------------------------------------------
# Ausgabe
# --------------------------------------------------------------------------
class TestAusgabe:
    @pytest.mark.asyncio
    async def test_die_trefferzahl_steht_in_der_ansicht(self):
        with respx.mock:
            respx.get(NB_SRU).mock(return_value=httpx.Response(200, text=MOCK_SRU_RECORDS))
            ergebnis = await heritage_search_helveticat(
                HelvticatSearchInput(query="Volksschule", limit=2)
            )
        assert "2 von 960 Treffern" in ergebnis

    @pytest.mark.asyncio
    async def test_ein_listenwert_wird_nicht_als_python_liste_gedruckt(self):
        """`oai_dc` liefert `['[2022]', '2022']` fuer EIN Erscheinungsjahr."""
        with respx.mock:
            respx.get(NB_SRU).mock(return_value=httpx.Response(200, text=MOCK_SRU_RECORDS))
            ergebnis = await heritage_search_helveticat(HelvticatSearchInput(query="Kunst"))
        assert "['" not in ergebnis, ergebnis
        assert "**Jahr:** [2022]" in ergebnis

    def test_ein_wert_nimmt_den_ersten_eintrag(self):
        assert server._ein_wert(["[2022]", "2022"]) == "[2022]"
        assert server._ein_wert("2022") == "2022"
        assert server._ein_wert(None) == ""
        assert server._ein_wert([]) == ""

    @pytest.mark.asyncio
    async def test_die_filterung_in_einer_sammlung_sagt_was_sie_ist(self):
        """Ein leeres Ergebnis heisst «nicht auf dieser Seite», nicht «gibt es nicht»."""
        with respx.mock:
            respx.get(NB_OAI_PMH).mock(return_value=httpx.Response(200, text=MOCK_OAI_MARC_RECORDS))
            ergebnis = await heritage_search_helveticat(
                HelvticatSearchInput(query="zzz-nicht-vorhanden", set_spec="swissbook")
            )
        assert "keine Aussage über die Sammlung" in ergebnis
        assert "`query` ohne" in ergebnis


# --------------------------------------------------------------------------
# Die Quersuche
# --------------------------------------------------------------------------
class TestQuersuche:
    @pytest.mark.asyncio
    async def test_die_nb_wird_ueber_sru_gefragt(self):
        """Vorher: `ListRecords` ohne `set` → `badArgument` in jeder Quersuche."""
        with respx.mock:
            sru = respx.get(NB_SRU).mock(return_value=httpx.Response(200, text=MOCK_SRU_RECORDS))
            oai = respx.get(NB_OAI_PMH).mock(return_value=httpx.Response(200, text=""))
            respx.get(url__startswith=server.CKAN_API).mock(
                return_value=httpx.Response(200, json={"success": True, "result": {"records": []}})
            )
            ergebnis = await heritage_cross_search(
                CrossSearchInput(query="Volksschule", sources=["nb"], limit_per_source=2)
            )
        assert sru.called
        assert not oai.called
        assert "⚠️" not in ergebnis, ergebnis
        assert "Geschichte der Schweizer Volksschule" in ergebnis

    @pytest.mark.asyncio
    async def test_ein_sru_fehler_faellt_nur_der_nb_zur_last(self):
        """Die anderen Quellen antworten weiter — das ist der Sinn der Fassade."""
        with respx.mock:
            respx.get(NB_SRU).mock(return_value=httpx.Response(200, text=MOCK_SRU_DIAGNOSE))
            respx.get(f"{server.CKAN_API}/datastore_search").mock(
                return_value=httpx.Response(
                    200, json={"success": True, "result": {"records": [{"NAME": "Hodler"}]}}
                )
            )
            ergebnis = await heritage_cross_search(
                CrossSearchInput(query="Hodler", sources=["sik_isea", "nb"], limit_per_source=2)
            )
        assert "SIK-ISEA" in ergebnis
        assert "200812" in ergebnis
