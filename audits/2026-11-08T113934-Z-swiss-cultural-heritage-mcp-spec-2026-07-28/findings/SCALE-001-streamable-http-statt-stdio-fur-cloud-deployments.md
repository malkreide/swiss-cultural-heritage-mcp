## Finding: SCALE-001 — Streamable HTTP statt stdio für Cloud-Deployments

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `SCALE-001` |
| **PDF-Reference** | Sec 5.1 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Code und Container-Pfad sind korrekt (ENV-Auswahl, Streamable HTTP, keine WebSockets, initialize 200 lokal). Der Befund liegt in der Betriebsdoku: der als 'recommended' gefuehrte Render-Weg bindet Loopback und schickt Clients an einen 404-Pfad. Wer Render mit Docker-Runtime faehrt, ist nicht betroffen; wer der README folgt, schon.

### Expected Behavior

Aus dem Katalog (`checks/SCALE-001.md`, Pass Criteria):

- [ ] ENV-basierte Transport-Selektion (stdio + streamable-http/sse)
- [ ] Cloud-Deployment nutzt streamable-http oder sse, nicht stdio
- [ ] Keine WebSocket-Implementierung mehr im Code
- [ ] Cloud-Endpoint antwortet auf `initialize` mit HTTP 200

### Evidence

- src/swiss_cultural_heritage_mcp/server.py:139 — `transport: Literal['stdio','http'] = 'stdio'` in Settings (env MCP_TRANSPORT); src/swiss_cultural_heritage_mcp/server.py:3592-3607 — `if settings.transport == 'http' or '--http' in sys.argv:` -> build_http_app + uvicorn.run(host=settings.host, port=settings.port), sonst mcp.run() (stdio). ENV-basierte Auswahl vorhanden
- Dockerfile:37 `MCP_HOST=0.0.0.0`, Dockerfile:53 `CMD ["python","-m","swiss_cultural_heritage_mcp.server","--http","--port","8000"]` — der Container-Pfad startet Streamable HTTP und bindet extern
- Runtime (lokal gestarteter Server HEAD 9b3a1b4 (editable install), MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT=8765, SDK mcp 2.3.0, 2026-11-08): POST /mcp initialize protocolVersion 2025-11-25 -> HTTP 200, content-type text/event-stream, mcp-session-id gesetzt, result.protocolVersion '2025-11-25'; POST server/discover mit MCP-Protocol-Version 2026-07-28 -> HTTP 200 JSON. Beide Aeras ueber HTTP bedient
- git grep -nIiE 'websocket' (repo, ohne audits) -> kein Treffer im Code; MCP_TRANSPORT=sse wird von Settings abgewiesen: `Input should be 'stdio' or 'http' [type=literal_error, input_value='sse']`
- git show HEAD:README.md:150-157 — empfohlener Render-Weg: Start-Command `python -m swiss_cultural_heritage_mcp.server --http --port 8000` OHNE MCP_HOST; Settings-Default ist 127.0.0.1 (Laufzeit ohne Env: `host= 127.0.0.1 transport= stdio port= 8000`). Render verlangt Bind auf 0.0.0.0 -> der dokumentierte Weg bindet Loopback
- git show HEAD:README.md:155 (und README.de.md:156) — Client-URL `https://your-app.onrender.com/sse`; Runtime GET /sse am lokalen Server -> HTTP 404 Not Found. Der dokumentierte Endpunkt existiert nicht; der echte ist /mcp

### Gaps

- high: README (EN+DE) beschreibt den empfohlenen Render-Deploy so, dass er nicht funktioniert: Bind auf 127.0.0.1 (kein MCP_HOST=0.0.0.0) und Client-URL /sse statt /mcp — genau das Symptom 'Server startet, Verbindungen schlagen fehl'
- medium: kein Deployment-Manifest (render.yaml o. ae.) im Repo, das MCP_TRANSPORT/MCP_HOST fuer Render explizit setzt; nur das Dockerfile tut es
- low: Konsolen-Skript `swiss-cultural-heritage-mcp = ...server:mcp.run` (pyproject.toml [project.scripts]) ignoriert MCP_TRANSPORT und startet immer stdio — nur `python -m ...server` liest die Variable
- not_verified-Teil: Cloud-Endpoint der ausgelieferten Render-Instanz nicht geprueft — keine Instanz-URL im Repo (server.json fuehrt nur stdio/pypi); initialize-200 ist lokal belegt

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

stdio-Transport ist für lokale Single-User-Sessions konzipiert: ein Subprozess, eine Stdin/Stdout-Pipe, ein Client. Cloud-Deployments mit Multi-User-Zugriff können stdio nicht sinnvoll bedienen — der TCP-Bruch killt die Pipe, kein Failover möglich. Streamable HTTP / SSE sind die Cloud-Standards 2026; sie unterstützen Reconnect via Event-IDs, Multi-User, Standard-HTTP-Infrastruktur. WebSocket-Implementierungen sind veraltet.

Symptom bei Fehlkonfiguration: Server startet, Health-Check grün, aber Client-Verbindungen schlagen fehl. Häufig übersehen, weil viele Tutorials `transport="stdio"` als Default zeigen.

### Remediation

Aus dem Katalog (`checks/SCALE-001.md`, Remediation), auf die Gaps oben anzuwenden:

```diff
- mcp.run(transport="stdio")
+ transport = os.environ.get("MCP_TRANSPORT", "stdio")
+ if transport in ("sse", "streamable-http"):
+     mcp.settings.host = os.environ.get("MCP_HOST", "0.0.0.0")
+     mcp.settings.port = int(os.environ.get("MCP_PORT", "8000"))
+ mcp.run(transport=transport)
```

Plus Deployment-Config (Railway):

```toml
[deploy.environment]
MCP_TRANSPORT = "streamable-http"
MCP_HOST = "0.0.0.0"
MCP_PORT = "8000"
```

### Effort Estimate

Katalog-Richtwert (checks/SCALE-001.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — < 1 Tag.
