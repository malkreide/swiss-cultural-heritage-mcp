## Finding: SCALE-007 — Wiederaufnahme abgerissener Streams via Last-Event-ID

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | enforced |
| **Check-Status** | fail |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `SCALE-007` |
| **PDF-Reference** | Sec 5.1 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Nur 2025-11-25. Read-only-Server mit lesenden Tools: ein wiederholter Tool-Call kommt ans Ziel, der Schaden ist Latenz, keine Doppelwirkung (deshalb Severity medium im Katalog). Auf 2026-07-28 entfaellt der Check (SEP-2575).

### Expected Behavior

Aus dem Katalog (`checks/SCALE-007.md`, Pass Criteria):

- [ ] SSE-Events tragen ein `id:`-Feld — ohne IDs ist Resume grundsätzlich unmöglich
- [ ] Der Transport ist mit einem Event-Store verdrahtet (`event_store=` / `eventStore:`), nicht mit dem Default `None`
- [ ] Der Store liegt bei ≥ 2 Replicas ausserhalb des Prozesses (Redis o. ä.), nicht nur im Speicher
- [ ] Ein Reconnect mit `Last-Event-ID` liefert die verpassten Events, nicht den Stream von vorn und nicht einen leeren Stream
- [ ] Der Replay ist auf den Stream der übergebenen ID begrenzt — keine Events fremder Requests derselben Session
- [ ] Eine unbekannte `Last-Event-ID` wird erkennbar behandelt statt still ignoriert
- [ ] Die Proxy-/Ingress-Schicht puffert SSE nicht und schliesst nicht vor dem Server
- [ ] Event-Store und Session-State liegen in derselben Schicht — beides muss denselben Reconnect überleben

### Evidence

- src/swiss_cultural_heritage_mcp/server.py:3574 — `mcp.streamable_http_app(transport_security=security, host=host)`: kein event_store-Argument; SDK-Signatur `event_store: EventStore | None = None` -> Default None, keine Resumability
- grep -rnE 'event_store|EventStore|StreamableHTTPSessionManager' src/ -> 0 Treffer; Negativkontrolle: dasselbe Muster greift in der SDK-Signatur (inspect.signature(MCPServer.streamable_http_app) nennt event_store)
- Runtime (lokal gestarteter Server HEAD 9b3a1b4 (editable install), MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT=8765, SDK mcp 2.3.0, 2026-11-08): SSE-Antwort auf initialize 2025-11-25 besteht aus `event: message` + `data: {...}` OHNE `id:`-Zeile — ohne Event-IDs ist Last-Event-ID-Resume grundsaetzlich unmoeglich

### Gaps

- medium: kein Event-Store verdrahtet, SSE-Events tragen keine id — ein abgerissener Stream verliert die laufende Antwort
- low: keine Proxy-Konfiguration (Buffering/Timeout) im Repo; der Server setzt selbst x-accel-buffering: no

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

Streamable HTTP kann eine abgerissene Verbindung fortsetzen, statt sie neu zu beginnen. Der Server hängt an jedes SSE-Event ein `id:`-Feld; der Client schickt beim Reconnect die zuletzt gesehene ID im `Last-Event-ID`-Header, und der Server spielt genau die Events danach nach. Ohne diesen Mechanismus ist ein Reconnect ein Neuanfang mit leerem Stream.

Der Abriss ist der Normalfall, nicht der Ausnahmefall. Reverse Proxies schliessen im Leerlauf (Railway, Render und die meisten Ingress-Defaults liegen im Bereich von Minuten), ein Rolling Deploy beendet den Pod, ein Mobilfunkwechsel wechselt die IP, ein zugeklappter Laptop schliesst die Verbindung. Genau währenddessen läuft der lange Tool-Call, für den sich Streaming überhaupt lohnt.

**Was dabei verloren geht, ist nicht die Sitzung, sondern die Antwort.** Der Request wurde angenommen, die Arbeit ist möglicherweise getan — nur die Bytes kommen nie an. Für den Client sieht das aus wie ein geschlossener Stream, nicht wie ein Fehler: kein JSON-RPC-Error, kein Statuscode, nichts, was eine Fehlerbehandlung greifen liesse. Der übliche Reflex des Clients ist, den Tool-Call erneut zu senden. Bei einem schreibenden Tool ohne Idempotency-Key (siehe `ARCH-010`) ist das eine zweite Ausführung.

**Abgrenzung zu `SCALE-002` / `SCALE-003`.** Affinität und Resumability lösen zwei verschiedene Hälften desselben Reconnects und ersetzen einander nicht:

| | Frage | Ohne sie |
|---|---|---|
| `SCALE-002` / `SCALE-003` | Landet der Reconnect auf **derselben Instanz**? | Richtiger Zustand, falscher Pod — Session weg |
| `SCALE-007` | Bekommt der Client die **verpassten Events**? | Richtiger Pod, richtige Session — Antwort weg |

Sticky Sessions sind korrekt konfiguriert, die `Mcp-Session-Id` ist gültig, der Reconnect landet auf der richtigen Instanz — und die Antwort auf den laufenden Request ist trotzdem verloren, weil niemand sie aufbewahrt hat. Das ist eine eigene Prüfdimension, kein zu enger Fall der beiden anderen.

**Der Replay ist stream-gebunden.** Event-IDs sind innerhalb einer Session eindeutig, aber jeder Stream hat seine eigene Folge. Beim Resume darf nur nachgespielt werden, was zu dem Stream gehört, aus dem die `Last-Event-ID` stammt. Ein Store, der nach ID sucht und alles Jüngere nachspielt, mischt die Antwort eines fremden Requests in die wiederaufgenommene Verbindung — im besten Fall ein Protokollfehler beim Client, im schlechteren ein Leck zwischen zwei Anfragen derselben Session.

`medium`: Die Spec stellt Resumability als **MAY**, und ein Client, der den Tool-Call wiederholt, kommt bei lesenden Tools ans Ziel. Ein Server ohne Event-Store ist degradiert, nicht kaputt. Auf Cloud-Deployments mit Idle-Timeout tritt der Fall aber nicht gelegentlich auf, sondern regelmässig — und die Wiederholung ist genau dann teuer, wenn der Call lange lief oder schrieb.

### Remediation

Aus dem Katalog (`checks/SCALE-007.md`, Remediation), auf die Gaps oben anzuwenden:

1. Klären, ob die Events überhaupt IDs tragen — ohne das ist alles Weitere gegenstandslos. Im Python-SDK entstehen die IDs im Event-Store; im TS-SDK ebenso. Kein Store, keine IDs.
2. Store verdrahten. Für Single-Replica genügt die In-Memory-Variante aus den SDK-Beispielen als Zwischenschritt.
3. Ab zwei Replicas den Store dorthin legen, wo `SCALE-002` bereits den Session-State hinlegt. Ein Deployment mit geteiltem Session-State und lokalem Event-Store ist inkonsistent — der Reconnect findet die Session und verliert trotzdem die Antwort.
4. TTL setzen. Events sind nur bis zum Reconnect-Fenster interessant; ohne Ablauf wächst der Store mit jedem Tool-Call.
5. Proxy-Konfiguration nachziehen: Buffering aus, Read-Timeout über die längste erwartete Tool-Laufzeit.
6. Den Abriss einmal wirklich auslösen — Verbindung hart trennen, mit `Last-Event-ID` wiederaufnehmen, nachgespielte Events zählen. Ein nie ausgelöster Resume-Pfad ist unbelegt.

```diff
- session_manager = StreamableHTTPSessionManager(app=server)
+ session_manager = StreamableHTTPSessionManager(
+     app=server,
+     event_store=RedisEventStore(url=os.environ["REDIS_URL"], ttl=900),
+ )
```

### Effort Estimate

Katalog-Richtwert (checks/SCALE-007.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

M — 1–3 Tage. Der Store ist schnell verdrahtet; die Zeit geht in die geteilte Ablage bei mehreren Replicas und in die Gegenprobe mit echtem Verbindungsabriss.
