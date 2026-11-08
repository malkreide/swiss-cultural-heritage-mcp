## Finding: OBS-008 — Der Server sagt an, dass er bedient — eine stabile Zeile auf stderr

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | advisory |
| **Check-Status** | fail |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `OBS-008` |
| **PDF-Reference** | Custom (Portfolio-Erhebung 2026-08-03, 42 veröffentlichte Server) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

adoption: advisory laut Frontmatter. Bei geschlossenem stdin beendet sich der Server sofort sauber (exit 0) — deshalb zusaetzlich mit leerlaufendem stdin gemessen.

### Expected Behavior

Aus dem Katalog (`checks/OBS-008.md`, Pass Criteria):

- [ ] Der Server schreibt beim Erreichen des Bedienzustands eine Zeile auf **stderr**, nicht auf stdout (`OBS-003`)
- [ ] Die Zeile erscheint innerhalb von sechs Sekunden bei **geschlossenem stdin**, ohne dass eine Anfrage gestellt wurde
- [ ] Bei strukturiertem Log ist das `event`- bzw. `msg`-Feld **exakt** der Marker — erklärende Zusätze stehen in eigenen Feldern
- [ ] Bei Klartext-Log ist eine **stabile Teilzeichenkette** als Marker benannt
- [ ] Der Marker enthält **keinen Zeitstempel** und nichts anderes Laufvariables (PID, Port, Dauer, konfigurationsabhängige Anzahlen)
- [ ] Der Marker stammt aus dem Code des Servers — der **SDK-Banner zählt nicht**
- [ ] Alles, was scheitern kann (Konfiguration, Clients, Tool-Registrierung), liegt **vor** dem Marker
- [ ] Der Marker ist im README dokumentiert, in der Schreibweise, auf die verglichen wird
- [ ] Die negative Kontrolle wurde durchgeführt: ein erzwungener Fehlstart erzeugt Ausgabe auf stderr — sonst misst der Aufbau nichts

### Evidence

- Laufzeit 2026-11-08T11:58Z (wiederholt nach dem Kill-Hinweis, Konsolen-Skript swiss-cultural-heritage-mcp.exe): stdin leerlaufend, timeout 6 → exit 124 (Server lief), stderr 0 Bytes, stdout 0 Bytes; stdin=/dev/null → exit 0 (EOF beendet sauber), stderr 0 Bytes. Erstlauf 11:45Z mit 'python -m ...server' identisch
- Negative Kontrolle, selber Aufbau: OTEL_EXPORTER_OTLP_ENDPOINT gesetzt → exit 124, stderr '{"reason": "opentelemetry nicht installiert ...", "event": "otel.unavailable", "level": "warning", ...}' — der Aufbau laesst Server-stderr durch; das Schweigen ist ein Ergebnis
- src/swiss_cultural_heritage_mcp/server.py:360-370 — lifespan erzeugt den HTTP-Client und yieldet ohne jede Log-Zeile; kein READY-Marker im Modul
- git show HEAD:README.md / README.de.md | grep -niE 'marker|bereitschaft|ready' → keine Treffer (Kontrolle 'Bereitschaftsmarker: server ready' trifft)

### Gaps

- medium: kein Bereitschaftsmarker auf stderr — von aussen nicht von einem beim Start gestorbenen Prozess unterscheidbar
- medium: kein dokumentierter Marker im README, kein Test

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

Ein MCP-Server auf stdio hat einen Moment, in dem sich alles entscheidet: Er hat seine Konfiguration gelesen, seine Clients gebaut, seine Tools registriert — und wartet ab jetzt auf Anfragen. Vor diesem Moment ist er ein Prozess, danach ist er ein Server. Von aussen sind beide Zustände dasselbe: eine PID, die nichts tut.

Genau deshalb ist «läuft» keine Beobachtung, sondern eine Annahme. Wer sie prüfen will, hat auf stdio nur einen Kanal: **stderr**. stdout gehört dem Protokoll und ist für Diagnose gesperrt (`OBS-003`), ein Exit-Code kommt erst, wenn es zu spät ist, und ein Port existiert nicht.

**Die Erhebung** (2026-08-03, 42 veröffentlichte Server): Gestartet wurde jeder mit **geschlossenem stdin** und sechs Sekunden Geduld. Ohne stdin gibt es keine Anfrage, also auch keine Antwort — was in diesem Fenster auf stderr erscheint, ist ausschliesslich die Selbstauskunft des Servers.

| Ergebnis | Server |
|---|---|
| Stabile Marker-Zeile auf stderr | 27 |
| **Nichts** | 13 |
| **Nur der FastMCP-Banner des SDK** | 2 |

15 von 42 sind damit von aussen nicht unterscheidbar von einem Server, der beim Import gestorben ist.

**Was dabei durchrutscht:** `zh-education-mcp` `0.2.4` startete überhaupt nicht. Der Prozess kam hoch, brach in der Initialisierung ab und beendete sich still. Weil er auch im Normalfall nichts gesagt hätte, gab es keinen Unterschied zu bemerken — der Zustand blieb **monatelang** unentdeckt. Kein Test war rot; es gab keinen, der etwas anderes erwartet hätte als Schweigen.

### Warum der SDK-Banner nicht zählt

Zwei Server der Erhebung gaben etwas aus, und es war trotzdem kein Marker. Der Banner, den FastMCP beim Start selbst schreibt, hat zwei Eigenschaften, die ihn disqualifizieren:

1. **Er ist die Ausgabe des SDK, nicht die des Servers.** Er erscheint, sobald das Framework-Objekt läuft — also *bevor* der Lifespan des Servers seine Clients gebaut und seine Konfiguration validiert hat. Er beweist, dass ein FastMCP existiert, nicht dass dieser Server bedient. Bei `zh-education-mcp` wäre er erschienen und der Server trotzdem tot gewesen.
2. **Er gehört jemand anderem.** Sein Wortlaut ist eine Darstellungsentscheidung des SDK und ändert sich beim nächsten Update, ohne dass ein Release des Servers dazwischenliegt — dieselbe Mechanik wie in `DEP-001`, nur eine Ebene höher. Ein Monitoring, das darauf greift, bricht an einem Tag, an dem niemand etwas getan hat.

Der Marker muss also aus dem Code des Servers stammen und an der Stelle stehen, an der er tatsächlich bedienbereit ist.

### Drei Regeln für den Marker — alle drei aus Messungen

**1. Strukturiertes Log: Das `event`/`msg`-Feld wird EXAKT verglichen.**

Wer `structlog` oder `logging` mit JSON-Renderer einsetzt, hat ein Feld, das die Meldung trägt. Dieses Feld ist der Marker, und es wird auf Gleichheit geprüft — **nicht** auf Präfix, nicht auf `startswith`, nicht auf «enthält».

Der Grund ist gemessen: `openlex-mcp` war mit dem Marker «Lifespan gestartet» dokumentiert. Das Feld lautete tatsächlich:

```
Lifespan gestartet — geteilter HTTP-Client bereit
```

Ein Präfix-Vergleich hätte gepasst und wäre in dem Moment gebrochen, in dem jemand den erklärenden Zusatz umformuliert — was niemand als Änderung an einer Schnittstelle wahrnimmt, weil es nach einem Log-Text aussieht. Ein exakter Vergleich zwingt die Frage sofort: Der Marker ist ein Vertrag, kein Fliesstext. Wer ihn ändert, ändert eine Schnittstelle und merkt es.

Praktisch heisst das: Erklärende Zusätze gehören in **eigene Felder**, nicht in das Feld, das den Marker trägt.

**2. Klartext: Eine stabile Teilzeichenkette genügt.**

Schreibt der Server unstrukturierten Text, gibt es kein Feld, das man exakt vergleichen könnte — die Zeile trägt Logger-Namen, Level und Formatierung mit. Hier ist die Anforderung eine **Teilzeichenkette, die stabil ist**: ein Stück Text, das der Server bewusst als Marker führt und nicht bei jeder Umformulierung mitwandert.

Das ist eine schwächere Zusage als Regel 1, und das ist der Preis für unstrukturierte Logs — kein Grund, Regel 1 aufzuweichen.

**3. Nie ein Zeitstempel — und nichts anderes Laufvariables.**

Ein Marker, der `2026-08-03T09:14:22Z` enthält, passt beim ersten Lauf und nie wieder. Dasselbe gilt für PID, Port, Hostname, Dauer in Millisekunden und die Anzahl geladener Tools, wenn sie von der Konfiguration abhängt. Der Marker ist die **invariante** Teilmenge der Zeile; alles Laufvariable gehört in andere Felder oder hinter den Marker, nie hinein.

Zeitstempel im Log sind selbstverständlich richtig und sollen bleiben. Sie dürfen nur nicht Teil dessen sein, worauf verglichen wird.

### Positivbeispiel

```python
import sys, structlog

log = structlog.get_logger()

# Der Marker: genau dieses Feld, genau dieser Wortlaut. Erklärendes steht
# daneben, nicht darin — sonst bricht der exakte Vergleich bei jedem
# Umformulieren (siehe openlex-mcp).
READY_MARKER = "server ready"

@asynccontextmanager
async def lifespan(_):
    client = await build_http_client()      # alles, was scheitern kann,
    tools = register_tools()                # liegt VOR dem Marker
    log.info(READY_MARKER, tools=len(tools), transport="stdio")
    try:
        yield
    finally:
        await client.aclose()
```

Auf stderr, mit geschlossenem stdin:

```json
{"event": "server ready", "tools": 7, "transport": "stdio", "timestamp": "2026-08-03T09:14:22Z"}
```

`event` ist exakt `server ready`. Anzahl Tools und Zeitstempel stehen daneben und dürfen sich bewegen.

Und der Marker ist dokumentiert — im README des Servers, damit ein Monitoring ihn nicht aus dem Quelltext raten muss:

```markdown
Bereitschaftsmarker (stderr, JSON-Feld `event`): `server ready`
```

### Negativbeispiel

```python
@asynccontextmanager
async def lifespan(_):
    log.info(f"[{datetime.now().isoformat()}] Lifespan gestartet — "
             f"HTTP-Client bereit, {len(tools)} Tools auf Port {port}")
    yield
```

Vier Fehler in einer Zeile:

| Stelle | Warum |
|---|---|
| `datetime.now()` | Regel 3 — passt beim ersten Lauf und nie wieder |
| `{len(tools)}` / `{port}` | Regel 3 — konfigurationsabhängig, also nicht invariant |
| «Lifespan gestartet — HTTP-Client bereit» als ein Feld | Regel 1 — der erklärende Zusatz steckt im Marker-Feld; genau der `openlex-mcp`-Fall |
| Marker vor `yield`, aber ohne dass etwas davor passiert | Er meldet «bereit», bevor irgendetwas gebaut wurde — er sagt nur, dass der Lifespan eingetreten ist |

Und der Fall, der die Erhebung dominiert:

```python
@asynccontextmanager
async def lifespan(_):
    yield                      # kein Marker. 13 von 42 Servern.
```

### Remediation

Aus dem Katalog (`checks/OBS-008.md`, Remediation), auf die Gaps oben anzuwenden:

```diff
+ # Bereitschaftsmarker. Exakter Vergleichswert — Änderungen hier sind
+ # Schnittstellenänderungen (README und Monitoring ziehen mit).
+ READY_MARKER = "server ready"
+
  @asynccontextmanager
  async def lifespan(_):
-     log.info(f"Lifespan gestartet — {len(tools)} Tools, Port {port}")
      client = await build_http_client()
      tools = register_tools()
+     # Erklärendes in eigene Felder, nicht in das Marker-Feld.
+     log.info(READY_MARKER, tools=len(tools), transport=settings.transport)
      try:
          yield
      finally:
          await client.aclose()
```

Dazu ins README, in der Schreibweise, auf die verglichen wird:

```markdown
Bereitschaftsmarker (stderr, JSON-Feld `event`): `server ready`
```

Und der Test, der die Zusage hält — er misst dasselbe wie Modus 1:

```python
def test_server_meldet_bereitschaft():
    p = subprocess.run(
        [sys.executable, "-m", "<pkg>"],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=6,
    )
    events = [json.loads(ln)["event"] for ln in p.stderr.splitlines() if ln.startswith("{")]
    assert READY_MARKER in events, (
        f"Kein Bereitschaftsmarker auf stderr. Gesehen: {events}. "
        "Exakter Vergleich auf das `event`-Feld — ein Präfix zählt nicht."
    )
    assert p.stdout == "", "stdout gehört dem Protokoll (OBS-003)"
```

### Effort Estimate

Katalog-Richtwert (checks/OBS-008.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — Der Marker selbst ist eine Zeile. Die Zeit geht in die Frage, an welcher Stelle des Lifespans er stehen muss, und in die Entscheidung, welche Zusätze aus dem Feld heraus in eigene Felder wandern.
