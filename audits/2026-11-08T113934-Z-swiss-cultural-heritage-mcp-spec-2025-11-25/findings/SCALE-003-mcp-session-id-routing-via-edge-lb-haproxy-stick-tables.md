## Finding: SCALE-003 — Mcp-Session-Id Routing via Edge-LB (HAProxy Stick-Tables)

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | enforced |
| **Check-Status** | fail |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `SCALE-003` |
| **PDF-Reference** | Sec 5.2 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Nur 2025-11-25. Folgebefund derselben Ursache wie SCALE-002: Die Architektur setzt auf Single-Instance, und dafuer braucht es keinen LB mit Header-Affinitaet — aber diese Voraussetzung ist nur dokumentiert (docs/scaling.md), nicht erzwungen. Wird der Single-Instance-Entscheid als Restrisiko akzeptiert, sollte das fuer SCALE-002 und SCALE-003 gemeinsam geschehen.

### Expected Behavior

Aus dem Katalog (`checks/SCALE-003.md`, Pass Criteria):

- [ ] Edge-LB liest `Mcp-Session-Id`-Header explizit
- [ ] Stick-Table / Hash-Mechanismus mit ausreichender Kapazität (≥100k Sessions)
- [ ] TTL ist explizit gesetzt (z.B. 24h, korreliert mit Session-TTL)
- [ ] Failover-Verhalten getestet: bei Backend-Ausfall wird Session nicht auf neuen Backend ohne Shared State geroutet

### Evidence

- git ls-files | grep -iE 'haproxy|nginx|ingress|render\.yaml|railway\.toml|docker-compose|k8s/|helm/|fly\.toml' -> leer (rc=1): keine Edge-LB-Konfiguration im Repo
- git grep -nIiE 'stick|http_mcp_session_id|session.?affinity' -- ':!audits' -> nur docs/scaling.md:30-48 (Beispiel-Snippets HAProxy 'stick on req.hdr(Mcp-Session-Id)', nginx 'hash $http_mcp_session_id consistent') — Doku-Vorschlag, keine ausgelieferte Konfiguration (Positivkontrolle: Muster schlaegt an)
- Runtime (lokal gestarteter Server HEAD 9b3a1b4 (editable install), MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT=8765, SDK mcp 2.3.0, 2026-11-08): initialize 2025-11-25 liefert `mcp-session-id`; der Header ist also das Routing-Merkmal, das ein LB lesen muesste — keine Instanz im Repo tut es

### Gaps

- high: kein Edge-LB liest Mcp-Session-Id; keine Stick-Table/Hash-Konfiguration, keine TTL, kein Failover-Test

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

Dieser Check ergänzt SCALE-002 (Stateful Load Balancing) mit dem konkreten Routing-Layer. Wenn die Architektur-Entscheidung Sticky Sessions ist, muss der Edge-Load-Balancer den `Mcp-Session-Id`-Header **lesen** und für Routing nutzen. Auf K8s-Ingress mit Default-Konfiguration läuft das nicht out-of-the-box — die meisten Ingress-Controller nutzen IP-basierte Affinität, was hinter NAT/Proxy bricht.

Konkrete LB-Optionen: HAProxy mit `stick-table` auf `hdr(Mcp-Session-Id)`, NGINX mit `ngx_http_upstream_module` und `hash $http_mcp_session_id consistent`, oder K8s Ingress mit `nginx.ingress.kubernetes.io/affinity-mode: persistent` plus Cookie-Mapping.

### Remediation

Aus dem Katalog (`checks/SCALE-003.md`, Remediation), auf die Gaps oben anzuwenden:

Für K8s-Ingress (NGINX):

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mcp-ingress
  annotations:
    nginx.ingress.kubernetes.io/affinity: "cookie"
    nginx.ingress.kubernetes.io/session-cookie-name: "mcp-route"
    nginx.ingress.kubernetes.io/upstream-hash-by: "$http_mcp_session_id"
spec:
  rules:
  - host: mcp.example.ch
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mcp-server
            port:
              number: 8080
```

### Effort Estimate

Katalog-Richtwert (checks/SCALE-003.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

M — 1–3 Tage. LB-Config + Failover-Tests.
