# CLAUDE.md

## Teil 1 — Konventionen (portfolio-weit)

### Vor der Arbeit

Klon-Aktualität prüfen — Standard-Branch ermitteln, nicht `main` annehmen:

```bash
B=$(git ls-remote --symref origin HEAD | sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p')
git fetch origin "${B:?Standard-Branch nicht ermittelbar}" &&
  git rev-list --count HEAD..FETCH_HEAD
```

Drei Server im Portfolio heissen ihren Standard-Branch `master`
(`openlex-mcp`, `swiss-courts-mcp`, `swisstopo-mcp`); dort scheitert ein fest
verdrahtetes `origin/main` mit «couldn't find remote ref main». Wer das für ein
Netzproblem hält, arbeitet weiter auf genau dem veralteten Klon, vor dem dieser
Absatz warnt. Den `:?`-Schutz nicht weglassen: Bei leerem `B` fetcht git still
den Remote-HEAD und endet mit 0.

Ein veralteter Klon erzeugt eine rote CI, deren Ursache nicht im Diff steht.
Am 3.8.2026 zweimal passiert — beide Male fehlten genau die Commits, die
das Gate einführten, an dem der Branch scheiterte.
In diesem Repo läuft dieser Handgriff seit dem SessionStart-Hook
`.claude/hooks/session-start.sh` automatisch: er meldet beim Sessionstart den
Rückstand auf `origin/<Standard-Branch>` und schweigt bei 0. Blockieren kann er
nicht — jeder Störfall endet mit Exit 0, jeder Netzaufruf unter Zeitlimit. Er
ersetzt den Handgriff oben nicht in anderen Repos des Portfolios.
Details: `.claude/hooks/README.md`.

Gates lokal fahren, mit der GEPINNTEN ruff-Version aus der CI. Eine andere
Version meldet Abweichungen, die niemand verursacht hat.

### Tests

Gegenprobe ist Pflicht. Ein Test, der grün bleibt, wenn man die
Implementierung entfernt, prüft nichts. Jede neue Zusicherung einzeln
neutralisieren und zeigen, dass genau die zugehörigen Tests fallen.
Zwei Fallen, die beide grün blieben:

- Eine Fake-Uhr, die nur beim Schlafen vorrückt, kann eine Zusicherung über
  echte Zeit nicht widerlegen.
- `monkeypatch.setattr(modul.asyncio, "sleep", ...)` greift ins Modul
  asyncio selbst und entschärft die Mechanik im ganzen Prozess. Patche
  einen Modul-Alias (`_sleep = asyncio.sleep`), nicht das fremde Modul.

Handgeschriebene Fixtures kodieren die Annahme des Autors und können sie
nicht widerlegen. Mindestens eine aufgezeichnete Antwort pro externem
Endpunkt, mit Aufnahmedatum.

### Wenn etwas rot ist

Roter Live-Test: erst die Quelle abfragen, dann einordnen. Nicht aus der
Fehlermeldung schliessen. Am 3.8.2026 hiess "nicht gefunden" nicht, dass der
Datensatz weg war, sondern dass die Quelle die Schreibweise ihrer Kopfzeile
gewechselt hatte — vier von sechs Datensätzen produktiv kaputt, alle
Unit-Tests grün.
PR ohne jeden Check ist selten ein Repo ohne CI, meistens ein
Merge-Konflikt: GitHub berechnet dafür keinen Merge-Commit und startet nichts.
Ein Codex-Review auf einem PR wird beantwortet oder behoben, nie ignoriert.

## Teil 2 — dieses Repo

**ruff-Pin: in `pyproject.toml`, an einer Stelle.** `[dev]` fordert
`ruff==0.16.1`; `pip install -e ".[dev]"` installiert damit lokal genau die
Version der CI, und `ci.yml` installiert ruff nicht mehr separat. Eine
`.pre-commit-config.yaml` gibt es nicht — wer eine anlegt, pinnt dort
dieselbe Version oder verlagert den Pin ganz dorthin, aber nie beides.

Vor dem Lauf `ruff --version` prüfen: ein älteres ruff früher im `PATH`
schlägt den Pin, ohne dass der Install etwas meldet.

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

**Live-Tests laufen geplant.** `.github/workflows/nightly-live.yml` fährt
`PYTHONPATH=src pytest tests/ -m live` täglich um 04:17 UTC (cron
`17 4 * * *`) und öffnet bei Upstream-Fehlern ein Issue mit Label
`nightly-live-failure`, statt den Lauf rot zu färben. DRIFT-005 ist damit
erfüllt — Live-Tests sind nicht bloss per `-m "not live"` ausgeschlossen.
Ein offenes `nightly-live-failure`-Issue vor der Arbeit prüfen.
