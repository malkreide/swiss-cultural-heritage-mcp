"""Die READMEs nennen die Zugaenge der Nationalbibliothek, die der Code nutzt.

Am 20.09.2026 bekam Helveticat einen zweiten Zugang (SRU fuer die Volltext-
suche) und einen anderen `metadataPrefix` (`marc21` statt `oai_dc`). Beide
READMEs beschrieben die Quelle danach noch zwei Tage lang als reinen
OAI-PMH-Zugang mit Dublin Core. Kein Gate hat das gefunden: Die CI prueft
Code, nicht Prosa — dieselbe Klasse wie die «drei Quellen», die monatelang
ueber fuenf angebundenen standen.

Was dieser Test haelt, leitet er aus dem Code ab und nicht aus einer Liste im
Test: Ist ein SRU-Endpunkt konfiguriert, muss das Wort in beiden Fassungen
vorkommen; der voreingestellte `metadataPrefix` muss genannt sein, wie er
heisst.

Was er NICHT halten kann: ob der Text die Zugaenge richtig BESCHREIBT. Er
zaehlt Namen, nicht Aussagen. Genau daran ist der `INSTRUCTIONS`-Text im
September vorbeigelaufen — er nannte alle fuenf Quellen und wies trotzdem das
falsche Tool als quellenuebergreifenden Einstieg aus. Ein gruener Lauf hier
heisst: die Begriffe stehen drin. Nicht mehr.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from swiss_cultural_heritage_mcp.server import NB_PREFIX_DEFAULT, NB_SRU

ROOT = Path(__file__).resolve().parent.parent
READMES = ("README.md", "README.de.md")


def lies(dateiname: str) -> str:
    return (ROOT / dateiname).read_text(encoding="utf-8")


@pytest.mark.parametrize("dateiname", READMES)
def test_readme_nennt_den_sru_zugang(dateiname: str) -> None:
    """Ein konfigurierter SRU-Endpunkt gehoert in beide Sprachfassungen."""
    assert NB_SRU, "Kein SRU-Endpunkt konfiguriert — dieser Test haette nichts zu halten."
    assert "SRU" in lies(dateiname), (
        f"{dateiname} nennt SRU nicht, obwohl der Server {NB_SRU} abfragt. "
        "Die Volltextsuche laeuft nicht mehr ueber OAI-PMH."
    )


@pytest.mark.parametrize("dateiname", READMES)
def test_readme_nennt_den_voreingestellten_metadataprefix(dateiname: str) -> None:
    """Der Prefix, mit dem 66 der 68 Sets tatsaechlich antworten.

    Ohne Ruecksicht auf Gross-/Kleinschreibung: Auf dem Draht heisst er
    `marc21`, in Prosa schreibt man das Format `MARC21`. Ein Test, der die
    Prosafassung fallen laesst, meldet eine Drift, die keine ist — und wird
    beim naechsten Mal abgeschaltet statt gelesen.
    """
    assert NB_PREFIX_DEFAULT.lower() in lies(dateiname).lower(), (
        f"{dateiname} nennt den metadataPrefix {NB_PREFIX_DEFAULT!r} nicht. "
        "Steht dort nur noch oai_dc, beschreibt die Doku den Zustand vor "
        "PR #96 — und genau der lieferte fuer 67 von 68 Sets nichts."
    )
