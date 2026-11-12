"""Die Gate-Skripte laufen auch auf einer Konsole, die kein UTF-8 spricht.

Befund vom 8.11.2026, Windows 11, `sys.stdout.encoding == "cp1252"`:
`scripts/check_version_sync.py` fand keine Abweichung und endete trotzdem mit
Exit 1 -- ein `UnicodeEncodeError` an dem `→` in der *Erfolgsmeldung*. Das Gate
war damit auf Windows immer rot, und der pre-commit-Hook, der es aufruft,
haette jeden Commit abgelehnt.

Nur `→` (U+2192) bricht: `—`, `…` und Umlaute kennt cp1252. `pin_tools.py`
sah im Terminal verdaechtig aus (`—` als `�`), laeuft aber nachgemessen
durch -- ein Test dafuer bliebe ohne jede Reparatur gruen und steht deshalb
nicht hier.

Die CI hat das nie gesehen: Linux-Runner sprechen UTF-8. Deshalb erzwingt
dieser Test die Kodierung per `PYTHONIOENCODING`, statt sich auf die Plattform
zu verlassen -- so faellt der Rueckfall auch auf Linux auf. cp1252 ist gewaehlt,
weil es die gemessene Konsole ist.

Geprueft werden beide Ausgabewege des Gates (gruen auf stdout, rot auf stderr),
weil die Meldungen verschieden sind und jeder fuer sich brechen kann.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
GATE = _ROOT / "scripts" / "check_version_sync.py"

_CP1252 = {**os.environ, "PYTHONIOENCODING": "cp1252"}


def _baum(tmp_path: Path, version: str, pin_version: str, badge: str) -> Path:
    """Minimal-Repo, in dem jede Ausgabezeile des Gates vorkommt.

    Mit Pin *und* Badge enthaelt die Meldung beide `->`-Bezeichnungen, die
    vorher `→` trugen. Fehlte eine, bliebe ihr Zeichen ungeprueft.
    """
    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(GATE, tmp_path / "scripts" / "check_version_sync.py")
    projekt = f'[project]\nname = "wegwerf-paket"\nversion = "{version}"\n'
    (tmp_path / "pyproject.toml").write_text(projekt, encoding="utf-8")
    pin = tmp_path / "audits" / "tool-pins" / "current.json"
    pin.parent.mkdir(parents=True)
    inhalt = json.dumps({"generated_for_version": pin_version, "tools": {}})
    pin.write_text(inhalt, encoding="utf-8")
    zeile = f"![Version](https://img.shields.io/badge/version-{badge}-blue)\n"
    (tmp_path / "README.md").write_text(zeile, encoding="utf-8")
    return tmp_path


def _gate(baum: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(baum / "scripts" / "check_version_sync.py")],
        capture_output=True,
        encoding="cp1252",
        env=_CP1252,
        timeout=120,
    )


def test_gruener_lauf_bricht_nicht_an_der_erfolgsmeldung(tmp_path: Path):
    ergebnis = _gate(_baum(tmp_path, "0.7.0", "0.7.0", "0.7.0"))

    assert "Traceback" not in ergebnis.stderr, ergebnis.stderr
    assert ergebnis.returncode == 0, ergebnis.stderr
    assert "Versions-Sync OK" in ergebnis.stdout, ergebnis.stdout


def test_roter_lauf_meldet_den_befund_statt_eines_tracebacks(tmp_path: Path):
    """Badge-Drift: der rote Weg, dessen Zeile `→` trug.

    Nicht die Pin-Drift: Deren Meldung enthielt nie ein Zeichen ausserhalb von
    cp1252 und waere auch mit der alten Fassung gruen -- als Test wertlos. Beide
    zugleich geht nicht: Das Gate bricht nach dem ersten Drift-Block ab.
    """
    ergebnis = _gate(_baum(tmp_path, "0.7.0", "0.7.0", "0.6.0"))

    assert "Traceback" not in ergebnis.stderr, ergebnis.stderr
    assert ergebnis.returncode == 1
    assert "README.md -> Versions-Badge = '0.6.0'" in ergebnis.stderr, ergebnis.stderr
