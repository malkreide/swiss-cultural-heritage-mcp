# CLAUDE.md

## Teil 1 — Konventionen (portfolio-weit)

### Vor der Arbeit

Klon-Aktualität prüfen: `git fetch origin main && git rev-list --count HEAD..origin/main`
Ein veralteter Klon erzeugt eine rote CI, deren Ursache nicht im Diff steht.
Am 3.8.2026 zweimal passiert — beide Male fehlten genau die Commits, die
das Gate einführten, an dem der Branch scheiterte.
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

**ruff-Pin: nur in der CI.** `.github/workflows/ci.yml` installiert
`ruff==0.16.1`. Es gibt keine `.pre-commit-config.yaml`, und `[dev]` in
`pyproject.toml` fordert nur `ruff>=0.4.0` — `pip install -e ".[dev]"` zieht
also die jeweils neueste Version. Lokal darum explizit
`pip install ruff==0.16.1`, sonst meldet ruff Abweichungen, die niemand
verursacht hat.

Gates, wörtlich aus `ci.yml` (Python 3.11 / 3.12 / 3.13):

```bash
PYTHONPATH=src pytest tests/ -m "not live"
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
python scripts/check_version_sync.py
```

**Live-Tests laufen geplant.** `.github/workflows/nightly-live.yml` fährt
`PYTHONPATH=src pytest tests/ -m live` täglich um 04:17 UTC (cron
`17 4 * * *`) und öffnet bei Upstream-Fehlern ein Issue mit Label
`nightly-live-failure`, statt den Lauf rot zu färben. DRIFT-005 ist damit
erfüllt — Live-Tests sind nicht bloss per `-m "not live"` ausgeschlossen.
Ein offenes `nightly-live-failure`-Issue vor der Arbeit prüfen.
