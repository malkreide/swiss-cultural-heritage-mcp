## Finding: IDENT-003 — Werte, die die Pipeline überschreibt, brauchen einen eigenen Check

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `IDENT-003` |
| **PDF-Reference** | Custom (Portfolio-Sweep 2026-07-29, 30 Server) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Committete und publizierte Seite stimmen; einzig die packages[0]-Transformation erfuellt Kriterium 8 nicht.

### Expected Behavior

Aus dem Katalog (`checks/IDENT-003.md`, Pass Criteria):

- [ ] `server.json → version` stimmt mit `pyproject.toml` überein
- [ ] **Jeder** `packages[*].version` stimmt überein, nicht nur der erste
- [ ] Ein CI-Check erzwingt das, nicht nur eine Konvention
- [ ] Der Check läuft ohne Projekt-Installation (schlanker Lint-Job genügt)
- [ ] Die Werte, die `publish.yml` zur Laufzeit überschreibt, sind dokumentiert
- [ ] Für jeden überschriebenen Wert existiert ein Check auf die committete Fassung
- [ ] **Und einer auf die geschriebene**: Der publizierte Wert wurde zurückgelesen — Registry gegen Index, oder die Transformation nachvollzogen (Modus 3)
- [ ] Die Transformation erfasst **jedes** Vorkommen des Wertes, nicht nur das erste (`packages[0]` ist kein `packages[*]`)
- [ ] Die Ableitung des Wertes ist gegen Nicht-Tag-Läufe abgesichert: Bei `workflow_dispatch` aus einem Branch ist `GITHUB_REF_NAME` der Branch-Name, und ein blindes `${VAR#v}` schreibt `main` als Version

### Evidence

- Modus 1 am HEAD-Export (git archive HEAD): server.json version = '0.7.0', packages[0].version = '0.7.0', pyproject '0.7.0' → beide OK; server.json hat genau einen Package-Eintrag
- git show HEAD:.github/workflows/ci.yml — Schritt 'python scripts/check_version_sync.py' im test-Job (alle drei Python-Versionen); Skript ist reine Standardbibliothek; zusaetzlich .githooks/pre-commit. Lauf HEAD-Export: 'Versions-Sync OK (0.7.0; geprueft: server.json -> version, server.json -> packages[0].version, README.de.md -> Versions-Badge, README.md -> Versions-Badge, audits\tool-pins\current.json -> generated_for_version ...)' exit 0
- Modus 2: git grep 'sed -i|jq |yq -i|GITHUB_REF_NAME|GITHUB_OUTPUT' .github/workflows/ → publish.yml:65-66 (VERSION="${GITHUB_REF_NAME#v}"; jq '.version = $v | .packages[0].version = $v'), nightly-live.yml:41 (nur pytest_exit-Output). Dokumentiert in scripts/check_version_sync.py Docstring und CLAUDE.md
- Modus 3a (geschriebener Wert zurueckgelesen): GET registry.modelcontextprotocol.io/v0/servers?search=swiss-cultural-heritage-mcp → isLatest-Eintrag version 0.6.0, packages[0].version 0.6.0 (publishedAt 2026-09-19T10:11); PyPI info.version 0.6.0 → Registry = Index
- publish.yml:3-5 — Trigger nur 'release: types [published]', kein workflow_dispatch → GITHUB_REF_NAME ist stets der Release-Tag

### Gaps

- low: Transformation schreibt nur .packages[0].version, nicht packages[*] — folgenlos, solange es einen Eintrag gibt (Zustand, keine Eigenschaft)
- low: check_version_sync.py bricht nach der ersten Befundkategorie ab (sys.exit(1) nach DRIFT, vor Tool-Pin und src/-Pruefung); in Kopie mit Badge-Drift UND src-Literal meldete es nur das Badge
- info: Modus 3b (jq lokal ausfuehren) nicht moeglich — jq nicht installiert; ersetzt durch 3a
- info: keine Tag-Form-Pruefung im Workflow (ein Release-Tag ohne 'v' oder mit Suffix ginge ungeprueft durch)

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

`server.json` ist das Manifest für die MCP Registry. Beim Veröffentlichen synchronisiert `publish.yml` die Version daraus **aus dem Tag-Namen** — die committete Fassung erreicht das publizierte Artefakt also nie.

Genau deshalb kann sie beliebig lange falsch sein. Bei `swiss-environment-mcp` stand sie von v0.2.3 bis v0.5.0 auf einer veralteten Nummer: funktional folgenlos, denn in der Registry landete jedes Mal korrekt die Tag-Version. Aufgefallen ist es niemandem, weil nichts brach.

Der Sweep fand vier Server mit dieser Abweichung (`news-monitor`, `swiss-courts`, `swiss-cultural-heritage`, `swiss-statistics` — letzterer 0.3.0 bei Paketversion 0.6.0).

**Der verallgemeinerbare Kern — und der eigentliche Grund für diesen Check:**

> Ein Wert, den die Pipeline zur Laufzeit überschreibt, wird nie geprüft. Er kann beliebig lange falsch sein, ohne dass etwas bricht.

Das gilt über `server.json` hinaus: überall dort, wo CI/CD einen committeten Wert ersetzt (Image-Tags, Chart-Versionen, generierte Manifeste, `.env.example`-Defaults), fehlt der Rückkanal. Der committete Wert wirkt dann nur noch auf **Menschen**, die ihn lesen — und führt sie in die Irre, ohne dass eine Maschine widerspricht.

### Remediation

Aus dem Katalog (`checks/IDENT-003.md`, Remediation), auf die Gaps oben anzuwenden:

`scripts/check_version_sync.py`, reine Standardbibliothek, im `lint`-Job:

```python
found = [("server.json → version", server.get("version", ""))]
for i, pkg in enumerate(server.get("packages", [])):
    found.append((f"server.json → packages[{i}].version", pkg.get("version", "")))

mismatches = [(w, v) for w, v in found if v != version]
if mismatches:
    ...
    sys.exit(1)
```

**Einbau als Schritt in einen bestehenden Job, nicht als eigener Job.** Ein neuer Job erzeugt einen neuen Check-Namen und kann mit Branch-Rulesets kollidieren, die bestimmte Namen als erforderlich führen — im Sweep bei einem Repo real aufgetreten.

Auf Python 3.10 gibt es `tomllib` noch nicht. Wo die Matrix dort beginnt, braucht der Check einen bedingten Import mit Minimal-Parser für die zwei benötigten Felder — sonst stürzt er ab, statt zu prüfen.

### Effort Estimate

Katalog-Richtwert (checks/IDENT-003.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — 30 Minuten inklusive CI-Einbau. Das Inventar der überschriebenen Werte kann länger dauern.
