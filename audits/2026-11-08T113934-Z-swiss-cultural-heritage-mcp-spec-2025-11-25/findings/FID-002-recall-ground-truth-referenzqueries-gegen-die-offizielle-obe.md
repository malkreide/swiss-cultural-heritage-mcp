## Finding: FID-002 — Recall-Ground-Truth: Referenzqueries gegen die offizielle Oberfläche

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | enforced |
| **Check-Status** | fail |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `FID-002` |
| **PDF-Reference** | Custom (Portfolio-Fundstück termdat-mcp#11) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Fail, weil die geforderten Artefakte vollstaendig fehlen und die vorhandene Live-Suite nachweislich gruen bleibt, waehrend eine Quelle inhaltlich ausfaellt. Das offene Issue #106 (nightly-live-failure, 2026-10-19) existiert; seine Ursache wurde nicht untersucht.

### Expected Behavior

Aus dem Katalog (`checks/FID-002.md`, Pass Criteria):

- [ ] 3–5 Referenzqueries definiert, die den typischen Nutzungsfall abdecken (nicht nur den Anchor-Demo-Query)
- [ ] Trefferzahlen beider Oberflächen zum selben Zeitpunkt gemessen und dokumentiert
- [ ] Jedes Delta ist erklärt — Zählweise, Kürzung, Sprachraum, Feldabdeckung
- [ ] Recall-Regressionstest mit Untergrenzen existiert und läuft unter `@pytest.mark.live`
- [ ] Der Vergleich deckt **Query-/Such-Endpoints** ab, nicht nur Listen-Endpoints
- [ ] Bei Servern ohne offizielles Web-UI: dokumentierte Ersatz-Ground-Truth (Bulk-Dump-Zeilenzahl, veröffentlichte Bestandszahlen)

### Evidence

- rg -n -i 'ground.truth|recall|Referenzquer|Web-UI|reality-check|Untergrenze|floor' ueber das Repo ohne audits/ und Fixture-Daten -> keine Referenzquery-Tabelle; die einzigen Treffer sind fachfremd (CHANGELOG.md:734 und pyproject.toml:35: 'floor' = SDK-Versionsuntergrenze). Kontrolle: das Muster 'Web-UI' trifft FID-002.md des Katalogs.
- tests/test_server.py:1956-2110 — alle 11 Live-Tests; keiner mit Mindest-Trefferzahl. SIKART/SNM pruefen nur 'Fehler' not in result (:1960-1977), Memobase/Dodis nur isinstance(result, str) (:2054-2075), NB nur 'Gefunden:' in result (:2003).
- pytest tests/ -m live (lokal, 2026-11-08) -> '11 passed, 417 deselected', waehrend heritage_search_artists live jede Person als '(Unbekannt)' mit SIKART-ID '—' ausgibt und heritage_get_artist auf jede ID HTTP 409 liefert (siehe FID-006). Die Live-Suite ist keine Recall- oder Inhaltswache.
- PROBE_REPORT_helveticat.md:195-206 — die einzigen Trefferzahlen (SRU, 20.09.2026), aber nur API gegen API, kein Vergleich mit helveticat.ch. Fuer SIKART, SNM, Memobase und Dodis gibt es keine Messung gegen eine offizielle Oberflaeche und keine Ersatz-Ground-Truth.
- Die Durchreiche selbst ist treu (gemessen 2026-11-08): SRU numberOfRecords 1990 fuer 'Volksschule' = Tool total 1990; datastore total 25 fuer 'Hodler' = Tool total 25; Memobase hydra:totalItems 56 = Tool total 56. Das belegt API-Treue, nicht Recall gegen die Web-UI.

### Gaps

- Kein Set von 3-5 Referenzqueries mit Trefferzahlen beider Oberflaechen (Severity high).
- Kein Recall-Regressionstest mit Untergrenzen unter @pytest.mark.live (Severity high).
- Keine Ersatz-Ground-Truth (Bestandszahl SIKART 17665, Dodis-/Memobase-Bestand) dokumentiert und gegen das Tool gehalten (Severity medium).
- Ein Web-UI-Vergleich wurde in diesem Lauf nicht durchgefuehrt (recherche.sik-isea.ch, memobase.ch und dodis.ch sind JS-Apps). Das Urteil stuetzt sich auf das Fehlen der Artefakte, nicht auf ein gemessenes Delta.

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

Ein MCP-Server ist eine zweite Oberfläche auf einen Bestand, für den es bereits eine erste gibt: das offizielle Web-UI der Datenquelle. Diese erste Oberfläche ist die einzige verfügbare Ground Truth. Wer sie nicht abfragt, hat kein Mittel festzustellen, ob der Server liefert, was die Quelle hat.

Der Unterschied zu einem gewöhnlichen Integrationstest ist grundsätzlich: Ein Test gegen die API prüft, ob der Server die API korrekt bedient. Ein Recall-Vergleich gegen das Web-UI prüft, ob die Bedienung **vollständig** ist. Der zweite Fall ist der, der `termdat-mcp` durchgerutscht ist — 33 grüne Offline-Tests und 3 grüne Live-Tests, während zwei Prozent des Bestands durchsucht wurden. Kein Mock kann diese Klasse finden, weil er genau die Annahme abbildet, die falsch ist.

Bemerkenswert am Portfolio-Fall: Der `mcp-data-source-probe`-Skill enthielt die Regel bereits (Abschnitt 1.4, «Reality-Check gegen Homepage-Zahlen»). Sie wurde auf die Listen-Endpoints angewandt — 140 Collections, 23 Classifications, beide korrekt — und nie auf den Such-Endpoint. Nicht die Regel fehlte, sondern ihre Reichweite. Dieser Check zieht die Regel auf Query-Endpoints, weil dort der Recall entsteht.

Der Vergleich ist zusätzlich das einzige Frühwarnsystem für **Upstream-Default-Änderungen**. Bei einem Portfolio aus 30+ Servern gegen Behörden-APIs ist die Frage nicht, ob eine Quelle ihre Defaults ändert, sondern welche zuerst.

### Remediation

Aus dem Katalog (`checks/FID-002.md`, Remediation), auf die Gaps oben anzuwenden:

1. 3–5 Referenzqueries wählen: je einer mit vielen Treffern, einer mit wenigen, einer mit Kompositum/Sonderzeichen.
2. Beide Oberflächen am selben Tag abfragen, Zahlen in eine Tabelle.
3. Jedes Delta auflösen, bis die Erklärung belastbar ist. Ist sie es nicht, ist der Befund offen und gehört ins README.
4. Untergrenzen als `@pytest.mark.live`-Test festschreiben.
5. Optional in den `mcp-continuous-auditor` als Recall-Canary übernehmen, damit der Vergleich wiederkehrend läuft statt einmalig.

### Effort Estimate

Katalog-Richtwert (checks/FID-002.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — Pro Server 2–3 Stunden für Erstmessung und Test. Der wiederkehrende Lauf ist Automatisierung, kein Aufwand.
