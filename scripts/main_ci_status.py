#!/usr/bin/env python3
"""Soll zum CI-Ergebnis auf dem Standard-Branch ein Issue auf- oder zugehen?

WARUM ES DAS GIBT
-----------------
Am 08.11.2026 wurde `main` rot und blieb es vier Tage, ohne dass es jemand
sah. PR #110 (ruff-Bump) trug einen gruenen Check vom 01.11. -- gerechnet gegen
einen Stand ohne die Audit-Reports, die PR #111 dreissig Sekunden vor dem Merge
von #110 nach `main` gebracht hatte. Jeder PR war fuer sich gruen, die
Kombination rot, und die Kombination hat vor dem Merge niemand gerechnet.

Verhindern laesst sich das nur in den Repo-Einstellungen («Require branches
to be up to date before merging»). Dieses Skript verhindert nichts; es sorgt
dafuer, dass ein rotes `main` nicht wieder vier Tage unbemerkt bleibt. Der
Workflow `.github/workflows/main-rot.yml` ruft es nach jedem CI-Lauf auf und
oeffnet, ergaenzt oder schliesst danach ein Issue mit Label `main-rot`.

WARUM DAS EIN SKRIPT IST UND KEIN YAML-BLOCK
--------------------------------------------
Dasselbe Argument wie bei `classify_live_run.py`: Die Entscheidung, ob ein
Issue aufgeht oder zugeht, ist der einzige Teil des Workflows, der etwas
behauptet. Im `if:` eines Workflows kann sie niemand testen; hier steht sie
neben ihrem Test.

WAS ALS ROT, GRUEN ODER GAR NICHTS ZAEHLT
-----------------------------------------
Rot: `failure`, `timed_out`, `startup_failure` -- der Lauf hat etwas
festgestellt oder ist nicht bis zum Ende gekommen. Gruen: `success`. Alles
andere (`cancelled`, `skipped`, `neutral`, `action_required`, `stale`) sagt
nichts ueber den Stand des Codes; darauf geht weder ein Issue auf noch zu.

NUR DIE SPITZE ZAEHLT
---------------------
Am 08.11. gingen drei PRs binnen dreissig Sekunden nach `main`, ihre
CI-Laeufe endeten in derselben Minute. Die Reihenfolge, in der sie enden, ist
nicht garantiert. Endet der gruene Lauf eines aelteren Commits nach dem roten
der Spitze, schloesse er ein berechtigtes Issue; endet ein alter roter nach
einem gruenen, meldete er einen Stand, den es nicht mehr gibt. Deshalb zaehlt
nur der Lauf, dessen Commit noch die Spitze des Standard-Branches ist.

Ist die Spitze nicht ermittelbar (Netz, API), entscheidet die Asymmetrie: Rot
wird trotzdem gemeldet -- ein Fehlalarm kostet einen Blick, ein verschluckter
Befund kostet Tage. Gruen schliesst dann nichts, weil es nicht belegen kann,
dass es den Stand betrifft, um den es im Issue geht.

DER STANDARD-BRANCH WIRD NICHT ANGENOMMEN
----------------------------------------
Er kommt aus der Event-Payload (`repository.default_branch`), nicht aus einem
`main` im Code. Drei Server im Portfolio heissen ihn `master`; ein fest
eingetragenes `main` liesse den Workflow dort nie anschlagen, und das sieht
genau so aus wie ein gruenes `master`.

PROBELAUF
---------
Ein Melder, der nur bei echtem Rot feuert, ist bis dahin ungeprueft. Per
`workflow_dispatch` laesst er sich darum einmal von Hand fahren. Ein Probelauf
arbeitet mit eigenem Label (`main-rot-probe`) und kann damit ein echtes
`main-rot`-Issue weder ergaenzen noch schliessen.

Aufruf (liest alles aus Umgebungsvariablen, siehe `_aus_umgebung`):
    python scripts/main_ci_status.py

Gibt `aktion`, `label`, `titel` und `grund` auf stdout aus und haengt sie an
`$GITHUB_OUTPUT` an, wenn gesetzt. Exit-Code immer 0: Ueber die Aktion
entscheidet diese Ausgabe, nicht der Prozessstatus.

Nur Standardbibliothek -- der Workflow braucht dafuer kein `pip install`.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

MELDEN = "melden"
SCHLIESSEN = "schliessen"
NICHTS = "nichts"

LABEL = "main-rot"
PROBE_LABEL = "main-rot-probe"

ROT = frozenset({"failure", "timed_out", "startup_failure"})
GRUEN = frozenset({"success"})

# Die Werte des `workflow_dispatch`-Inputs `probe`, uebersetzt in das, was ein
# echter Lauf als `conclusion` liefern wuerde.
PROBE_ERGEBNIS = {"rot": "failure", "gruen": "success"}


@dataclass(frozen=True)
class Entscheid:
    aktion: str
    label: str
    titel: str
    grund: str


def _titel(zweig: str, probe: bool) -> str:
    titel = f"CI auf {zweig} ist rot"
    return f"[Probe] {titel}" if probe else titel


def entscheide(
    *,
    ausloeser: str,
    lauf_ereignis: str = "",
    ergebnis: str = "",
    zweig: str = "",
    standard_zweig: str = "",
    herkunft: str = "",
    repo: str = "",
    kopf_sha: str = "",
    spitze_sha: str = "",
    probe: str = "",
) -> Entscheid:
    """Die ganze Entscheidung, ohne Netz und ohne Umgebung."""
    if ausloeser == "workflow_dispatch":
        simuliert = PROBE_ERGEBNIS.get(probe)
        titel = _titel(standard_zweig or "dem Standard-Branch", probe=True)
        if simuliert is None:
            return Entscheid(NICHTS, PROBE_LABEL, titel, f"unbekannter Probewert {probe!r}")
        aktion = MELDEN if simuliert in ROT else SCHLIESSEN
        return Entscheid(aktion, PROBE_LABEL, titel, f"Probelauf: {probe}")

    titel = _titel(standard_zweig or zweig, probe=False)

    if ausloeser != "workflow_run":
        return Entscheid(NICHTS, LABEL, titel, f"unbekannter Ausloeser {ausloeser!r}")
    if lauf_ereignis != "push":
        return Entscheid(NICHTS, LABEL, titel, f"kein Push, sondern {lauf_ereignis!r}")
    if not standard_zweig or zweig != standard_zweig:
        return Entscheid(NICHTS, LABEL, titel, f"Zweig {zweig!r} ist nicht der Standard-Branch")
    # Ein Fork kann einen Branch gleichen Namens haben. Sein Lauf sagt nichts
    # ueber den Standard-Branch dieses Repos.
    if herkunft != repo:
        return Entscheid(NICHTS, LABEL, titel, f"Lauf aus {herkunft!r}, nicht aus {repo!r}")

    rot = ergebnis in ROT
    gruen = ergebnis in GRUEN
    if not rot and not gruen:
        return Entscheid(NICHTS, LABEL, titel, f"Ergebnis {ergebnis!r} sagt nichts ueber den Code")

    if not spitze_sha:
        if rot:
            return Entscheid(
                MELDEN, LABEL, titel, "rot; Spitze nicht ermittelbar, trotzdem gemeldet"
            )
        return Entscheid(NICHTS, LABEL, titel, "gruen, aber Spitze nicht ermittelbar")
    if kopf_sha != spitze_sha:
        return Entscheid(
            NICHTS,
            LABEL,
            titel,
            f"ueberholt: Lauf fuer {kopf_sha[:7]}, Spitze ist {spitze_sha[:7]}",
        )

    if rot:
        return Entscheid(MELDEN, LABEL, titel, f"{ergebnis} auf der Spitze {kopf_sha[:7]}")
    return Entscheid(SCHLIESSEN, LABEL, titel, f"gruen auf der Spitze {kopf_sha[:7]}")


def _aus_umgebung(env: Mapping[str, str]) -> Entscheid:
    """Uebersetzt die Workflow-Umgebung in die Argumente von `entscheide`.

    Die Werte kommen ueber `env:` in den Schritt, nie ueber `${{ }}` in eine
    Shell -- `head_branch` und `conclusion` stammen aus der Event-Payload.
    """
    return entscheide(
        ausloeser=env.get("AUSLOESER", ""),
        lauf_ereignis=env.get("LAUF_EREIGNIS", ""),
        ergebnis=env.get("ERGEBNIS", ""),
        zweig=env.get("ZWEIG", ""),
        standard_zweig=env.get("STANDARD_ZWEIG", ""),
        herkunft=env.get("HERKUNFT", ""),
        repo=env.get("REPO", ""),
        kopf_sha=env.get("KOPF_SHA", ""),
        spitze_sha=env.get("SPITZE_SHA", ""),
        probe=env.get("PROBE", ""),
    )


def main(env: Mapping[str, str] | None = None) -> int:
    quelle = os.environ if env is None else env
    entscheid = _aus_umgebung(quelle)
    felder = {
        "aktion": entscheid.aktion,
        "label": entscheid.label,
        "titel": entscheid.titel,
        "grund": entscheid.grund,
    }
    for name, wert in felder.items():
        print(f"{name}={wert}")

    out = quelle.get("GITHUB_OUTPUT")
    if out:
        # Zeilenumbrueche raus, aus demselben Grund wie in
        # `classify_live_run.py`: `key=value` endet an der ersten neuen Zeile,
        # und was danach steht, liest der Runner als naechstes Output. Ein
        # Ergebniswert mit Zeilenumbruch, der in den Grund wandert, koennte
        # sonst ein `aktion=schliessen` nachschieben.
        with open(out, "a", encoding="utf-8") as fh:
            for name, wert in felder.items():
                fh.write(f"{name}={' '.join(wert.split())}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
