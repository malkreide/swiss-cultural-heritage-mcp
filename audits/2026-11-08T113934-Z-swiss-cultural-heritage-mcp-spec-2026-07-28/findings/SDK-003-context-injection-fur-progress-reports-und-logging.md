## Finding: SDK-003 — Context Injection für Progress Reports und Logging

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `SDK-003` |
| **PDF-Reference** | Sec 3.1 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Gilt fuer beide Revisionen. Auf 2025-11-25 erfuellt (Progress + Warning ueber Context, stderr-Logging). Auf 2026-07-28 ist das Verhalten korrekt (SDK unterdrueckt Logmeldungen ohne Opt-in, gemessen mit Positivkontrolle), aber der verlangte Test und das Ausstiegsdatum fehlen — deshalb partial.

### Expected Behavior

Aus dem Katalog (`checks/SDK-003.md`, Pass Criteria):

- [ ] Tools mit voraussichtlicher Laufzeit > 2s haben `ctx: Context`-Parameter
- [ ] Lang laufende Tools rufen `ctx.report_progress()` mindestens alle 1–2 Sekunden
- [ ] Fehlerfälle, die nicht direkt Tool-Result werden, werden via `ctx.warning()` / `ctx.error()` geloggt (nicht stumm geschluckt)
- [ ] Bei schreibenden Tools (HITL-005): `ctx.elicit()` für Bestätigung verwendet
- [ ] Logger-Statements im Code-Body nutzen `ctx.info()`, nicht direkt `print()` oder Stdlib-`logger` (für stdio-Server kritisch — siehe OBS-004)
- [ ] Auf `2026-07-28`: kein `logging/setLevel`-Handler mehr; der Level kommt aus `io.modelcontextprotocol/logLevel` in `_meta`
- [ ] Auf `2026-07-28`: `notifications/message` wird ausschliesslich für Requests gesendet, die das `logLevel`-Feld trugen — mit einem Test belegt, der einen Request **ohne** das Feld stellt und prüft, dass keine Meldung kommt
- [ ] Auf `2026-07-28`: Der Ausstieg aus dem Logging-Feature hat ein Datum (`ARCH-019`), und der Zielzustand ist `stderr` oder OTel — nicht Stille

### Evidence

- src/swiss_cultural_heritage_mcp/server.py:2366 `heritage_cross_search(params, ctx: Context = None)` und src/swiss_cultural_heritage_mcp/server.py:2808 `search_heritage(params, ctx: Context = None)` — die beiden Fan-out-Tools haben Context; src/swiss_cultural_heritage_mcp/server.py:2486 / :2864 `await ctx.report_progress(progress=done, total=len(keys), message=...)` je abgeschlossener Quelle; src/swiss_cultural_heritage_mcp/server.py:2488 / :2870 `await ctx.warning(...)` bei fehlgeschlagener Quelle
- grep -rnE 'setLevel|set_logging_level|logging_level' src/ -> 0 Treffer (rc=1): kein logging/setLevel-Handler
- Runtime in-process (scratchpad/probe/sdk003_probe.py, respx: SIK-ISEA 503, SNM 200): Client(mode='2026-07-28', log_level=None) -> progress=2, log_msgs=0; Client(mode='2026-07-28', log_level='debug') -> progress=2, log_msgs=1 ['warning'] (Positivkontrolle); Client(mode='legacy') -> negotiated 2025-11-25, log_msgs=1. notifications/message geht auf 2026-07-28 nur an Requests mit logLevel-Opt-in
- SDK site-packages/mcp/server/connection.py:69-90 `allowed_log_levels()` — modern ohne `io.modelcontextprotocol/logLevel` -> leere Menge ('the server MUST NOT send'); die Gate-Logik liegt im SDK, nicht im Server
- src/swiss_cultural_heritage_mcp/server.py:155-190 — strukturiertes JSON-Logging via structlog nach stderr (Zielzustand laut Baseline-Hinweis), kein print() in Tools

### Gaps

- medium: kein Repo-Test, der einen 2026-07-28-Request OHNE logLevel stellt und das Ausbleiben von notifications/message prueft (Pass-Kriterium); belegt nur durch diese Audit-Probe
- low: kein datierter Ausstieg aus dem deprecateten MCP-Logging-Feature (ctx.warning) — grep 'SEP-2577|logging.*deprecat' in README/CHANGELOG/docs -> nichts (ARCH-019)
- low: Einzelquellen-Tools ohne ctx, obwohl das Retry-Budget bis 25 s reicht (Settings.retry_total_budget, server.py:111); Progress kommt je Quelle, nicht alle 1-2 s
- low: Progress-Test im Repo (tests/test_server.py:1117-1149) nutzt einen Context-Doppelgaenger, nicht den Protokollweg

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

FastMCP bietet via `Context`-Parameter ein typsicheres Interface zu Server-Internals: Logging, Progress-Reports, Client-Info, Session-State, Sampling, Elicitation. Tools, die `ctx: Context` als Parameter deklarieren, bekommen dieses Objekt automatisch injiziert (Dependency Injection durch FastMCP).

**Relevante Anwendungen:**

- **Progress-Reports:** Bei lang laufenden Tools (>2s) sollte der Client Fortschritts-Events sehen — sonst Timeout oder UX-Bruch.
- **Strukturiertes Logging:** `ctx.info()`, `ctx.debug()`, `ctx.warning()` werden über das MCP-Protokoll an den Client weitergeleitet (Stichwort `notifications/message`, siehe OBS-003).

> **Baseline-Hinweis (seit v2.0.0) — das Logging-Interface hat sich geändert.**
> Auf `mcp_spec_version: 2026-07-28` gilt:
>
> - **`logging/setLevel` ist entfernt** (SEP-2575). Der Log-Level wird pro
>   Request über `io.modelcontextprotocol/logLevel` in `_meta` gesetzt.
> - **Der Server DARF `notifications/message` nicht senden**, wenn der Request
>   dieses Feld nicht enthielt. Ein `ctx.info()` in jedem Tool ist damit auf der
>   neuen Baseline nicht mehr unbedenklich, sondern potenziell spec-widrig.
> - **Das Logging-Feature als solches ist deprecated** (SEP-2577, Fenster bis
>   frühestens 2027-07-28). Empfohlene Migration: `stderr` bei stdio, sonst
>   OpenTelemetry (`OBS-006`).
>
> Was **nicht** betroffen ist: `ctx.report_progress()`. Request-bezogene
> Benachrichtigungen laufen weiter auf dem Antwortstrom ihres Requests
> (`SCALE-010`).
>
> Die naheliegende Reaktion — «Logging ist deprecated, also weg damit» — ist der
> falsche Schluss und bricht `OBS-003` und `OBS-004`. Deprecated ist das
> **MCP-Protokoll-Feature**, nicht das Logging des Servers. `stderr` ist der
> Zielzustand, nicht Stille.
- **Client-Info:** `ctx.client_info.name` ermöglicht Tool-Verhalten je nach Client (z.B. Token-Limit für Claude Desktop vs. Browser-Client).
- **Sampling:** `ctx.sample()` für umgekehrte LLM-Anfragen (Server fragt LLM via Client).
- **Elicitation:** `ctx.elicit()` für strukturierte User-Bestätigungen (siehe HITL-005).

Tools ohne `ctx` haben keinen Zugriff auf diese Mechanismen — was bei langen Operationen oder schreibenden Tools eine schwere Einschränkung ist.

### Remediation

Aus dem Katalog (`checks/SDK-003.md`, Remediation), auf die Gaps oben anzuwenden:

Migrationsweg für ein langes Tool:

```diff
+ from mcp.server.fastmcp import Context

  @mcp.tool()
- async def export_all_records(format: str) -> dict:
-     records = await db.fetch_all()
-     for record in records:
-         await transform(record, format)
-     return {"count": len(records)}
+ async def export_all_records(format: str, ctx: Context) -> dict:
+     await ctx.info(f"Starting export in format={format}")
+     records = await db.fetch_all()
+     await ctx.info(f"Loaded {len(records)} records, transforming...")
+
+     transformed = []
+     for i, record in enumerate(records):
+         if i % 50 == 0:
+             await ctx.report_progress(
+                 progress=i,
+                 total=len(records),
+                 message=f"Transformed {i}/{len(records)}",
+             )
+         transformed.append(await transform(record, format))
+
+     await ctx.info(f"Export complete: {len(transformed)} records")
+     return {"count": len(transformed), "format": format}
```

### Effort Estimate

Katalog-Richtwert (checks/SDK-003.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — < 1 Tag. Pro Tool 10 Minuten + Tests.
