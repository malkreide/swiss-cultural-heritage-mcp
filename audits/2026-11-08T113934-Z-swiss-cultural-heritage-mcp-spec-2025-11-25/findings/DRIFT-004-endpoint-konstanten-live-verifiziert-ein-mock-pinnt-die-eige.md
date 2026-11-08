## Finding: DRIFT-004 — Endpoint-Konstanten live verifiziert — ein Mock pinnt die eigene Annahme

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `DRIFT-004` |
| **PDF-Reference** | Custom (Portfolio-Fundstück meteoswiss-mcp#35, 2026-07-30) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Alle fünf Basis-Konstanten sind live abgedeckt, und die Suite läuft nachweislich täglich gegen die Quelle. Abzüge: keine 404/5xx-Trennung, zwei Pfade bzw. Konstanten ohne wirksame Live-Prüfung. Ein Probe-Manifest (mcp-continuous-auditor) liegt nicht im Repo.

### Expected Behavior

Aus dem Katalog (`checks/DRIFT-004.md`, Pass Criteria):

- [ ] Jede Endpoint-Konstante wird von mindestens einem Live-Test oder einem Probe-Manifest abgedeckt
- [ ] Mocks registrieren gegen die importierte Konstante, nicht gegen ein wiederholtes URL-Literal
- [ ] Der Live-Test unterscheidet 404 (Endpoint weg) von 5xx (transient) — nur Ersteres ist ein Befund
- [ ] Die Abdeckung ist vollständig: kein Endpoint, der nur in Mocks vorkommt

### Evidence

- server.py:267-273 — 5 Endpoint-Konstanten; Live-Abdeckung in tests/test_server.py:1956-2081: CKAN datastore_search (TestLiveSIKISEA), CKAN package_search (TestLiveSNM), NB_OAI_PMH ListSets/ListRecords/GetRecord (TestLiveNB), NB_SRU (test_live_volltextsuche_liefert_treffer), MEMOBASE_API '/' (test_live_search_memobase), DODIS_API solr/query und solr/full (TestLiveHeritageInstitutions)
- gh run view 42475229230 --log (Nightly 2026-11-08, headSha 7f665fa; git diff origin/main HEAD -- tests/test_server.py .github/workflows tests/conftest.py ist leer) — '11 passed, 415 deselected in 13.87s', state=clear
- tests/test_server.py:618-927, tests/test_response_shape.py:102-161, tests/test_helveticat_zugaenge.py:78-408 — respx-Routen gegen die importierten Konstanten (f"{CKAN_API}/datastore_search", NB_SRU, NB_OAI_PMH, f"{DODIS_API}/solr/query"); das einzige Upstream-Literal, tests/test_server.py:550, ist ein Egress-Test (http-Schema) und kein Mock
- scripts/classify_live_run.py:96-140 — die Einordnung kennt nur clear/finding/unknown nach JUnit-Zählern; 404 und 5xx bzw. Timeout landen beide in 'finding'. Beleg: Lauf 39233988544 (2026-10-19) state=finding wegen httpx.ReadTimeout (transient) -> Issue #106
- server.py:3122 MEMOBASE_API '/record/{id}' — kein Live-Test ruft get_heritage_item(collection='memobase'); test_live_search_snm (tests/test_server.py:1975-1978) besteht auch bei 0 Treffern und prüft SNM_ORG (server.py:1636) damit nicht wirksam

### Gaps

- Die Live-Einordnung trennt 404 (Endpoint weg) nicht von 5xx oder Timeout; ein transienter Timeout ergibt denselben Befund wie ein abgeschalteter Endpoint (medium)
- Der Pfad MEMOBASE_API/record/{id} kommt nur in Mocks und Fixtures vor, nicht live (medium)
- Die Konstante SNM_ORG wird im Live-Test nicht wirksam geprüft, 0 Treffer bestehen (medium)

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

`FID-002` und der Recall-Canary decken ab, dass ein Mock eine falsche Annahme über den **Umfang** einer Antwort nicht widerlegen kann. Derselbe Mechanismus gilt eine Ebene tiefer, für die **Existenz** des Endpoints.

Ein `respx`-Mock wird gegen die eigene Konstante registriert:

```python
r.get(OPEN_METEO_BASE).respond(200, json=FIXTURE)
```

Verschwindet der Endpoint upstream, antwortet der Mock unverändert. Die Konstante zeigt ins Leere, die Testsuite bleibt grün, und zwar dauerhaft — es gibt keinen Zeitpunkt, an dem dieser Aufbau den Ausfall bemerken könnte. Der Test prüft die Konsistenz des Servers mit sich selbst.

**Der Fall** (`meteoswiss-mcp`, 2026-07-30): Open-Meteo hat die provider-eigenen Pfade abgeschafft. `https://api.open-meteo.com/v1/meteoswiss` antwortete mit 404, womit `meteo_forecast` und `meteo_school_check` gar keine Daten mehr lieferten — zwei von sechs Tools. Die Unit-Tests waren grün und mockten dieselbe tote URL. Aufgefallen ist es erst, als jemand die Live-Suite ausführte, die aus CI ausgeschlossen ist (siehe `DRIFT-005`).

Der Punkt ist nicht, dass Mocks falsch sind. Er ist, dass die Frage «existiert dieser Endpoint noch» prinzipiell nicht gemockt beantwortet werden kann, und dass es keinen anderen Test gibt, der sie stellt.

### Remediation

Aus dem Katalog (`checks/DRIFT-004.md`, Remediation), auf die Gaps oben anzuwenden:

### Schritt 1: Konstanten inventarisieren

Jede `*_BASE`/`*_URL` in `src/` auflisten. Erfahrungsgemäss sind es mehr als erinnert — Geocoding, Asset-Hosts und Vokabular-Endpoints werden beim ersten Zählen übersehen.

### Schritt 2: Contract-Canary schreiben

Ein parametrisierter `@pytest.mark.live`-Test über alle Konstanten. Er braucht pro Endpoint ein minimales gültiges Parameter-Set — das ist der eigentliche Aufwand und lohnt sich, weil es zugleich dokumentiert, was ein gültiger Aufruf ist.

### Schritt 3: Mocks auf die Konstante umstellen

```diff
- r.get("https://api.open-meteo.com/v1/meteoswiss").respond(...)
+ r.get(OPEN_METEO_BASE).respond(...)
```

### Schritt 4: Dafür sorgen, dass er läuft

Ein Live-Test, den niemand ausführt, ist kein Schutz. Siehe `DRIFT-005`.

### Effort Estimate

Katalog-Richtwert (checks/DRIFT-004.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — ein bis zwei Stunden pro Server. Der Canary ist kurz; das minimale Parameter-Set pro Endpoint kostet die Zeit.
