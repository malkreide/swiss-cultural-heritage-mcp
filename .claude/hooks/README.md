# SessionStart-Hook: Klon-Aktualität

`session-start.sh` meldet beim Sessionstart, wie viele Commits der
ausgecheckte Stand hinter `origin/<Standard-Branch>` liegt. Liegt er nicht
zurück, sagt er nichts.

Registriert ist er in [`../settings.json`](../settings.json) unter
`hooks.SessionStart`. Dort steht zusätzlich ein `timeout` von 20 Sekunden als
Rückfallebene der Laufzeitumgebung — das eigentliche Zeitlimit setzt das
Skript selbst (siehe unten).

## Warum es diesen Hook gibt

Am 3.8.2026 hat ein veralteter Klon in diesem Repo **zweimal** eine rote CI
erzeugt, deren Ursache nicht im Diff stand. Die fehlenden Commits waren
jeweils genau die, die das Gate einführten, an dem der Branch scheiterte —
die Fehlersuche lief also in Dateien, die nichts damit zu tun hatten.

Die Prüfung kostet eine Sekunde und ersetzt diese Fehlersuche. Das ist der
ganze Zweck.

Derselbe Ablauf steht als Handgriff auch in [`../../CLAUDE.md`](../../CLAUDE.md)
(«Vor der Arbeit»). Der Hook ist die Variante, an die niemand denken muss.

## Was er zusichert

**1. Er blockiert die Session nie.** Diese Anforderung steht über allen
anderen. Ein Hook, der bei Netzproblemen die Arbeit anhält, wird nach dem
zweiten Mal abgeschaltet und schützt danach gar nichts. Umgesetzt ist das so:

- **Kein `set -e`, kein `set -u`, kein `set -o pipefail`.** Das ist Absicht
  und die auffälligste Abweichung von der üblichen Hook-Vorlage. Unter
  `set -e` würde der erste fehlschlagende `git`-Aufruf das Skript mit dessen
  Exit-Code beenden, und ein Exit ≠ 0 aus einem SessionStart-Hook wird als
  Fehler gemeldet statt still verworfen. Wer die Zeile später „aufräumend"
  ergänzt, kehrt die Zusicherung dieses Hooks um.
- Der gesamte Ablauf steckt in der Funktion `pruefe`; die letzte Zeile der
  Datei ist ein unbedingtes `exit 0`.
- Jeder Netzaufruf läuft unter einem Zeitlimit (Default 5 s, siehe unten).
- Kein Aufruf darf interaktiv werden: `GIT_TERMINAL_PROMPT=0`, `GIT_ASKPASS`,
  `SSH_ASKPASS_REQUIRE=never`, `ssh -o BatchMode=yes`. Ohne diese Variablen
  wartet git bei einem privaten Remote ohne Credential-Helper auf eine
  Eingabe, die im Sessionstart niemand sieht — und hängt bis ins Zeitlimit.
- `stderr` geht nach `/dev/null`; auf `stdout` steht ausschliesslich die
  Meldung.

Still durchgehen: kein `git` im PATH, kein Repo, kein Remote `origin`, leeres
Repo ohne Commit, DNS-Aussetzer, hängendes Netz, gelöschter oder
unerreichbarer Standard-Branch.

Detached HEAD steht bewusst **nicht** in dieser Liste: dort ist der Rückstand
ganz normal zählbar, und der Hook meldet ihn. Blockieren tut er auch da nicht.

**2. Bei 0 fehlenden Commits schweigt er.** Eine Meldung, die immer kommt,
wird nicht mehr gelesen.

**3. Der Standard-Branch wird ermittelt, nicht angenommen.** Quelle ist
`git ls-remote --symref origin HEAD`. Im Portfolio heissen drei Server ihren
Standard-Branch `master` (`openlex-mcp`, `swiss-courts-mcp`, `swisstopo-mcp`);
dort bricht ein fest verdrahtetes `origin/main` mit «couldn't find remote ref
main» ab. Das sieht aus wie ein Netzproblem, ist aber der Fehler selbst — und
hat schon einmal einen Branch 15 Commits alt werden lassen.

## Wie er zählt

`git ls-remote --symref origin HEAD` liefert in **einem** Aufruf beides: den
Namen des Standard-Branches und die SHA seiner Spitze. `ls-remote` überträgt
keine Objekte und ist damit deutlich billiger als ein `fetch`.

Kennt der Klon diese SHA bereits, ist kein weiterer Netzaufruf nötig — der
Normalfall «Klon aktuell» kostet genau einen `ls-remote`. Erst wenn die Spitze
lokal fehlt, folgt ein `git fetch --no-tags origin <branch>`. Gezählt wird
dann `git rev-list --count HEAD..<spitze>`.

## Konfiguration

| Variable | Default | Wirkung |
| --- | --- | --- |
| `CLAUDE_SKIP_FRESHNESS_CHECK` | — | Auf `1` gesetzt: Hook tut nichts. |
| `CLAUDE_FRESHNESS_TIMEOUT` | `5` | Zeitlimit **pro Netzaufruf**, in Sekunden. |

Das Zeitlimit gilt pro Aufruf, nicht als Gesamtbudget. Im Normalfall gibt es
nur einen Aufruf (5 s Obergrenze); liegt der Klon zurück, kommt der `fetch`
dazu (zusammen 10 s Obergrenze) — dann ist die Meldung die Wartezeit wert.

`timeout` (coreutils) fehlt auf macOS ohne Homebrew-coreutils. Das Skript
nimmt dort `gtimeout`, und wenn auch das fehlt, einen eigenen
Hintergrund-plus-`kill`-Zweig. Das Limit entfällt nirgends still — ein
ungekapptes `git fetch` in einem hängenden Netz ist genau der Fall, den
dieser Hook nicht verursachen darf.

## Reichweite

Der Hook läuft in **jeder** Session, nicht nur in Claude Code on the web
(kein `CLAUDE_CODE_REMOTE`-Filter). Er installiert nichts und ist
umgebungsunabhängig; ein veralteter Klon führt lokal zur selben rätselhaften
roten CI wie remote.

## Tests

`../../tests/test_session_start_hook.py` fährt das Skript gegen echte
Wegwerf-Repos (lokale `file://`-Remotes): Rückstand wird gemeldet, 0
schweigt, `master` wird erkannt, und die Störfälle (kein Remote,
unerreichbares Remote, detached HEAD, kein Repo, leeres Repo) enden alle mit
Exit 0 und leerer Ausgabe.
