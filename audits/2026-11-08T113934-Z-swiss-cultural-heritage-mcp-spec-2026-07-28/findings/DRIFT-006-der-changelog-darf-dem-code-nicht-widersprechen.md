## Finding: DRIFT-006 — Der CHANGELOG darf dem Code nicht widersprechen

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | enforced |
| **Check-Status** | fail |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `DRIFT-006` |
| **PDF-Reference** | Custom (Portfolio-Fundstück swiss-energy-mcp, 2026-08-01) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Modus 1 geführt an CHANGELOG [0.7.0] (Stichprobe von 8 Behauptungen, alle gedeckt), an den README-Einschränkungen und an den Workflow-Kommentaren. Die drei Widersprüche liegen ausserhalb des CHANGELOG. Nicht jede Zeile des 0.7.0-Abschnitts wurde einzeln geprüft, etwa die Messaussagen vom 20.09.

### Expected Behavior

Aus dem Katalog (`checks/DRIFT-006.md`, Pass Criteria):

- [ ] Jeder Eintrag in `[Unreleased]` beschreibt Arbeit, die **nicht** auf `main` ist oder noch nicht publiziert wurde
- [ ] Kein Satz in CHANGELOG, README oder Doku bezeichnet als ausstehend, geplant oder ausserhalb des Scopes, was bereits gemergt ist
- [ ] Keine dokumentierte Einschränkung, die der Code nicht mehr hat
- [ ] Keine Docstrings oder Kommentare mit «noch nicht», die der umgebende Code widerlegt
- [ ] Widersprüche wurden **gefunden, indem jede Behauptung geprüft wurde** (Modus 1) — eine leere `grep`-Trefferliste allein ist `not_verified`, nicht Pass
- [ ] Der PR, der eine Absicht ausführt, korrigiert im selben Diff den Satz, der sie als Absicht führt

### Evidence

- git show HEAD:README.md:155 und README.de.md:156 — 'In claude.ai … add: https://your-app.onrender.com/sse'. Laufzeit-Probe scratchpad/probe/sse_probe.py (build_http_app über den Starlette TestClient, ohne Port): routes ['/mcp', '/health'], GET /sse -> 404, GET /mcp -> 400; server.py:3574 baut nur mcp.streamable_http_app. Dazu README:146 'Cloud Deployment (SSE for browser access)', :157 'SSE for the browser' und das Diagramm :223 'Stdio | SSE'
- git show HEAD:README.md:289 und README.de.md:290 — 'All tools perform HTTP GET requests only'; dem widerspricht server.py:2724-2726: _search_dodis ruft _http_post(f"{DODIS_API}/solr/query") (search_heritage mit collection dodis oder all); docs/roadmap.md:7 wiederholt 'only HTTP GET requests'
- .github/workflows/nightly-live.yml:3-6 — Kommentar 'Upstream failures do NOT fail this workflow … The job itself stays green by design'; widerlegt durch :116-124 (exit 1 bei state != clear) und durch Lauf 39233988544 (2026-10-19) mit conclusion failure. CLAUDE.md:368-369 behauptet dasselbe ('statt den Lauf rot zu färben')
- CHANGELOG.md:8 — [Unreleased] ist leer. [0.7.0] stichprobenartig gegen den Code gehalten, alles gedeckt: SOURCE_NB.name (server.py:599), SRU-Index-Whitelist _SRU_INDEXES/_cql_term (server.py:1204-1222), SRU_MAX_RECORDS=50 (1212), '11 von 15' = 11 @mcp.tool + 2 resource + 2 prompt (grep zählt 15), codex-gate-Dateien entfernt (ls .github/workflows scripts | grep -i codex leer), 32 Tests in tests/test_helveticat_zugaenge.py, SKIP_VERSION_SYNC_HOOK in .githooks/pre-commit:79

### Gaps

- README (EN/DE) nennt einen /sse-Endpunkt, den der Server nicht ausliefert (404); die Cloud-Anleitung führt ins Leere (medium)
- Workflow-Kopfkommentar und CLAUDE.md beschreiben einen Live-Job, der grün bleibt; tatsächlich wird er rot, seit es 'Ergebnis durchreichen' gibt (medium)
- README (EN/DE) und docs/roadmap.md behaupten 'nur HTTP GET', die Dodis-Suche nutzt POST; read-only bleibt richtig, die Begründung nicht (low)

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

Ein CHANGELOG ist kein Beiwerk, sondern eine Reihe von Behauptungen über den Code. Der Abschnitt `[Unreleased]` ist dabei die einzige Stelle im Repository, die in die **Zukunft** zeigt: Wer ihn liest — die Maintainerin nach zwei Wochen, die Auditorin beim Einstieg, die Nutzerin vor dem Upgrade —, liest ihn als Plan. Was dort steht, gilt als noch nicht getan.

**Der Fall** (`swiss-energy-mcp`): Im `[Unreleased]` stand, die Migration auf das 2.x-SDK bleibe

> a separate, deliberate piece of work

— sie war zu diesem Zeitpunkt längst gemergt. Der Satz war einmal richtig gewesen, hatte den PR überlebt, der ihn widerlegte, und stand nun als Absichtserklärung über einem Repo, das die Absicht bereits ausgeführt hatte.

**Warum das teurer ist als ein fehlender Satz.** Eine Lücke in der Doku führt dazu, dass jemand nachsieht. Ein falscher Satz führt dazu, dass niemand nachsieht — er beantwortet die Frage, bevor sie gestellt wird, und zwar plausibel. Im Fall oben lieferte er zusätzlich eine fertige Erklärung für einen Zustand, der dringend war: Ein Artefakt auf dem Index, das nicht mehr startete, sah aus wie die bekannte, bewusst zurückgestellte Migration — nicht wie ein Ausfall (`IDENT-007`). Die falsche Prosa war die Deckung, unter der ein Befund liegen blieb.

Das ist derselbe Mechanismus wie in `DRIFT-003`, eine Ebene höher: Dort erfüllt der Degradationspfad die Assertion, hier erfüllt die veraltete Absicht die Frage. Beide Male sieht der Ausfall aus wie der erwartete Fall.

### Abgrenzung

| Check | Frage |
|---|---|
| `IDENT-004` | Stimmt die **Zahl** in der Doku (Badge, dokumentierte Version)? Mechanisch vergleichbar, per Skript erzwingbar |
| `IDENT-006` | Ist `[Unreleased]` zu **alt** — steht dort Unveröffentlichtes, das längst hätte released sein müssen? |
| `DRIFT-006` | Ist der Inhalt **wahr** — beschreibt er den Code, wie er heute ist? |

Die drei sind unabhängig. Ein leeres `[Unreleased]` besteht `IDENT-006` und sagt hier nichts; ein aktuelles Badge sagt nichts über einen Satz drei Zeilen darunter. Und dieser Check ist der einzige der drei, für den kein Skript existiert: Zahlen lassen sich vergleichen, Sätze nicht. Deshalb überlebt genau diese Sorte Fehler am längsten — und deshalb ist die Severity `medium` und nicht niedriger: Es bricht nichts, aber es führt die Person in die Irre, die gerade hinsieht.

### Drei Familien, dieselbe Wurzel

1. **`[Unreleased]`-Einträge, die Arbeit als ausstehend beschreiben, die gemergt ist.** Der Fall oben. Entsteht typischerweise so: Der PR, der die Arbeit tat, fügte oben einen `### Added`-Eintrag hinzu — und liess den Satz weiter unten stehen, der sie als ausserhalb des Scopes bezeichnete.
2. **README oder Doku behauptet eine Einschränkung, die es nicht mehr gibt.** «Unterstützt derzeit nur stdio», nachdem HTTP-Transport ausgeliefert wurde. Kostet Nutzung, nicht Korrektheit — aber es kostet sie still.
3. **Kommentare und Docstrings mit «noch nicht».** Der lokalste Fall und der langlebigste, weil ihn nur liest, wer ohnehin schon im Code steht — und dann glaubt.

### Remediation

Aus dem Katalog (`checks/DRIFT-006.md`, Remediation), auf die Gaps oben anzuwenden:

### Schritt 1: Den Satz korrigieren, wo er steht

Streichen oder umschreiben — und zwar in dem Zustand, den der Code heute hat, nicht im nächsten Release:

```diff
  ## [Unreleased]

  ### Added
  - Migration auf das 2.x-SDK

- Die Migration auf 2.x bleibt a separate, deliberate piece of work.
```

### Schritt 2: In denselben PR ziehen

Die Regel, die den Rückfall verhindert, ist eine Reihenfolge, kein Werkzeug: **Wer eine Absicht ausführt, streicht sie im selben Diff.** Das kostet dort dreissig Sekunden und ist der einzige Moment, in dem beide Textstellen jemandem gleichzeitig vor Augen stehen.

### Schritt 3: Beim Release den Abschnitt lesen, nicht verschieben

Ein Release ist der letzte Punkt, an dem `[Unreleased]` als Ganzes gelesen wird. Wer den Abschnitt dort einmal Zeile für Zeile gegen `git log` hält, findet die Sätze, die Schritt 2 durchgerutscht sind. Bei generierten CHANGELOGs gehört dieser Blick explizit in die Release-Checkliste, weil ihn sonst niemand tut.

### Effort Estimate

Katalog-Richtwert (checks/DRIFT-006.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — den einzelnen Satz zu korrigieren, kostet Minuten. Der Aufwand liegt im Durchgehen: Ein Repo mit langem `[Unreleased]` braucht eine halbe Stunde, in der jede Zeile gegen die Historie gehalten wird.
