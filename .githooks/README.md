# Git-Hooks

Versionierte Hooks für dieses Repo. Git sucht sie nicht von selbst hier —
`.git/hooks/` ist nicht versioniert. Einmal pro Klon:

```bash
git config core.hooksPath .githooks
```

Prüfen, ob es sitzt: `git config --get core.hooksPath` muss `.githooks`
ausgeben.

## `pre-commit` — Versions-Synchronität

Fährt [`../scripts/check_version_sync.py`](../scripts/check_version_sync.py)
gegen den Stand, der committet werden wird, und lehnt den Commit ab, wenn die
Version in `pyproject.toml` und eine der Stellen, die sie wiederholen,
auseinanderstehen. Das sind `server.json`, die Versions-Badges der READMEs und
`generated_for_version` in `audits/tool-pins/current.json`.

### Warum

Beim Bump auf 0.5.0 blieb der Tool-Pin auf 0.4.0 stehen. Rot wurde das erst in
der CI, auf Python 3.11, in
`tests/test_server.py::TestToolPins::test_pin_records_the_declared_version` —
einem Namen, der den Zusammenhang nicht nennt. Der Handgriff daneben kostet
eine Sekunde:

```bash
PYTHONPATH=src python scripts/pin_tools.py
```

Man muss nur dran denken. Genau das übernimmt der Hook.

### Er dupliziert keine Prüfung

Der Hook ruft das vorhandene CI-Gate auf, statt dessen Logik nachzubilden.
Hook und CI können damit nicht auseinanderlaufen — und niemand muss die
Prüfung an zwei Stellen nachführen.

Dieselbe Überlegung hat die Pin-Prüfung von den Tests in das Gate gezogen:
`check_version_sync.py` kommt mit der Standardbibliothek aus und läuft ohne
`pip install -e ".[dev]"`. Erst das macht den Hook schnell (~140 ms) und
unabhängig von der Dev-Installation.

### Er prüft den Index, nicht den Arbeitsbaum

Das ist die eigentliche Zusicherung. Ein Hook, der die Dateien liest, wie sie
auf der Platte liegen, prüft etwas anderes als das, was gleich entsteht.

Nachgemessen am 28.10.2026 in einem Wegwerf-Repo: Steht `A` im Index und `B`
im Arbeitsbaum, legt `git commit` `A` ab. Der gefährliche Fall ist genau der
hier gemeinte — den Pin regeneriert, aber nicht gestaged: Arbeitsbaum grün,
Commit kaputt, CI rot. Dieselbe Klasse wie der Test, der grün bleibt, wenn man
die Implementierung entfernt.

Quelle ist darum `git write-tree`, der Index als Baum. Auch bei
`git commit -a` ist der Index bereits aktualisiert, wenn der Hook läuft
(ebenfalls nachgemessen) — es gibt keinen Fall, in dem der Index die falsche
Quelle wäre.

### Was er nicht tut

Kein ruff, kein pytest. Beide brauchen die Dev-Installation und Sekunden statt
Millisekunden; ein Hook, der bei jedem Commit wartet oder ohne
`pip install -e ".[dev]"` meckert, wird abgeschaltet und schützt danach gar
nichts. Die vollen Gates stehen in [`../CLAUDE.md`](../CLAUDE.md) und in
[`../CONTRIBUTING.md`](../CONTRIBUTING.md) und laufen in der CI auf Python
3.11, 3.12 und 3.13.

### Bei Erfolg schweigt er

Nur ein Befund erzeugt Ausgabe. Eine Bestätigung bei jedem Commit wird nach der
dritten Woche nicht mehr gelesen — dieselbe Begründung wie beim Schweigen des
SessionStart-Hooks bei 0 fehlenden Commits.

### Er blockiert nur bei einem echten Befund

Kann er nicht messen — kein `python` im PATH, Index nicht als Baum auflösbar
(unaufgelöster Merge), Gate im gestagten Stand nicht vorhanden —, lässt er den
Commit durch und sagt in **einer Zeile auf stderr**, dass er nichts geprüft
hat. Durchlassen ja, stillschweigend nein: nicht geprüft und niemand weiss es,
wäre die schlechtere Hälfte beider Welten. Die CI hält die Linie ohnehin; ein
Hook, der aus eigener Fehlfunktion blockiert, kostet mehr als er bringt.

### Umgehen

```bash
git commit --no-verify          # einmalig
SKIP_VERSION_SYNC_HOOK=1 git commit …   # ebenso, ohne --no-verify zu tippen
```

Der Ausweg ist Absicht. Ein Hook ohne Ausweg wird deinstalliert, und dann
schützt er nichts mehr.

## Reichweite

`core.hooksPath` gilt pro Klon und ist nicht versionierbar — ein Hook, den
niemand installiert, schützt nichts. Deshalb steht der Befehl auch in
[`../CONTRIBUTING.md`](../CONTRIBUTING.md) (und
[`../CONTRIBUTING.de.md`](../CONTRIBUTING.de.md)) unter den Einrichtungs-
schritten.

Dazu **meldet** der SessionStart-Hook
([`../.claude/hooks/session-start.sh`](../.claude/hooks/session-start.sh)) bei
jedem Sessionstart, solange `core.hooksPath` nicht auf `.githooks` zeigt — mit
dem Befehl in der Meldung. Ist er einmal gesetzt, schweigt die Zeile.

**Gesetzt** wird er absichtlich nicht automatisch: Der SessionStart-Hook ist
streng lesend und ändert keine git-Konfiguration. Eine Session, die
stillschweigend `core.hooksPath` umbiegt, überschriebe eine Einstellung, die
jemand bewusst anders haben kann — etwa einen eigenen Hook-Ordner. Wer die
Meldung nicht will: `CLAUDE_SKIP_HOOKS_CHECK=1`. Einzelheiten in
[`../.claude/hooks/README.md`](../.claude/hooks/README.md).

## Tests

[`../tests/test_pre_commit_hook.py`](../tests/test_pre_commit_hook.py) fährt
den Hook über echte `git commit`-Aufrufe in Wegwerf-Repos: unvollständiger
Bump wird abgelehnt, stimmiger durchgelassen, `--no-verify` und der Abschalter
gehen durch, `git commit -a` wird in beiden Richtungen geprüft, und der
Störfall «Gate fehlt» endet mit Exit 0 plus Meldung.

Zwei Zusicherungen dort verdienen einen eigenen Blick:

- `test_fix_nur_im_arbeitsbaum_rettet_den_commit_nicht` ist die Gegenprobe zur
  Index-Lesung. In einem Lauf gegen eine Arbeitsbaum-Fassung des Hooks war es
  der **einzige** Test, der fiel.
- `test_ausfuehrungsrecht_steht_auch_im_index` hält den Modus `100755` in git.
  Ohne Ausführungsrecht überspringt git den Hook lautlos — der Ausfall, der am
  leichtesten unbemerkt bleibt: alles da, alles versioniert, geprüft nichts.

Die Prüfung im Gate hat ihre eigene Datei:
[`../tests/test_version_sync_tool_pin.py`](../tests/test_version_sync_tool_pin.py).
