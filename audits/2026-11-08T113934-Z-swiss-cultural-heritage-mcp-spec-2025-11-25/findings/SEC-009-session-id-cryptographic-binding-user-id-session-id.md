## Finding: SEC-009 — Session-ID Cryptographic Binding (user_id:session_id)

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `SEC-009` |
| **PDF-Reference** | Sec 4.6 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Measured only for 2025-11-25 as instructed. Generation (criterion 1), TTL (5) and server-side invalidation (6) come from SDK 2.3.0 and are met. Criteria 2-4 assume OAuth; without auth there is no victim context that a stolen session ID could take over, beyond progress/log notifications on that session's GET stream. That is why this is partial and not fail. Whether criteria 2-4 should count as n/a in this profile is the caller's call.

### Expected Behavior

Aus dem Katalog (`checks/SEC-009.md`, Pass Criteria):

- [ ] Session-ID-Generierung verwendet `secrets.token_urlsafe()` / `crypto.randomUUID()` (≥128 Bit Entropie)
- [ ] User-ID kommt aus **validiertem** OAuth-Token (`sub`-Claim), nicht aus Client-Headern
- [ ] Session-ID ist kryptografisch an User-ID gebunden (z.B. signiertes JWT mit `user_id`+`session_id` als Payload)
- [ ] Bei Mismatch (Session gehört zu anderem User): HTTP 401/403
- [ ] Session-TTL ist explizit gesetzt (z.B. 1h)
- [ ] Sessions werden bei Logout serverseitig invalidiert (nicht nur Client-Cookie löschen)

### Evidence

- venv/Lib/site-packages/mcp/server/streamable_http_manager.py:313 (mcp 2.3.0) — mcp_session_id=uuid4().hex (CSPRNG via os.urandom, 122 random bits); runtime log of the rebind probe: 'Created new transport with session ID: 9a4d96429fe54fe0a6f12bd25b1207fa' (32 hex)
- streamable_http_manager.py:38,94 — DEFAULT_SESSION_IDLE_TIMEOUT = 30*60; the server does not override it (server.py:3574 mcp.streamable_http_app(transport_security=..., host=...) without session_idle_timeout) -> TTL 30 min
- streamable_http_manager.py:252-259,283-284 — DELETE terminates the transport server-side and removes the session
- Profile auth_model: none; grep -rniE 'authorization|bearer|token_verifier|auth=' src/ -> no auth surface. There is no validated identity (no 'sub') to bind a session to

### Gaps

- No binding of the session ID to a user identity, no 401/403 on mismatch. Structurally impossible under auth_model none (severity: low in this profile: public, read-only, no per-user context)

### Risk Description

Siehe Gaps; Severity laut Katalog `critical`. Katalogbeschreibung:

In statusbehafteten MCP-Setups mit Streamable HTTP / SSE wird jeder Verbindung eine `Mcp-Session-Id` zugewiesen. Diese ID identifiziert den Sitzungszustand auf Server-Seite und wird bei jedem Folge-Request mitgesendet.

**Angriffsmuster (Session Hijacking):**

1. Server generiert vorhersagbare Session-IDs (z.B. inkrementell oder mit schwachem PRNG)
2. Angreifer rät / erschöpft Session-ID-Raum
3. Angreifer sendet bösartiges Event (Tool-Call) mit der erratenen Session-ID
4. Server führt Operation im Kontext des Opfers aus

**Verschärfung in Cloud-Architekturen:** Bei Shared-State-Setups (z.B. Redis als Session-Store, siehe SCALE-002) liegen alle Sessions in einer gemeinsamen Queue. Eine einzige geleakte Session-ID kompromittiert nicht nur die User-Verbindung, sondern erlaubt auch Event-Injection in laufende Konversationen.

**Mitigation in zwei Schritten:**

1. **Kryptografisch sichere Generierung:** UUIDv4 oder `secrets.token_urlsafe(32)` — niemals `random.random()` oder Timestamps.
2. **Binding an User-Identität:** Session-ID wird kombiniert mit der `user_id` aus dem **validierten** OAuth-Token (nicht aus Client-Headern). Format: `<user_id>:<session_id>`. Bei jedem Request wird geprüft, ob die Session-ID zur authentifizierten User-Identität gehört.

### Remediation

Aus dem Katalog (`checks/SEC-009.md`, Remediation), auf die Gaps oben anzuwenden:

Volles Pattern oben. Zusätzlich:

### Session-Rotation bei Privilege-Wechsel

```python
@mcp.tool()
async def elevate_to_admin(ctx: Context, justification: str):
    # Bei Privilege-Wechsel neue Session-ID generieren
    new_token = await session_store.create(ctx.user_id, scopes=["admin"])
    ctx.set_response_header("Mcp-Session-Id", new_token)
    # Alte Session invalidieren
    await session_store.invalidate(ctx.session_token)
```

### Logout-Endpoint mit Server-Side-Invalidation

```python
@app.post("/mcp/logout")
async def logout(request: Request):
    session_token = request.headers.get("Mcp-Session-Id")
    if session_token:
        await session_store.invalidate(session_token)
    return Response(status_code=204)
```

### Effort Estimate

Katalog-Richtwert (checks/SEC-009.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

M — 1–3 Tage. Session-Manager-Refactoring + Binding-Logic + Tests.
