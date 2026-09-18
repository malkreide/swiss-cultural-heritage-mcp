"""Was der Verzeichniseintrag ueber diesen Server behauptet.

`server.json` ist die einzige Datei des Repos, die niemand beim Arbeiten
liest: Sie wirkt erst im MCP-Verzeichnis, und der Eintrag dort ist das, was
ein Mensch vor der Installation sieht. Entsprechend lange stand darin
«Heritage inventories, monument lists, archaeological registers» — drei
Dinge, die dieser Server nicht liefert (`monument`, `archaeolog` und
`inventor` kommen in `src/` nicht vor), waehrend keine der fuenf
angebundenen Quellen genannt war.

Gemessen, bevor diese Datei entstand: Mit genau dieser Zeile liefen alle
fuenf CI-Gates gruen, 267 Tests eingeschlossen. `check_version_sync.py`
vergleicht Versionsfelder und ruehrt die Beschreibung nicht an, und kein
Test las `server.json`. Der Fall fiel also nirgends — deshalb steht hier
etwas.

Beide Richtungen kommen aus dem Code, nicht aus einer Liste in dieser
Datei: die verbundenen Quellen aus den `SourceInfo`-Konstanten, die
NICHT verbundenen aus `_HERITAGE_COLLECTIONS`. Letzteres ist der
Unterschied zur Vorlage in `swiss-democracy-mcp`, wo die fremden Quellen
handgeschrieben stehen mussten: Hier fuehrt der Server selbst Buch
darueber, was er nicht erreicht.

Was die Pruefungen NICHT leisten: Sie lesen keinen Text. Eine sachlich
schiefe, aber marker-treue Beschreibung kommt durch. Sie fangen die
mechanischen Klassen, die unten je einen Test tragen, und behaupten
darueber hinaus nichts.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from swiss_cultural_heritage_mcp import server as srv

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SERVER_JSON = _ROOT / "server.json"

# `ServerDetail.description.maxLength`, je Schema-Fassung. Als Zahl abgelegt,
# weil der Test sonst im CI-Lauf ans Netz muesste — aber NICHT allein: Das
# Limit steht unter dem `$schema`-Wert, aus dem es stammt.
#
# Sonst waere es eine Kopie, die ihre Quelle nicht kennt. Wer `server.json`
# auf eine neue Schema-Fassung umstellt, erbte still die Grenze der alten:
# bei einem kleineren neuen Wert bliebe das Gate gruen und die Registry
# wiese erst nach der PyPI-Veroeffentlichung zurueck, bei einem groesseren
# blockierte es gueltige Beschreibungen.
_MAX_LAENGE_JE_SCHEMA: dict[str, int] = {
    "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json": 100,
}

# Je Quelle die Schreibweisen, von denen mindestens eine in der Beschreibung
# vorkommen muss. Die SCHLUESSEL sind nicht aufgeschrieben, sondern werden
# unten gegen die `SourceInfo`-Konstanten des Moduls gehalten: Wer eine
# sechste Quelle anbindet, legt dafuer eine Konstante an (ohne sie gibt es
# keine Provenienz im Envelope) und faellt damit hier auf, solange er sie im
# Verzeichniseintrag verschweigt.
_MARKER: dict[str, tuple[str, ...]] = {
    "SOURCE_SIKART": ("SIKART", "SIK-ISEA"),
    "SOURCE_SNM": ("Nationalmuseum", "SNM"),
    "SOURCE_NB": ("Helveticat", "Nationalbibliothek"),
    "SOURCE_MEMOBASE": ("Memobase", "Memoriav"),
    "SOURCE_DODIS": ("Dodis",),
}

# Fuer eine Institution, die `_HERITAGE_COLLECTIONS` als nicht verbunden
# fuehrt, das Wort, unter dem sie in einer Beschreibung auftauchen wuerde.
# Auch hier sind die SCHLUESSEL abgeleitet: Eine neue nicht verbundene
# Institution faellt auf, weil sie hier fehlt.
#
# Die Worte sind mit Bedacht gewaehlt und nicht aus `name` oder `url`
# genommen: Der Eintrag `landesmuseum` traegt die URL
# `sammlung.nationalmuseum.ch`, und ein daraus abgeleitetes Verbot von
# «nationalmuseum» wuerde die verbundene Quelle SOURCE_SNM treffen — ein
# Test, der die richtige Beschreibung rot faerbt.
_NICHT_VERBUNDEN_MARKER: dict[str, str] = {
    "bar": "Bundesarchiv",
    "landesmuseum": "Landesmuseum",
}


def _quellen_konstanten() -> dict[str, srv.SourceInfo]:
    """Alle `SourceInfo`-Objekte, die das Servermodul auf Modulebene fuehrt."""
    return {name: wert for name, wert in vars(srv).items() if isinstance(wert, srv.SourceInfo)}


def _nicht_verbunden() -> dict[str, str]:
    """Institutionen aus `_HERITAGE_COLLECTIONS`, die der Server nicht erreicht."""
    return {
        eintrag["id"]: eintrag["name"]
        for eintrag in srv._HERITAGE_COLLECTIONS
        if eintrag.get("status") != "active"
    }


def _docstring_aufzaehlung() -> str:
    """Nur die Aufzaehlungszeilen des Modul-Docstrings.

    Die Liste im Docstring beginnt jede Quelle mit «·». Alles andere ist
    Fliesstext, der ueber die Quellen reden darf, ohne als Nennung zu zaehlen.
    """
    doku = srv.__doc__ or ""
    return "\n".join(z for z in doku.splitlines() if z.lstrip().startswith("·"))


def _manifest() -> dict:
    return json.loads(_SERVER_JSON.read_text(encoding="utf-8"))


def test_die_beschreibung_haelt_die_schema_grenze() -> None:
    """Zu lang faellt sonst erst beim Release — und dort zu spaet.

    `publish.yml` haengt den Registry-Schritt hinter den PyPI-Job. Ein
    Manifest, das die Registry zurueckweist, bricht also ab, nachdem das
    Paket bereits veroeffentlicht ist. Geprueft wird gegen die Fassung, auf
    die `server.json` per `$schema` zeigt, nicht gegen eine fest
    verdrahtete Zahl.
    """
    manifest = _manifest()
    schema = manifest.get("$schema", "")
    grenze = _MAX_LAENGE_JE_SCHEMA.get(schema)
    assert grenze is not None, (
        f"server.json verweist auf {schema!r}. Fuer diese Schema-Fassung ist in "
        "_MAX_LAENGE_JE_SCHEMA keine Grenze hinterlegt. Ihr "
        "`ServerDetail.description.maxLength` nachschlagen und dort eintragen — "
        "die Grenze der alten Fassung weiterzuerben pruefte das falsche Schema."
    )

    beschreibung = manifest["description"]
    assert beschreibung, "leere Beschreibung — das Schema verlangt minLength 1"
    assert len(beschreibung) <= grenze, f"{len(beschreibung)} Zeichen, erlaubt sind {grenze}."


@pytest.mark.parametrize("konstante", sorted(_quellen_konstanten()))
def test_jede_angebundene_quelle_steht_im_verzeichniseintrag(konstante: str) -> None:
    """Was der Server bedient, muss der Eintrag auch nennen."""
    marker = _MARKER.get(konstante)
    assert marker is not None, (
        f"{konstante} ist eine SourceInfo-Konstante des Servermoduls, aber in "
        "_MARKER nicht eingeordnet. Dort die Schreibweisen eintragen, unter "
        "denen die Quelle in der Beschreibung erscheinen darf."
    )
    beschreibung = _manifest()["description"]
    assert any(m in beschreibung for m in marker), (
        f"server.json nennt {konstante} nicht (erwartet eine von {list(marker)}), "
        f"obwohl das Modul sie als {_quellen_konstanten()[konstante].name!r} fuehrt."
    )


@pytest.mark.parametrize("institution", sorted(_nicht_verbunden()))
def test_der_eintrag_nennt_keine_quelle_die_der_server_nicht_erreicht(
    institution: str,
) -> None:
    """Der Rueckfall in genau den Fehler, der diese Datei ausgeloest hat.

    Abgeleitet statt aufgeschrieben: `_HERITAGE_COLLECTIONS` fuehrt den
    Status selbst. Faellt eine Institution von `active` auf etwas anderes,
    wird ihr Name hier automatisch verboten.
    """
    marker = _NICHT_VERBUNDEN_MARKER.get(institution)
    assert marker is not None, (
        f"_HERITAGE_COLLECTIONS fuehrt {institution!r} als nicht verbunden, aber "
        "_NICHT_VERBUNDEN_MARKER kennt kein Wort dafuer. Dort eines eintragen, "
        "das keine verbundene Quelle trifft."
    )
    beschreibung = _manifest()["description"]
    assert marker.lower() not in beschreibung.lower(), (
        f"server.json nennt {marker!r}, aber _HERITAGE_COLLECTIONS fuehrt "
        f"{_nicht_verbunden()[institution]!r} als nicht verbunden — der Server "
        "fragt diese Quelle nicht ab."
    )


@pytest.mark.parametrize("konstante", sorted(_quellen_konstanten()))
def test_der_modul_docstring_nennt_jede_quelle(konstante: str) -> None:
    """Dieselbe Frage am zweiten Ort, an dem die Quellen aufgezaehlt werden.

    Der Modul-Docstring ist das, was beim Lesen des Codes zuerst ins Auge
    faellt — und er trug dieselbe Luecke wie der Verzeichniseintrag: Er
    sprach von «drei Quellen» und zaehlte SIK-ISEA, Nationalmuseum und
    Nationalbibliothek auf, waehrend Memobase und Dodis ueber die
    foederierte Fassade laengst dazugekommen waren.

    Das ist der Fall «Zahlen, die eine Aufzaehlung wiederholen» aus
    CLAUDE.md, und er faellt nirgends von selbst auf: Ein Docstring hat
    keine Gegenprobe. Geprueft wird gegen dieselbe abgeleitete Menge wie der
    Eintrag, damit beide Orte nicht auseinanderlaufen koennen.

    Gelesen werden nur die AUFZAEHLUNGSZEILEN, nicht der ganze Docstring.
    Der Unterschied ist gemessen: Eine erste Fassung suchte im gesamten
    Text — und blieb gruen, als die Memobase-Zeile aus der Liste entfernt
    wurde, weil der erklaerende Absatz darunter den Namen ebenfalls nennt.
    Die Prosa haette die Zusicherung entwertet, und zwar genau die, deren
    Verletzung sie beschreibt. Die Aufzaehlung ist die Quelle; ein Satz, der
    ueber sie redet, ist keine.
    """
    marker = _MARKER.get(konstante)
    assert marker is not None, (
        f"{konstante} ist in _MARKER nicht eingeordnet — siehe den Test darueber."
    )
    liste = _docstring_aufzaehlung()
    assert any(m in liste for m in marker), (
        f"Die Quellen-Aufzaehlung im Modul-Docstring nennt {konstante} nicht "
        f"(erwartet eine von {list(marker)}), obwohl das Modul sie als "
        f"{_quellen_konstanten()[konstante].name!r} fuehrt."
    )


def test_die_aufzaehlung_nennt_keine_quelle_mehr_die_es_nicht_gibt() -> None:
    """Die Rueckrichtung — und ohne sie ist der Test oben halb blind.

    Der Test darueber belegt, dass jede angebundene Quelle in der
    Aufzaehlung steht. Er belegt NICHT, dass jede Zeile der Aufzaehlung zu
    einer Quelle gehoert. Wird eine Integration entfernt — die
    `SourceInfo`-Konstante und ihr `_MARKER`-Eintrag verschwinden, die
    Docstring-Zeile bleibt stehen —, laeuft der Test darueber ueber die
    verbliebenen Quellen und findet nichts zu beanstanden. Das Modul
    bewuerbe dann eine Quelle, die es nicht mehr abfragen kann: genau die
    Drift, gegen die diese Datei geschrieben ist, nur in die andere
    Richtung.

    Aufgefallen durch einen Codex-Review (P2) auf PR #88 — die erste Fassung
    hatte die Luecke.

    Geprueft wird zeilenweise und nicht ueber die Anzahl: Eine Zahl waere
    wieder die Kopie einer Aufzaehlung, und sie sagte nicht, WELCHE Zeile
    verwaist ist.
    """
    bekannt = {m for marker in _MARKER.values() for m in marker}
    verwaist = [
        zeile.strip()
        for zeile in _docstring_aufzaehlung().splitlines()
        if not any(m in zeile for m in bekannt)
    ]
    assert not verwaist, (
        "Diese Zeilen der Quellen-Aufzaehlung im Modul-Docstring gehoeren zu "
        "keiner SourceInfo-Konstante mehr:\n  " + "\n  ".join(verwaist) + "\n"
        "Entweder ist die Quelle weggefallen — dann die Zeile streichen — oder "
        "sie ist neu und braucht eine Konstante samt _MARKER-Eintrag."
    )


def test_die_ableitung_findet_ueberhaupt_etwas() -> None:
    """Sichert die Parametrisierungen oben gegen leere Eingaben ab.

    Faende `_quellen_konstanten()` nichts, erzeugte der Quellen-Test null
    Faelle und die Suite bliebe gruen, ohne den Eintrag angesehen zu haben —
    gruen aus Mangel an Pruefung.
    """
    quellen = _quellen_konstanten()
    assert quellen, "keine SourceInfo-Konstante gefunden — der Scan sucht falsch"
    assert _docstring_aufzaehlung(), (
        "der Modul-Docstring hat keine Aufzaehlungszeilen — dann prueft der "
        "Docstring-Test nichts. (python -OO entfernt Docstrings ganz; die "
        "Suite laeuft ohne, und dieser Test waere dort gruen aus Mangel an "
        "Pruefung.)"
    )
    assert _nicht_verbunden(), (
        "_HERITAGE_COLLECTIONS fuehrt keine nicht verbundene Institution mehr — "
        "dann prueft der Negativ-Test nichts"
    )
    veraltet = set(_MARKER) - set(quellen)
    assert not veraltet, f"_MARKER nennt Konstanten, die es nicht gibt: {sorted(veraltet)}"
    veraltet_neg = set(_NICHT_VERBUNDEN_MARKER) - set(_nicht_verbunden())
    assert not veraltet_neg, (
        "_NICHT_VERBUNDEN_MARKER nennt Institutionen, die inzwischen verbunden "
        f"sind oder fehlen: {sorted(veraltet_neg)}"
    )
