"""Tests fuer scripts/main_ci_status.py und .github/workflows/main-rot.yml.

Das Skript entscheidet, ob zu einem CI-Lauf auf dem Standard-Branch ein Issue
auf- oder zugeht. Anlass: Am 08.11.2026 blieb `main` vier Tage rot, ohne dass
es jemand sah (PR #110 trug einen gruenen Check gegen einen Stand ohne die
Audit-Reports aus PR #111).

Zwei Faelle tragen den Grossteil: `test_ueberholter_gruener_lauf_schliesst_nicht`
-- drei PRs gingen an jenem Tag binnen dreissig Sekunden nach `main`, und die
Reihenfolge, in der ihre Laeufe enden, ist nicht garantiert -- und
`test_master_wird_erkannt`, weil ein fest eingetragenes `main` den Melder in
drei Repos des Portfolios nie anschlagen liesse.

Der Workflow selbst laesst sich hier nicht fahren. Was sich pruefen laesst,
steht im letzten Abschnitt: dass er ueberhaupt ausgeloest wird (der Name von
ci.yml), dass er keinen Branch fest eintraegt, und dass keine Payload-Werte
ungeprueft in Shell oder Skript landen.

Nur Standardbibliothek, kein Netz.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))

import main_ci_status as mcs  # noqa: E402

WORKFLOW = _ROOT / ".github" / "workflows" / "main-rot.yml"
CI = _ROOT / ".github" / "workflows" / "ci.yml"

SPITZE = "a" * 40
ALT = "b" * 40


def _lauf(**abweichend: str) -> mcs.Entscheid:
    """Ein Push-Lauf auf der Spitze von `main` -- jede Abweichung benannt."""
    werte = {
        "ausloeser": "workflow_run",
        "lauf_ereignis": "push",
        "ergebnis": "failure",
        "zweig": "main",
        "standard_zweig": "main",
        "herkunft": "malkreide/swiss-cultural-heritage-mcp",
        "repo": "malkreide/swiss-cultural-heritage-mcp",
        "kopf_sha": SPITZE,
        "spitze_sha": SPITZE,
    }
    werte.update(abweichend)
    return mcs.entscheide(**werte)


# ─────────────────────────────── Rot, gruen, nichts ────────────────────────────


@pytest.mark.parametrize("ergebnis", ["failure", "timed_out", "startup_failure"])
def test_rot_auf_der_spitze_wird_gemeldet(ergebnis):
    entscheid = _lauf(ergebnis=ergebnis)

    assert entscheid.aktion == mcs.MELDEN
    assert entscheid.label == mcs.LABEL


def test_gruen_auf_der_spitze_schliesst():
    entscheid = _lauf(ergebnis="success")

    assert entscheid.aktion == mcs.SCHLIESSEN
    assert entscheid.label == mcs.LABEL


@pytest.mark.parametrize(
    "ergebnis", ["cancelled", "skipped", "neutral", "action_required", "stale", ""]
)
def test_was_nichts_ueber_den_code_sagt_aendert_nichts(ergebnis):
    """Ein abgebrochener Lauf ist weder rot noch gruen.

    Schloesse `cancelled` ein Issue, verschwaende ein echter Befund, sobald
    jemand einen Lauf abbricht. Oeffnete es eines, gaebe jedes Abbrechen
    einen Fehlalarm.
    """
    assert _lauf(ergebnis=ergebnis).aktion == mcs.NICHTS


# ───────────────────────────────── Welcher Lauf zaehlt ──────────────────────────


def test_pull_request_lauf_zaehlt_nicht():
    """Ein roter PR ist Sache des PRs, nicht ein rotes `main`."""
    assert _lauf(lauf_ereignis="pull_request").aktion == mcs.NICHTS


def test_anderer_zweig_zaehlt_nicht():
    assert _lauf(zweig="feature/x").aktion == mcs.NICHTS


def test_lauf_aus_einem_fork_zaehlt_nicht():
    """Ein Fork kann einen Branch namens `main` haben; sein Lauf sagt nichts ueber diesen."""
    entscheid = _lauf(herkunft="jemand/swiss-cultural-heritage-mcp")

    assert entscheid.aktion == mcs.NICHTS


def test_master_wird_erkannt():
    """Der Standard-Branch kommt aus der Payload, nicht aus einem `main` im Code.

    Gegenprobe zu einem fest eingetragenen `main`: Damit schluege der Melder in
    `openlex-mcp`, `swiss-courts-mcp` und `swisstopo-mcp` nie an.
    """
    rot_auf_master = _lauf(zweig="master", standard_zweig="master")
    main_neben_master = _lauf(zweig="main", standard_zweig="master")

    assert rot_auf_master.aktion == mcs.MELDEN
    assert "master" in rot_auf_master.titel
    assert main_neben_master.aktion == mcs.NICHTS


def test_fehlender_standard_zweig_zaehlt_nicht():
    """Ohne Standard-Branch aus der Payload ist nichts zu vergleichen.

    Gegenprobe zu `zweig != standard_zweig` allein: Waeren beide leer, hielte
    der Vergleich sie fuer gleich.
    """
    assert _lauf(zweig="", standard_zweig="").aktion == mcs.NICHTS


# ─────────────────────────────── Nur die Spitze zaehlt ─────────────────────────


def test_ueberholter_gruener_lauf_schliesst_nicht():
    """Ein gruener Lauf eines aelteren Commits darf ein Issue nicht schliessen.

    Am 08.11.2026 endeten drei CI-Laeufe auf `main` in derselben Minute. Endet
    der gruene des aelteren Commits nach dem roten der Spitze, schloesse er
    ein berechtigtes Issue.
    """
    entscheid = _lauf(ergebnis="success", kopf_sha=ALT)

    assert entscheid.aktion == mcs.NICHTS
    assert "ueberholt" in entscheid.grund


def test_ueberholter_roter_lauf_meldet_nicht():
    """Die andere Richtung: ein alter roter Lauf beschreibt einen Stand, den es nicht mehr gibt."""
    assert _lauf(ergebnis="failure", kopf_sha=ALT).aktion == mcs.NICHTS


def test_unbekannte_spitze_meldet_rot_trotzdem():
    """Asymmetrie: Ein Fehlalarm kostet einen Blick, ein verschluckter Befund Tage."""
    assert _lauf(ergebnis="failure", spitze_sha="").aktion == mcs.MELDEN


def test_unbekannte_spitze_schliesst_nichts():
    """Gruen ohne Spitze kann nicht belegen, dass es den Stand im Issue betrifft."""
    assert _lauf(ergebnis="success", spitze_sha="").aktion == mcs.NICHTS


# ─────────────────────────────────── Probelauf ─────────────────────────────────


def test_probelauf_rot_meldet_mit_eigenem_label():
    entscheid = mcs.entscheide(ausloeser="workflow_dispatch", probe="rot", standard_zweig="main")

    assert entscheid.aktion == mcs.MELDEN
    assert entscheid.label == mcs.PROBE_LABEL
    assert entscheid.titel.startswith("[Probe]")


def test_probelauf_gruen_schliesst_nur_probe_issues():
    entscheid = mcs.entscheide(ausloeser="workflow_dispatch", probe="gruen", standard_zweig="main")

    assert entscheid.aktion == mcs.SCHLIESSEN
    assert entscheid.label == mcs.PROBE_LABEL


def test_probe_label_ist_nicht_das_echte():
    """Sonst schloesse ein gruener Probelauf ein echtes `main-rot`-Issue."""
    assert mcs.PROBE_LABEL != mcs.LABEL


def test_unbekannter_probewert_tut_nichts():
    assert mcs.entscheide(ausloeser="workflow_dispatch", probe="lila").aktion == mcs.NICHTS


def test_unbekannter_ausloeser_tut_nichts():
    assert _lauf(ausloeser="schedule").aktion == mcs.NICHTS


# ──────────────────────────────── Ausgabe an GitHub ────────────────────────────


def _env(tmp_path: Path, **werte: str) -> dict[str, str]:
    basis = {
        "AUSLOESER": "workflow_run",
        "LAUF_EREIGNIS": "push",
        "ERGEBNIS": "failure",
        "ZWEIG": "main",
        "STANDARD_ZWEIG": "main",
        "HERKUNFT": "o/r",
        "REPO": "o/r",
        "KOPF_SHA": SPITZE,
        "SPITZE_SHA": SPITZE,
        "GITHUB_OUTPUT": str(tmp_path / "output"),
    }
    basis.update(werte)
    return basis


def _outputs(tmp_path: Path) -> list[tuple[str, str]]:
    zeilen = (tmp_path / "output").read_text(encoding="utf-8").splitlines()
    return [tuple(z.split("=", 1)) for z in zeilen]  # type: ignore[misc]


def test_main_schreibt_die_vier_outputs(tmp_path: Path):
    assert mcs.main(_env(tmp_path)) == 0

    outputs = dict(_outputs(tmp_path))
    assert outputs["aktion"] == mcs.MELDEN
    assert outputs["label"] == mcs.LABEL
    assert outputs["titel"] == "CI auf main ist rot"
    assert outputs["grund"]


def test_zeilenumbruch_kann_keine_aktion_nachschieben(tmp_path: Path):
    """Ein Wert aus der Payload darf kein zweites `aktion=` erzeugen.

    Der Zweigname geht in den Titel. Mit Zeilenumbruch und ohne Glaetten
    laese der Runner `aktion=schliessen` als eigenes Output -- und ein roter
    Lauf schloesse das Issue.
    """
    env = _env(tmp_path, ZWEIG="x\naktion=schliessen", STANDARD_ZWEIG="x\naktion=schliessen")

    mcs.main(env)

    aktionen = [wert for name, wert in _outputs(tmp_path) if name == "aktion"]
    assert len(aktionen) == 1, f"mehr als ein aktion-Output: {aktionen}"


def test_main_endet_immer_mit_null(tmp_path: Path):
    """Ueber die Aktion entscheidet die Ausgabe, nicht der Prozessstatus."""
    assert mcs.main(_env(tmp_path, AUSLOESER="", ERGEBNIS="")) == 0


# ───────────────────────────── Der Workflow drumherum ──────────────────────────


def _workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_workflow_haengt_am_namen_von_ci():
    """`workflow_run` verweist per Name. Stimmt er nicht, feuert der Melder nie.

    Das ist der stillste moegliche Ausfall: kein Fehler, kein Lauf, und ein
    rotes `main` sieht aus wie ein gruenes. Eine Umbenennung von ci.yml faellt
    hier auf.
    """
    ci_name = re.search(r"^name:\s*(.+?)\s*$", CI.read_text(encoding="utf-8"), re.MULTILINE)
    gemeint = re.search(r"workflows:\s*\[\s*\"([^\"]+)\"\s*\]", _workflow())

    assert ci_name and gemeint, "Name von ci.yml oder Verweis im Melder nicht gefunden"
    assert gemeint.group(1) == ci_name.group(1).strip("\"'")


def test_workflow_traegt_keinen_branch_fest_ein():
    """Der Standard-Branch kommt aus der Payload; ein `branches:`-Filter umginge das."""
    on_block = _workflow().split("\npermissions:", 1)[0]

    assert not re.search(r"^\s*branches:", on_block, re.MULTILINE)
    assert "github.event.repository.default_branch" in _workflow()


def test_workflow_reicht_payload_nicht_per_ausdruck_ins_skript():
    """Im JavaScript des `github-script`-Schritts steht kein `${{ }}`.

    Ein Ausdruck dort wird vor dem Start woertlich in den Quelltext
    eingesetzt; ein Commit-Titel mit Backtick oder Anfuehrungszeichen liefe
    dann als Code. Werte gehen ueber `env:` und `process.env` oder
    `context.payload` hinein.
    """
    text = _workflow()
    skript = text.split("script: |", 1)
    assert len(skript) == 2, "Kein github-script-Block gefunden -- der Test misst nichts"

    assert "${{" not in skript[1]


def test_workflow_ruft_keine_shell_mit_payload_ausdruecken_auf():
    """In `run:`-Zeilen kein `${{ github.event... }}` -- nur ueber `env:`."""
    run_zeilen = [z for z in _workflow().splitlines() if z.strip().startswith(("run:", "sha="))]

    assert run_zeilen, "Keine run:-Zeile gefunden -- der Test misst nichts"
    for zeile in run_zeilen:
        assert "${{" not in zeile, zeile


def test_workflow_schreibt_nur_issues():
    """Schreibrecht nur dort, wo es gebraucht wird."""
    block = _workflow().split("\npermissions:", 1)[1].split("\n\n", 1)[0]
    rechte = dict(re.findall(r"^\s+([\w-]+):\s*(\w+)\s*$", block, re.MULTILINE))

    assert rechte == {"contents": "read", "issues": "write", "actions": "read"}
