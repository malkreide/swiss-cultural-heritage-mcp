## Finding: SCALE-009 — Legacy HTTP+SSE abgeschaltet — mit Datum, nicht mit Vorsatz

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | advisory |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `SCALE-009` |
| **PDF-Reference** | SEP-2596 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Der Legacy-Pfad ist im Code geschlossen und an der Laufzeit mit Gegenprobe belegt (404 hier, 200 am SSE-Kontrollserver). Offen sind die Doku (SSE als empfohlener Browser-Transport, falsche URL) und die Pruefung an der ausgelieferten Instanz, die der Check ausdruecklich verlangt. Kein Abschaltdatum noetig, da kein Pfad offen ist.

### Expected Behavior

Aus dem Katalog (`checks/SCALE-009.md`, Pass Criteria):

- [ ] Der Server bedient keinen HTTP+SSE-Legacy-Endpunkt mehr — geprüft an der ausgelieferten Instanz, nicht nur am Code
- [ ] Ist er noch offen, nennt README oder CHANGELOG ein **Datum**, nicht «demnächst»
- [ ] Das Datum liegt nicht nach dem frühesten Entfernungstermin (2027-07-28), oder die Abweichung ist begründet
- [ ] Ist er noch offen, gelten dort dieselben Kontrollen wie am Streamable-HTTP-Pfad: `SEC-024` (Host-Allow-List), `SEC-016` (Bind-Adresse), Auth — belegt je einzeln, nicht behauptet
- [ ] Das README nennt Streamable HTTP als den unterstützten Transport, ohne SSE als gleichwertige Alternative zu führen
- [ ] Die Deployment-Konfiguration (Ingress, Railway/Render, Compose) enthält keine Route mehr auf den Legacy-Pfad
- [ ] **Gegenprobe:** Der `curl`-Aufruf ist einmal gegen einen Server mit offenem SSE-Pfad gelaufen und hat dort `200` bekommen — sonst belegt ein `404` nur, dass die URL falsch war

### Evidence

- grep -rnE 'sse_app|SseServerTransport|/sse|text/event-stream|EventSourceResponse' src/ --include=*.py -> 0 Treffer (rc=1); Routen-Grep 'mount|add_route|@app.(get|post)|router.|custom_route' -> nur src/swiss_cultural_heritage_mcp/server.py:3466 `@mcp.custom_route('/health')`
- Runtime (lokal gestarteter Server HEAD 9b3a1b4 (editable install), MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT=8765, SDK mcp 2.3.0, 2026-11-08): GET /sse (Accept: text/event-stream) -> HTTP 404 Not Found; GET /messages/ -> 404
- Gegenprobe: Kontrollserver `MCPServer('sse-control').sse_app()` via uvicorn auf 127.0.0.1:8766 -> GET /sse -> HTTP 200, content-type text/event-stream; charset=utf-8. Derselbe curl-Aufruf erkennt einen offenen Legacy-Pfad, das 404 oben ist also kein URL-Tippfehler
- MCP_TRANSPORT=sse -> pydantic literal_error 'Input should be stdio or http' — Legacy-Transport ist auch per Umgebung nicht einschaltbar; Konsolen-Skript ruft mcp.run() ohne Argument (stdio)
- git show HEAD:README.md:146 '### Cloud Deployment (SSE for browser access)', :155 Client-URL `https://your-app.onrender.com/sse`, :157 '"stdio for the developer laptop, SSE for the browser."', :223 Diagramm 'Stdio | SSE'; README.de.md:147,156,160,224 gleichlautend

### Gaps

- medium: README EN/DE fuehrt SSE als den Cloud-Transport und schickt Clients an /sse, das der Server nicht bedient (404) — Kriterium 'README nennt Streamable HTTP ohne SSE als Alternative' verfehlt; Folge ist eine fehlschlagende Client-Konfiguration
- not_verified-Teil: ausgelieferte Render-Instanz nicht geprueft — keine Instanz-URL im Repo

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

Der HTTP+SSE-Transport ist seit `2025-03-26` deprecated. Was `2026-07-28` ändert, ist nicht die Empfehlung, sondern ihre Verbindlichkeit: SEP-2596 stellt ihn unter die neue Feature-Lifecycle-Politik und gibt ihm damit den formalen Zustand **Deprecated** — mit einem Fenster von mindestens zwölf Monaten, also einem frühesten Entfernungstermin von **2027-07-28**.

**Warum es diesen Check braucht, obwohl «deprecated seit 2025-03» seit anderthalb Jahren im Raum steht.** Genau deswegen. Eine Empfehlung ohne Termin erzeugt keinen Vorgang; sie erzeugt einen Kompatibilitätspfad, den niemand abschaltet, weil er niemanden stört. Der Legacy-Pfad ist dabei nicht neutral: Er ist ein zweiter Netzweg mit eigener Verdrahtung, und die Erfahrung aus `ARCH-013` ist, dass der zweite Pfad die Härtung des ersten nicht mitbekommt. Ein Server, dessen Streamable-HTTP-Endpunkt Host-Allow-Listing (`SEC-024`) und Header-Prüfung (`SCALE-008`) durchsetzt, während der SSE-Endpunkt daneben weiterläuft, hat beides nicht.

**`beide` als Baseline**, weil die Abschaltung nicht auf die Migration wartet: Ein Server auf der alten Baseline soll den Legacy-Pfad heute schliessen, nicht erst mit dem Sprung auf `2026-07-28`.

**Auf `2026-07-28` verschärft sich die Lage zusätzlich**, denn dort ist auch der GET-Endpunkt weg (siehe `SCALE-010`). Ein verbliebener SSE-Pfad spricht dann ein Protokoll, das der Server nach eigener Aussage nicht mehr führt.

### Remediation

Aus dem Katalog (`checks/SCALE-009.md`, Remediation), auf die Gaps oben anzuwenden:

```diff
-app.mount("/sse", sse_app())          # Legacy, deprecated seit 2025-03-26
 app.mount("/mcp", streamable_http_app())
```

Und im README, Sektion «MCP Protocol Version»:

> **Transport:** Streamable HTTP (`/mcp`). Der HTTP+SSE-Pfad wurde am 2026-09-30 abgeschaltet.

Bleibt der Pfad im Restfenster offen, gehört er in dieselbe Härtungskette wie der neue — nicht in eine Ausnahme. Ein Kompatibilitätspfad, der die Kontrollen des Hauptpfads nicht trägt, ist die Umgehung dieser Kontrollen.

### Effort Estimate

Katalog-Richtwert (checks/SCALE-009.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S, wenn nur eine Route zu entfernen ist. M, wenn Clients daran hängen: dann braucht es eine Ankündigung mit Frist und eine Prüfung, wer den Pfad noch nutzt — Zugriffszahlen vor dem Abschalten, nicht danach.
