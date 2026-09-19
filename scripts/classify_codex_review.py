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

DER STATUS-KOMMENTAR IST KEIN URTEIL
------------------------------------
Codex setzt seit September 2026 zusaetzlich eine Statustabelle als Kommentar
(erkennbar am HTML-Marker `codex-pull-request-review-summary`). Sie trug auf
#90 und #91 «🔄 Running» und wurde nie fortgeschrieben. Sie wird hier
uebersprungen, sonst waere jeder frisch getriggerte PR sofort `unknown`.

Das ist die EINE ungepruefte Annahme dieses Skripts: dass Codex sein Urteil
weiterhin auch als eigenen Kommentar postet und nicht nur noch in dieser
Tabelle fuehrt. Beobachtet ist es aus der Zeit vor der Tabelle. Laeuft das
Gate in den Timeout, obwohl Codex sichtbar fertig ist, ist das hier der erste
Ort zum Nachsehen.

Aufruf:
    python scripts/classify_codex_review.py --head-sha <sha> \
        --reviews reviews.json --comments comments.json --since <ISO-8601>
"""

from __future__ import annotations

import argparse
import json
import os
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


def classify(
    reviews: list[dict[str, Any]],
    comments: list[dict[str, Any]],
    head_sha: str,
    since: str | None = None,
) -> tuple[str, str]:
    """(state, reason) aus Reviews und Kommentaren eines PR.

    Zwei verschiedene Abfragen, und beide werden gebraucht: Das Review-Objekt
    kommt aus `pulls/{n}/reviews`, alle drei Meldungstexte aus
    `issues/{n}/comments`. Wer nur eine nimmt, uebersieht den Rest — genau so
    ist die Kontingent-Meldung im Portfolio zuerst durchgerutscht.

    Das Review-Objekt wird ueber `commit_id` an den Head gebunden, die
    Kommentare ueber `since`: Ein Review aus einem frueheren Commit belegt
    nichts ueber den, der gemergt wird.
    """
    grenze = _parse_iso(since)

    for review in reviews:
        if not _codex_authored(review):
            continue
        if head_sha and str(review.get("commit_id", "")) != head_sha:
            continue
        return (
            REVIEWED,
            f"Codex-Review-Objekt zu {head_sha[:7]} — Befunde liegen vor und "
            "gehoeren beantwortet oder behoben, bevor gemergt wird.",
        )

    unbekannt: list[str] = []
    for comment in comments:
        if not _codex_authored(comment):
            continue
        body = str(comment.get("body", ""))
        if STATUS_MARKER in body:
            continue  # Statustabelle, kein Urteil — siehe Modul-Docstring.
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
                "Fuer dieses Repo fehlt eine Codex-Environment. Sie wird je "
                "Repo angelegt (chatgpt.com/codex/cloud/settings/environments); "
                "eine fuers Konto genuegt nicht.",
            )
        unbekannt.append(" ".join(body.split())[:300])

    if unbekannt:
        return (
            UNKNOWN,
            "Codex hat etwas geschrieben, das in keinen der vier bekannten "
            f"Faelle passt. Woertlich: «{unbekannt[0]}» — einordnen und die "
            "Marker in scripts/classify_codex_review.py ergaenzen, statt es "
            "als «kein Befund» durchzuwinken.",
        )
    return PENDING, f"Noch kein Codex-Urteil zu {head_sha[:7] if head_sha else '?'}."


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
