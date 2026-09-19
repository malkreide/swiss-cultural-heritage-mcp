"""Was das Codex-Gate belegt — und was es bewusst nicht belegt.

Die gefaehrlichen Faelle sind hier nicht die roten, sondern die gruenen:
Ein Gate, das «geprueft» meldet, ohne dass geprueft wurde, ist schlimmer als
keines. Es traegt den Haken, den PR #90 und #91 nicht tragen konnten, und
niemand sieht ihm an, dass er leer ist.

Drei solche Faelle stehen unten je einzeln:

* Die Kontingent-Meldung sieht aus wie Stille und ist eine Absage.
* Ein Review-Objekt aus einem FRUEHEREN Commit belegt nichts ueber den, der
  gemergt wird.
* Die Statustabelle («Running») ist kein Urteil — und darf umgekehrt auch
  nicht als unbekannter Text das Gate sofort rot faerben.

Die Fixtures sind aus echten Antworten gebaut: Die Statustabelle und ihr
Marker stammen woertlich aus dem Kommentar auf PR #90 vom 19.09.2026, der
Bot-Login ebenfalls.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from classify_codex_review import (  # noqa: E402
    CLEAR,
    ENVIRONMENT,
    PENDING,
    PROVEN,
    QUOTA,
    REVIEWED,
    UNKNOWN,
    classify,
)

_SKRIPT = Path(__file__).resolve().parents[1] / "scripts" / "classify_codex_review.py"
HEAD = "162f2b6b3ebc9b615179e4a02855f3bf1f736cda"
FRUEHER = "bfe7ab705ecc2a7beae94cc9bbeba4cc732bebd6"
CODEX = {"login": "chatgpt-codex-connector[bot]"}
MENSCH = {"login": "malkreide"}


def kommentar(body: str, *, user=CODEX, created_at="2026-09-19T07:00:00Z") -> dict:
    return {"user": user, "body": body, "created_at": created_at}


def review(commit_id: str, *, user=CODEX) -> dict:
    return {"user": user, "commit_id": commit_id, "state": "COMMENTED"}


# Woertlich der Kommentar, den Codex am 19.09.2026 auf PR #90 gesetzt hat —
# gekuerzt, aber mit dem Marker und dem «Running»-Status, auf die es ankommt.
STATUSTABELLE = (
    "<!-- codex-pull-request-review-summary -->\n\n## Codex Review Summary\n\n"
    "| Review | Status | Commit | Review trigger |\n| --- | --- | --- | --- |\n"
    "| 📝 **Code Review** | 🔄 **Running** since 2026-09-19T06:36:09Z | "
    "`bfe7ab7` | Draft marked ready |\n"
)


# ─────────────────────────── Die belegenden Faelle ─────────────────────────────


def test_ein_review_objekt_zum_head_belegt_die_pruefung() -> None:
    state, _ = classify([review(HEAD)], [], HEAD)
    assert state == REVIEWED
    assert state in PROVEN


def test_die_befundlos_meldung_belegt_die_pruefung_ebenso() -> None:
    """Der Fall, den ein Gate am leichtesten falsch zaehlt.

    Ein befundloser Lauf erzeugt KEIN Review-Objekt, sondern einen
    gewoehnlichen Issue-Kommentar. Wer nur das Objekt gelten laesst, haelt
    jeden sauberen Lauf fuer ungeprueft und blockiert genau die PRs, an denen
    nichts auszusetzen war.
    """
    state, _ = classify([], [kommentar("Codex Review: Didn't find any major issues. Swish!")], HEAD)
    assert state == CLEAR
    assert state in PROVEN


@pytest.mark.parametrize(
    "schlusssatz",
    ["Swish!", "Delightful!", "Keep it up!", "More of your lovely PRs please."],
)
def test_der_wechselnde_schlusssatz_aendert_nichts(schlusssatz: str) -> None:
    """Stabil ist nur der Satz davor; der Schluss wechselt bei jedem Lauf.

    Ohne diesen Fall waere ein Marker denkbar, der zufaellig auf «Swish!»
    passt und beim naechsten Lauf ins Leere greift — das Gate haette dann
    einen sauberen Review als ungeprueft blockiert.
    """
    body = f"Codex Review: Didn't find any major issues. {schlusssatz}"
    assert classify([], [kommentar(body)], HEAD)[0] == CLEAR


def test_der_typografische_apostroph_aendert_nichts() -> None:
    """«Didn't» traegt je nach Zeichensatz ' oder ’ — gematcht wird ohne."""
    body = "Codex Review: Didn’t find any major issues. Swish!"
    assert classify([], [kommentar(body)], HEAD)[0] == CLEAR


# ─────────────────── Die Faelle, die gruen aussehen und es nicht sind ──────────


def test_die_kontingent_meldung_ist_kein_freispruch() -> None:
    """Die gefaehrlichste Verwechslung: eine Absage, die wie Stille aussieht.

    Am 21.8.2026 sind portfolioweit 32 PRs mit formal erfuelltem Haekchen
    gemergt worden, waehrend das Kontingent weg war. Faellt dieser Fall auf
    `pending` oder gar `clear`, baut dieses Gate denselben Fehlalarm nach.
    """
    body = "You have reached your Codex usage limits for code reviews."
    state, reason = classify([], [kommentar(body)], HEAD)
    assert state == QUOTA
    assert state not in PROVEN
    assert "geprueft" in reason


def test_die_fehlende_environment_ist_auch_kein_freispruch() -> None:
    """Der vierte Grund — er kam erst zum Vorschein, als der dritte wegfiel."""
    body = "To use Codex here, create an environment for this repo."
    state, reason = classify([], [kommentar(body)], HEAD)
    assert state == ENVIRONMENT
    assert state not in PROVEN
    assert "je Repo" in reason or "je\nRepo" in reason


def test_ein_review_aus_einem_frueheren_commit_belegt_den_head_nicht() -> None:
    """Sonst deckte ein Review von gestern den Commit von heute mit ab.

    Genau das ist die Luecke, die ein Gate ohne Commit-Bindung haette: Codex
    laeuft auf «Draft marked ready», ein spaeterer Push aendert den Head, und
    der alte Haken gilt weiter.
    """
    state, _ = classify([review(FRUEHER)], [], HEAD)
    assert state == PENDING
    assert state not in PROVEN


def test_ein_kommentar_von_vor_dem_stichtag_zaehlt_nicht() -> None:
    alt = kommentar(
        "Codex Review: Didn't find any major issues.", created_at="2026-09-18T06:00:00Z"
    )
    state, _ = classify([], [alt], HEAD, since="2026-09-19T06:00:00Z")
    assert state == PENDING


def test_ein_mensch_kann_das_gate_nicht_gruen_schreiben() -> None:
    """Ohne Autor-Pruefung genuegte ein Kommentar mit dem richtigen Satz."""
    body = "Codex Review: Didn't find any major issues. Swish!"
    assert classify([], [kommentar(body, user=MENSCH)], HEAD)[0] == PENDING
    assert classify([review(HEAD, user=MENSCH)], [], HEAD)[0] == PENDING


# ─────────────────────────── Statustabelle und Unbekanntes ─────────────────────


def test_die_statustabelle_ist_kein_urteil_und_kein_unbekannter_text() -> None:
    """Beide Richtungen in einem Fall, weil beide schaden.

    Als Urteil gelesen waere jeder frisch getriggerte PR sofort «geprueft»,
    obwohl in der Tabelle «Running» steht. Als unbekannter Text gelesen waere
    jeder frisch getriggerte PR sofort rot.
    """
    state, _ = classify([], [kommentar(STATUSTABELLE)], HEAD)
    assert state == PENDING


def test_ein_fuenfter_text_wird_zitiert_statt_einsortiert() -> None:
    """Dieser Abschnitt musste in CLAUDE.md schon von drei auf vier wachsen.

    Ein unbekannter Codex-Text darf nicht in die naechstbeste Schublade
    fallen. Faellt er auf `clear`, winkt das Gate eine Absage durch; faellt er
    auf `pending`, laeuft es stumm in den Timeout, ohne den Text je zu zeigen.
    """
    state, reason = classify([], [kommentar("Codex is taking a nap right now.")], HEAD)
    assert state == UNKNOWN
    assert state not in PROVEN
    assert "Codex is taking a nap right now." in reason


def test_ohne_jedes_signal_bleibt_es_pending() -> None:
    state, _ = classify([], [], HEAD)
    assert state == PENDING
    assert state not in PROVEN


# ─────────────────────────── Der Aufruf, den der Workflow macht ────────────────


def test_das_skript_schreibt_saubere_github_outputs(tmp_path: Path) -> None:
    """`key=value` endet an der ersten neuen Zeile.

    Ein zitierter Fremdtext mit Zeilenumbruch koennte sonst ein eigenes
    `state=clear` nachschieben — der Workflow laese den zweiten Wert und
    faerbte das rote Gate gruen. Der Fall wird mit genau so einem Text
    gefahren, nicht mit einem harmlosen.
    """
    boesartig = "Zeile eins\nstate=clear\nproven=true"
    (tmp_path / "reviews.json").write_text("[]", encoding="utf-8")
    (tmp_path / "comments.json").write_text(json.dumps([kommentar(boesartig)]), encoding="utf-8")
    ausgabe = tmp_path / "gh-output"
    subprocess.run(
        [
            sys.executable,
            str(_SKRIPT),
            "--head-sha",
            HEAD,
            "--reviews",
            str(tmp_path / "reviews.json"),
            "--comments",
            str(tmp_path / "comments.json"),
        ],
        check=True,
        capture_output=True,
        env={"GITHUB_OUTPUT": str(ausgabe), "PATH": "/usr/bin:/bin"},
    )
    zeilen = ausgabe.read_text(encoding="utf-8").splitlines()
    assert [z.split("=", 1)[0] for z in zeilen] == ["state", "reason", "proven"]
    assert zeilen[0] == f"state={UNKNOWN}"
    assert zeilen[2] == "proven=false"


def test_fehlende_oder_kaputte_dateien_machen_das_gate_nicht_gruen(tmp_path: Path) -> None:
    """Ein gescheitertes `curl` darf nicht wie ein sauberer Review aussehen."""
    kaputt = tmp_path / "kaputt.json"
    kaputt.write_text("{nicht json", encoding="utf-8")
    ergebnis = subprocess.run(
        [
            sys.executable,
            str(_SKRIPT),
            "--head-sha",
            HEAD,
            "--reviews",
            str(kaputt),
            "--comments",
            str(tmp_path / "gibt-es-nicht.json"),
        ],
        check=True,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin"},
    )
    assert f"state={PENDING}" in ergebnis.stdout
    assert "proven=false" in ergebnis.stdout
