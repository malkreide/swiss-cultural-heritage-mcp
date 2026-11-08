## Finding: SCALE-004 — Containerization mit Multi-Stage-Builds

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `SCALE-004` |
| **PDF-Reference** | Sec 5.3 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

5 von 6 Kriterien am Dockerfile belegt. Das Groessenkriterium ist das einzige offene und ohne laufenden Docker-Daemon nicht messbar; bei `docker build` + `docker images` < 200 MB waere der Check pass. Kein Befund am Dockerfile selbst.

### Expected Behavior

Aus dem Katalog (`checks/SCALE-004.md`, Pass Criteria):

- [ ] Dockerfile hat ≥ 2 `FROM`-Statements (multi-stage)
- [ ] Stages haben Namen (`AS builder`, `AS runtime`)
- [ ] Final-Image basiert auf `-slim` oder `-alpine` Base
- [ ] Final-Image-Grösse < 200 MB (Python) / < 80 MB (Go/Rust)
- [ ] `USER nobody` oder explizit non-root User gesetzt
- [ ] `HEALTHCHECK`-Direktive für LB-Integration

### Evidence

- Dockerfile:19 `FROM python:3.14-slim AS builder`, Dockerfile:33 `FROM python:3.14-slim AS runtime` — grep -cE '^FROM ' Dockerfile = 2, beide Stages benannt, beide -slim
- Dockerfile:30 `pip install --no-cache-dir --prefix=/install .` im Builder; Dockerfile:42 `COPY --from=builder /install /usr/local` — Runtime-Stage traegt nur die installierten Pakete, keine Build-Toolchain, kein Quellbaum
- Dockerfile:44-45 `useradd --uid 10001 ... app` / `USER 10001` — non-root
- Dockerfile:50-51 `HEALTHCHECK --interval=30s ... CMD python -c "...urlopen('http://127.0.0.1:8000/health'...)"` gegen die In-App-Route src/swiss_cultural_heritage_mcp/server.py:3466 `@mcp.custom_route('/health')`; Runtime: GET /health -> 200 {"status":"ok",...}

### Gaps

- medium (unverifiziert): Final-Image-Groesse < 200 MB nicht gemessen — `docker images` scheitert: 'failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine' (Daemon nicht gestartet)

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

Container-Images für MCP-Server sind oft 800 MB – 1.5 GB gross, weil Build-Toolchains (gcc, Rust, npm-build-deps) im finalen Image bleiben. Multi-Stage-Builds trennen Build und Runtime: das finale Image enthält nur den fertigen Server plus minimale Runtime-Dependencies (typischerweise 80–150 MB).

Vorteile über Image-Grösse hinaus: kleinere Angriffsfläche (kein gcc, kein curl, keine Test-Tools im Production-Image), schnellere Pull-Zeiten (relevant bei Auto-Scaling), weniger CVE-Treffer im Container-Scan.

### Remediation

Aus dem Katalog (`checks/SCALE-004.md`, Remediation), auf die Gaps oben anzuwenden:

```diff
- FROM python:3.11
- WORKDIR /app
- COPY . .
- RUN pip install -e .
- CMD ["python", "-m", "server"]
+ FROM python:3.11-slim AS builder
+ WORKDIR /build
+ COPY pyproject.toml .
+ COPY src/ ./src/
+ RUN pip install --no-cache-dir --user -e .
+
+ FROM python:3.11-slim AS runtime
+ COPY --from=builder /root/.local /root/.local
+ COPY src/ /app/src/
+ WORKDIR /app
+ ENV PATH=/root/.local/bin:$PATH PYTHONUNBUFFERED=1
+ USER nobody
+ HEALTHCHECK CMD curl -f http://localhost:8000/healthz || exit 1
+ CMD ["python", "-m", "server"]
```

### Effort Estimate

Katalog-Richtwert (checks/SCALE-004.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — < 1 Tag.
