"""Der SessionStart-Hook `.claude/hooks/session-start.sh` gegen echte Repos.

Der Hook meldet beim Sessionstart den Rueckstand auf origin/<Standard-Branch>.
Seine wichtigste Zusicherung ist nicht die Zahl, sondern dass er die Session
**nie** blockiert: Exit 0 in jedem Stoerfall, Zeitlimit auf jeden Netzaufruf.

Getestet wird darum gegen echte Wegwerf-Repos mit lokalen ``file://``-Remotes,
nicht gegen ein Mock von ``git``. Ein Mock koennte genau die Annahme
bestaetigen, die hier zu widerlegen waere -- etwa dass ``ls-remote --symref``
das Format hat, das der Autor im Kopf hatte. Kein Test hier braucht Netz.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "session-start.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None or shutil.which("bash") is None,
    reason="Hook-Tests brauchen git und bash",
)


def _git_env(home: Path) -> dict[str, str]:
    """git-Umgebung ohne Benutzer- und Systemkonfiguration.

    Ohne diese Isolation entscheidet die Konfiguration der ausfuehrenden
    Maschine ueber ``init.defaultBranch`` -- und ein Test, der auf einem
    Laptop mit ``defaultBranch = master`` anders laeuft als in der CI, sagt
    ueber den Hook nichts aus.
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


def _git(*args: str, cwd: Path, env: dict[str, str]) -> str:
    ergebnis = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    return ergebnis.stdout.strip()


def _commit(repo: Path, env: dict[str, str], text: str) -> None:
    (repo / "datei.txt").write_text(text + "\n", encoding="utf-8")
    _git("add", "datei.txt", cwd=repo, env=env)
    _git("commit", "-m", text, cwd=repo, env=env)


@pytest.fixture
def werkstatt(tmp_path: Path):
    """Baut Upstream + Klon und gibt einen Helfer zum Nachschieben von Commits.

    Rueckgabe: ``(klon, env, voraus)`` -- ``voraus(n)`` legt n weitere Commits
    auf den Upstream-Standard-Branch, ohne den Klon anzufassen.
    """
    env = _git_env(tmp_path)

    def bauen(branch: str = "main"):
        upstream = tmp_path / f"upstream-{branch}.git"
        arbeit = tmp_path / f"saat-{branch}"
        klon = tmp_path / f"klon-{branch}"

        _git("init", "--bare", "-b", branch, str(upstream), cwd=tmp_path, env=env)
        _git("clone", upstream.as_uri(), str(arbeit), cwd=tmp_path, env=env)
        _commit(arbeit, env, "erster Commit")
        _git("push", "-u", "origin", branch, cwd=arbeit, env=env)
        _git("clone", upstream.as_uri(), str(klon), cwd=tmp_path, env=env)

        def voraus(anzahl: int) -> None:
            for i in range(anzahl):
                _commit(arbeit, env, f"nachgeschoben {i}")
            _git("push", "origin", branch, cwd=arbeit, env=env)

        return klon, voraus

    return bauen, env


def hook_laufen_lassen(
    projekt: Path,
    env: dict[str, str],
    **zusatz: str,
) -> subprocess.CompletedProcess[str]:
    lauf_env = dict(env)
    lauf_env["CLAUDE_PROJECT_DIR"] = str(projekt)
    lauf_env.update(zusatz)
    return subprocess.run(
        ["bash", str(HOOK)],
        cwd=projekt,
        env=lauf_env,
        capture_output=True,
        text=True,
        timeout=120,
    )


# --------------------------------------------------------------------------
# Die Meldung selbst
# --------------------------------------------------------------------------


def test_rueckstand_wird_mit_zahl_und_branch_gemeldet(werkstatt):
    bauen, env = werkstatt
    klon, voraus = bauen("main")
    voraus(3)

    ergebnis = hook_laufen_lassen(klon, env)

    assert ergebnis.returncode == 0
    assert "3 Commits" in ergebnis.stdout
    assert "origin/main" in ergebnis.stdout


def test_ein_einzelner_commit_wird_im_singular_gemeldet(werkstatt):
    bauen, env = werkstatt
    klon, voraus = bauen("main")
    voraus(1)

    ergebnis = hook_laufen_lassen(klon, env)

    assert "1 Commit " in ergebnis.stdout
    assert "1 Commits" not in ergebnis.stdout


def test_aktueller_klon_schweigt(werkstatt):
    """Bei 0 keine Ausgabe -- eine Meldung, die immer kommt, wird nicht gelesen."""
    bauen, env = werkstatt
    klon, _ = bauen("main")

    ergebnis = hook_laufen_lassen(klon, env)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


def test_eigene_commits_voraus_zaehlen_nicht_als_rueckstand(werkstatt):
    """``HEAD..spitze`` zaehlt nur, was fehlt.

    Gegenprobe zu einem ``rev-list --count spitze...HEAD`` (symmetrisch), das
    hier faelschlich melden wuerde.
    """
    bauen, env = werkstatt
    klon, _ = bauen("main")
    _commit(klon, env, "lokale Arbeit")

    ergebnis = hook_laufen_lassen(klon, env)

    assert ergebnis.stdout == ""


def test_master_als_standard_branch_wird_erkannt(werkstatt):
    """Der Standard-Branch wird ermittelt, nicht als ``main`` angenommen.

    Drei Server im Portfolio heissen ihn ``master``; die Annahme ``main``
    hat dort schon einen Branch 15 Commits alt werden lassen.
    """
    bauen, env = werkstatt
    klon, voraus = bauen("master")
    voraus(2)

    ergebnis = hook_laufen_lassen(klon, env)

    assert ergebnis.returncode == 0
    assert "2 Commits" in ergebnis.stdout
    assert "origin/master" in ergebnis.stdout
    assert "origin/main" not in ergebnis.stdout


def test_abschalter_macht_den_hook_stumm(werkstatt):
    bauen, env = werkstatt
    klon, voraus = bauen("main")
    voraus(4)

    ergebnis = hook_laufen_lassen(klon, env, CLAUDE_SKIP_FRESHNESS_CHECK="1")

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


def test_detached_head_wird_gezaehlt_statt_zu_scheitern(werkstatt):
    """Detached HEAD ist kein Stoerfall, sondern ein zaehlbarer Zustand."""
    bauen, env = werkstatt
    klon, voraus = bauen("main")
    voraus(2)
    _git("fetch", "origin", "main", cwd=klon, env=env)
    _git("checkout", "--detach", "HEAD", cwd=klon, env=env)

    ergebnis = hook_laufen_lassen(klon, env)

    assert ergebnis.returncode == 0
    assert "2 Commits" in ergebnis.stdout


# --------------------------------------------------------------------------
# Blockiert nie: jeder Stoerfall endet mit Exit 0 und leerer Ausgabe
# --------------------------------------------------------------------------


def test_kein_git_repo_geht_still_durch(tmp_path: Path):
    env = _git_env(tmp_path)
    einfaches_verzeichnis = tmp_path / "kein-repo"
    einfaches_verzeichnis.mkdir()

    ergebnis = hook_laufen_lassen(einfaches_verzeichnis, env)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


def test_repo_ohne_remote_geht_still_durch(tmp_path: Path):
    env = _git_env(tmp_path)
    repo = tmp_path / "ohne-remote"
    repo.mkdir()
    _git("init", "-b", "main", ".", cwd=repo, env=env)
    _commit(repo, env, "einziger Commit")

    ergebnis = hook_laufen_lassen(repo, env)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


def test_leeres_repo_ohne_commit_geht_still_durch(werkstatt, tmp_path: Path):
    """HEAD zeigt auf einen Branch ohne Commit -- ``rev-list`` haette keinen Start.

    Das Remote ist hier bewusst **erreichbar**: sonst scheiterte schon der
    ``ls-remote`` und der Test wuerde den unborn-HEAD-Pfad nie betreten.
    """
    bauen, env = werkstatt
    bauen("main")  # nur fuer den Upstream
    repo = tmp_path / "leer"
    repo.mkdir()
    _git("init", "-b", "main", ".", cwd=repo, env=env)
    _git(
        "remote",
        "add",
        "origin",
        (tmp_path / "upstream-main.git").as_uri(),
        cwd=repo,
        env=env,
    )

    ergebnis = hook_laufen_lassen(repo, env)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


def test_verschwundenes_remote_geht_still_durch(werkstatt, tmp_path: Path):
    """Der Klon steht, das Remote nicht mehr -- kein Netz, kein Abbruch."""
    bauen, env = werkstatt
    klon, voraus = bauen("main")
    voraus(2)
    shutil.rmtree(tmp_path / "upstream-main.git")

    ergebnis = hook_laufen_lassen(klon, env)

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""


def test_haengendes_netz_wird_nach_wenigen_sekunden_abgebrochen(werkstatt):
    """Zeitlimit auf den Netzaufruf, damit der Sessionstart nicht haengt.

    ``GIT_SSH_COMMAND`` wird auf ein 20-Sekunden-``sleep`` gesetzt; der Hook
    uebernimmt eine bereits gesetzte Variable, also laeuft ``ls-remote`` genau
    in das simulierte haengende Netz. Ohne Zeitlimit dauert der Lauf ein
    Vielfaches davon -- nachgemessen 50 s gegen 2 s mit Limit.
    """
    bauen, env = werkstatt
    klon, _ = bauen("main")
    _git(
        "remote",
        "set-url",
        "origin",
        "ssh://git@example.invalid/repo.git",
        cwd=klon,
        env=env,
    )

    beginn = time.monotonic()
    ergebnis = hook_laufen_lassen(
        klon,
        env,
        GIT_SSH_COMMAND="sh -c 'sleep 20'",
        CLAUDE_FRESHNESS_TIMEOUT="2",
    )
    dauer = time.monotonic() - beginn

    assert ergebnis.returncode == 0
    assert ergebnis.stdout == ""
    assert dauer < 12, f"Hook lief {dauer:.1f}s -- das Zeitlimit greift nicht"


def test_kaputtes_remote_gibt_nichts_auf_stderr_aus(werkstatt, tmp_path: Path):
    """git-Geschwaetz gehoert nicht in den Sessionstart."""
    bauen, env = werkstatt
    klon, _ = bauen("main")
    shutil.rmtree(tmp_path / "upstream-main.git")

    ergebnis = hook_laufen_lassen(klon, env)

    assert ergebnis.stderr == ""


# --------------------------------------------------------------------------
# Die Nicht-Blockade steht im Skript selbst -- und soll dort bleiben
# --------------------------------------------------------------------------


def test_skript_ist_ausfuehrbar_und_ohne_set_e():
    """``set -e`` waere hier keine Sorgfalt, sondern die Umkehr der Zusicherung.

    Unter ``set -e`` beendet der erste fehlschlagende git-Aufruf das Skript
    mit dessen Exit-Code; ein Exit != 0 aus einem SessionStart-Hook wird als
    Fehler gemeldet statt still verworfen. Dieser Test faengt ein spaeteres
    "aufraeumendes" Ergaenzen der Zeile.
    """
    quelltext = HOOK.read_text(encoding="utf-8")

    assert os.access(HOOK, os.X_OK), "Hook ist nicht ausfuehrbar"
    for verboten in ("set -e", "set -u", "set -o pipefail"):
        assert f"\n{verboten}" not in quelltext, f"`{verboten}` macht den Hook blockierend"
    assert quelltext.rstrip().endswith("exit 0"), "Letzte Zeile muss `exit 0` sein"


def test_hook_ist_in_settings_json_registriert():
    import json

    settings = HOOK.resolve().parents[1] / "settings.json"
    eintraege = json.loads(settings.read_text(encoding="utf-8"))["hooks"]["SessionStart"]
    befehle = [h["command"] for gruppe in eintraege for h in gruppe["hooks"]]

    assert any(befehl.endswith("/.claude/hooks/session-start.sh") for befehl in befehle)
