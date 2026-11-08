## Finding: SCALE-006 — Resource-Limits per Container (Memory, CPU, FDs)

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `SCALE-006` |
| **PDF-Reference** | Sec 5.3 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Der Check laesst fuer Render/Railway die dokumentierte UI-Konfiguration gelten ('pruefen ob dokumentiert') — die Dokumentation ist vorhanden und inhaltlich vollstaendig (Requests < Limits, FD, Restart). Durchgesetzt ist nichts davon im Repo, und ein OOM-Test fehlt. Deshalb partial statt pass.

### Expected Behavior

Aus dem Katalog (`checks/SCALE-006.md`, Pass Criteria):

- [ ] Memory-Limit ist explizit gesetzt (nicht Default)
- [ ] CPU-Limit ist gesetzt (Multi-Tenant-Scheduling-Schutz)
- [ ] Requests sind kleiner als Limits (Burst-Erlaubnis)
- [ ] FD-Limit prüfen: bei vielen ausgehenden Connections `ulimit -n` ≥ 4096
- [ ] OOM-Verhalten getestet: Server stürzt sauber ab, restart-policy aktiv

### Evidence

- git ls-files | grep -iE 'docker-compose|k8s/|helm/|render\.yaml|railway\.toml' -> leer: kein Manifest im Repo setzt Memory-/CPU-Limits
- Dockerfile:16 — Limits nur als Kommentar ('resources: { requests: {cpu: 100m, memory: 128Mi}, limits: {cpu: 500m, memory: 256Mi} }'); die Dockerfile-Syntax kann keine Limits setzen
- docs/security.md:91-101 — Abschnitt 'Resource limits (SCALE-006)': CPU 100m/500m, Memory 128Mi/256Mi (Requests < Limits), ulimit -n >= 4096 mit Begruendung (Fan-out in heritage_cross_search), Restart-Policy-Empfehlung; Satz 'The container declares no limits itself; operators should set them at the platform level'

### Gaps

- medium: Memory- und CPU-Limit nirgends konfiguriert, nur empfohlen (Render: Plan/UI, nicht eingecheckt)
- low: FD-Limit >= 4096 nur empfohlen, nicht gesetzt
- low: OOM-Verhalten nicht getestet

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

Ohne explizite Resource-Limits kann ein einzelner MCP-Server-Bug das ganze System destabilisieren: ein Memory-Leak frisst die Host-Ressourcen, ein File-Descriptor-Leak öffnet Tausende dangling Connections, ein CPU-bound Query starvt nachbar-Pods. In Multi-Tenant-Cloud-Umgebungen (Railway, Render, K8s) müssen Memory, CPU, FDs explizit gedeckelt werden.

Faustregeln für MCP-Server: 256 MB – 1 GB RAM (je nach Daten-Cache), 0.5–1 CPU, FD-Limit 1024 (Standard reicht meistens). Bei Hybrid-Servern mit lokalem Dump-Cache eher 1–2 GB RAM einplanen.

### Remediation

Aus dem Katalog (`checks/SCALE-006.md`, Remediation), auf die Gaps oben anzuwenden:

Für Railway: in der Web-UI unter Project Settings → Resources die Limits setzen.

Für Docker-Compose-Production:

```yaml
services:
  mcp:
    image: malkreide/mcp-server:v0.1.0
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
    ulimits:
      nofile:
        soft: 4096
        hard: 8192
```

### Effort Estimate

Katalog-Richtwert (checks/SCALE-006.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — < 1 Tag pro Server.
