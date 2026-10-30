# SessionStart-Hook: Klon-Aktualität und Git-Hooks

`session-start.sh` meldet beim Sessionstart zwei Dinge, die sonst
stillschweigend schieflaufen:

1. wie viele Commits der ausgecheckte Stand hinter `origin/<Standard-Branch>`
   liegt;
2. dass `core.hooksPath` nicht auf `.githooks` zeigt, die versionierten
   git-Hooks dieses Klons also nicht laufen (seit dem 28.10.2026, siehe
   [unten](#zweite-meldung-corehookspath)).

Stimmt beides, sagt er nichts.

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

## Zweite Meldung: `core.hooksPath`

`.githooks/pre-commit` lehnt einen Commit ab, in dem die Version und eine
Stelle, die sie wiederholt, auseinanderstehen (siehe
[`../../.githooks/README.md`](../../.githooks/README.md)). Er läuft aber nur,
wenn git weiss, wo er liegt — und `core.hooksPath` gilt pro Klon und ist nicht
versionierbar. Ein Hook, den niemand installiert, schützt nichts. Diese Zeile
erinnert daran, bis der Befehl einmal gelaufen ist; danach schweigt sie.

**Er meldet, er setzt nicht.** Der Hook bleibt streng lesend. Eine Session,
die `core.hooksPath` stillschweigend umbiegt, überschriebe eine Einstellung,
die jemand bewusst anders haben kann — etwa einen eigenen Hook-Ordner.

Was gemeldet wird und was nicht:

| Lage | Ausgabe |
| --- | --- |
| zeigt auf `.githooks` — in jeder Schreibweise, die git ausführt | nichts |
| nicht gesetzt | «nicht gesetzt» plus Befehl |
| zeigt anderswohin, auch auf einen nicht existierenden Pfad | der gesetzte Wert plus Befehl |
| `.githooks/` fehlt oder enthält nichts Ausführbares | nichts |

Fünf Entscheidungen, jede mit eigenem Test:

- **Verglichen werden Verzeichnisse, nicht Zeichenketten.** Nachgemessen am
  28.10.2026 mit git 2.43: git führt den Hook bei `.githooks`, `./.githooks`,
  `.githooks/` und dem absoluten Pfad gleichermassen aus und löst relativ gegen
  die Wurzel auf. Die erste Fassung verglich Zeichenketten, kannte davon zwei
  und hätte bei den anderen gemeldet — bei **jedem** Sessionstart, also genau
  die Meldung, die man abschaltet. Jetzt bildet ein `cd` aus der Wurzel die
  Auflösung von git nach, `pwd -P` löst Symlinks auf, und `git config --path`
  expandiert `~` so, wie git es tut. Ein Pfad, auf den kein `cd` geht, wird
  gemeldet, nicht verschluckt: Aus ihm führt git auch nichts aus.

- **Bedingung ist eine ausführbare Datei in `.githooks/`, nicht der Name
  `pre-commit`.** Ein fester Name deckte einen später dazukommenden `pre-push`
  nicht, und `-d .githooks` meckerte auch über einen Ordner mit bloss einer
  README. Ausführbar ist genau die Bedingung, unter der git einen Hook
  startet — eine Ausnahmeliste für `README.md` braucht es so nicht. Das hält
  die Zeile auch aus jedem Repo des Portfolios fern, in das dieser Hook
  kopiert wird und das keine Hooks ausliefert. Preis: Verliert ein Hook sein
  `+x`, schweigt die Zeile, obwohl nichts läuft; diesen Fall hält
  `tests/test_pre_commit_hook.py::test_ausfuehrungsrecht_steht_auch_im_index`
  in der CI.
- **Gesucht wird an der Wurzel** (`git rev-parse --show-toplevel`), nicht im
  aktuellen Verzeichnis — dort, wo git auch ein relatives `core.hooksPath`
  auflöst. Eine Session in `src/` sähe sonst kein `.githooks`.
- **Sie hängt nicht am Remote.** Darum eine eigene Funktion statt eines
  Abschnitts in `pruefe`: Die Aktualitätsprüfung steigt ohne `origin` aus,
  ein Klon ohne Remote hat aber denselben nicht installierten Hook.
- **Eigener Abschalter.** `CLAUDE_SKIP_FRESHNESS_CHECK` schaltet weiter nur die
  Aktualität ab. Eine Variable mit diesem Namen, die auch die hooksPath-Zeile
  schluckte, löge über das, was sie tut. Wer sie gesetzt hatte, um Ruhe zu
  haben, sieht also die neue Zeile — und stellt sie mit
  `CLAUDE_SKIP_HOOKS_CHECK=1` ebenso ab.

Kommen beide Meldungen, steht die Aktualität zuerst: Der veraltete Klon ist
das Risiko für die Arbeit, die gerade beginnt; die Einrichtung ist einmalig.

## Konfiguration

| Variable | Default | Wirkung |
| --- | --- | --- |
| `CLAUDE_SKIP_FRESHNESS_CHECK` | — | Auf `1` gesetzt: keine Aktualitätsprüfung. Die hooksPath-Zeile bleibt. |
| `CLAUDE_SKIP_HOOKS_CHECK` | — | Auf `1` gesetzt: keine hooksPath-Zeile. Die Aktualitätsprüfung bleibt. |
| `CLAUDE_FRESHNESS_TIMEOUT` | `5` | Zeitlimit **pro Netzaufruf**, in Sekunden. Die hooksPath-Prüfung macht keinen. |

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
(kein `CLAUDE_CODE_REMOTE`-Filter). Er installiert nichts, ändert keine
Konfiguration und ist umgebungsunabhängig; ein veralteter Klon führt lokal zur
selben rätselhaften roten CI wie remote, und ein nicht installierter Hook
schützt lokal genauso wenig.

## Tests

`../../tests/test_session_start_hook.py` fährt das Skript gegen echte
Wegwerf-Repos (lokale `file://`-Remotes): Rückstand wird gemeldet, 0
schweigt, `master` wird erkannt, und die Störfälle (kein Remote,
unerreichbares Remote, detached HEAD, kein Repo, leeres Repo) enden alle mit
Exit 0 und leerer Ausgabe.

Die hooksPath-Tests legen `.githooks/` im Wegwerf-Repo selbst an und decken
die Tabelle oben ab — sechs Schreibweisen von `.githooks` als ein
parametrisierter Test, darunter `~` und ein Pfad über einen Symlink —, dazu: Meldung auch ohne Remote, Wurzel aus einem
Unterverzeichnis gefunden, beide Abschalter getrennt, Reihenfolge bei zwei
Meldungen. Die älteren Tests laufen in Repos ohne `.githooks/` und prüfen
weiter auf leere Ausgabe — damit sind sie zugleich die Wache, dass die neue
Zeile nicht in Repos auftaucht, die keine Hooks ausliefern.

Gegenprobe am 28.10.2026, jede Zusicherung einzeln rückgängig gemacht: Es
fiel jeweils genau der zugehörige Test. Ausnahme mit Grund: Ohne den Wert in
der Meldung fallen beide Tests, die ihn zusichern (fremder und nicht
existierender Pfad). Eine Gegenprobe blieb grün und hat Code gekostet statt
einen Test: Ein Schutz gegen leeres `soll` liess sich nicht auslösen, weil
`hooks_vorhanden` das schon ausschliesst. Er ist entfernt — ein Schutz, den
nichts prüfen kann, behauptet nur, etwas zu schützen.
