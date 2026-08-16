"""Die ruff-Version steht an genau einer Stelle — und bleibt dort.

Der Zustand, den diese Tests festhalten, ist bereits hergestellt: `[dev]` fordert
`ruff==0.16.1`, und kein Workflow installiert ruff selbst. Nur hielt ihn nichts
fest. Beide Rückfälle sind still — sie machen kein Gate rot, sie lassen es
lediglich mit einer anderen Version laufen als der, gegen die lokal geprüft
wurde:

* Eine Spanne im Extra lässt `pip install -e ".[dev]"` auf die jeweils neueste
  Version auflösen. Gemessen an Schwester-Servern dieses Portfolios: 0.16.3
  statt der 0.16.1, gegen die die Gates formuliert sind.
* Ein `pip install ruff==<version>` in einem Workflow läuft nach dem Install des
  Extras und überstimmt den Pin. Der Wert in `pyproject.toml` wäre dann
  Dekoration — eine Änderung dort bewirkte in der CI nichts.

Der letzte Test ist ein Sentinel gegen die eigene Prüfmechanik: Fände der
Workflow-Glob nichts, wäre die Schleife im Test darüber leer und seine
Zusicherung trivialerweise wahr.
"""

from __future__ import annotations

import pathlib
import re
import tomllib

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_WORKFLOWS = _ROOT / ".github" / "workflows"


def _dev_abhaengigkeiten() -> list[str]:
    daten = tomllib.loads((_ROOT / "pyproject.toml").read_text())
    return daten["project"]["optional-dependencies"]["dev"]


def test_ruff_ist_exakt_gepinnt() -> None:
    """Eine Spanne lässt lokalen Lauf und CI verschiedene Versionen fahren."""
    specs = [s for s in _dev_abhaengigkeiten() if re.match(r"^ruff\b", s)]
    assert len(specs) == 1, f"genau ein ruff-Specifier erwartet, gefunden: {specs}"
    assert re.fullmatch(r"ruff==\d+\.\d+\.\d+", specs[0]), (
        f"ruff muss als ruff==X.Y.Z gepinnt sein, gefunden {specs[0]!r}. "
        "Eine Spanne lässt lokal und in der CI verschiedene Versionen laufen."
    )


def test_der_pin_ist_die_einzige_versionsquelle() -> None:
    """Kein Workflow darf ruff selbst installieren."""
    for workflow in sorted(_WORKFLOWS.glob("*.yml")):
        # Kommentare ausgenommen, damit ein erklärender Hinweis auf den
        # verbotenen Befehl den Test nicht selbst auslöst.
        zeilen = [z for z in workflow.read_text().splitlines() if not z.lstrip().startswith("#")]
        treffer = [z.strip() for z in zeilen if re.search(r"pip install\s+ruff", z)]
        assert not treffer, (
            f"{workflow.name} installiert ruff direkt ({treffer}). Dieser Schritt "
            "läuft nach dem [dev]-Install und überstimmt den Pin in pyproject."
        )


def test_der_workflow_scan_findet_ueberhaupt_etwas() -> None:
    """Sichert die Prüfung oben gegen ein leeres Verzeichnis ab."""
    workflows = list(_WORKFLOWS.glob("*.yml"))
    assert len(workflows) >= 2, f"Workflow-Scan findet fast nichts: {workflows}"
    assert any("ruff check" in w.read_text() for w in workflows), (
        "kein Workflow ruft ruff auf — der Scan sucht am falschen Ort"
    )
