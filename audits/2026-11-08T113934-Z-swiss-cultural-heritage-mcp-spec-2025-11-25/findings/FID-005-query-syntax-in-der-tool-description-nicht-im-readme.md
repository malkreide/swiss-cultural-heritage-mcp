## Finding: FID-005 — Query-Syntax in der Tool-Description, nicht im README

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | enforced |
| **Check-Status** | fail |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `FID-005` |
| **PDF-Reference** | Custom (Portfolio-Fundstück termdat-mcp#11) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Die Descriptions beschreiben Zugangswege und Fuzzy-Retries ausfuehrlich, aber nicht die Syntax, die das Modell selbst einsetzen koennte. Fuer eine deutschsprachige Quellenlandschaft wiegt die fehlende Granularitaetsangabe am schwersten.

### Expected Behavior

Aus dem Katalog (`checks/FID-005.md`, Pass Criteria):

- [ ] Jedes Tool mit freiem Such-Argument nennt die Abfragesprache namentlich in der Description
- [ ] Die unterstützten Operatoren sind konkret aufgeführt (`*`, `?`, `~`, Phrasen-Quoting, boolesche Operatoren)
- [ ] Die Matching-Granularität ist benannt (ganze Wörter / Substring / Präfix) — bei deutschsprachigen Quellen mit Kompositum-Beispiel
- [ ] Ein Live-Test belegt die Wildcard-Wirkung
- [ ] Falls Sonderzeichen escaped werden müssen, ist das dokumentiert — inklusive Verhalten bei ungültiger Syntax
- [ ] Die Description steht im Tool, nicht ausschliesslich im README

### Evidence

- tools/list (lokal aus dem installierten Paket, 11 Tools) | rg -n -i -U 'wildcard|lucene|cql|solr|whole\s+word|ganze[nm]?\s+W|Kompos|trunkier|platzhalter' -> nur zwei Treffer: heritage_search_museum_datasets 'Präfix-Wildcards' (beschreibt den automatischen Fuzzy-Retry des Servers, keine Syntax fuer den Aufrufer) und search_heritage 'JSON-REST/Solr' (Protokoll). Damit ist auch belegt, dass das Muster anschlaegt. Kein Tool nennt Abfragesprache, Operatoren oder Matching-Granularitaet.
- src/swiss_cultural_heritage_mcp/server.py:1340-1344, :1376-1384 — heritage_search_artists sagt nur 'mehrere Begriffe werden UND-verknüpft'. Live 2026-11-08 (datastore_search, plain=Default): 'Hodler' 25, 'Hodl' 0, 'Hodl*' 0 — Ganzwort-Matching, `*` wirkungslos; nur plain=false mit 'Hodl:*' ergibt 26, und das sendet der Server nie.
- src/swiss_cultural_heritage_mcp/server.py:1215-1225, :1877-1886 — Helveticat: der Begriff wird in eine CQL-Phrase gesetzt, `*` bleibt erhalten. Live: alma.all_for_ui="Volksschule" 1990, "Volksschul*" 81, "Volksschule*" 1990. Trunkierung wirkt, aber nicht wie erwartet, und keine Description dokumentiert sie.
- src/swiss_cultural_heritage_mcp/server.py:2762-2767, :2326-2334, :1755 — search_heritage, heritage_cross_search, heritage_browse_collection: das Such-Argument ist nur 'Suchbegriff (z. B. ...)', ohne jede Syntax-Angabe.
- tests/test_server.py:1956-2050 — die 4 Live-Klassen pruefen keine Wildcard- oder Kompositum-Wirkung.

### Gaps

- Kein Tool mit freiem Such-Argument nennt die Abfragesprache (CKAN-Volltext, Solr, CQL, Memobase, Dodis-Solr) (Severity medium).
- Die Matching-Granularitaet (ganze Woerter, kein Teilwort, deutsches Kompositum-Beispiel) ist nirgends benannt, obwohl sie live belegt ist (Hodl 0 vs Hodler 25) (Severity medium).
- SIKART: Praefixsuche ist ueber den Server gar nicht moeglich (plain=true fest), und das steht nicht in der Description (Severity medium).
- Kein Live-Test der Wildcard-Wirkung; kein Hinweis zu Escaping oder ungueltiger Syntax (Severity low).

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

Wenn ein Such-Argument eine eigene Abfragesprache spricht — Lucene, CQL, SQL-Fragmente, Regex, Glob, SPARQL-Filter —, dann ist diese Sprache Teil der Aufrufkonvention und gehört in die Tool-Description. Steht sie nur im README, existiert sie für das Modell nicht: Das README wird nicht an den Kontext weitergereicht, die Description schon.

Besonders folgenreich ist die **Matching-Granularität**. Die meisten Volltextindizes matchen auf ganzen Wörtern. Für Deutsch heisst das: Komposita werden von ihren Bestandteilen nicht gefunden. «Quellensteuer» findet «Quellensteuerverordnung» nicht — «Quellensteuer\*» schon. Im Portfolio-Fall kostete das drei von sechs erreichbaren Treffern, und zwar zusätzlich zum eigentlichen Scope-Bug: Selbst nach dessen Behebung bleibt ein Modell ohne Kenntnis der Wildcard-Semantik unter dem möglichen Recall.

Für ein Portfolio aus Schweizer Verwaltungsdatenquellen ist das kein Randfall, sondern der Normalfall. Deutsche Verwaltungssprache ist Kompositasprache; die Trefferquote hängt daran, ob das Modell weiss, dass es einen Stern anhängen darf.

Der Check ist eng verwandt mit FID-003: Der dort geforderte Hinweis bei Leermengen ist nur dann umsetzbar, wenn das Modell die Syntax kennt, auf die er verweist.

### Remediation

Aus dem Katalog (`checks/FID-005.md`, Remediation), auf die Gaps oben anzuwenden:

```diff
  """Search the terminology database for official designations.
+
+ `search_term` is **Lucene query syntax**: `*` and `?` wildcards and the `~`
+ fuzzy operator work. Matching is on whole words, so a compound is not found
+ by its parts — «Quellensteuer» does not match «Quellensteuerverordnung», but
+ «Quellensteuer*» does. Reach for a wildcard before concluding a term is absent.
  """
```

Automatisches Anhängen von Wildcards ist ausdrücklich **kein** akzeptabler Ersatz: Es macht Phrasensuche unmöglich und verschiebt das Problem, statt es zu dokumentieren.

### Effort Estimate

Katalog-Richtwert (checks/FID-005.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — Pro Tool 10–20 Minuten.
