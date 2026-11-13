# CLAUDE.md

## Teil 1 — Konventionen (portfolio-weit)

### Vor der Arbeit

Der SessionStart-Hook meldet beim Sessionstart den Rückstand auf
`origin/<Standard-Branch>` und schweigt bei 0 (Details:
`.claude/hooks/README.md`). In Repos ohne diesen Hook den Standard-Branch
ermitteln, nicht `main` annehmen — Handgriff in
`docs/claude/wenn-etwas-rot-ist.md`. Gates lokal fahren, mit der GEPINNTEN
ruff-Version aus der CI; eine andere Version meldet Abweichungen, die niemand
verursacht hat.

### Tests

Gegenprobe ist Pflicht. Ein Test, der grün bleibt, wenn man die
Implementierung entfernt, prüft nichts. Jede neue Zusicherung einzeln
neutralisieren und zeigen, dass genau die zugehörigen Tests fallen.
Zwei Fallen, die beide grün blieben (Fake-Uhr, `asyncio`-Patch):
`docs/claude/wenn-etwas-rot-ist.md`.

Handgeschriebene Fixtures kodieren die Annahme des Autors und können sie
nicht widerlegen. Mindestens eine aufgezeichnete Antwort pro externem
Endpunkt, mit Aufnahmedatum.

### Bei Bedarf lesen

- Roter Test, rote CI, ein 4xx/403, ein «nicht gefunden», eine scheinbar wirkungslose Option oder ein blockierter PR: lies zuerst `docs/claude/wenn-etwas-rot-ist.md`.
- Vor dem Anlegen eines Branches mit vorgegebenem Namen und bei einem PR mit leerem Diff: lies zuerst `docs/claude/parallele-agenten.md`.

## Teil 2 — dieses Repo

**ruff-Pin: in `pyproject.toml`, an einer Stelle.** `[dev]` fordert ihn;
`pip install -e ".[dev]"` installiert damit lokal genau die Version der CI,
und `ci.yml` installiert ruff nicht mehr separat. Eine
`.pre-commit-config.yaml` gibt es nicht — wer eine anlegt, pinnt dort
dieselbe Version oder verlagert den Pin ganz dorthin, aber nie beides.

Die Nummer steht hier bewusst nicht mehr. Am 18.9.2026 stand an dieser
Stelle `0.16.3`, während ein Dependabot-Lauf den Pin längst auf eine neuere
Version gehoben hatte. Die Überschrift «an einer Stelle» stand also über
einer Kopie, und wer ihr folgte, installierte genau das abweichende ruff,
vor dem der Absatz darunter warnt — der Satz erzeugte den Fehler, den er
verhindern sollte. Seither gleicht `tests/test_ruff_pin_doku.py` jede
`ruff==`-Angabe in den versionierten Markdown-Dateien gegen den Pin ab; er
verbietet sie nicht, er verlangt, dass sie stimmt.

Den Abgleich macht `scripts/check_ruff_pin.py`, das erste Gate unten: Es
liest den Pin aus `pyproject.toml` und nennt ihn in seiner Ausgabe.
`ruff --version` von Hand genügt nicht — es sieht nur das Binary aus dem
`PATH`, und ein älteres ruff früher darin schlägt den Pin, ohne dass der
Install etwas meldet.

Gates, wörtlich aus `ci.yml` (Python 3.11 / 3.12 / 3.13):

```bash
PYTHONPATH=src pytest tests/ -m "not live"
python scripts/check_ruff_pin.py
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
python scripts/check_version_sync.py
```

**Alle vier laufen in einem Job auf allen drei Versionen.** Kein zweiter Job,
keine `if: matrix.python-version`-Ausnahme — ein grünes 3.13 heisst hier
wirklich, dass alles auf 3.13 lief. (Im Portfolio nicht selbstverständlich:
`swiss-food-safety-mcp` gated zwei Gates auf 3.11, `swiss-housing-mcp` fährt
seine ruff-Gates in einem eigenen 3.11-Job.) Ein `fail-fast: false` steht
nicht da: Eine rote 3.11 bricht 3.12 und 3.13 ab, bevor sie etwas sagen.

Das `PYTHONPATH=src` in der ersten Zeile stammt wörtlich aus `ci.yml`, trägt
aber nichts: Nach `pip install -e ".[dev]"` importiert
`swiss_cultural_heritage_mcp` auch mit `env -u PYTHONPATH` — nachgemessen.
Wer einen Importfehler über den Env-Eintrag erklärt, sucht an der falschen
Stelle; es fehlt dann der Install.

**Das letzte Gate läuft auch als pre-commit-Hook.** Einmal pro Klon
`git config core.hooksPath .githooks`; dann lehnt `.githooks/pre-commit` einen
Commit ab, in dem die Version und eine Stelle, die sie wiederholt,
auseinanderstehen. Er ruft dasselbe `scripts/check_version_sync.py` auf, statt
dessen Logik nachzubilden — Hook und CI können nicht auseinanderlaufen.
Details: `.githooks/README.md`.

Ist `core.hooksPath` nicht gesetzt, sagt das der SessionStart-Hook bei jedem
Sessionstart, mit dem Befehl in der Meldung; danach schweigt er. Er **meldet**,
er setzt nicht — der Hook bleibt streng lesend. Wer die Zeile in einer Session
liest: den Befehl ausführen, bevor committet wird, sonst läuft der
pre-commit-Hook in dieser Session nicht. Abschalten mit
`CLAUDE_SKIP_HOOKS_CHECK=1`; `CLAUDE_SKIP_FRESHNESS_CHECK` schaltet weiter nur
die Aktualitätsprüfung ab.

Zwei Eigenschaften, die man beim Ändern nicht umkehren darf. Er prüft den
**Index**, nicht den Arbeitsbaum: Steht `A` im Index und `B` im Arbeitsbaum,
legt `git commit` `A` ab (nachgemessen am 28.10.2026) — ein Arbeitsbaum-Check
ginge genau beim regenerierten, aber nicht gestagten Pin grün durch. Und er
blockiert **nur bei einem echten Befund**: kein python, unaufgelöster Merge,
Gate nicht im gestagten Stand → Commit durch, plus eine Zeile auf stderr, dass
nichts geprüft wurde. Die CI hält die Linie ohnehin.

`generated_for_version` im Tool-Pin ist seit dem 28.10.2026 Teil dieses
Gates — vorher hielt es nur `tests/test_server.py::TestToolPins`, das die
Projekt-Installation braucht. Den Pin **nicht** von Hand nachtragen: Die
Hashes daneben beschreiben die freigegebene Tool-Oberfläche, ein
nachgeschriebenes Feld behauptete eine Freigabe, die es nie gab. Im selben
Commit wie den Bump neu erzeugen mit
`PYTHONPATH=src python scripts/pin_tools.py`.

**Live-Tests laufen geplant.** `.github/workflows/nightly-live.yml` fährt
`PYTHONPATH=src pytest tests/ -m live` täglich um 04:17 UTC (cron
`17 4 * * *`) und öffnet bei Upstream-Fehlern ein Issue mit Label
`nightly-live-failure`, statt den Lauf rot zu färben. DRIFT-005 ist damit
erfüllt — Live-Tests sind nicht bloss per `-m "not live"` ausgeschlossen.
Ein offenes `nightly-live-failure`-Issue vor der Arbeit prüfen.

**Ein rotes `main` öffnet ein Issue.** `.github/workflows/main-rot.yml` läuft
nach jedem CI-Lauf und öffnet bei Rot auf der Spitze des Standard-Branches ein
Issue mit Label `main-rot`, ergänzt es bei jedem weiteren roten Lauf und
schliesst es, sobald die Spitze wieder grün ist. Anlass: Vom 08. bis
12.11.2026 war `main` rot, ohne dass es jemand sah — PR #110 trug einen grünen
Check gegen einen Stand ohne die Audit-Reports aus #111. Verhindern lässt sich
das nur in den Repo-Einstellungen («Require branches to be up to date before
merging»); dieser Workflow macht es sichtbar. Ein offenes `main-rot`-Issue vor
der Arbeit prüfen, wie oben.

Die Entscheidung trifft `scripts/main_ci_status.py`, nicht der Workflow:
Nur der Lauf der aktuellen Spitze zählt (die Laufreihenfolge ist nicht
garantiert), der Standard-Branch kommt aus der Payload statt aus einem `main`
im Code, und `cancelled` öffnet und schliesst nichts. Per `workflow_dispatch`
lässt er sich mit eigenem Label `main-rot-probe` von Hand probefahren — ein
Probelauf berührt kein echtes `main-rot`-Issue. Wird `ci.yml` umbenannt, muss
`workflows:` im Melder mit; sonst feuert er nie, und das hält
`tests/test_main_ci_status.py` fest.
