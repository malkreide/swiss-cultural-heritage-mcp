## Finding: OBS-006 — OpenTelemetry Distributed Tracing pro Tool-Call

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `OBS-006` |
| **PDF-Reference** | Anhang B10 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

applies_when is_cloud_deployed: Render/Docker-Profil → anwendbar. Code-Grundlage solide, aber im Deployment nicht wirksam und nicht getestet; Propagation nach SEP-414 fehlt.

### Expected Behavior

Aus dem Katalog (`checks/OBS-006.md`, Pass Criteria):

- [ ] OpenTelemetry SDK installiert und initialisiert
- [ ] TracerProvider konfiguriert mit OTLP-Exporter
- [ ] Auto-Instrumentation für HTTP-Clients (httpx, requests) aktiv
- [ ] Pro Tool-Call ein Span mit: `mcp.tool.name`, `mcp.user.id`, `mcp.tool.result.is_error`
- [ ] Backend-API-Calls automatisch als Child-Spans (via Auto-Instrumentation)
- [ ] **Keine** sensitiven Daten in Span-Attributen (kein PII, kein Token, kein freier Args-Inhalt)
- [ ] OTLP-Endpoint via Env-Var konfigurierbar (typisch in Cloud-Deployments)
- [ ] Service-Name und Environment-Tag explizit gesetzt
- [ ] Auf `mcp_spec_version: 2026-07-28`: Trace-Kontext wird über die von der Spec konventionierten `_meta`-Schlüssel propagiert — `traceparent`, `tracestate`, `baggage` (SEP-414), nicht über selbst erfundene Feldnamen
- [ ] Eingehender Trace-Kontext aus `_meta` wird übernommen, statt bei jedem Request einen neuen Trace zu beginnen — sonst zerfällt die Kette genau an der Grenze, die sie überbrücken soll
- [ ] Ausgehende Requests an weitere MCP-Server tragen den Kontext in denselben Schlüsseln weiter

### Evidence

- src/swiss_cultural_heritage_mcp/server.py:191-241 — _init_tracing: gated ueber OTEL_EXPORTER_OTLP_ENDPOINT; TracerProvider mit Resource service.name 'swiss-cultural-heritage-mcp', service.version, deployment.environment (DEPLOYMENT_ENV, Default 'production'); BatchSpanProcessor(OTLPSpanExporter) (HTTP); HTTPXClientInstrumentor().instrument() → Upstream-Calls als Child-Spans
- src/swiss_cultural_heritage_mcp/server.py:245-253, 515-535 — Span 'mcp.tool.<name>' je Tool-Call mit Attributen mcp.tool.name, mcp.tool.is_error, error.type; keine Argumente/PII als Attribut (grep set_attribute → nur diese drei)
- git show HEAD:Dockerfile:30 — 'pip install --no-cache-dir --prefix=/install .' (ohne [otel]); Laufzeit mit gesetztem Endpoint ohne Extra → stderr '{"event": "otel.unavailable", "reason": "opentelemetry nicht installiert ..."}' — im ausgelieferten Container/Render-Image ist Tracing nicht aktivierbar
- grep -rnE 'traceparent|tracestate|baggage|propagat|extract\(' src/ → exit 1: kein Uebernehmen/Weiterreichen des Trace-Kontexts aus _meta (SEP-414, 2026-07-28)
- ci.yml installiert nur '.[dev]'; tests/test_server.py::TestTracing lokal: '1 passed, 2 skipped' (OTel nicht installiert) — die Span-Tests laufen auch in der CI nicht

### Gaps

- medium: Trace-Kontext aus _meta (traceparent/tracestate/baggage) wird weder uebernommen noch weitergegeben — jede Anfrage beginnt einen neuen Trace (2026-07-28-Kriterien)
- medium: Docker-Image (Render-Deployment) enthaelt das otel-Extra nicht; Tracing ist im Cloud-Deployment ohne Umbau des Images nicht einschaltbar
- medium: Span-Tests werden in CI uebersprungen (otel nicht in [dev]) — die Instrumentierung ist ungeprueft
- low: Attributname mcp.tool.is_error statt mcp.tool.result.is_error; mcp.user.id entfaellt (auth_model none)

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

OBS-005 deckt Audit-Logs für SIEM-Integration ab — Security-fokussiert. OBS-006 ergänzt das auf der **Performance- und Behavior-Seite**: jeder Tool-Call wird als OpenTelemetry-Span erfasst, mit:

- **Trace-ID** über die ganze LLM-Host → Gateway → Server → Backend-Kette
- **Tool-Name** als Span-Name
- **User-Identity** als Span-Attribut (aus `ctx.user_claims`)
- **Latenz** der einzelnen Hop-Schritte
- **Token-Count** falls Sampling involviert
- **Backend-API-Latenzen** als Child-Spans

Dieser Check ist `medium`, weil ohne Tracing zwar der Server funktioniert, aber drei wichtige Forensik- und Optimization-Workflows nicht möglich sind:

1. **Slow-Tool-Identifikation:** welche Tools haben P99-Latenzen > 5s?
2. **User-Behavior-Analyse:** welche Tool-Sequenzen sind anomal? (z.B. read+exfiltrate-Pattern)
3. **Backend-Bottleneck-Erkennung:** liegt die Latenz im Server oder bei der Datenquelle?

OpenTelemetry ist Industriestandard, vendor-neutral, mit Anbindern an alle gängigen Observability-Tools (Datadog, Splunk, Grafana Tempo, Honeycomb, Jaeger).

Im lokalen stdio-Setup ist Tracing weniger wichtig (Single-User-Latenzen sind meist nicht das Problem), daher `applies_when: is_cloud_deployed == true`.

### Remediation

Aus dem Katalog (`checks/OBS-006.md`, Remediation), auf die Gaps oben anzuwenden:

### Schritt 1: SDK-Installation

```toml
# pyproject.toml
[project.dependencies]
"opentelemetry-api" = "^1.21"
"opentelemetry-sdk" = "^1.21"
"opentelemetry-exporter-otlp" = "^1.21"
"opentelemetry-instrumentation-httpx" = "^0.42b0"
```

### Schritt 2: Setup-Modul

```python
# src/server_name/observability.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
# ...

def setup_tracing():
    resource = Resource.create({
        "service.name": os.environ.get("OTEL_SERVICE_NAME", "schulamt-mcp"),
        "deployment.environment": os.environ.get("ENVIRONMENT", "development"),
    })
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    HTTPXClientInstrumentor().instrument()
```

### Schritt 3: Decorator anwenden

`@traced_tool` als Standard auf alle Tool-Decorators stacken.

### Schritt 4: OTLP-Backend wählen

Für Schulamt-Kontext: Datadog (DSG-konform mit `DD_SITE=datadoghq.eu`), Grafana Tempo (selbst-gehostet, OpenBao-Compatible), oder Honeycomb (EU-Region).

### Effort Estimate

Katalog-Richtwert (checks/OBS-006.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

M — 1–3 Tage. SDK-Setup + Decorator + Backend-Konfiguration + Tests.
