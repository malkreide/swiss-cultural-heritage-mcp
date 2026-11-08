## Finding: ARCH-019 — Roots, Sampling und Logging: keine Neuimplementierung, Bestand mit Fristdatum

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | advisory |
| **Check-Status** | fail |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `ARCH-019` |
| **PDF-Reference** | SEP-2577 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Baseline beide. Roots und Sampling ungenutzt; das Logging-Protokoll-Feature wird an zwei Stellen genutzt, eine davon nach dem letzten Audit eingefuehrt, und nirgends mit Frist dokumentiert. Das SDK selbst warnt zur Laufzeit. Erfuellt sind nur die Kriterien stderr-Logging und keine Capability-Ankuendigung -> fail.

### Expected Behavior

Aus dem Katalog (`checks/ARCH-019.md`, Pass Criteria):

- [ ] Keine **neue** Nutzung von Roots, Sampling oder dem Logging-Protokoll-Feature seit dem letzten Audit
- [ ] Vorhandene Nutzung ist im README oder CHANGELOG benannt — je Feature mit Zielzustand und Datum
- [ ] Das genannte Datum liegt nicht nach dem frühesten Entfernungstermin (2027-07-28), oder die Abweichung ist begründet
- [ ] Der Zielzustand entspricht der Spec-Empfehlung (Tool-Parameter / Provider-API / `stderr` bzw. OTel), oder die Abweichung ist begründet
- [ ] Anwendungs-Logging nach `stderr` bleibt unberührt und erfüllt weiterhin `OBS-003` und `OBS-004`
- [ ] Auf `spec_baseline: 2026-07-28`: Die Server-Capabilities kündigen keines der drei Features mehr an, sofern nicht bewusst im Restfenster geführt

### Evidence

- Logging-Protokoll-Feature in Gebrauch: server.py:2488 'await ctx.warning(f"Quelle ...")' in heritage_cross_search und server.py:2870 in search_heritage. ctx.warning ruft im SDK Context.log -> session.send_log_message (mcp/server/mcpserver/context.py:265-286, 384-386) und ist dort mit @deprecated('The logging capability is deprecated as of 2026-07-28 (SEP-2577).') markiert.
- Laufzeit (scratchpad/probe_log.py, Dodis 503 via respx, Client(mcp)): search_heritage loest MCPDeprecationWarning an server.py:2870 aus — 'The logging capability is deprecated as of 2026-07-28 (SEP-2577).'
- Herkunft: git log -S'ctx.warning(' -- src/ -> aaec569 2026-06-02 (cross_search, SDK-003) und df58c50 2026-07-19 (federated facade Memobase+Dodis) — die zweite Nutzung ist nach dem letzten Audit (2026-06-02) neu hinzugekommen.
- Dokumentation: rg -c -i 'deprecat|abkündig|rückbau|2027-07-28' auf HEAD:README.md, README.de.md, CHANGELOG.md -> je 0 Treffer; Negative Kontrolle: dasselbe Muster trifft venv/.../mcp/server/mcpserver/context.py 12-mal. CHANGELOG.md:830 beschreibt ctx.warning nur als Feature (SDK-003), ohne Frist oder Zielzustand.
- Roots/Sampling: rg 'roots/list|list_roots|RootsCapability|ListRootsRequest|sampling/createMessage|create_message|CreateMessageRequest|samplingCapability' src/ -> keine Treffer im eigenen Code (dieselbe rg-Zeile trifft die ctx.warning-Stellen, Muster greift).
- Positiv: Anwendungs-Logging geht als JSON nach stderr (server.py:155-183, structlog WriteLoggerFactory(file=sys.stderr)); server/discover (2026-07-28) kuendigt keine logging-Capability an (capabilities nur prompts/resources/tools, scratchpad/probe_modern.out).

### Gaps

- Bestehende Nutzung des deprecated Logging-Protokolls (ctx.warning, 2 Stellen) ohne Benennung in README/CHANGELOG, ohne Zielzustand und ohne Datum (Kriterien 2-4).
- Neue Nutzung nach dem letzten Audit: search_heritage (df58c50, 2026-07-19) hat einen zweiten ctx.warning-Pfad eingefuehrt (Kriterium 1).
- Spec-Migration waere stderr/OTel — beides ist im Server bereits vorhanden (structlog nach stderr, OBS-006 Tracing); die Warnung an den Client koennte im Result (meta.errors existiert bereits, tests/test_server.py:1803) statt als notifications/message laufen.

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

`2026-07-28` erklärt drei Features für deprecated (SEP-2577) und stellt sie unter die neue Feature-Lifecycle-Politik (SEP-2596) mit einem **Fenster von mindestens zwölf Monaten**:

| Feature | Empfohlene Migration laut Spec |
|---|---|
| **Roots** | Verzeichnisse und Dateien über Tool-Parameter, Resource-URIs oder Server-Konfiguration übergeben |
| **Sampling** | Direkt gegen die API des LLM-Anbieters integrieren |
| **Logging** | Auf `stderr` schreiben (stdio) oder OpenTelemetry verwenden |

**Warum `beide` und nicht `2026-07-28`.** Ein Server, der heute auf der alten Baseline steht, wird in Welle A–D migriert. Ein Sampling-Pfad, den er *jetzt* neu baut, ist Arbeit, die in derselben Migration wieder herausfällt. Der Check greift deshalb auf beiden Ständen — auf der alten als Warnung vor Neubau, auf der neuen zusätzlich mit Frist.

**Was dieser Check nicht ist.** Er verlangt keinen Rückbau bestehender Nutzung. Deprecated heisst «bleibt funktionsfähig», und ein Zwölfmonatsfenster ist kein Notfall. Er verlangt zweierlei: dass **nichts Neues** auf diesen drei Features aufsetzt, und dass bestehende Nutzung ein **Datum** hat statt eines Vorsatzes. Ein Rückbau ohne Datum ist kein Plan, sondern eine Absichtserklärung — und die überlebt die nächste Priorisierung nicht.

**Fristdatum.** Die Spec nennt zwölf Monate als Minimum ab `2026-07-28`, also **frühestens 2027-07-28**. Das ist der früheste Entfernungstermin, nicht der angekündigte; wer danach plant, plant knapp. Der Katalog verlangt ein dokumentiertes Datum, nicht dieses Datum.

### Remediation

Aus dem Katalog (`checks/ARCH-019.md`, Remediation), auf die Gaps oben anzuwenden:

```diff
-# Roots: Client nach erlaubten Verzeichnissen fragen
-roots = await ctx.session.list_roots()
-base = roots.roots[0].uri
+# Verzeichnis kommt als Konfiguration herein — explizit, prüfbar, ohne Rückkanal
+base = settings.data_root          # aus MCP_DATA_ROOT, validiert gegen SEC-017
```

```diff
-# Sampling: den Host-LLM um eine Zusammenfassung bitten
-summary = await ctx.session.create_message(messages=[...])
+# Direkte Anbindung an den Anbieter, mit eigenem Schlüssel und eigenem Budget
+summary = await anthropic.messages.create(model=..., messages=[...])
```

Beim zweiten Muster wandern zwei Dinge mit, die vorher der Host getragen hat: die Kosten und der Datenabfluss. Ein Server, der neu selbst an einen LLM-Anbieter sendet, wird damit zu einer eigenständigen Bekanntgabe — bei `data_class != "Public Open Data"` ist das ein Fall für `CH-002` und `HITL-003`, nicht nur eine technische Umstellung.

### Effort Estimate

Katalog-Richtwert (checks/ARCH-019.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S für die Dokumentationspflicht. M–L für den tatsächlichen Rückbau von Sampling, weil Kosten, Schlüssel und Datenschutzfolgen mitwandern.
