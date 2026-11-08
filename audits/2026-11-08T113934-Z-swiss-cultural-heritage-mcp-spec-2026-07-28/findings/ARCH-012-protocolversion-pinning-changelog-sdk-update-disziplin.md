## Finding: ARCH-012 — protocolVersion-Pinning + CHANGELOG + SDK-Update-Disziplin

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `ARCH-012` |
| **PDF-Reference** | Anhang A9 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Beide Baselines gemessen. 2026-07-28: Pro-Request-Pruefung gegen _meta, -32022 mit supported-Liste und dieselbe Liste in server/discover sind am Draht belegt, ueber HTTP und stdio; die Mechanik stammt vollstaendig aus dem SDK. 2025-11-25: die Version ist nicht im Server gepinnt, sondern per CI-Test an das installierte SDK gebunden; das verfehlt das woertliche Kriterium und laesst die Betriebsinstallation frei. CHANGELOG, README-Abschnitt und Dependabot vorhanden. Mehr als die Haelfte erfuellt, die Pin-Luecke ist medium -> partial.

### Expected Behavior

Aus dem Katalog (`checks/ARCH-012.md`, Pass Criteria):

- [ ] `protocolVersion` ist im Server-Code explizit gepinnt (kein «latest», kein Default)
- [ ] Auf `2026-07-28`: Die gepinnte Version wird **pro Request** gegen `io.modelcontextprotocol/protocolVersion` aus `_meta` geprüft — eine Konstante ohne diesen Vergleich zählt nicht
- [ ] Auf `2026-07-28`: Nichtübereinstimmung liefert `UnsupportedProtocolVersionError` (`-32022`), und `server/discover` nennt dieselbe Versionsliste (`ARCH-016`)
- [ ] `CHANGELOG.md` vorhanden, im Keep-a-Changelog-Format
- [ ] CHANGELOG-Einträge nennen explizit Spec-Version-Bumps
- [ ] README hat Sektion «MCP Protocol Version» mit aktuell unterstützter Version
- [ ] Update-Policy im README dokumentiert
- [ ] Dependabot oder Renovate aktiv für monatliche SDK-Update-PRs

### Evidence

- grep -rnE 'protocolVersion|protocol_version|PROTOCOL_VERSION|SUPPORTED_PROTOCOL' src/ -> nur Kommentare (server.py:395,403,453,464); kein protocol_version= am MCPServer(...) (server.py:470-479). Die Version kommt aus dem SDK, nicht aus Server-Code.
- tests/test_protocol_version.py:56-57,67-82,166-183 — DOCUMENTED_HANDSHAKE_VERSION='2025-11-25' und DOCUMENTED_MODERN_VERSION='2026-07-28' gegen mcp.types.version (LATEST_HANDSHAKE_VERSION / LATEST_MODERN_VERSION) gebunden, dazu echter initialize durch den ASGI-Stack (2024-11-05..2025-11-25 behalten ihre Revision, 2026-07-28 im Handshake wird auf 2025-11-25 gedeckelt).
- Laufzeit 2026-07-28 (scratchpad/probe_modern.py, ASGI-Stack aus build_http_app): tools/list mit _meta protocolVersion '2099-01-01' -> HTTP 400, error.code -32022, data.supported=['2026-07-28'], requested='2099-01-01'; server/discover -> supportedVersions=['2026-07-28'] (dieselbe Liste).
- Laufzeit stdio (scratchpad/probe_stdio2.py, python -m swiss_cultural_heritage_mcp.server): auf DERSELBEN Verbindung erst tools/list mit '2099-01-01' -> -32022, danach server/discover mit '2026-07-28' -> resultType complete, supportedVersions ['2026-07-28'] — die Version wird pro Request aus _meta gelesen (SDK mcp/shared/inbound.py:374-386 classify_inbound_request, mcp/server/runner.py:755-790).
- CHANGELOG.md:1-8 Keep-a-Changelog 1.0.0 + SemVer, [Unreleased] vorhanden; CHANGELOG.md:389-400 nennt beide Revisionen beim Protokoll-Gate, :740-742 den SDK-2.x-Wechsel; letzte Aenderung git log -1 CHANGELOG.md = 2026-11-08 12:33 +0100.
- git show HEAD:README.md Zeilen 325-340 — Abschnitt '## MCP Protocol Version' mit Tabelle (Handshake 2024-11-05..2025-11-25, Envelope 2026-07-28) und Zeile 'Update policy' (Dependabot monatlich, Bumps im CHANGELOG).
- .github/dependabot.yml:4-13 — package-ecosystem pip, interval monthly, open-pull-requests-limit 5, Gruppe python-deps '*' (deckt mcp ab).
- pyproject.toml:39 — 'mcp[cli]>=2.0.0,<3' (Spanne, kein exakter Pin); installiert gemessen: mcp 2.3.0, mcp-types==2.3.0 (importlib.metadata.requires('mcp')).

### Gaps

- Kein Pin im Server-Code: auf 2025-11-25 gilt der SDK-Default (Fail-Pattern 'keine explizite Version'). Gebunden ist er nur durch tests/test_protocol_version.py in der CI — eine Neuinstallation mit einem spaeteren mcp 2.x (pyproject.toml:39 erlaubt <3) kann die Handshake-Obergrenze im Betrieb verschieben, ohne dass ein Test laeuft. Das SDK bietet laut Test-Docstring keinen setzbaren Pin; die Abhilfe waere eine engere Spanne oder ein Laufzeit-Assert.
- README-Update-Policy nennt keine Breaking-Change-Regel (Major-Release bei Bruch) und kein Kompatibilitaetsfenster fuer alte Spec-Versionen (Pass-Pattern Modus 3).
- Beobachtung (SDK-Verhalten, kein Server-Code): ein Envelope mit protocolVersion '2025-11-25' und gleichlautendem MCP-Protocol-Version-Header ergibt ueber HTTP -32600 'Bad Request: Missing session ID' statt -32022 (scratchpad/probe_modern.out, 'handshake version in envelope').

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

Die MCP-Spec hat in 21 Monaten fünf Major-Updates erlebt (2024-11, 2025-03, 2025-06, 2025-11, 2026-07). Das ist eine ungewöhnlich hohe Velocity für einen Industriestandard. Konkrete Folgen für Server-Maintainer:

1. **Tool Annotations** kamen erst 2025-03-26
2. **OAuth Resource Server** mit RFC 8707 wurde erst 2025-06-18 verpflichtend
3. **WebSocket-Transport** wurde 2025-03 abgeschafft, durch Streamable HTTP ersetzt
4. **Sitzungen und der `initialize`-Handshake** sind mit 2026-07-28 ersatzlos entfallen

Wer die `protocolVersion` als «latest» (oder gar nicht) pinnt, riskiert dass:

- Ein SDK-Update auf einer neuen Spec-Version den Server bricht (Client erwartet altes Protokoll)
- Sicherheits-Erweiterungen unbemerkt aktiviert oder deaktiviert werden
- Compliance-Anforderungen (z.B. RFC 8707 für DSG-konforme Multi-Tenant-Setups) ohne dokumentierten Übergang verloren gehen

Der Anhang verlangt drei Disziplinen:

1. **`protocolVersion` explizit gepinnt** im Server-Code, nicht «latest»
2. **`CHANGELOG.md`** im Keep-a-Changelog-Format mit Spec-Version-Referenzen pro Release
3. **Breaking-Change-Policy** im README dokumentiert
4. **Monatliche SDK-Update-Prüfung**, Breaking-Changes auf Branch testen vor Major-Update

Severity ist `medium`, weil Verstösse meist über Tests oder CI sichtbar werden — nicht stille Sicherheitslücken, sondern offene Brüche, die behoben werden.

### Wo die Version steht, hängt an der Baseline

Punkt 1 hat mit `2026-07-28` seinen Ort gewechselt, und das ist keine Feinheit — es ist der Unterschied zwischen einer Konstruktor-Konstante und einem Feld an jeder Anfrage:

| | `2025-11-25` | `2026-07-28` |
|---|---|---|
| Wo verhandelt | einmal im `initialize`-Handshake | gar nicht — jede Anfrage trägt die Version selbst |
| Wo im Code | `protocol_version=` am Server-Objekt | `io.modelcontextprotocol/protocolVersion` in `_meta`, pro Request gelesen |
| Wie ausgewiesen | Capabilities aus dem Handshake | `server/discover` (`ARCH-016`), als **Liste** unterstützter Versionen |
| Bei Nichtübereinstimmung | Handshake scheitert | `UnsupportedProtocolVersionError` (`-32022`) je Anfrage |

**Was dabei kippt:** Auf der alten Baseline war eine gepinnte Version eine Zusicherung — der Handshake liess nichts anderes zu. Auf der neuen ist eine im Konstruktor gepinnte Version bestenfalls Dekoration und schlimmstenfalls eine Lüge: Sie hindert niemanden daran, eine Anfrage mit einer anderen Version zu schicken, und wenn der Server das `_meta`-Feld nicht liest, bearbeitet er sie trotzdem. Der Server behauptet dann eine Version, die er nicht durchsetzt.

Deshalb prüft Modus 1 unten **je Baseline etwas anderes**. Dieselbe Frage, zwei Orte.

### Remediation

Aus dem Katalog (`checks/ARCH-012.md`, Remediation), auf die Gaps oben anzuwenden:

### Schritt 1: protocolVersion pinnen

```diff
+ from importlib.metadata import version

  mcp = FastMCP(
      name="zh-education-mcp",
+     protocol_version="2025-06-18",
  )
```

### Schritt 2: CHANGELOG initialisieren

Wenn nicht vorhanden, mit Template starten und retroaktiv Major-Versionen dokumentieren (mindestens letzte 3).

### Schritt 3: Dependabot konfigurieren

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "monthly"
    open-pull-requests-limit: 5
```

### Schritt 4: Quartalsweise Spec-Review

Im Audit-Tracker (Notion) oder GitHub Issues ein recurring Reminder für quartalsweise Spec-Velocity-Review:

- Was hat sich an der MCP-Spec geändert seit letztem Release?
- Welche Server müssen ihre `protocolVersion` aktualisieren?
- Gibt es Compliance-relevante Spec-Änderungen?

### Effort Estimate

Katalog-Richtwert (checks/ARCH-012.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — < 1 Tag pro Server. Pinning + CHANGELOG-Template + Dependabot-Setup.
