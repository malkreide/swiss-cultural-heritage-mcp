#!/usr/bin/env python3
"""Hat Codex diesen Commit angesehen — und was kam dabei heraus?

WARUM ES DIESES GATE GIBT
-------------------------
Am 19.09.2026 lagen bei PR #90 fuenf und bei PR #91 vier Sekunden zwischen
«ready for review» und Merge. Codex startete beide Male NACH dem Merge (#90:
Merge 06:36:06, Start 06:36:09; #91: Merge 06:56:32, Start 06:56:34) und stand
danach in beiden Statuskommentaren unveraendert auf «Running». Die Zeile
«Codex-Review beantwortet oder behoben» im PR-Template war damit ein Haken,
den niemand haette setzen koennen.

Auto-Merge behebt das NICHT, und das ist der Grund fuer dieses Skript:
Auto-Merge wartet auf *required status checks*. Codex erzeugt keinen — gemessen
an PR #91: `get_check_runs` nennt nur die drei `test`-Jobs, und die Liste der
Commit-Statuses ist leer (`total_count: 0`). Ein Codex-Befund ist ein
Review-Objekt, ein befundloser Lauf ein gewoehnlicher Issue-Kommentar; keines
von beidem kann ein Check sein oder «approven». Damit Auto-Merge auf Codex
warten kann, muss jemand das Urteil ueberhaupt erst als Check ausgeben. Das
tut der Workflow, der dieses Skript aufruft.

VIER GRUENDE, WARUM CODEX SCHWEIGT — NUR EINER IST HARMLOS
----------------------------------------------------------
Die Einordnung unten stammt nicht aus einem Ratespiel ueber Statuscodes,
sondern aus den vier in CLAUDE.md dokumentierten Faellen:

  reviewed     Ein Review-OBJEKT zum Head-Commit. Codex hat Befunde.
  clear        Die Befundlos-Meldung («Didn't find any major issues»). Ein
               gewoehnlicher Issue-Kommentar, KEIN Review-Objekt.
  quota        «You have reached your Codex usage limits for code reviews.»
  environment  «To use Codex here, create an environment for this repo.»

`reviewed` und `clear` sind beide ein Beleg, dass geprueft wurde. Wer nur das
Review-Objekt gelten laesst, zaehlt jeden befundlosen Lauf als ungeprueft und
baut sich denselben Fehlalarm ein, nur in die andere Richtung.

`quota` und `environment` sind KEIN Beleg. Sie sehen aus wie Stille und sind
eine Absage — deshalb faerben sie das Gate rot, statt es offen zu lassen.

UND EIN FUENFTER TEXT, DEN NOCH NIEMAND GESEHEN HAT
---------------------------------------------------
Dieser Abschnitt musste in CLAUDE.md schon einmal von drei auf vier Gruende
wachsen. Ein Codex-Kommentar, der in keine der vier Schubladen passt, wird
deshalb `unknown` und WOERTLICH zitiert, statt in die naechstbeste gezwungen
zu werden. Ein Gate, das einen unbekannten Text als «kein Befund» liest, ist
schlimmer als keines.

DIE STATUSTABELLE IST DAS URTEIL — GEMESSEN, NICHT ANGENOMMEN
-------------------------------------------------------------
Codex setzt seit September 2026 eine Statustabelle als Kommentar (HTML-Marker
`codex-pull-request-review-summary`) und schreibt sie in Ort fort:

    | \U0001f4dd **Code Review** | \u2705 **Completed** <relative-time ...> | `bfe7ab7` | ... |

Die erste Fassung dieses Skripts hat sie uebersprungen und nur auf einen
eigenen Kommentar gewartet («Didn't find any major issues»). Das war falsch,
und zwar in die gefaehrliche Richtung: Gemessen am 19.09.2026 an PR #90 und
#91 lief der Review durch — `Completed` um 06:37:08 bzw. 06:57:34, je rund
60 Sekunden nach dem Merge — und Codex hinterliess WEDER ein Review-Objekt
NOCH einen eigenen Kommentar. Das Urteil stand nur in der Tabelle. Ein Gate,
das sie ueberspringt, haette jeden sauberen PR 20 Minuten blockiert und dann
rot gemeldet.

Deshalb wird die Tabelle jetzt gelesen, und zwar VOR den Einzelkommentaren:

  Completed zum Head  → geprueft. Liegt kein Review-Objekt vor, gab es keine
                        Befunde.
  Running zum Head    → laeuft noch, weiterwarten.
  anderer Status      → `unknown`, woertlich zitiert.

Gebunden wird ueber die Commit-Spalte, nicht ueber den Zeitstempel: Die
Tabelle wird fortgeschrieben, ihr `created_at` ist deshalb aelter als die
Aussage, die sie heute trifft.

Die Reihenfolge ist auch inhaltlich richtig. Am 19.09.2026 kam auf PR #92
(Draft) die Environment-Meldung, waehrend #90 und #91 am selben Morgen
regulaer geprueft wurden — die Meldung allein belegt also nicht, dass in
diesem Repo keine Reviews laufen. Sagt die Tabelle `Completed`, gilt sie;
fehlt eine Zeile zum Head, faellt die Einordnung auf die Meldungstexte
durch und wird rot.

EINE LEHRE UEBER DAS MESSEN SELBST
-----------------------------------
Zwei Abfragen der Kommentare von #90 (06:47 und 07:00 UTC) lieferten noch
`Running` mit unveraendertem `updated_at`, obwohl die Tabelle bereits um
06:37:10 auf `Completed` stand. Ein einzelner Blick auf einen
fortgeschriebenen Kommentar ist eine Momentaufnahme, keine Feststellung —
und eine zwischengespeicherte Antwort sieht genauso aus wie eine aktuelle.

Aufruf:
    python scripts/classify_codex_review.py --head-sha <sha> \
        --reviews reviews.json --comments comments.json --since <ISO-8601>
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

CODEX_LOGIN = "chatgpt-codex-connector[bot]"

# Der HTML-Marker der Statustabelle. Woertlich aus einem echten Kommentar auf
# PR #90 uebernommen, nicht nachgebaut.
STATUS_MARKER = "codex-pull-request-review-summary"

REVIEWED = "reviewed"
CLEAR = "clear"
QUOTA = "quota"
ENVIRONMENT = "environment"
UNKNOWN = "unknown"
PENDING = "pending"

#: Zustaende, die belegen, dass Codex diesen Commit angesehen hat.
PROVEN = frozenset({REVIEWED, CLEAR})

# Nur der stabile Teil der Befundlos-Meldung. Der Schlusssatz wechselt bei
# jedem Lauf («Swish!», «Delightful!», «Keep it up!»), der Satz davor nicht.
# Ohne Apostroph gematcht, weil «Didn't» je nach Zeichensatz ' oder ’ traegt.
_CLEAR_MARKERS = ("find any major issues",)
_QUOTA_MARKERS = ("reached your codex usage limits",)
_ENVIRONMENT_MARKERS = ("create an environment for this repo",)


def _codex_authored(item: dict[str, Any]) -> bool:
    user = item.get("user") or {}
    return str(user.get("login", "")) == CODEX_LOGIN


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


# Eine Commit-Spalte traegt einen abgekuerzten SHA in Backticks. Kopf- und
# Trennzeile der Tabelle fallen an dieser Pruefung heraus, ohne dass jemand
# sie zaehlen muss — «Commit» und «---» sind keine Hex-Ziffern.
_KURZ_SHA = re.compile(r"^[0-9a-f]{7,40}$")


def _statuszeilen(body: str) -> list[tuple[str, str]]:
    """(Status, Kurz-SHA) je Datenzeile der Codex-Statustabelle."""
    zeilen: list[tuple[str, str]] = []
    for roh in body.splitlines():
        zeile = roh.strip()
        if not zeile.startswith("|"):
            continue
        zellen = [z.strip() for z in zeile.strip("|").split("|")]
        if len(zellen) < 3:
            continue
        commit = zellen[2].strip("`").strip()
        if not _KURZ_SHA.match(commit):
            continue
        zeilen.append((zellen[1], commit))
    return zeilen


def classify(
    reviews: list[dict[str, Any]],
    comments: list[dict[str, Any]],
    head_sha: str,
    since: str | None = None,
) -> tuple[str, str]:
    """(state, reason) aus Reviews und Kommentaren eines PR.

    Zwei verschiedene Abfragen, und beide werden gebraucht: Das Review-Objekt
    kommt aus `pulls/{n}/reviews`, Statustabelle und Meldungstexte aus
    `issues/{n}/comments`. Wer nur eine nimmt, uebersieht den Rest.

    Reihenfolge: Review-Objekt, dann Statustabelle, dann Einzelkommentare.
    Jede Stufe bindet an den Head — das Objekt ueber `commit_id`, die Tabelle
    ueber ihre Commit-Spalte, die Kommentare ueber `since`. Ein Urteil zu
    einem frueheren Commit belegt nichts ueber den, der gemergt wird.
    """
    grenze = _parse_iso(since)
    kurz = head_sha[:7] if head_sha else ""

    for review in reviews:
        if not _codex_authored(review):
            continue
        if head_sha and str(review.get("commit_id", "")) != head_sha:
            continue
        return (
            REVIEWED,
            f"Codex-Review-Objekt zu {kurz} — Befunde liegen vor und gehoeren "
            "beantwortet oder behoben, bevor gemergt wird.",
        )

    laeuft = False
    fertig = False
    fremder_status: str | None = None
    for comment in comments:
        if not _codex_authored(comment) or STATUS_MARKER not in str(comment.get("body", "")):
            continue
        for status, commit in _statuszeilen(str(comment.get("body", ""))):
            if head_sha and not head_sha.startswith(commit):
                continue
            gesenkt = status.lower()
            if "running" in gesenkt or "queued" in gesenkt or "in progress" in gesenkt:
                laeuft = True
            elif "completed" in gesenkt:
                fertig = True
            elif fremder_status is None:
                fremder_status = " ".join(status.split())[:200]

    if fremder_status is not None:
        return (
            UNKNOWN,
            f"Die Codex-Statustabelle fuehrt zu {kurz} einen unbekannten Status. "
            f"Woertlich: «{fremder_status}» — einordnen statt durchwinken.",
        )
    if laeuft:
        return PENDING, f"Codex-Review zu {kurz} laeuft noch."
    if fertig:
        return (
            CLEAR,
            f"Codex hat den Review zu {kurz} abgeschlossen und kein Review-Objekt "
            "hinterlassen — also keine Befunde.",
        )

    unbekannt: list[str] = []
    for comment in comments:
        if not _codex_authored(comment):
            continue
        body = str(comment.get("body", ""))
        if STATUS_MARKER in body:
            continue  # oben schon gelesen; hier waere sie ein «fremder Text».
        erstellt = _parse_iso(comment.get("created_at"))
        if grenze is not None and erstellt is not None and erstellt < grenze:
            continue
        gesenkt = body.lower()
        if any(m in gesenkt for m in _CLEAR_MARKERS):
            return CLEAR, "Codex meldet keine Befunde zu diesem Commit."
        if any(m in gesenkt for m in _QUOTA_MARKERS):
            return (
                QUOTA,
                "Codex-Kontingent fuer Code-Reviews ist aufgebraucht. Das ist "
                "KEIN Freispruch: Es wurde nichts geprueft. Kontingent haengt "
                "am Konto, nicht am Repo.",
            )
        if any(m in gesenkt for m in _ENVIRONMENT_MARKERS):
            return (
                ENVIRONMENT,
                "Fuer dieses Repo fehlt eine Codex-Environment, und die "
                "Statustabelle nennt keinen Lauf zu diesem Commit. Sie wird je "
                "Repo angelegt (chatgpt.com/codex/cloud/settings/environments); "
                "eine fuers Konto genuegt nicht.",
            )
        unbekannt.append(" ".join(body.split())[:300])

    if unbekannt:
        return (
            UNKNOWN,
            "Codex hat etwas geschrieben, das in keinen der bekannten Faelle "
            f"passt. Woertlich: «{unbekannt[0]}» — einordnen und die Marker in "
            "scripts/classify_codex_review.py ergaenzen, statt es als «kein "
            "Befund» durchzuwinken.",
        )
    return PENDING, f"Noch kein Codex-Urteil zu {kurz or '?'}."


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="classify_codex_review")
    ap.add_argument("--head-sha", default="", help="Head-Commit des PR")
    ap.add_argument("--reviews", type=Path, required=True, help="JSON aus pulls/{n}/reviews")
    ap.add_argument("--comments", type=Path, required=True, help="JSON aus issues/{n}/comments")
    ap.add_argument(
        "--since",
        default=None,
        help="ISO-8601; aeltere Kommentare zaehlen nicht als Urteil zu diesem Head.",
    )
    args = ap.parse_args(argv)

    def load(path: Path) -> list[dict[str, Any]]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return data if isinstance(data, list) else []

    state, reason = classify(load(args.reviews), load(args.comments), args.head_sha, args.since)
    print(f"state={state}")
    print(f"reason={reason}")
    print(f"proven={'true' if state in PROVEN else 'false'}")

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        # Zeilenumbruch raus: Die `key=value`-Form endet an der ersten neuen
        # Zeile, und ein zitierter Fremdtext koennte sonst ein eigenes
        # `state=clear` nachschieben und das rote Gate gruen faerben.
        flat = " ".join(reason.split())
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"state={state}\n")
            fh.write(f"reason={flat}\n")
            fh.write(f"proven={'true' if state in PROVEN else 'false'}\n")
    # Immer 0: Ueber rot oder gruen entscheidet der Workflow.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
