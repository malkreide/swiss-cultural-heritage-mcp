"""`check_version_sync.py` haelt jetzt auch `generated_for_version` im Tool-Pin.

Gehalten wurde das Feld bis zum 28.10.2026 nur von
`tests/test_server.py::TestToolPins::test_pin_records_the_declared_version`.
Dort gehoert es auch hin -- derselbe Test stellt die *lebenden*
Tool-Definitionen gegen die Hashes und braucht dafuer die Projekt-Installation.
Genau deshalb konnte er aber nicht ueberall greifen: Der pre-commit-Hook
(`.githooks/pre-commit`) faehrt ohne installiertes Paket, und in einer
schlanken Umgebung ohne `pip install -e ".[dev]"` gibt es den Test nicht.

Der Befund, der das ausgeloest hat: Beim Bump auf 0.5.0 blieb der Pin auf
0.4.0, und rot wurde es erst in der CI auf Python 3.11.

Geprueft wird hier das Gate als Prozess, gegen echte Verzeichnisse. Die Datei
wird dafuer kopiert, nicht importiert: `ROOT` leitet sie aus `__file__` ab, und
nur eine Kopie an einer anderen Stelle laesst sich gegen einen anderen Baum
fahren. Nebenbei prueft das mit, dass das Gate ohne Projekt-Installation laeuft
-- die Eigenschaft, auf der der Hook beruht.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
GATE = _ROOT / "scripts" / "check_version_sync.py"

PIN_PFAD = "audits/tool-pins/current.json"


def _baum(tmp_path: Path, version: str, pin: str | None) -> Path:
    """Minimal-Repo: nur pyproject.toml und (optional) der Tool-Pin.

    Ohne `server.json`, READMEs und `src/` bleibt genau eine Pruefung
    aussagefaehig -- die neue. Waere eine Nachbarpruefung mit im Spiel, koennte
    ein rotes Ergebnis auch von ihr kommen, und der Test misst nicht, was sein
    Name behauptet.
    """
    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(GATE, tmp_path / "scripts" / "check_version_sync.py")
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "wegwerf-paket"\nversion = "{version}"\n', encoding="utf-8"
    )
    if pin is not None:
        ziel = tmp_path / PIN_PFAD
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(pin, encoding="utf-8")
    return tmp_path


def _lauf(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(tmp_path / "scripts" / "check_version_sync.py")],
        capture_output=True,
        text=True,
        timeout=120,
    )


def _pin_text(version: str) -> str:
    return json.dumps({"generated_for_version": version, "tools": {}}, indent=2) + "\n"


# ────────────────────────────── Positivkontrollen ──────────────────────────────


def test_stimmiger_pin_laeuft_durch(tmp_path: Path):
    """Ohne diese Kontrolle messen die roten Faelle unten nichts.

    Ein Gate, das in diesem Minimal-Baum aus einem anderen Grund immer faellt,
    liesse jeden Test unten gruen sein, ohne dass die neue Pruefung existiert.
    """
    ergebnis = _lauf(_baum(tmp_path, "0.5.0", _pin_text("0.5.0")))

    assert ergebnis.returncode == 0, ergebnis.stderr


def test_ausgabe_nennt_den_pin_als_geprueft(tmp_path: Path):
    """Ein gruener Lauf muss sagen, dass er den Pin angesehen hat.

    Sonst sieht "Versions-Sync OK" genauso aus, wenn die Pruefung
    stillschweigend herausfaellt -- etwa weil die Datei umbenannt wurde und
    `TOOL_PIN.exists()` seither falsch ist. Dieser Test ist die Wache fuer
    diesen Fall; das `exists()`-Ueberspringen ist sonst ein Falsch-Gruen.
    """
    ergebnis = _lauf(_baum(tmp_path, "0.5.0", _pin_text("0.5.0")))

    assert "generated_for_version" in ergebnis.stdout, ergebnis.stdout
    assert PIN_PFAD in ergebnis.stdout, ergebnis.stdout


def test_fehlender_pin_ist_kein_befund(tmp_path: Path):
    """Dieselbe Regel wie bei `server.json`: gemessen wird Uebereinstimmung.

    Dass es den Pin ueberhaupt gibt, haelt `tests/test_server.py::TestToolPins`
    -- dort liegt die Zusicherung ueber die Hashes selbst. Hier waere ein
    Befund nur ein Fehlalarm in jedem Repo ohne Pin.
    """
    ergebnis = _lauf(_baum(tmp_path, "0.5.0", None))

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert PIN_PFAD not in ergebnis.stdout, (
        "Ohne Datei darf die Ausgabe den Pin nicht als geprueft auffuehren"
    )


# ─────────────────────────────── Die roten Faelle ──────────────────────────────


def test_pin_fuer_andere_version_ist_rot(tmp_path: Path):
    """Der Fall vom 0.5.0-Bump, nachgestellt."""
    ergebnis = _lauf(_baum(tmp_path, "0.5.0", _pin_text("0.4.0")))

    assert ergebnis.returncode == 1
    assert "0.4.0" in ergebnis.stderr and "0.5.0" in ergebnis.stderr
    assert "scripts/pin_tools.py" in ergebnis.stderr, (
        "Die Meldung muss den Handgriff nennen, nicht nur den Widerspruch"
    )


def test_meldung_warnt_vor_dem_haendischen_nachtragen(tmp_path: Path):
    """Der naheliegende Fehlgriff ist, das Feld einfach zu ueberschreiben.

    Die Hashes daneben beschreiben die freigegebene Tool-Oberflaeche. Ein
    nachgeschriebenes Feld behauptete eine Freigabe fuer eine Version, gegen
    die nie geprueft wurde -- das Gate waere dann gruen und die Aussage des
    Pins falsch. Schlimmer als der Zustand, den es melden soll.
    """
    ergebnis = _lauf(_baum(tmp_path, "0.5.0", _pin_text("0.4.0")))

    assert "NICHT von Hand" in ergebnis.stderr, ergebnis.stderr


def test_pin_ohne_das_feld_ist_rot(tmp_path: Path):
    """Ein Pin ohne `generated_for_version` sagt nicht, wofuer er gilt.

    Fruehere Faelle im Portfolio sahen so aus: `pin_tools.py` schrieb
    `0.0.0+local` oder gar nichts, weil es die installierte Metadata las.
    """
    ohne = json.dumps({"tools": {}}, indent=2) + "\n"

    ergebnis = _lauf(_baum(tmp_path, "0.5.0", ohne))

    assert ergebnis.returncode == 1
    assert "generated_for_version" in ergebnis.stderr


def test_unlesbarer_pin_ist_rot(tmp_path: Path):
    """Kaputtes JSON darf nicht als "nichts gefunden" durchgehen.

    Ein stilles Ueberspringen waere hier dieselbe Falle wie der 403, der als
    Fund-Fehlschlag verpackt daherkommt: Die Pruefung hat nicht geantwortet,
    und das Ergebnis liest sich wie ein gruener Befund.
    """
    ergebnis = _lauf(_baum(tmp_path, "0.5.0", "{kein json"))

    assert ergebnis.returncode == 1
    assert "nicht als Pin lesbar" in ergebnis.stderr, ergebnis.stderr


def test_pin_der_kein_objekt_ist_ist_rot(tmp_path: Path):
    """Gueltiges JSON, aber kein Objekt -- `.get` gibt es darauf nicht.

    Ohne den eigenen Zweig endete das Gate hier mit einem AttributeError und
    einem Traceback. Ein Gate, das mit einem Traceback statt einer Meldung
    abbricht, wird als Werkzeugfehler gelesen und nicht als Befund.
    """
    ergebnis = _lauf(_baum(tmp_path, "0.5.0", "[]\n"))

    assert ergebnis.returncode == 1
    assert "Traceback" not in ergebnis.stderr, ergebnis.stderr
    assert "JSON-Objekt" in ergebnis.stderr, ergebnis.stderr


# ───────────── Die Nachbarpruefungen sind dabei nicht abgeraucht ───────────────


def test_badge_drift_wird_weiter_gemeldet(tmp_path: Path):
    """Regressionswache: Der neue Block steckt mitten in `main()`.

    Geprueft wird mit der generischen Meldung, nicht mit der des Pins -- die
    beiden duerfen nicht zusammenfallen, weil ihre Abhilfe verschieden ist.
    """
    baum = _baum(tmp_path, "0.5.0", _pin_text("0.5.0"))
    (baum / "README.md").write_text(
        "![Version](https://img.shields.io/badge/version-0.4.0-blue)\n", encoding="utf-8"
    )

    ergebnis = _lauf(baum)

    assert ergebnis.returncode == 1
    assert "DRIFT:" in ergebnis.stderr, ergebnis.stderr
    assert "Versions-Badge" in ergebnis.stderr, ergebnis.stderr
