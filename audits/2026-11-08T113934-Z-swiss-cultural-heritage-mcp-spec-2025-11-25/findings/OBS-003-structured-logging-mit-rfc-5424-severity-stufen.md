## Finding: OBS-003 — Structured Logging mit RFC 5424 Severity-Stufen

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `OBS-003` |
| **PDF-Reference** | Sec 6.3 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Strukturierung und Ausgabeformat korrekt; der beworbene Request-Kontext existiert zur Laufzeit nicht (tests/test_server.py:1332 deckt nur den Fall 'kein aktiver Request' ab und bleibt deshalb gruen).

### Expected Behavior

Aus dem Katalog (`checks/OBS-003.md`, Pass Criteria):

- [ ] Structured Logger (structlog/pino/loguru) im `dependencies`
- [ ] JSON oder logfmt als Output-Format
- [ ] Mindestens 4 Severity-Stufen aktiv genutzt (debug, info, warning, error)
- [ ] Pro Tool-Call: bound context (tool name, session_id, correlation_id)
- [ ] Keine `print()`-Statements im Tool-Code (siehe OBS-004 für stdio)

### Evidence

- pyproject.toml:48 — 'structlog>=24.1.0,<27.0.0' in dependencies
- src/swiss_cultural_heritage_mcp/server.py:155-181 — structlog.configure mit merge_contextvars, add_log_level, TimeStamper(iso, utc), format_exc_info, JSONRenderer, WriteLoggerFactory(file=sys.stderr); Level via MCP_LOG_LEVEL
- Laufzeit stderr: {"tool": "heritage_search_artists", "event": "tool.call", "level": "info", ...}, {"error_kind": "ConnectError", "status": null, "event": "upstream.error", "level": "warning", ...}, {"event": "tool.unexpected_error", "level": "error", ...} — JSON, Felder statt f-Strings
- grep -rnoE 'log\.(debug|info|warning|error|exception|critical)|bound\.(...)' src/ | uniq -c → info 2, warning 3, error 1; kein debug-Aufruf
- src/swiss_cultural_heritage_mcp/server.py:491-502 _request_log_context — will request_id via mcp.get_context() setzen; Laufzeit: in KEINEM Log-Event (ASGI beide Aeren, In-Process-Client) erscheint request_id. Ursache: MCPServer (mcp 2.3.0) hat kein get_context ('AttributeError: type object MCPServer has no attribute get_context'), der Fehler wird von 'except Exception: pass' verschluckt
- Laufzeit stderr: SDK/httpx/uvicorn-Logs kommen im selben Strom als mehrzeiliger rich-Klartext ('[11/08/26 12:46:22] INFO StreamableHTTP session manager started ...'), nicht JSON
- grep -rnE '\bprint\(' src/ → exit 1 (negative Kontrolle 'print("x")' trifft)

### Gaps

- medium: Korrelations-ID fehlt zur Laufzeit — request_id wird nie gebunden (toter Code nach SDK-Migration), session_id gar nicht; nur der Tool-Name ist pro Aufruf gebunden
- low: nur 3 von 4 geforderten Stufen genutzt (kein debug)
- low: gemischter stderr-Strom — SDK-/Bibliotheks-Logs als Klartext (rich), nicht JSON; Aggregation braucht weiterhin Regex

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

MCP-Server-Logs müssen strukturiert sein (JSON oder logfmt), nicht plaintext. Das ermöglicht Aggregation in Datadog/Splunk/Loki ohne Regex-Parsing, korrelierte Suche über Correlation-IDs, und konsistente Severity-Filterung.

Der MCP-Standard nutzt RFC 5424's 8 Severity-Stufen: `debug`, `info`, `notice`, `warning`, `error`, `critical`, `alert`, `emergency`. Über das `notifications/message`-Event können Logs auch an den Client weitergereicht werden — der Client kann via `logging/setLevel` dynamisch filtern.

Für Python ist `structlog` der Standard, für TypeScript `pino`.

### Remediation

Aus dem Katalog (`checks/OBS-003.md`, Remediation), auf die Gaps oben anzuwenden:

```diff
- import logging
- logger = logging.getLogger(__name__)
+ import structlog
+ logger = structlog.get_logger("mcp.server")

  @mcp.tool()
  async def search(query: str, ctx):
-     logger.info(f"Searching for {query}")
-     result = await api.search(query)
-     logger.info(f"Got {len(result)} results")
+     log = logger.bind(tool="search", query=query, session=ctx.session_id)
+     log.info("tool_invoked")
+     result = await api.search(query)
+     log.info("tool_succeeded", count=len(result))
      return result
```

### Effort Estimate

Katalog-Richtwert (checks/OBS-003.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — < 1 Tag pro Server.
