## Finding: OPS-003 — Phasenarchitektur: Read-only First, dann Write, dann Multi-Agent

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `OPS-003` |
| **PDF-Reference** | Anhang C4 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Die Phase ist deklariert und durch die Laufzeit-Annotationen gedeckt, eine Roadmap mit Gates gibt es. Abzug für das abweichende Phasenmodell. Folgen hat es derzeit keine (keine Write-Tools), es lenkt aber die nächste Erweiterung.

### Expected Behavior

Aus dem Katalog (`checks/OPS-003.md`, Pass Criteria):

- [ ] Aktuelle Phase explizit im README deklariert (Phase 1 / 2 / 3)
- [ ] Phase entspricht den tatsächlichen Tool-Annotations (kein Phase-1-Server mit destruktiven Tools)
- [ ] Roadmap-File mit phasenspezifischen Tasks vorhanden
- [ ] Phase-Übergang erfordert dokumentierte Voraussetzungen:
  - Phase 1 → 2: Audit-Run, ISDS, DSG-Verarbeitungsverzeichnis abgeschlossen
  - Phase 2 → 3: Semantic Layer, Identity-Resolution, GL-Sign-off, Datenschutzbeauftragte:r-Sign-off
- [ ] Phase-Übergänge im CHANGELOG dokumentiert (Synergie zu ARCH-012)

### Evidence

- git show HEAD:README.md:60 und README.de.md:61 — 'Project phase: Phase 1 — read-only. Every tool is annotated readOnlyHint: true'
- Laufzeit scratchpad/probe/annot.py (mcp.list_tools()): alle 11 Tools mit read_only_hint=True, destructive_hint=False; grep '"destructiveHint": (True|False)' in server.py: 11x False, 0x True (das Muster schlägt an einer Testzeile '"destructiveHint": True' an: 1 Treffer)
- docs/roadmap.md:1-40 — Roadmap mit Phase-1-Scope und Checkliste für 1 -> 2 (Audit ohne offene critical/high, ISDS, revDSG-Verzeichnis, Idempotenz, HITL, Trifecta-Neubewertung); Übergänge im CHANGELOG (CHANGELOG.md:765, :834)
- docs/roadmap.md:14 und :24 — 'Phase 2 — write-capable', 'Phase 3 — multi-agent / semantic layer'. Das kehrt das Katalogmodell um (Phase 2 = Anreicherung/Semantic Layer ohne Write, Phase 3 = Write); das Roadmap-Gate erlaubt Schreibzugriff vor Semantic Layer und Identity Resolution

### Gaps

- Die Phasenreihenfolge in docs/roadmap.md weicht vom Katalog ab: Write (Phase 2) vor Semantic Layer (Phase 3); die Voraussetzungen Semantic Layer, Identity Resolution sowie GL- und DSB-Sign-off hängen am falschen Übergang (medium)
- docs/roadmap.md:7 begründet Phase 1 mit 'only HTTP GET', die Dodis-Suche nutzt POST (low, siehe DRIFT-006)

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

Der Anhang sagt klar: «Die häufigste Ursache von MCP-Sicherheitsvorfällen 2025/26 war: ‹Wir haben gleich Schreibzugriffe gebaut, weil es ging.›»

Disziplin: jeder Server durchläuft drei Phasen. Übersprungene Phasen produzieren Sicherheits- und Compliance-Vorfälle.

| Phase | Dauer | Zustand | Was wird gebaut | Was darf NICHT |
|---|---|---|---|---|
| **Phase 1** | Wochen | Read-only-Wrapper | Tools mit `readOnlyHint: true`, OAuth, Gateway davor, Doku, Tests | Kein Write, keine Compensating Actions, kein Multi-Agent |
| **Phase 2** | Monate | Anreicherung | Semantic Layer, Identity Resolution, Knowledge-Graph, Cross-Server-Federation | Noch immer kein Write |
| **Phase 3** | Quartale | Aktion | Schreibzugriffe mit Idempotency + Compensating Actions, optional A2A für Multi-Agent | — |

Die Reihenfolge ist nicht negotiable. Phase 1 muss **abgeschlossen** sein bevor Phase 2 startet:

- Alle Read-Tools sind dokumentiert, getestet, mit Rate-Limit, mit DLP, mit Audit-Logs
- ISDS-Klassifikation und DSG-Verarbeitungsverzeichnis liegen vor (Synergie zu CH-002, CH-005)
- Audit gegen den Skill-Katalog ist gelaufen, kritische Findings sind behoben

Phase 2 muss abgeschlossen sein bevor Phase 3 startet:

- Semantic Layer liegt vor (entweder selbst oder via Federation-Engine — Synergie zu ARCH-007)
- Identity-Resolution ist klar (welcher User darf was schreiben?)
- Compensating-Action-Library ist getestet, idempotency_key-Pattern ist Standard

Dieser Check ist `high`, weil das Überspringen architektonisch und operativ teuer wird — Refactoring eines Phase-3-Servers zurück in Phase 1 ist deutlich aufwendiger als sauberer Phasenaufbau.

### Remediation

Aus dem Katalog (`checks/OPS-003.md`, Remediation), auf die Gaps oben anzuwenden:

### Schritt 1: Phase-Audit pro Server

Pro Server im Portfolio:

| Frage | Antwort |
|---|---|
| Hat der Server destruktive Tools? | ja → mindestens Phase 3 |
| Hat der Server Semantic Layer / Federation? | ja → mindestens Phase 2 |
| Sonst | Phase 1 |

### Schritt 2: Phase-Sektion ins README

Mit Status-Tabelle wie im Pass-Pattern Modus 1.

### Schritt 3: Roadmap erstellen

Mit Phase-Voraussetzungen als Tasks. Falls aktueller Server in Phase 2 oder 3 ist und Phase-1-Voraussetzungen fehlen: Findings im Audit-Tracker dokumentieren, retroaktiv schliessen.

### Schritt 4: Phase-Gate als Notion-Workflow

In Notion-Audit-Tracker-Schema (`a2736a65-...`) ein Feld «Phase» (Single-Select: 1, 2, 3) mit klaren Übergangs-Anforderungen.

### Effort Estimate

Katalog-Richtwert (checks/OPS-003.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — < 1 Tag pro Server für Initial-Phase-Deklaration. M — Wochen für Phase-Übergänge mit allen Compensating-Action-Anforderungen.
