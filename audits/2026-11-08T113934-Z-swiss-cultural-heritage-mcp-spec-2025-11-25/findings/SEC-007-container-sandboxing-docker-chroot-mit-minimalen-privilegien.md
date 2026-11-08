## Finding: SEC-007 — Container-Sandboxing: Docker / chroot mit minimalen Privilegien

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `SEC-007` |
| **PDF-Reference** | Sec 4.5 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

The criteria the repo itself controls (Dockerfile USER >= 10000, no file tools) are met. The Kubernetes criteria are conditional ('Bei Kubernetes'); the repo ships no k8s manifest and documents the recommended SecurityContext. Without a docker daemon there is no runtime evidence. Status: partial.

### Expected Behavior

Aus dem Katalog (`checks/SEC-007.md`, Pass Criteria):

- [ ] Dockerfile setzt `USER` mit nicht-root UID (≥ 10000)
- [ ] Bei Kubernetes: `runAsNonRoot: true`, `runAsUser` explizit, `allowPrivilegeEscalation: false`
- [ ] Bei Kubernetes: `readOnlyRootFilesystem: true` mit `tmpfs`-Volume für `/tmp`
- [ ] Bei Kubernetes: `capabilities.drop: ["ALL"]`
- [ ] seccomp-Profile mindestens `RuntimeDefault`
- [ ] Bei File-Tools: Volume-Mounts nur für erlaubte Pfade, ggf. read-only

### Evidence

- Dockerfile:44-45 — 'RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin app' + 'USER 10001' (non-root, UID >= 10000)
- Dockerfile:19,33,42 — multi-stage build: only /install from the builder lands in the runtime image, no build tooling
- Dockerfile:11-15 and docs/security.md (Container hardening) — readOnlyRootFilesystem, allowPrivilegeEscalation:false, capabilities.drop ALL, seccompProfile RuntimeDefault appear ONLY as a recommendation in comments and docs, not in a shipped manifest; git ls-files | grep -iE 'k8s|helm|render|compose' -> no deployment manifest in the repo
- docs/security.md:132 — 'There is no container boundary in this mode' (local stdio): the server runs with the user's privileges, without a sandbox
- No file tools: all 11 tools readOnlyHint True (grep -c '"readOnlyHint": True' server.py = 11 = number of @mcp.tool); no open()/Path write in tool code, so criterion 6 does not apply
- Runtime test not possible: 'docker info' -> 'failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine' (daemon not running)

### Gaps

- seccomp RuntimeDefault, read-only root and dropped capabilities are enforced in no artifact the repo ships. Render (named deployment) is native/Docker without a SecurityContext (severity: medium)
- The local-stdio deployment (in the profile) runs without any sandbox; there is no documented Docker variant for Claude Desktop (severity: medium)
- Privilege reduction not verified at runtime (id, read-only FS, CapEff), no Trivy/container scan in CI (severity: medium)

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

Lokale stdio-Server (siehe SEC-006) eliminieren die Netzwerk-Angriffsfläche, behalten aber das Risiko, dass ein kompromittierter Server-Code (durch Supply-Chain-Attack, böswilliges Update, oder Bug-Exploitation) mit User-Privilegien ausgeführt wird. Read-Zugriff auf `~/.ssh/`, `~/.aws/credentials`, Browser-Cookies, lokal gespeicherte Tokens — alles direkt erreichbar.

Defense-in-Depth: Server in einer Sandbox ausführen, die nur das nötige Minimum an Filesystem- und System-Call-Zugriff erlaubt:

| Mechanismus | Stärke | Aufwand | Wann |
|---|---|---|---|
| **Docker Container** | Mittel | Niedrig | Default für Cloud-Deployments |
| **Docker + seccomp + AppArmor** | Hoch | Mittel | Production mit sensitiven Tools |
| **gVisor / Firecracker** | Sehr hoch | Hoch | Multi-Tenant, untrusted Code |
| **chroot + UID-Drop** | Niedrig | Niedrig | Legacy-Pattern, nicht mehr empfohlen |
| **WASM Runtime** | Hoch | Hoch | Experimentell für MCP, 2026 noch Early |

Für Schulamt-Portfolio: Docker mit non-root User + read-only-Filesystem + seccomp-Default-Profile ist der pragmatische Standard.

### Remediation

Aus dem Katalog (`checks/SEC-007.md`, Remediation), auf die Gaps oben anzuwenden:

### Schritt 1: Dockerfile-User anpassen

Wie im Pass-Pattern oben.

### Schritt 2: Kubernetes-SecurityContext setzen

Im Helm-Chart oder Deployment-Manifest.

### Schritt 3: Tests gegen Privileg-Eskalation

```python
def test_container_runs_as_non_root():
    result = subprocess.run(
        ["docker", "exec", CONTAINER_ID, "id", "-u"],
        capture_output=True, text=True,
    )
    assert int(result.stdout.strip()) >= 10000

def test_filesystem_read_only():
    result = subprocess.run(
        ["docker", "exec", CONTAINER_ID, "touch", "/etc/test"],
        capture_output=True, text=True,
    )
    assert "Read-only" in result.stderr or result.returncode != 0
```

### Schritt 4: CI-Check via Trivy / Snyk

```yaml
- name: Container security scan
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: malkreide/mcp-server:${{ github.sha }}
    severity: CRITICAL,HIGH
    exit-code: 1
```

### Effort Estimate

Katalog-Richtwert (checks/SEC-007.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — < 1 Tag bei sauberem Dockerfile-Setup. Bei Legacy-Container mit root-Defaults: 1–2 Tage.
