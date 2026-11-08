## Finding: SEC-014 — Tool-Allow-Listing via MCP-Gateway-Pattern

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | enforced |
| **Check-Status** | fail |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `SEC-014` |
| **PDF-Reference** | Sec 5.3 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Applies through is_cloud_deployed (Render). The control normally lives in a central gateway, not in the single-server repo; nothing points to one, and none is referenced in the docs. Risk in this profile is low (all tools read-only, public data), but the criteria are not met.

### Expected Behavior

Aus dem Katalog (`checks/SEC-014.md`, Pass Criteria):

- [ ] Bei `enterprise_context`: Tool-Allow-List pro Team/Rolle dokumentiert (im Gateway-Config oder Server-Config)
- [ ] Allow-List ist explizit ("default-deny"): nur gelistete Tools werden exponiert
- [ ] Server-Side Defense-in-Depth: Group-/Role-Check für sensitive Tools, ergänzend zum Gateway
- [ ] Denied-Tool-Aufrufe werden auditiert (siehe OBS-005)
- [ ] Tool-Liste, die der LLM-Client sieht, ist team-/rollen-spezifisch gefiltert (im `tools/list`-Response)

### Evidence

- find . (without .git/audits) -iname '*allowlist*' -o -iname '*tool-policy*' -o -iname '*gateway*' -> no hit; positive control: the same find with '*egress*' finds ./docs/network-egress.md
- git grep -ciE 'require_group|allowed_tools|tool_allowlist' HEAD -- src/ -> 0 (rc=1): no role/group check in src
- Profile auth_model none; there are no claims or groups a server-side check could read. tools/list returns all 11 tools unfiltered (11 @mcp.tool in server.py, the TestToolPins snapshot lists 11)

### Gaps

- No documented tool allow-list per team or role, neither as a gateway config nor in the server config (severity: medium)
- No default-deny, no audit of denied calls, no role-specific tools/list filtering (severity: medium)

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

Wenn mehrere MCP-Server in einer Organisation laufen, exponiert jeder Server Dutzende von Tools. Der LLM-Client (z.B. Claude Desktop pro Mitarbeiter) erhält die volle Tool-Manifest-Sammlung — und kann jedes Tool aufrufen. Ohne zentrale Kontrolle entstehen drei Risiken:

1. **Lateral Movement zwischen Servern:** Ein kompromittierter Server kann den LLM dazu bringen, Tools eines anderen Servers aufzurufen — z.B. Daten aus `schulamt-mcp` exportieren via Tool von `gateway-mcp`.

2. **Rolle-/Team-übergreifende Tool-Aufrufe:** Ein Schulamt-Mitarbeiter sollte nicht versehentlich Tools des Finanz-MCPs aufrufen können, auch wenn beide via OAuth korrekt authentifiziert sind.

3. **Compliance-Verstösse durch Tool-Kombinationen:** Tool A liefert Verwaltungsdaten, Tool B sendet E-Mails an Externe. Die Kombination beider durch das LLM erzeugt einen Datenfluss, der einzeln okay, kombiniert aber meldepflichtig ist.

Mitigation: **MCP-Gateway als zentrale Vermittlung** (verwandt zu SCALE-005). Pro Team / Rolle wird eine Allow-List definiert: welche Tools welcher Server darf der LLM aufrufen? Tools ausserhalb der Allow-List werden vor der Tool-Liste vom Gateway gefiltert — der LLM sieht sie gar nicht.

### Remediation

Aus dem Katalog (`checks/SEC-014.md`, Remediation), auf die Gaps oben anzuwenden:

### Schritt 1: Tool-Inventar pro Team

Pro Team/Rolle dokumentieren, welche Use-Cases anfallen und welche Tools dafür nötig sind. Output: Allow-Listen.

### Schritt 2: Gateway-Konfiguration

YAML wie im Pass-Pattern, eingecheckt im zentralen Gateway-Config-Repo (separater Repo, eigene Audit-Hierarchie).

### Schritt 3: Server-Side `require_group`-Decorator

Wie im Pass-Pattern. Mindestens für `Verwaltungsdaten`/`PII`-Tools verpflichtend.

### Schritt 4: Audit-Logging für denied tool calls

```python
@mcp.middleware
async def log_tool_attempts(request, call_next):
    response = await call_next(request)
    if response.status_code == 403 and "tools/call" in request.url.path:
        audit_logger.warning(
            "tool_call_denied",
            user=request.state.user_claims.get("sub"),
            attempted_tool=request.json.get("name"),
            user_groups=request.state.user_claims.get("groups"),
        )
    return response
```

### Schritt 5: Periodischer Allow-List-Review

Quartalsweise prüfen: sind alle Allow-List-Einträge noch relevant? Welche User-Beschwerden gab's wegen denied calls? Allow-List zu breit oder zu eng?

### Effort Estimate

Katalog-Richtwert (checks/SEC-014.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

L — 1–2 Wochen für Initial-Setup. Quartalsweise ~1 Tag für Review.
