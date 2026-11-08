## Finding: OBS-001 — Protocol vs. Execution Errors: korrekte Trennung

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `OBS-001` |
| **PDF-Reference** | Sec 6.1 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Validierungs- und Upstream-Fehler laufen auf beiden Protokollstaenden korrekt als isError. Abzug: cross_search-Totalausfall, SDK-Mapping des unbekannten Tools, fehlende Protokoll-Tests. Laeufe in-process (ASGI) bzw. via Konsolen-Skript, ausserhalb des Kill-Musters.

### Expected Behavior

Aus dem Katalog (`checks/OBS-001.md`, Pass Criteria):

- [ ] Tool-Handler fangen anwendungsspezifische Fehler (FileNotFound, RateLimit, InvalidArgument) ab
- [ ] Anwendungsfehler werden mit `isError: true` in `tool-result` zurückgegeben (nicht als JSON-RPC-Error)
- [ ] **Input- und Schema-Validierungsfehler laufen über den Execution-Pfad**, nicht über JSON-RPC (SEP-1303) — gilt auf beiden Baselines
- [ ] Die Fehlermeldung eines Validierungsfehlers nennt das betroffene Feld und den erwarteten Wertebereich; ohne das ist der nächste Versuch geraten
- [ ] Standardisierte Fehlercodes für Protocol-Level-Errors
- [ ] Auf `mcp_spec_version: 2026-07-28`: keine eigenen Codes im reservierten Bereich `-32020`…`-32099`; «resource not found» ist `-32602`, nicht `-32002`
- [ ] Mindestens 1 dokumentierter Test deckt Execution-Error-Pfad ab
- [ ] Mindestens 1 dokumentierter Test deckt Protocol-Error-Pfad ab (falsches Tool)
- [ ] Mindestens 1 Test belegt, dass ein **ungültiges Argument** als Execution-Error zurückkommt und nicht als JSON-RPC-Error

### Evidence

- src/swiss_cultural_heritage_mcp/server.py:951-961 — _raise_tool_error wirft ToolError(_handle_error(e)); src/swiss_cultural_heritage_mcp/server.py:922-948 handlungsorientierte Meldungen je Fehlerart; Tools fangen ExpectedUpstreamError (src/swiss_cultural_heritage_mcp/server.py:661-667) und melden ueber diesen Pfad
- src/swiss_cultural_heritage_mcp/server.py:506-537 — mask_unexpected_errors: ToolError durchgereicht, alle anderen Exceptions → generische ToolError
- Laufzeit beide Aeren (ASGI, probe_errors.py validation): ungueltiges Argument limit=9999 → MODERN 2026-07-28 und LEGACY (negotiated 2025-11-25) je http 200, result.isError=true, Text 'params.limit Input should be less than or equal to 100'; ebenso response_format='xml' (nennt 'markdown' oder 'json') und Extra-Feld → Validierung ueber den Execution-Pfad, Feld und Wertebereich benannt
- Laufzeit beide Aeren: Upstream ConnectError → isError=true 'Fehler: Netzwerkfehler (ConnectError): '; HTTP 503 → isError=true 'Dienst voruebergehend nicht verfuegbar' (probe_cross2.py)
- Laufzeit beide Aeren + stdio: unbekanntes Tool 'gibt_es_nicht' → result {content:'Unknown tool: gibt_es_nicht', isError:true}, KEIN JSON-RPC-Error (SDK-Verhalten mcp 2.3.0; Server ueberschreibt nichts)
- grep -rnE -- '-320[0-9]{2}|McpError|ErrorData|JSONRPCError' src/ → exit 1: keine eigenen Codes, also keine im reservierten Bereich -32020…-32099
- tests/test_server.py:1421-1458 TestErrorIsFlagged — Execution-Error-Pfad ueber echten Client (503 → is_error True; leeres Ergebnis → False)
- Laufzeit heritage_cross_search, alle Quellen ConnectError bzw. 503 (httpx.MockTransport): is_error=False, results[*].error = '' bzw. httpx-Rohtext; search_heritage im selben Fall dagegen isError=true 'Alle angefragten Quellen sind derzeit nicht erreichbar' ({SV}:2904-2905)

### Gaps

- high: heritage_cross_search meldet den Totalausfall aller Quellen als normales Ergebnis (isError=false, count 0, error-Felder leer bei ConnectError) — anders als search_heritage
- medium: unbekanntes Tool kommt als Execution-Error (isError) statt als Protocol-Error (JSON-RPC -32602) zurueck, auf beiden Aeren — die Spec 2025-11-25 fuehrt 'unknown tools' als Protocol Error; Ursache im SDK, im Server nicht abgefangen
- medium: kein Test fuer den Protocol-Error-Pfad (falsches Tool) und kein Test, der ein ungueltiges Argument ueber den Protokollpfad als Execution-Error belegt (tests/test_server.py:699 prueft nur das Pydantic-Modell direkt)

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

Die MCP-Spezifikation fordert eine strikte Trennung zwischen zwei Fehler-Typen. Werden sie verwechselt, kann das LLM den Fehler nicht korrekt interpretieren und bricht in eine Halluzinations- oder Sackgassen-Schleife.

| Fehler-Typ | Beispiele | Format |
|---|---|---|
| **Protocol Error** | Tool existiert nicht, JSON-Parsing-Fehler, nicht unterstützte Protokollversion, Header-Widerspruch, interner Server-Crash beim Routing | Standard JSON-RPC Error Response (`{"jsonrpc": "2.0", "error": {...}}`) |
| **Execution Error** | API-Ratenlimit, Datei nicht gefunden, **Schema- und Input-Validierungsfehler**, ungültige Geschäfts-Parameter, Drittanbieter-API down | Tool-Result mit `isError: true`, **niemals** als JSON-RPC-Error |

> **Korrektur gegenüber dem Katalogstand bis v1.7.0.** Dieser Check führte
> «Schema-Mismatch» als Protocol Error. Das ist seit `2025-11-25` falsch:
> SEP-1303 stellt klar, dass Input-Validierungsfehler als **Tool Execution
> Error** zurückzugeben sind, damit das Modell sich selbst korrigieren kann.
> Die Korrektur gilt auf **beiden** Baselines und ist ein Re-Audit-Auslöser
> nach SKILL.md §5c: Ein `pass` aus der Zeit davor kann für einen Server
> vergeben worden sein, der genau das Gegenteil tat.

**Warum das wichtig ist:** Wenn ein Datei-Lookup-Tool «Datei nicht gefunden» als JSON-RPC-Error wirft, denkt das LLM: «Verbindung zum Tool gebrochen, kann es nicht mehr verwenden». Wenn es als Execution Error mit `isError: true` und Text «File not found: /var/log/app.log» kommt, denkt das LLM: «Pfad ist falsch, ich versuche `find /var -name app.log` mit dem List-Tool».

**Und genau dieselbe Logik trägt die Validierung.** Ein `query`-Argument, das zu lang ist oder ein Enum verletzt, ist ein Fehler, den das Modell im nächsten Versuch beheben kann — vorausgesetzt, es erfährt davon in einer Form, die einen nächsten Versuch nahelegt. Als JSON-RPC-Error liest es «dieses Werkzeug ist kaputt» und hört auf. Deshalb liegt die Grenze nicht bei «wer hat den Fehler verursacht», sondern bei **«kann das Modell daraus etwas machen»**.

### Fehlercodes je Baseline

Auf `2026-07-28` ist der Zahlenraum neu aufgeteilt (Minor #6 und #12 im Spec-Changelog):

| | `2025-11-25` | `2026-07-28` |
|---|---|---|
| Resource not found | `-32002` | **`-32602`** (Invalid Params) |
| Implementierungsdefiniert | `-32000`…`-32099` | `-32000`…`-32019` (Bestand grandfathered) |
| Für die Spec reserviert | — | **`-32020`…`-32099`** |
| `HeaderMismatch` | — | `-32020` |
| `MissingRequiredClientCapability` | — | `-32021` |
| `UnsupportedProtocolVersion` | — | `-32022` |

Für einen Server auf der neuen Baseline heisst das: Eigene Codes oberhalb von `-32019` sind ab jetzt Anmassung eines reservierten Bereichs. Wer dort etwas belegt hat, kollidiert früher oder später mit einem Spec-Fehler und wird von Clients falsch behandelt.

### Remediation

Aus dem Katalog (`checks/OBS-001.md`, Remediation), auf die Gaps oben anzuwenden:

```diff
+ from mcp.types import TextContent
+
  @mcp.tool()
  async def query_database(query: str) -> dict:
-     # FAIL: alle Exceptions werden zu JSON-RPC-Errors
-     conn = await asyncpg.connect(DATABASE_URL)
-     return {"rows": await conn.fetch(query)}
+     try:
+         conn = await asyncpg.connect(DATABASE_URL)
+         try:
+             rows = await conn.fetch(query)
+             return {"rows": [dict(r) for r in rows]}
+         finally:
+             await conn.close()
+     except asyncpg.PostgresSyntaxError as e:
+         # Execution Error: Query-Problem ist Aufgabe des LLMs zu lösen
+         return {
+             "isError": True,
+             "content": [TextContent(
+                 type="text",
+                 text=f"SQL syntax error: {str(e)}. Try simplifying the query."
+             )],
+         }
+     except asyncpg.PostgresConnectionError:
+         # Protocol-nahe: Server ist degraded
+         raise McpError(code=-32603, message="Database temporarily unavailable")
```

### Effort Estimate

Katalog-Richtwert (checks/OBS-001.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

M — 1–3 Tage. Pro Tool muss der Error-Pfad reviewed werden. Bei vielen Tools (>10) entsprechend aufwändiger.
