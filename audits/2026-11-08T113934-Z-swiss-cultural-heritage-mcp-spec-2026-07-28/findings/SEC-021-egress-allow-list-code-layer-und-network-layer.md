## Finding: SEC-021 — Egress-Allow-List: Code-Layer und Network-Layer

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `SEC-021` |
| **PDF-Reference** | Anhang B5 + B12 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Note for the SEC-024 gate run: per the check text, the mcp-continuous-auditor rebind gate sets MCP_ALLOWED_HOSTS. In this server that is exactly the egress list (pydantic env_prefix MCP_ + field allowed_hosts) and would overwrite it during the probe. That is an artifact, not a SEC-021 finding. The finding stands on its own: the egress list is env-mutable, measured.

### Expected Behavior

Aus dem Katalog (`checks/SEC-021.md`, Pass Criteria):

- [ ] Code-Layer Allow-List als `frozenset` im Code (nicht config-mutierbar)
- [ ] Network-Layer Egress Control via NetworkPolicy / Security Group / Cloudflare WARP
- [ ] Allow-List-Hosts dokumentiert in `docs/network-egress.md` oder README
- [ ] Pre-Request-Check (`assert_host_allowed`) wird vor jedem ausgehenden Request aufgerufen
- [ ] Update-Verfahren für Allow-List-Erweiterungen dokumentiert
- [ ] DNS-Resolution-Path im Network-Layer explizit erlaubt (sonst Hostname-Lookup bricht)

### Evidence

- src/swiss_cultural_heritage_mcp/server.py:129-136 — allowed_hosts: frozenset[str] is a FIELD of Settings(BaseSettings, env_prefix='MCP_'); src/swiss_cultural_heritage_mcp/server.py:281 ALLOWED_HOSTS: Final[frozenset[str]] = settings.allowed_hosts
- Runtime: control without env -> ['api.memobase.ch','beta.dodis.ch','ckan.opendata.swiss','helveticat.nb.admin.ch']; MCP_ALLOWED_HOSTS='["evil.example.com"]' MCP_CKAN_API='https://evil.example.com/api' -> ALLOWED_HOSTS ['evil.example.com'], CKAN_API https://evil.example.com/api, _assert_allowed('https://evil.example.com/x') passes, ckan.opendata.swiss is rejected: the allow-list and the endpoints are config-mutable (Modus 2 fail pattern 'allow-list from env var')
- src/swiss_cultural_heritage_mcp/server.py:746,756,771 — pre-request check on every request and every redirect hop; all 13 call sites go through _http_get/_http_post (grep)
- docs/network-egress.md — lists the 4 hosts with their purpose and documents an update procedure (PR + doc + test + review); Kubernetes NetworkPolicy example with DNS egress (port 53) and 0.0.0.0/0:443 (lines 64-65)
- git ls-files | grep -iE 'k8s|helm|render|compose|terraform' -> no network-layer manifest in the repo; docs/network-egress.md:77-79 — 'Render / Railway / Fly.io ... do not currently expose fine-grained egress controls'

### Gaps

- Code-layer allow-list is overridable through MCP_ALLOWED_HOSTS (and the base URLs through MCP_CKAN_API etc.), contrary to the 'immutable frozenset' claim in docs/network-egress.md and docs/security.md (severity: high)
- No network-layer egress control in any shipped or named deployment. The NetworkPolicy example allows 0.0.0.0/0:443 without excluding private ranges or restricting to the 4 hosts; on Render it cannot be done (severity: medium)
- docs/network-egress.md:71,75 still names 'two FQDNs' / only 2 hosts for proxy and Cloudflare (stale, severity: low)

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

SEC-004 (SSRF-Prevention) blockiert Requests an interne IP-Ranges. SEC-021 ergänzt das auf der **anderen Seite**: welche externen Ziele darf der Server überhaupt erreichen?

Defense-in-Depth verlangt zwei Layer:

**1. Code-Layer Allow-List:** Im Server-Code wird vor jedem ausgehenden HTTP-Request geprüft, ob die Ziel-Domain in einer expliziten Allow-Liste steht. Verhindert versehentliche oder durch Prompt-Injection getriggerte Kontakte zu nicht-autorisierten Domains.

**2. Network-Layer Egress Control:** Auf Cloud-Ebene (AWS Security Groups, Azure NSG, Cloudflare WARP, Kubernetes NetworkPolicies) wird der Container nur an die erlaubten Domains/IPs ausgehende Verbindungen erlauben. Verhindert Datenexfiltration auch bei kompromittiertem Code.

Der Anhang verlangt explizit beide Layer. Code-only ist unzureichend — ein kompromittiertes Server-Image kann den Code-Check umgehen. Network-only ist unzureichend — der Server kann immer noch zu Hostnames im Allow-Bereich beliebige Pfade aufrufen, was für Datenexfiltration via parametrisierte Pfade reicht.

Beispiel im Schulamt-Kontext: ein Server, der nur `opendata.swiss`, `data.stadt-zuerich.ch` und `statistik.zh.ch` erreichen muss. Jeder andere ausgehende Request ist a priori verdächtig.

### Remediation

Aus dem Katalog (`checks/SEC-021.md`, Remediation), auf die Gaps oben anzuwenden:

### Schritt 1: Allow-List-Inventar

Pro Server alle ausgehenden HTTP-Hosts identifizieren:

```bash
grep -rE 'https://[a-z0-9.-]+' src/ | \
  sed -E 's/.*https:\/\/([a-z0-9.-]+).*/\1/' | sort -u
```

Resultat: minimale Allow-Liste.

### Schritt 2: Code-Layer einbauen

Wie Pass-Pattern Modus 1.

### Schritt 3: Network-Layer einbauen

Bei Kubernetes: NetworkPolicy wie oben. Bei AWS: Security Group mit egress-Rules. Bei Cloudflare WARP: Zero-Trust-Policy.

### Schritt 4: Tests gegen Regression

```python
async def test_egress_blocked_to_non_allowlisted_host():
    with pytest.raises(PermissionError, match="not in allow-list"):
        await fetch_external_data("https://evil.example.com/", mock_ctx())


async def test_egress_allowed_to_allowlisted_host():
    # Mock-Response, kein echter Network-Call
    with respx.mock:
        respx.get("https://opendata.swiss/api/...").respond(200, json={"ok": True})
        result = await fetch_external_data("https://opendata.swiss/api/...", mock_ctx())
        assert result["ok"]
```

### Effort Estimate

Katalog-Richtwert (checks/SEC-021.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

M — 1–3 Tage. Code-Layer-Allow-List + Network-Policy + Doku + Tests.
