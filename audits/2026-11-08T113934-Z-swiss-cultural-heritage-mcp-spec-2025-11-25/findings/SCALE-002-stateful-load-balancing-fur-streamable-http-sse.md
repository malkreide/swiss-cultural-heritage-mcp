## Finding: SCALE-002 — Stateful Load Balancing für Streamable HTTP / SSE

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | enforced |
| **Check-Status** | fail |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `SCALE-002` |
| **PDF-Reference** | Sec 5.2 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Gemessen nur fuer 2025-11-25 (Legacy-Handshake mit Mcp-Session-Id). Der dokumentierte Single-Instance-Betrieb entschaerft das Risiko praktisch, ist aber kein Pass-Muster des Checks und wird durch keine Konfiguration erzwungen (Render-Autoscaling koennte ihn still brechen). Eine Akzeptanz als bewusstes Restrisiko waere ein Entscheid des Owners, nicht ein Pass. Billigste Behebung fuer die Legacy-Aera: stateless_http=True pruefen (Tool-Logik ist zustandslos) oder replicas=1 in einem eingecheckten render.yaml festschreiben.

### Expected Behavior

Aus dem Katalog (`checks/SCALE-002.md`, Pass Criteria):

- [ ] Mindestens **eines** der folgenden Muster ist nachweisbar implementiert:
  - Sticky Sessions auf Edge-LB-Ebene (HAProxy/Nginx/K8s-Ingress) basierend auf `Mcp-Session-Id`
  - Shared-State-Session-Manager mit Redis, Cloudflare Durable Objects oder vergleichbarem
- [ ] Session-Lifetime ist explizit gesetzt (TTL definiert)
- [ ] Failover-Test (Modus 3) zeigt korrektes Verhalten ODER wurde nachgewiesen über Tests

### Evidence

- src/swiss_cultural_heritage_mcp/server.py:3574 — `mcp.streamable_http_app(transport_security=security, host=host)` ohne stateless_http/event_store; SDK-Signatur (mcp 2.3.0): `stateless_http: bool = False, session_idle_timeout: float | None = 1800, max_sessions = 10000` -> Sessions liegen im Prozessspeicher
- Runtime (lokal gestarteter Server HEAD 9b3a1b4 (editable install), MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT=8765, SDK mcp 2.3.0, 2026-11-08): POST /mcp initialize 2025-11-25 -> Antwortheader `mcp-session-id: 1705ca61107f46ef823af62c3697d9c7`; GET /mcp ohne Session -> HTTP 400 `Bad Request: Missing session ID`. Die Legacy-Aera ist sitzungsgebunden
- git grep -nIiE 'stick|session.?affinity|sessionAffinity|redis|memcached|DurableObject|SessionStore|http_mcp_session_id' -- ':!audits' -> Treffer nur in docs/scaling.md (Beispielkonfigurationen), CHANGELOG.md:820, docs/security.md:73 — keiner in src/ oder in einer Konfigurationsdatei (Positivkontrolle: das Muster schlaegt auf die Doku-Beispiele an)
- git ls-files | grep -iE 'haproxy|nginx|ingress|render\.yaml|railway\.toml|docker-compose|k8s/|helm/|fly\.toml' -> leer (rc=1): kein LB- oder Deployment-Manifest, das Affinitaet oder replicas=1 erzwingt
- docs/scaling.md:5-9 — 'The server must run as a single instance' (Behauptung, keine Evidenz; durch nichts im Repo erzwungen)

### Gaps

- high: weder Sticky Sessions noch Shared-State-Session-Manager implementiert; Session-State nur in-process
- medium: Session-TTL nicht explizit gesetzt — es gilt der SDK-Default session_idle_timeout=1800 s, im Code nicht verankert
- medium: kein Failover-Test; die Single-Instance-Auflage ist nur dokumentiert, nicht in einer Deploy-Konfiguration festgeschrieben

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

MCP-Verbindungen über Streamable HTTP / SSE sind **fundamental zustandsbehaftet**. Bei der Verbindungsinitialisierung verhandeln Client und Server Protokollversionen, Capability-Flags und etablieren Abonnements für Ressourcenänderungen.

In horizontal skalierten Deployments (Kubernetes, mehrere Pods, Cloudflare Workers, Railway-Replicas) routen Standard-Load-Balancer naive Anfragen ohne Affinität zu unterschiedlichen Backend-Instanzen. Wenn eine MCP-Session mitten im Lifecycle auf einen anderen Pod springt, geht der Sitzungskontext verloren — der Agent bricht ab, Konversation kollabiert.

Es gibt zwei legitime Lösungsmuster: Sticky Sessions (infrastrukturell) oder Shared State (cloud-native).

### Remediation

Aus dem Katalog (`checks/SCALE-002.md`, Remediation), auf die Gaps oben anzuwenden:

### Variante A: Sticky Sessions mit HAProxy

```haproxy
frontend mcp_frontend
    bind *:443 ssl crt /etc/ssl/server.pem
    mode http
    # Backend-Selection nach Mcp-Session-Id
    default_backend mcp_backend

backend mcp_backend
    mode http
    balance roundrobin
    stick-table type string len 64 size 200k expire 24h peers mycluster
    stick on hdr(Mcp-Session-Id)
    option httpchk GET /healthz
    server mcp1 10.0.1.1:8080 check
    server mcp2 10.0.1.2:8080 check
    server mcp3 10.0.1.3:8080 check
```

### Variante B: Redis-basierter Session-Manager

```python
# pyproject.toml
# dependencies = ["fastmcp", "redis>=5.0", "structlog"]

from contextlib import asynccontextmanager
from fastmcp import FastMCP
from redis.asyncio import Redis
import json

@asynccontextmanager
async def lifespan(app):
    redis_client = Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    app.state.session_store = redis_client
    try:
        yield
    finally:
        await redis_client.aclose()

mcp = FastMCP("zurich-opendata", lifespan=lifespan)
```

### Effort-Empfehlung

- **Variante A** schneller bei vorhandener LB-Infrastruktur (1–2 Tage)
- **Variante B** robuster langfristig, vermeidet Sticky-Session-Komplikationen (3–5 Tage)

### Effort Estimate

Katalog-Richtwert (checks/SCALE-002.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

M — 1–3 Tage je nach Komplexität der bestehenden Infrastruktur.
