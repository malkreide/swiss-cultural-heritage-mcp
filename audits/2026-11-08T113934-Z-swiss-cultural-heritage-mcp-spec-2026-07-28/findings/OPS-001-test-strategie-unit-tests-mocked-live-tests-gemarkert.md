## Finding: OPS-001 — Test-Strategie: Unit-Tests mocked + Live-Tests gemarkert

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `OPS-001` |
| **PDF-Reference** | Anhang C1 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Die Struktur (Marker, respx, CI-Ausschluss, geplanter Live-Workflow mit Obergrenze) steht. Abzüge: Live-Abdeckung je Tool und die Kostendisziplin der Live-Suite. Test-Credentials entfallen (auth_model none).

### Expected Behavior

Aus dem Katalog (`checks/OPS-001.md`, Pass Criteria):

- [ ] `tests/test_unit.py` mit mindestens 5 Unit-Tests pro Tool
- [ ] `tests/test_live.py` mit mindestens 1 Live-Test pro Tool
- [ ] Unit-Tests verwenden `respx` (Python) oder `nock` (Node) für HTTP-Mocking
- [ ] Live-Tests sind mit `@pytest.mark.live` (oder Äquivalent) markiert
- [ ] Marker im `pyproject.toml` registriert
- [ ] CI-Workflow läuft `pytest -m "not live"`
- [ ] Separater nightly/manueller Live-Test-Workflow
- [ ] Live-Tests nutzen Test-spezifische Credentials, nicht Production-Keys (Synergie zu SEC-013)
- [ ] Der Live-Workflow hat `timeout-minutes` — eine Obergrenze, die den Normalfall nicht schneidet
- [ ] Die Live-Suite teilt Client und Cache, statt pro Test neu zu laden; der Pool wird beim Teardown geschlossen
- [ ] Test-Timeouts sind enger gesetzt als die Prod-Defaults: eine tote Quelle meldet sich in Minuten, nicht in einer Viertelstunde

### Evidence

- pyproject.toml:88 — Marker registriert: 'live: live API tests (skipped in CI by default)'; tests/test_server.py:1956-2081 — 11 Tests mit @pytest.mark.live (Klassen-Decorator)
- grep -rc respx tests/*.py — respx in test_server.py (131), test_helveticat_zugaenge.py (35), test_response_shape.py (10), test_recorded_fixtures.py (5); Mocks gegen die importierten Konstanten
- .github/workflows/ci.yml:28-29 'PYTHONPATH=src pytest tests/ -m "not live"'; CI-Lauf 41281505123 (2026-11-01): '413 passed, 2 skipped, 11 deselected' auf 3.11 und 3.13
- .github/workflows/nightly-live.yml:10-13, :22 — eigener Live-Workflow (cron täglich, workflow_dispatch), timeout-minutes: 10
- Kein Live-Test für heritage_get_artist, heritage_browse_collection und heritage_cross_search (Zählung der await-Aufrufe in tests/test_server.py:1953-2081: jeweils 0); list_heritage_collections ist statisch
- tests/conftest.py:14-20 — der Client wird nach jedem Test geschlossen, auch für Live-Tests (kein Pool-Leck, aber kein geteilter Client); die Live-Suite läuft mit den Prod-Timeouts http_timeout=30.0, retry_total_budget=25.0 (server.py:94-111), ohne engere Test-Werte

### Gaps

- 3 von 10 Werkzeugen mit externem Abruf haben keinen Live-Test: heritage_get_artist, heritage_browse_collection, heritage_cross_search (medium)
- Mindestens 5 Unit-Tests pro Tool nicht durchgehend: direkte Aufrufe in Tests z. B. heritage_browse_collection 2, heritage_list_nb_collections 2, heritage_get_artist 3 (parametrisierte Aufrufe in test_recorded_fixtures.py nicht mitgezählt) (low)
- Die Live-Suite teilt keinen Client und nutzt Prod-Timeouts; bei 11 Tests begrenzt timeout-minutes: 10 den Schaden (low)
- Datei-Layout weicht ab (kein tests/test_unit.py/test_live.py, Live-Tests in test_server.py); funktional gleichwertig (low)

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

Aus dem Sormena-Pattern bewährt: zwei Test-Kategorien mit klarer Trennung.

| Kategorie | Zweck | Wann ausgeführt | Mock | Speed |
|---|---|---|---|---|
| **Unit-Tests** | Server-Logik isoliert prüfen | CI bei jedem PR | respx-mocked HTTP | ~1s pro Test |
| **Live-Tests** | Echte API-Antworten gegen aktuelle Schnittstellen prüfen | Manuell, nightly, vor Release | keiner | 5-30s pro Test |

Die Trennung ist nicht akademisch — sie löst drei reale Probleme:

1. **CI-Stabilität:** Live-Tests scheitern bei API-Outages der Datenquelle (z.B. opendata.swiss-Wartung). Wenn alle Tests in CI laufen, wird der Server für stable-merge unbrauchbar.
2. **API-Quote-Schutz:** Manche Datenquellen haben Rate-Limits. Live-Tests bei jedem PR brennen Quote, die für Production-Traffic nötig wäre.
3. **Schema-Drift-Detection:** Live-Tests fangen Änderungen der Quell-API auf, die unit-Tests nicht sehen würden — aber sie brauchen Zeit, idealerweise nightly.

Implementation in Python mit pytest:

- Unit-Tests: `tests/test_unit.py` mit `respx` für HTTP-Mocking
- Live-Tests: `tests/test_live.py` mit `@pytest.mark.live`-Decorator
- CI-Workflow: `pytest -m "not live"` (skipt live-Tests)
- Manuell: `pytest -m live` oder `pytest tests/test_live.py`

Dieser Check ist `high`, weil ohne saubere Test-Strategie:

- Refactorings unsicher sind (keine Regression-Detection)
- API-Schema-Drift unbemerkt bleibt
- CI-Pipeline unzuverlässig wird (random Live-Failures)

### Remediation

Aus dem Katalog (`checks/OPS-001.md`, Remediation), auf die Gaps oben anzuwenden:

### Schritt 1: pyproject.toml-Marker registrieren

```toml
[tool.pytest.ini_options]
markers = [
    "live: tests against real APIs (manual, nightly only)",
]
```

### Schritt 2: respx als Dev-Dependency

```toml
[project.optional-dependencies]
dev = [
    "pytest >= 7.4",
    "pytest-asyncio >= 0.21",
    "pytest-cov >= 4.1",
    "respx >= 0.20",
]
```

### Schritt 3: Unit-Test-Suite aufbauen

Pro Tool mindestens drei Tests:
- Happy-Path (200, expected schema)
- Error-Path (4xx/5xx)
- Edge-Case (leere Antwort, malformed input)

### Schritt 4: CI-Workflow updaten

`.github/workflows/test.yml`:

```yaml
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: pytest -m "not live" --cov=src
```

### Schritt 5: Nightly-Live-Workflow

Wie im Pass-Pattern Modus 4, inklusive `timeout-minutes`.

### Schritt 6: Live-Suite auf einen geteilten Client umstellen

Fixture wie im Pass-Pattern Modus 5, Tests nehmen sie als Parameter. Die Laufzeit der Suite vorher und nachher notieren — die Differenz ist das Mass für die eingesparte Fremdlast.

### Effort Estimate

Katalog-Richtwert (checks/OPS-001.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

M — 1–3 Tage Initial-Setup. Tests-Schreiben skaliert mit Tool-Anzahl.
