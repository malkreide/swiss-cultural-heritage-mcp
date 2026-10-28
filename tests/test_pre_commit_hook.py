"""Der pre-commit-Hook `.githooks/pre-commit` und die Pruefung, die er faehrt.

Der Hook faehrt `scripts/check_version_sync.py` gegen den **Index**, nicht
gegen den Arbeitsbaum. Das ist seine eigentliche Zusicherung, und sie ist die
einzige, die ein Test leicht uebersieht: Ein Hook, der die Dateien im
Arbeitsbaum liest, laesst genau den Commit durch, um den es geht.

Nachgemessen am 28.10.2026 mit einer Arbeitsbaum-Fassung des Hooks: Von den
Zusicherungen dieser Datei fiel genau eine,
`test_fix_nur_im_arbeitsbaum_rettet_den_commit_nicht`. Alle Aussagen ueber
Ablehnung, Meldungstext, `--no-verify` und `git commit -a` blieben gruen. Wer
diesen einen Test fuer umstaendlich haelt und streicht, hat danach eine Suite,
die den Unterschied nicht mehr sieht.

Getestet wird darum gegen echte Wegwerf-Repos mit echtem `git commit`, nicht
gegen ein Mock. Dieselbe Begruendung wie in `test_session_start_hook.py`: Ein
Mock bestaetigte die Annahme des Autors darueber, wann git den Index
aktualisiert -- und genau die war hier zu pruefen.

Das Gate im Wegwerf-Repo ist eine **Kopie der echten Datei**, keine
handgeschriebene Nachbildung. Ein Stub kodierte die Annahme des Autors
darueber, was das Gate prueft, und koennte sie nicht widerlegen; im Portfolio
ist genau das schon einmal gruen geblieben. Dass die Kopie im Minimal-Repo nur
den Tool-Pin bemaengeln kann (kein `server.json`, keine READMEs, kein `src/`),
ist Absicht: So haengt die Messung an der neuen Zusicherung und nicht an
Nachbarpruefungen.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
HOOK_DIR = _ROOT / ".githooks"
HOOK = HOOK_DIR / "pre-commit"
GATE = _ROOT / "scripts" / "check_version_sync.py"

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None or shutil.which("bash") is None or shutil.which("tar") is None,
    reason="Hook-Tests brauchen git, bash und tar",
)


def _git_env(home: Path) -> dict[str, str]:
    """git-Umgebung ohne Benutzer- und Systemkonfiguration.

    Ohne diese Isolation entscheidet die Konfiguration der ausfuehrenden
    Maschine ueber `init.defaultBranch` -- und, schlimmer, ein global
    gesetztes `core.hooksPath` wuerde die Zuweisung hier ueberschreiben.
    """
    env = dict(os.environ)
    env.update(
        {
            "HOME": str(home),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": str(home / "gitconfig-leer"),
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
        }
    )
    return env


def _git(*args: str, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """git-Aufruf ohne `check=True` -- der Commit darf scheitern, das ist der Punkt."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _git_ok(*args: str, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    ergebnis = _git(*args, cwd=cwd, env=env)
    assert ergebnis.returncode == 0, f"git {args} scheiterte: {ergebnis.stderr}"
    return ergebnis


def _pyproject(version: str) -> str:
    return f'[project]\nname = "wegwerf-paket"\nversion = "{version}"\n'


def _pin(version: str) -> str:
    return (
        json.dumps(
            {
                "generated_for_version": version,
                "tool_count": 1,
                "manifest_sha256": "0" * 64,
                "tools": {"ein_tool": "1" * 64},
            },
            indent=2,
        )
        + "\n"
    )


@pytest.fixture
def repo(tmp_path: Path):
    """Ein Repo mit Gate, Pin und installiertem Hook -- beides auf 0.4.0, gruen.

    Rueckgabe: `(pfad, env)`. Der Hook wird ueber `core.hooksPath` auf das
    echte `.githooks/` dieses Repos gezeigt; getestet wird also die
    ausgelieferte Datei und nicht eine Kopie, die altern koennte.
    """
    env = _git_env(tmp_path)
    pfad = tmp_path / "repo"
    (pfad / "scripts").mkdir(parents=True)
    (pfad / "audits" / "tool-pins").mkdir(parents=True)

    shutil.copy2(GATE, pfad / "scripts" / "check_version_sync.py")
    (pfad / "pyproject.toml").write_text(_pyproject("0.4.0"), encoding="utf-8")
    (pfad / "audits" / "tool-pins" / "current.json").write_text(_pin("0.4.0"), encoding="utf-8")

    _git_ok("init", "-b", "main", ".", cwd=pfad, env=env)
    _git_ok("config", "core.hooksPath", str(HOOK_DIR), cwd=pfad, env=env)
    _git_ok("add", "-A", cwd=pfad, env=env)
    _git_ok("commit", "-m", "Saat", cwd=pfad, env=env)
    return pfad, env


def _bump(pfad: Path, version: str) -> None:
    (pfad / "pyproject.toml").write_text(_pyproject(version), encoding="utf-8")


def _pin_schreiben(pfad: Path, version: str) -> None:
    (pfad / "audits" / "tool-pins" / "current.json").write_text(_pin(version), encoding="utf-8")


# ───────────────────────────── Der Hook am Commit ──────────────────────────────


def test_saat_commit_laeuft_durch(repo):
    """Positivkontrolle. Ohne sie messen die Tests unten ihre eigene Stille.

    Scheiterte die Fixture schon am ersten Commit -- falscher Hook-Pfad,
    kaputtes Gate, fehlendes python --, waere jedes "Commit abgelehnt" unten
    richtig und bedeutungslos.
    """
    pfad, env = repo
    assert _git("log", "--oneline", cwd=pfad, env=env).stdout.strip().endswith("Saat")


def test_stimmiger_bump_wird_committet(repo):
    """Version und Pin gemeinsam gehoben: der Hook haelt nicht auf."""
    pfad, env = repo
    _bump(pfad, "0.5.0")
    _pin_schreiben(pfad, "0.5.0")
    _git_ok("add", "-A", cwd=pfad, env=env)

    ergebnis = _git("commit", "-m", "Bump auf 0.5.0", cwd=pfad, env=env)

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert "Versions-Sync" not in ergebnis.stdout + ergebnis.stderr, (
        "Bei Erfolg soll der Hook schweigen -- eine Zeile bei jedem Commit "
        "wird nach der dritten Woche nicht mehr gelesen."
    )


def test_bump_ohne_pin_wird_abgelehnt(repo):
    """Der Fall, um den es geht: Version gehoben, Pin stehen gelassen."""
    pfad, env = repo
    _bump(pfad, "0.5.0")
    _git_ok("add", "-A", cwd=pfad, env=env)

    ergebnis = _git("commit", "-m", "Bump auf 0.5.0", cwd=pfad, env=env)

    assert ergebnis.returncode != 0, "Der Commit haette abgelehnt werden muessen"
    assert _git("log", "--oneline", cwd=pfad, env=env).stdout.count("\n") == 1, (
        "Trotz Ablehnung ist ein Commit entstanden"
    )
    meldung = ergebnis.stderr
    assert "0.4.0" in meldung and "0.5.0" in meldung, meldung
    assert "scripts/pin_tools.py" in meldung, (
        "Die Meldung muss den Handgriff nennen, nicht nur den Widerspruch"
    )
    assert "--no-verify" in meldung, "Der Ausweg gehoert in die Meldung"


def test_meldung_raet_nicht_zum_haendischen_nachtragen(repo):
    """Die Abhilfe ist regenerieren, nicht das Feld ueberschreiben.

    Ein von Hand gesetztes `generated_for_version` behauptete eine Freigabe
    fuer eine Version, gegen die die Hashes daneben nie geprueft wurden. Der
    Hook darf also nicht in denselben Rat laufen wie die generische
    Drift-Meldung des Gates ("Alle Stellen im selben Commit bumpen").
    """
    pfad, env = repo
    _bump(pfad, "0.5.0")
    _git_ok("add", "-A", cwd=pfad, env=env)

    meldung = _git("commit", "-m", "Bump", cwd=pfad, env=env).stderr

    assert "NICHT von Hand" in meldung, meldung
    assert "Alle Stellen im selben Commit bumpen" not in meldung, (
        "Das ist der Rat fuer server.json und die Badges, nicht fuer den Pin"
    )


def test_fix_nur_im_arbeitsbaum_rettet_den_commit_nicht(repo):
    """DIE Zusicherung: geprueft wird der Index, nicht der Arbeitsbaum.

    Hier liegt der regenerierte Pin im Arbeitsbaum, ist aber nicht gestaged --
    der haeufigste Weg, diesen Fehler trotz Regenerieren zu committen. Ein
    Hook, der die Dateien liest, wie sie auf der Platte liegen, sieht einen
    stimmigen Stand und laesst den kaputten Commit durch.

    Nachgemessen am 28.10.2026 in einem Wegwerf-Repo: steht `A` im Index und
    `B` im Arbeitsbaum, legt `git commit` `A` ab. Dieser Test ist die
    Gegenprobe zu einem Arbeitsbaum-Hook -- und war im Lauf gegen eine solche
    Fassung der einzige, der fiel.
    """
    pfad, env = repo
    _bump(pfad, "0.5.0")
    _git_ok("add", "pyproject.toml", cwd=pfad, env=env)
    # Nach dem `add`: der Fix existiert, aber nur auf der Platte.
    _pin_schreiben(pfad, "0.5.0")

    ergebnis = _git("commit", "-m", "Bump auf 0.5.0", cwd=pfad, env=env)

    assert ergebnis.returncode != 0, (
        "Der Hook hat den Arbeitsbaum geprueft statt den Index -- der "
        "abgelegte Commit haette den Pin auf 0.4.0 getragen"
    )
    assert "0.4.0" in ergebnis.stderr


def test_commit_a_prueft_den_aktualisierten_index(repo):
    """`git commit -a` staged vor dem Hook -- der Index ist auch dort richtig.

    Gegenprobe zur naheliegenden Sorge, der Index sei bei `-a` noch der alte
    und der Hook melde deshalb einen Widerspruch, den der Commit nicht hat:
    Hier ist der Pin im Arbeitsbaum mitgehoben, aber nichts gestaged. Der
    Commit muss durchgehen.
    """
    pfad, env = repo
    _bump(pfad, "0.5.0")
    _pin_schreiben(pfad, "0.5.0")

    ergebnis = _git("commit", "-a", "-m", "Bump auf 0.5.0", cwd=pfad, env=env)

    assert ergebnis.returncode == 0, ergebnis.stderr


def test_commit_a_faengt_den_unvollstaendigen_bump(repo):
    """Dieselbe Mechanik in der anderen Richtung -- sonst zeigt der Test oben nur,
    dass bei `-a` nie etwas faellt."""
    pfad, env = repo
    _bump(pfad, "0.5.0")

    ergebnis = _git("commit", "-a", "-m", "Bump auf 0.5.0", cwd=pfad, env=env)

    assert ergebnis.returncode != 0, ergebnis.stdout + ergebnis.stderr


# ──────────────────────────────── Die Auswege ──────────────────────────────────


def test_no_verify_geht_durch(repo):
    """Der Ausweg muss offen sein -- ein Hook ohne Ausweg wird deinstalliert."""
    pfad, env = repo
    _bump(pfad, "0.5.0")
    _git_ok("add", "-A", cwd=pfad, env=env)

    ergebnis = _git("commit", "--no-verify", "-m", "Bump", cwd=pfad, env=env)

    assert ergebnis.returncode == 0, ergebnis.stderr


def test_abschalter_macht_den_hook_stumm(repo):
    pfad, env = repo
    _bump(pfad, "0.5.0")
    _git_ok("add", "-A", cwd=pfad, env=env)
    env = dict(env, SKIP_VERSION_SYNC_HOOK="1")

    ergebnis = _git("commit", "-m", "Bump", cwd=pfad, env=env)

    assert ergebnis.returncode == 0, ergebnis.stderr


# ──────── Nicht messbar heisst durchlassen -- aber nicht stillschweigend ───────


def test_fehlendes_gate_blockiert_nicht_und_sagt_es(repo):
    """Der Commit, der das Gate selbst loescht, darf nicht an ihm scheitern.

    Durchlassen ja, stillschweigend nein: Nicht geprueft und niemand weiss es,
    waere die schlechtere Haelfte beider Welten.
    """
    pfad, env = repo
    _bump(pfad, "0.5.0")
    (pfad / "scripts" / "check_version_sync.py").unlink()
    _git_ok("add", "-A", cwd=pfad, env=env)

    ergebnis = _git("commit", "-m", "Gate entfernen", cwd=pfad, env=env)

    assert ergebnis.returncode == 0, ergebnis.stderr
    assert "nicht geprueft" in ergebnis.stderr, ergebnis.stderr


def test_hook_ist_ausfuehrbar():
    """Ohne Ausfuehrungsrecht ueberspringt git den Hook -- lautlos.

    Das ist der Ausfall, der am leichtesten unbemerkt bleibt: Alles ist da,
    alles ist versioniert, und geprueft wird nichts.
    """
    assert os.access(HOOK, os.X_OK), "`chmod +x .githooks/pre-commit` fehlt"


def test_ausfuehrungsrecht_steht_auch_im_index():
    """Das Recht muss in git stehen, nicht nur auf dieser Platte.

    `os.access` oben prueft die Arbeitskopie. Ein Hook, der im Repo ohne
    Modus 100755 liegt, kommt beim naechsten Klon ohne Ausfuehrungsrecht an
    und wird dort lautlos uebersprungen.
    """
    ruf = ["git", "-C", str(_ROOT), "ls-files", "-s", "--", ".githooks/pre-commit"]
    zeile = subprocess.run(ruf, capture_output=True, text=True, check=True).stdout
    assert zeile.startswith("100755 "), f"Modus im Index ist nicht 100755: {zeile!r}"
