"""Die Protokoll-Tabelle der READMEs wird geprüft, nicht geglaubt.

Beide READMEs nannten bis 2026-08-16 `mcp[cli] >=1.0.0,<2.0.0`, während
`pyproject.toml` seit dem 2.x-Wechsel `mcp[cli]>=2.0.0,<3` fordert und 1.x
gar nicht mehr lauffähig ist. Dieselbe Zeile behauptete, der SDK-Pin sei die
Quelle der Wahrheit für die Protokoll-Version — sie zeigte auf einen Pin, den
es nicht mehr gab. Aufgefallen ist es beim Lesen, nicht durch einen Lauf.

`scripts/check_version_sync.py` konnte das nicht finden: Es prüft die
Projektversion und kommt bewusst ohne Projekt-Installation aus. Diese Zusiche-
rung braucht dagegen die Registry des *installierten* SDK — welche Revisionen
es tatsächlich bedient, steht nirgends sonst. Deshalb liegt der Check hier
und nicht dort; er läuft im bestehenden Gate `pytest tests/ -m "not live"`
auf allen drei Python-Versionen mit.

Was hier fällt, ist nie ein Code-Fehler, sondern immer eine veraltete Doku
nach einem SDK-Bump oder einer Pin-Änderung.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
from mcp_types.version import (
    HANDSHAKE_PROTOCOL_VERSIONS,
    KNOWN_PROTOCOL_VERSIONS,
    MODERN_PROTOCOL_VERSIONS,
)

ROOT = Path(__file__).resolve().parent.parent

# Überschrift → Datei. Beide Sprachfassungen tragen dieselbe Tabelle; eine
# allein zu prüfen liesse die andere still veralten.
READMES = {
    "README.md": "## MCP Protocol Version",
    "README.de.md": "## MCP-Protokoll-Version",
}

_DATE_VERSION = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def protocol_section(filename: str) -> str:
    """Der Abschnitt zwischen seiner Überschrift und der nächsten `## `-Zeile.

    Bewusst über die Überschrift und nicht über Zeilennummern: Ein Abschnitt
    darüber wächst, Zeilennummern verschieben sich, und ein Check, der dann
    den falschen Text liest, prüft nichts mehr.
    """
    text = (ROOT / filename).read_text(encoding="utf-8")
    heading = READMES[filename]
    start = text.find(heading)
    assert start != -1, f"{filename}: Abschnitt {heading!r} fehlt"
    rest = text[start + len(heading) :]
    end = rest.find("\n## ")
    return rest if end == -1 else rest[:end]


def mcp_requirement() -> str:
    """Die `mcp[...]`-Zeile aus `[project] dependencies`, wörtlich."""
    with (ROOT / "pyproject.toml").open("rb") as fh:
        deps = tomllib.load(fh)["project"]["dependencies"]
    matches = [d for d in deps if d.split("[")[0].split(">")[0].split("=")[0].strip() == "mcp"]
    assert len(matches) == 1, f"genau eine mcp-Abhängigkeit erwartet, gefunden: {matches}"
    return matches[0]


def squeeze(text: str) -> str:
    """Ohne Leerraum — `mcp[cli] >=2.0.0, <3` und `mcp[cli]>=2.0.0,<3` sind
    dieselbe Zusicherung, und ein Check, der an einem Leerzeichen scheitert,
    wird abgeschaltet statt gelesen."""
    return "".join(text.split())


@pytest.mark.parametrize("filename", sorted(READMES))
def test_readme_nennt_den_sdk_pin_aus_pyproject(filename: str):
    """Der in der Tabelle genannte Pin ist der, der auch installiert wird."""
    assert squeeze(mcp_requirement()) in squeeze(protocol_section(filename)), (
        f"{filename}: Die Protokoll-Tabelle nennt nicht den mcp-Pin aus "
        f"pyproject.toml ({mcp_requirement()!r})."
    )


@pytest.mark.parametrize("filename", sorted(READMES))
def test_readme_nennt_jede_bediente_revision(filename: str):
    """Handshake-Grenzen und jede moderne Revision stehen in der Tabelle.

    Genannt werden die *Ränder* des Handshake-Bereichs, weil die Tabelle ihn
    als Spanne schreibt (`2024-11-05 … 2025-11-25`); die Werte dazwischen
    stehen dort absichtlich nicht.
    """
    section = protocol_section(filename)
    erwartet = {
        HANDSHAKE_PROTOCOL_VERSIONS[0],
        HANDSHAKE_PROTOCOL_VERSIONS[-1],
        *MODERN_PROTOCOL_VERSIONS,
    }
    fehlend = sorted(v for v in erwartet if v not in section)
    assert not fehlend, (
        f"{filename}: Die Protokoll-Tabelle nennt {fehlend} nicht — das SDK "
        f"bedient sie. Nach einem mcp-Bump gehört die Tabelle nachgezogen."
    )


@pytest.mark.parametrize("filename", sorted(READMES))
def test_readme_nennt_keine_revision_die_es_nicht_gibt(filename: str):
    """Keine Datums-Version im Abschnitt, die das SDK nicht kennt.

    Fängt den umgekehrten Fall: Eine Revision, die ein SDK-Bump fallen liess,
    bleibt in der Tabelle stehen und liest sich weiter wie eine Zusage.
    """
    genannt = set(_DATE_VERSION.findall(protocol_section(filename)))
    unbekannt = sorted(genannt - set(KNOWN_PROTOCOL_VERSIONS))
    assert not unbekannt, (
        f"{filename}: Die Protokoll-Tabelle nennt {unbekannt}; das installierte "
        f"SDK kennt diese Revision(en) nicht."
    )
