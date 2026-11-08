## Finding: ARCH-013 — Alle Netz-Transportpfade identisch verdrahtet

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `ARCH-013` |
| **PDF-Reference** | Sec 2.1 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Es gibt genau einen Netzweg (python -m ... --http bzw. MCP_TRANSPORT=http), Dockerfile nutzt ihn, kein SSE, keine Factory; Host und Port reisen vollstaendig, die Host-Allow-List greift laufzeitbelegt auf POST/GET/DELETE. Die Verdrahtung selbst ist korrekt. Es fehlt der Test an der Naht samt Gegenprobe, und die Doku nennt einen /sse-Weg und ein --port-Flag, die es nicht gibt. Prozess nach der Messung beendet (kill).

### Expected Behavior

Aus dem Katalog (`checks/ARCH-013.md`, Pass Criteria):

- [ ] Alle Codepfade, die eine ASGI-App konstruieren oder servieren, sind aufgezählt — eigener Builder, `run()`-Pfad, SSE, Factory
- [ ] Die Deployment-Manifeste sind mitgelesen; ein dort verdrahteter Pfad (`--factory`, eigener `CMD`) zählt mit
- [ ] Die Sicherheitsverdrahtung ist auf **allen** identisch, nicht nur auf dem bedingten Zweig
- [ ] Kein Scharfschalten hängt an einer sachfremden Bedingung (Auth gesetzt, CORS gesetzt, Debug aus)
- [ ] Der **vollständige** Bind-Parametersatz reist mit — Host **und** Port, nicht nur der Host
- [ ] Eine `uvicorn --factory` liest den Bind selbst aus derselben Quelle wie `main()`
- [ ] Pro Pfad existiert ein Test, der die Verdrahtung an der Naht prüft, nicht nur im Builder
- [ ] Gegenprobe geführt: Verdrahtung aus je einem Pfad entfernt, jedes Mal scheitert mindestens ein Test

### Evidence

- Pfad-Inventar: grep 'streamable_http_app\(|sse_app\(|http_app\(' -> einzig server.py:3574 (mcp.streamable_http_app in build_http_app); 'mcp.run\(|uvicorn.run\(' -> server.py:3600 (uvicorn.run im __main__-HTTP-Zweig) und server.py:3607 (mcp.run() im stdio-Zweig); keine Factory, kein SSE-Pfad im Code.
- pyproject.toml [project.scripts] swiss-cultural-heritage-mcp = 'swiss_cultural_heritage_mcp.server:mcp.run' — MCPServer.run(transport='stdio') ist der Default (inspect.signature: transport='stdio'); das Konsolen-Skript ist reiner stdio-Pfad, kein Netzweg.
- Deployment-Manifeste: Dockerfile:63 CMD ['python','-m','swiss_cultural_heritage_mcp.server','--http','--port','8000'] -> derselbe __main__-HTTP-Zweig; render.yaml/railway.toml/Procfile/docker-compose existieren nicht (ls: No such file).
- server.py:3592-3605 — der einzige Netzpfad uebergibt host UND port aus settings an build_http_app(cors, settings.host, settings.port) und an uvicorn.run(host=settings.host, port=settings.port); build_http_app ruft build_transport_security(host, port) (server.py:3565) — keine fremde Bedingung (Auth/CORS) entscheidet ueber die Haertung.
- Laufzeit am echten Einstieg: MCP_TRANSPORT=http MCP_PORT=8765 python -m swiss_cultural_heritage_mcp.server --port 9999 -> POST /mcp Host=127.0.0.1:8765 -> 200, Host=evil.example.com -> 421, Host=127.0.0.1:9999 -> 421; curl :9999/health -> 000 (kein Listener); GET /sse -> 404.
- Laufzeit ASGI (scratchpad/probe_get.py): GET /mcp und DELETE /mcp mit Host=evil.example.com -> 421, mit 127.0.0.1:8000 -> 400; app.routes = ['/mcp','/health'] — auch die Legacy-GET/DELETE-Wege tragen dieselbe Host-Pruefung.
- tests/test_transport_security.py:115-144 und tests/test_cors.py:45 rufen build_http_app direkt mit explizitem host/port; grep '__main__|runpy|subprocess|uvicorn' tests/*.py trifft keinen Test des Einstiegs (nur Hook-/Gate-Tests nutzen subprocess).

### Gaps

- Kein Test an der Naht: Die Verdrahtung __main__ -> build_http_app(settings.host, settings.port) ist ungeprueft; alle Transport-Tests rufen den Builder mit allen Parametern (Common Failure 'Test ruft den Builder direkt'). Eine Gegenprobe (Port aus dem __main__-Aufruf entfernen) wuerde keinen Test faerben — nicht ausgefuehrt, weil das Repo nicht veraendert werden darf; aus dem Testinventar geschlossen.
- Das CLI-Flag --port wird nirgends geparst (server.py:3592 prueft nur '--http' in sys.argv); gemessen: --port 9999 bleibt wirkungslos, Listener und App folgen MCP_PORT. Dockerfile:63 und README (Quickstart Z. 99, Render Z. 154) reichen --port 8000 weiter, das nur zufaellig dem Default entspricht.
- README (HEAD) Z. 146-157 dokumentiert einen Render-Weg mit Endpunkt '/sse' — den der Server nicht bedient (GET /sse -> 404) — und eine Startzeile ohne MCP_HOST, mit der der Listener auf 127.0.0.1 bindet (Settings.host-Default, server.py:140). Ein dokumentierter Pfad, der weder erreichbar ist noch der realen Route entspricht.
- Konsolen-Skript ignoriert MCP_TRANSPORT=http (mcp.run ohne Argumente, kein Settings-Zugriff) — kein Sicherheitsdefekt, aber eine zweite Einstiegslogik neben __main__.

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

Ein Server, der über Netz erreichbar ist, konstruiert seine ASGI-App fast nie an genau einer Stelle. Typisch sind drei bis vier Wege, und sie entstehen nacheinander, ohne dass jemand sie als Menge betrachtet:

| Pfad | Wann er greift |
|---|---|
| Eigener App-Builder (`build_http_app()`, `create_http_app()`) | Oft nur unter einer Bedingung — etwa wenn Auth oder CORS konfiguriert ist |
| SDK-servierter `run()`-Pfad | Wenn diese Bedingung *nicht* zutrifft |
| Deprecateter SSE-Pfad | Parallel zu Streamable HTTP, für ältere Clients |
| Factory für uvicorn (`--factory`) | Im Container-Deployment, statt `main()` |

**Die Kontrolle sitzt dann auf einem dieser Pfade und nicht auf den anderen.** Das ist kein Bug, den man beim Lesen sieht: Jeder Pfad für sich ist korrekt, der Server startet, die Tests laufen. Nur die Antwort auf «ist die Kontrolle aktiv» lautet plötzlich *es kommt darauf an* — und zwar auf eine Bedingung, die mit der Kontrolle nichts zu tun hat.

**Zwei Ausprägungen, in zwei Repos unabhängig voneinander aufgetreten:**

**1. Die Kontrolle hängt an einer fremden Bedingung.** Ein Server nahm seinen eigenen App-Builder nur, wenn Auth **oder** CORS konfiguriert war; sonst servierte das SDK über `run()`. Wäre die Sicherheitskonfiguration nur dem Builder mitgegeben worden, hinge das Scharfschalten einer Sicherheitskontrolle still davon ab, ob zufällig ein Auth-Token gesetzt ist. Zwei Deployments desselben Images, eines geschützt, eines nicht — und der Unterschied steht in einer Variablen, die von etwas anderem handelt.

**2. Der Parametersatz reist unvollständig mit.** Im selben Portfolio bekam ein App-Builder nur den `host`, nicht den `port`, und defaultete den Port intern. Die Loopback-Einträge der Host-Allow-List nannten dadurch einen Port, den niemand bedient. Die Kontrolle war verdrahtet, aktiv, und trotzdem falsch — sie schützte eine Adresse, die es nicht gab. Bemerkt hat das kein Test, weil der vorhandene Port-Test den Builder mit explizitem Port rief; die Naht davor war ungeprüft.

**Warum das ein eigener Check ist und keine Fussnote in `SEC-024`:** Die Fehlerklasse ist nicht an eine bestimmte Kontrolle gebunden. Dieselbe Lücke entsteht mit Auth-Middleware, Rate-Limiting, Request-Logging oder Tracing-Instrumentierung. Was geprüft wird, ist die **Vollständigkeit der Aufzählung** — und die ist eine Struktureigenschaft des Servers, nicht eine Eigenschaft der Sicherheitskontrolle, die zufällig gerade betrachtet wird.

### Remediation

Aus dem Katalog (`checks/ARCH-013.md`, Remediation), auf die Gaps oben anzuwenden:

1. Die Pfade **aufschreiben**, bevor irgendetwas geändert wird — Code und Deployment-Manifeste. Die Liste ist das eigentliche Ergebnis dieses Checks; alles Weitere folgt daraus.
2. Die Verdrahtung in **eine** Funktion ziehen, die alle Pfade aufrufen. Nicht in jedem Pfad wiederholen: Duplikate driften.
3. Den vollständigen Parametersatz durchreichen. Wo ein Builder einen Wert defaultet, den der Aufrufer kennt, ist der Default die Fehlerquelle.
4. Für `uvicorn --factory` den Bind in der Factory aus derselben Konfiguration lesen wie `main()`, und in der README festhalten, warum die Environment-Variablen neben den Flags nötig sind.
5. Pro Pfad einen Test an der **Naht** — nicht im Builder, der ohnehin alles bekommt.
6. Mutationsgegenprobe: Verdrahtung aus je einem Pfad entfernen. Scheitert kein Test, ist dieser Pfad ungeprüft, und die Suite hat nur bestätigt, was sie ohnehin annahm.

### Effort Estimate

Katalog-Richtwert (checks/ARCH-013.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

M — 1–3 Tage. Die Aufzählung ist schnell; die Zeit geht in die Tests an den Nähten und die Mutationsgegenprobe pro Pfad.
