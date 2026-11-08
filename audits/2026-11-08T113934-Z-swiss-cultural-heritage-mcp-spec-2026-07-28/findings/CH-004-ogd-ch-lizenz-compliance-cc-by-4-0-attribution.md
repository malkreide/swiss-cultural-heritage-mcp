## Finding: CH-004 — OGD-CH Lizenz-Compliance: CC BY 4.0 Attribution

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `CH-004` |
| **PDF-Reference** | Custom (OGD-CH-Richtlinien) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Quelle+Lizenz-Felder sind vorhanden und bei Aggregation pro Quelle erhalten (Kriterien 1 und 3 erfuellt). Nicht erfuellt: korrekte Lizenz (SIKART) und README-Lizenztabelle. Nebenbefund ausserhalb des Checks: Das Live-Schema des SIKART-Datensatzes hat NAME, HAUPTNR, SIKART_LINK nicht mehr (Felder heute: _id, NUTZUNGSLIZENZ, ID, PERMALINK, NACHNAME_VORNAME, VORNAME_NACHNAME, ...). server.py:1317 liest rec.get('NAME'), 1473 SIKART_LINK, 1527 filtert heritage_get_artist auf HAUPTNR. Laufzeit am publizierten 0.6.0: heritage_search_artists rendert '## (Unbekannt)' statt des Namens. Fixtures (2026-09-20) tragen die alten Felder, daher alle Unit-Tests gruen.

### Expected Behavior

Aus dem Katalog (`checks/CH-004.md`, Pass Criteria):

- [ ] Tool-Antworten enthalten `source`-Feld mit Quelle und Lizenz
- [ ] README dokumentiert alle verwendeten Datenquellen mit Lizenzen
- [ ] Bei Aggregation: Provenance pro Datensatz erhalten (nicht nur global)
- [ ] Keine Lizenz-Konflikte (z.B. CC BY-NC mit kommerzieller Verwendung)
- [ ] Attribution-Text genau gemäss Lizenz-Vorgabe (z.B. CC BY 4.0 verlangt: Autor, Quelle, Lizenz, ggf. Modifikation)

### Evidence

- src/swiss_cultural_heritage_mcp/server.py:587-616 — SourceInfo-Konstanten je Quelle (name, license, url); SIKART: license="CC BY" (Zeile 588), SNM "CC BY / CC0 (pro Datensatz)", NB "offen / pro Datensatz", Memobase/Dodis getrennt Metadaten/Digitalisat
- src/swiss_cultural_heritage_mcp/server.py:619-631 — _attribution() haengt an jede Markdown-Antwort einen Footer «Datenquelle & Lizenz» mit Quelle + Lizenz + URL
- src/swiss_cultural_heritage_mcp/server.py:2400-2465 — heritage_cross_search fuehrt source/license/url pro Quelle (Provenienz pro Teilergebnis bei Aggregation erhalten); JSON-Envelope traegt `source`-Liste (Laufzeit: probe_cross2.py, Feld "source" mit name/license/url je Quelle)
- curl -A 'swiss-cultural-heritage-mcp/0.7.0 (...)' 'https://ckan.opendata.swiss/api/3/action/datastore_search?resource_id=ef3a9fd2-2fb3-49ee-bfba-75d58e40b2ea&q=Hodler&limit=2' am 2026-11-08T11:54:13Z → HTTP 200, total 25, NUTZUNGSLIZENZ beider Records = 'Nutzungslizenz: CC0' (bestaetigt die Messung der Hauptsession von 11:53 UTC; mit curl-Default-UA kam nginx-403 — keine Auskunft, nur UA-Sperre)
- tests/fixtures/artists_1.json:16 (aufgezeichnet 2026-09-20 laut tests/fixtures/PROVENANCE.md:3) — NUTZUNGSLIZENZ = 'Nutzungslizenz: CC-BY-NC-SA'; der Server meldete damals wie heute pauschal 'CC BY'
- git show HEAD:README.md:293 — nur Fliesstext «opendata.swiss datasets carry open licences (CC0 / CC BY)» und «The licence line in the attribution footer is the source's general statement, not a per-record one, and JSON responses carry no footer at all»; keine Tabelle Quelle | Lizenz | Attribution
- src/swiss_cultural_heritage_mcp/server.py:1562 — Per-Record-Lizenz (NUTZUNGSLIZENZ) wird nur in heritage_get_artist ausgewiesen; Suchergebnisse zeigen den pauschalen Footer

### Gaps

- medium: SIKART-Lizenzangabe 'CC BY' ist durch die Quelle nicht gedeckt — live heute CC0, in der Aufzeichnung vom 2026-09-20 CC-BY-NC-SA. Im zweiten Fall verschwieg das Label NC und SA (Lizenzkonflikt/Re-Lizenzierung), im ersten fuegt es eine Attributionspflicht hinzu, die es nicht gibt. Der Footer der Suchantworten gibt so eine falsche Lizenz weiter
- medium: README fuehrt keine Tabelle aller fuenf Quellen mit Lizenz und Attribution-Text (Pass-Kriterium 2); nur ein Sammelsatz
- low: Per-Record-Lizenz nur in der Detailansicht; die Detailansicht filtert ueber HAUPTNR, das im Live-Schema fehlt (siehe Hinweis) — damit erreicht die massgebliche Lizenz die nutzende Person kaum

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

Die Schweizer Open-Government-Data-Strategie (OGD-CH) verlangt, dass Daten von Bund, Kantonen und Gemeinden unter offenen Lizenzen publiziert werden. Standard ist **CC BY 4.0** (Creative Commons Attribution 4.0 International) oder vergleichbare offene Lizenzen.

Für MCP-Server, die OGD-Daten abrufen und an LLM-Clients weiterleiten, gilt:

1. **Quelle nennen:** Jede Tool-Antwort, die OGD-Daten enthält, muss die Datenquelle angeben (Anbieter + Lizenz)
2. **Lizenz im README:** Der Server muss klar dokumentieren, welche Datenquellen unter welcher Lizenz verwendet werden
3. **Keine Re-Lizenzierung:** Daten können nicht unter restriktivere Lizenzen weitergegeben werden
4. **Provenance erhalten:** Bei Aggregation aus mehreren Quellen muss die Quelle pro Datensatz nachvollziehbar bleiben

OGD-CH-Datenquellen im Schweizer Kontext:
- opendata.swiss (zentrales Portal Bund)
- statistik.zh.ch (Kanton Zürich)
- data.stadt-zuerich.ch (Stadt Zürich)
- meteoswiss / MétéoSuisse
- BFS Bundesamt für Statistik
- Curia Vista (parlament.ch)

### Remediation

Aus dem Katalog (`checks/CH-004.md`, Remediation), auf die Gaps oben anzuwenden:

### Schritt 1: Provenance-Envelope einführen

Wie im Pass-Pattern oben — `OGDResponse` als Standard-Return-Type für alle OGD-Tools.

### Schritt 2: README-Sektion ergänzen

Standardvorlage:

```markdown

### Effort Estimate

Katalog-Richtwert (checks/CH-004.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — < 1 Tag pro Server.
