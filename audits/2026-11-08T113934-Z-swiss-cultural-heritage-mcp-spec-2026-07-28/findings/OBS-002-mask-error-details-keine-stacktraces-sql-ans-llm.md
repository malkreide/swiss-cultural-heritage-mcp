## Finding: OBS-002 — Mask Error Details: keine Stacktraces / SQL ans LLM

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `OBS-002` |
| **PDF-Reference** | Sec 6.2 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Kern erfuellt und zur Laufzeit belegt: keine Stacktraces/Secrets ans LLM, Original nur im Log. Teilweise wegen des rohen httpx-Texts in cross_search. Alter Lauf (v0.5) blockierte hier — heute behoben, unabhaengig nachgemessen.

### Expected Behavior

Aus dem Katalog (`checks/OBS-002.md`, Pass Criteria):

- [ ] FastMCP-Init hat `mask_error_details=True` (oder TypeScript-Äquivalent)
- [ ] Keine `traceback.format_exc()` / `sys.exc_info()`-Outputs in Tool-Returns
- [ ] Execution-Errors haben User-Friendly-Messages ohne Internals
- [ ] Originale Errors landen ausschliesslich im Server-Log (nicht im Tool-Result)
- [ ] Logs sind selbst geschützt: kein Klartext-Token, kein PII

### Evidence

- src/swiss_cultural_heritage_mcp/server.py:478-537 — mask_unexpected_errors (Aequivalent zu mask_error_details; MCPServer kennt das Flag nicht): unerwartete Exception → bound.error('tool.unexpected_error', error_type=..., exc_info=True) ins Log, an den Client 'Interner Fehler bei der Tool-Ausfuehrung. Details wurden serverseitig protokolliert.' (from None); alle 11 Tools dekoriert
- Laufzeit beide Aeren (probe_errors.py unexpected, RuntimeError('SECRET-INTERNAL /etc/app/config.toml token=abc123')): MODERN und LEGACY → isError=true, Text nur 'Error executing tool heritage_search_artists: Interner Fehler ...' — kein Secret, kein Pfad; stderr-JSON enthaelt den vollen Traceback (event tool.unexpected_error)
- grep -rnE 'traceback|format_exc|sys\.exc_info' src/ → nur structlog format_exc_info-Prozessor im Logging ({SV}:171), nichts in Tool-Returns
- src/swiss_cultural_heritage_mcp/server.py:922-948 — Execution-Errors mit kuratierten deutschen Meldungen (404/429/503/Timeout/XML)
- Laufzeit heritage_cross_search mit HTTP 503 (MockTransport): results[*].error = "Server error '503 Service Unavailable' for url 'https://ckan.opendata.swiss/api/3/action/datastore_search?resource_id=ef3a9fd2-...&q=Hodler&limit=5'\nFor more information check: https://developer.mozilla.org/..." — roher httpx-Text ins Tool-Ergebnis ({SV}:2411, 2434, 2464: 'error': str(e))
- stderr des HTTP-Laufs: SDK-Logging (rich, INFO) protokolliert httpx-Requests mit voller URL ('HTTP Request: GET https://...') — Query-Strings mit Suchbegriffen landen im Log

### Gaps

- medium: heritage_cross_search reicht str(e) ungefiltert ans Modell durch (interne Upstream-URL samt resource_id und Query, httpx-Hilfetext) — Kriterium 3 an dieser Stelle nicht erfuellt
- low: ValueError-Unterklassen (UpstreamSchemaError listet Upstream-Schluessel, Allow-List-Host) und jede ValueError aus Parsing-Code gehen als 'Fehler: {e}' an den Client ({SV}:945) — kein Stacktrace, aber unkuratierter Text
- low: httpx-INFO-Logs enthalten Suchbegriffe aus Query-Strings (Nutzereingaben) — widerspricht dem Docstring 'keine Payloads/PII' ({SV}:156-160); keine Tokens, auth_model none

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

Wenn Tool-Errors Stacktraces, SQL-Syntax, Datei-Pfade oder gar Credentials enthalten, fliesst dieser Inhalt in den LLM-Kontext und damit potentiell ins User-Sichtbare zurück. Das ist Information Disclosure: Angreifer mit User-Zugriff erfahren über provozierte Errors die Server-Architektur, DB-Schema, gemountete Pfade, sogar geleakte Tokens (z.B. in `Authorization`-Headern, die im Stacktrace landen).

FastMCP bietet `mask_error_details=True`: Server-Errors werden auf eine generische Message reduziert (`"An error occurred"`), Original-Details landen nur im Server-Log. Trade-off: LLM kann nicht mehr aus Error-Details ableiten, was zu tun ist (Stichwort OBS-001 Execution-Errors). Lösung: für Execution-Errors (wo das LLM helfen soll) explizit User-Friendly-Messages, für Server-Crashes generisch maskieren.

### Remediation

Aus dem Katalog (`checks/OBS-002.md`, Remediation), auf die Gaps oben anzuwenden:

```diff
  mcp = FastMCP(
      "server",
+     mask_error_details=True,
  )

  @mcp.tool()
  async def search(query: str):
      try:
          return await db.search(query)
-     except Exception as e:
-         return {"error": str(e), "traceback": traceback.format_exc()}
+     except UserInputError as e:
+         return {"isError": True, "content": [
+             TextContent(type="text", text=f"Invalid input: {e.user_message}")
+         ]}
+     except Exception:
+         logger.exception("Unhandled error in search tool")
+         raise  # mask_error_details greift, generische Message ans LLM
```

### Effort Estimate

Katalog-Richtwert (checks/OBS-002.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — < 1 Tag pro Server.
