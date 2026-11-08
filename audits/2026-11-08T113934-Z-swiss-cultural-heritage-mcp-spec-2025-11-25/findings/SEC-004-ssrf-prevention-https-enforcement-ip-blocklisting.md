## Finding: SEC-004 — SSRF-Prevention: HTTPS-Enforcement + IP-Blocklisting

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `SEC-004` |
| **PDF-Reference** | Sec 4.4 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Criterion 1 (HTTPS before every request, including redirect hops) is met and verified at runtime. Criteria 3 and 4 hold in behaviour: metadata IP, loopback and link-local are rejected, but only because they are not on the four-host allow-list, not because of an explicit IP check. Criterion 2 (resolved-IP check) and criterion 5 (egress proxy) are not met. Threat model: no tool takes a URL or host. Only query strings and path segments are LLM-controlled, and the host is fixed (measured). So the direct SSRF class is not reachable as long as the allow-list stays at its default. That makes 'partial' and not 'fail'; the missing IP layer keeps it from 'pass'. Whether the env override counts as an operator risk is a judgment call; the check counts it as config-mutable.

### Expected Behavior

Aus dem Katalog (`checks/SEC-004.md`, Pass Criteria):

- [ ] HTTPS-Schema wird vor jedem ausgehenden Request validiert
- [ ] Resolved IP wird gegen Blocklist (private + link-local + loopback) geprüft
- [ ] Cloud-Metadata-IP `169.254.169.254` ist explizit blockiert
- [ ] IPv6-Loopback (`::1`) und IPv6-Link-local (`fe80::/10`) sind blockiert
- [ ] In Production: Egress-Proxy (Smokescreen o.ä.) als Defense-in-Depth

**Nicht hier bewertet: DNS-Pinning.** Ob die geprüfte IP auch die benutzte IP ist, prüft `SEC-005`. Das Pass-Pattern oben löst bereits einmal auf und verwendet die IP — echter Code macht beides in derselben Funktion —, aber das **Kriterium** gehört dorthin, nicht hierher.

Der Grund ist `SKILL.md` §2.5: Zwei Checks, die einander überlappen, doppeln das Finding, und wenn der Server die Ursache behebt, bleibt der zweite rot — der Fix sieht aus, als hätte er nicht gewirkt. Bis v1.3.1 stand «DNS-Resolution erfolgt einmal» wortgleich in beiden Checks.

Zusammengelegt wurden sie trotzdem nicht: Blocklisting und Pinning sind **getrennt behebbar**, und §2.5 verlangt, dass ein Check in *einem* Schritt behebbar bleibt. Ein Server kann die Blockliste korrekt führen und trotzdem zweimal auflösen — das sind zwei Befunde mit zwei Remediationen, nicht einer.

### Evidence

- src/swiss_cultural_heritage_mcp/server.py:726-730 — _assert_allowed: httpx.URL(url).scheme != 'https' -> ValueError; parsed.host not in ALLOWED_HOSTS -> ValueError (string allow-list, no IP resolution)
- src/swiss_cultural_heritage_mcp/server.py:746,756,771 — guard runs before the first GET, on every manual redirect hop, and before the Dodis POST; src/swiss_cultural_heritage_mcp/server.py:349 client has follow_redirects=False
- grep -nE '_http_get\(|_http_post\(|client\.(get|post)' src/swiss_cultural_heritage_mcp/server.py — all 13 outbound call sites go through _http_get/_http_post; only 3 raw client.get/post calls, all inside those two helpers (lines 748,758,773); no requests/urllib/aiohttp/socket import in src/
- venv python -I _assert_allowed probe — https://[::1]/, https://[fe80::1]/, https://0x7f.0x0.0x0.0x1/, https://localtest.me/, https://127.0.0.1/, https://169.254.169.254/latest, https://ckan.opendata.swiss@evil.com/ -> all 'Host nicht in Allow-List'; http://ckan.opendata.swiss/x and file:///etc/passwd -> 'Nur HTTPS erlaubt'; https://ckan.opendata.swiss/ok -> ALLOWED (positive control)
- venv python -I path-interpolation probe — item_id '../../solr/admin', '1?q=*:*', '@evil.example.com/x' in f'{DODIS_API}/solr/full/{item_id}' (src/swiss_cultural_heritage_mcp/server.py:3135-3137) keep host beta.dodis.ch; no tool argument can change the request host
- grep -rnE 'getaddrinfo|gethostbyname|ipaddress|smokescreen|sni_hostname|HTTPS_PROXY|proxy=' src/ -> no match (rc=1); control: same pattern matches 'socket.getaddrinfo(h)' (count 1)
- MCP_ALLOWED_HOSTS='["169.254.169.254"]' venv python -I -c '...s._assert_allowed("https://169.254.169.254/latest/meta-data/")' -> accepted: the only barrier in front of the metadata IP is an env-overridable host string list
- docs/security.md:45 — resolved-IP blocklist explicitly 'Deferred'

### Gaps

- No resolved-IP blocklist (private, loopback, link-local, 169.254.169.254, ::1, fe80::/10) after DNS resolution. Blocking happens only by hostname string match (severity: high)
- The allow-list that stands in for the blocklist can be replaced through the MCP_ALLOWED_HOSTS environment variable (pydantic-settings field, server.py:129). That removes the only SSRF barrier without a code change (severity: high, same root cause as SEC-021)
- No egress proxy as defense in depth. Render cannot provide one, as docs/network-egress.md:77 itself says (severity: medium)

### Risk Description

Siehe Gaps; Severity laut Katalog `critical`. Katalogbeschreibung:

Server-Side Request Forgery (SSRF) entsteht, wenn ein MCP-Server URLs aus User-Input (oder LLM-generierten Args) direkt an HTTP-Clients weitergibt. Ein Angreifer kann den Server dann zwingen, beliebige interne Adressen abzurufen — insbesondere die Cloud-Metadata-Endpunkte.

**Kritische Targets:**

| Target | IP/Range | Risiko |
|---|---|---|
| AWS IMDS | `169.254.169.254` | EC2-Credentials, IAM-Rollen-Token |
| GCP Metadata | `169.254.169.254` (Header `Metadata-Flavor: Google`) | Service-Account-Token |
| Azure IMDS | `169.254.169.254` (Header `Metadata: true`) | Managed-Identity-Token |
| Localhost | `127.0.0.1`, `::1` | interne Admin-Endpoints |
| Private IPs | `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` | interne Services |
| Link-local | `169.254.0.0/16`, `fe80::/10` | Cloud-Metadata + DHCP |

**Zwei Angriffs-Klassen:**

1. **Direkt:** LLM gibt `http://169.254.169.254/latest/meta-data/iam/security-credentials/...` als Tool-Arg, Server fetcht es.
2. **DNS-Rebinding (TOCTOU):** URL `http://attacker.com` wird gegen DNS aufgelöst, beim Validation-Check zu öffentlicher IP, beim eigentlichen Request zu privater IP. Resolver gibt verschiedene Antworten.

**Reichweite: ausgehende Requests, nicht der eigene Transport.** SSRF setzt voraus, dass der Server eine URL abruft, die aus Tool-Argumenten stammt. Ob er selbst über stdio oder über HTTP angesprochen wird, ändert daran nichts: Ein stdio-only-Server, der URLs fetcht, ist voll exponiert; ein HTTP-Server ohne ausgehende Requests hat keine SSRF-Oberfläche, die man prüfen könnte — jedes Pass-Kriterium unten spräche ins Leere. Deshalb gilt der Check bei `tools_make_external_requests == true`, ohne Transport-Bedingung.

Die Netzwerk-Ebene eines Cloud-Deployments ist damit **nicht** ungeprüft: `SEC-021` (Egress-Allow-List) greift zusätzlich bei `is_cloud_deployed == true`. Die Zuständigkeit liegt dort, wo sie hingehört — beim Deployment, nicht beim Transport.

### Remediation

Aus dem Katalog (`checks/SEC-004.md`, Remediation), auf die Gaps oben anzuwenden:

Volles Pattern oben. Zusätzlich für Defense-in-Depth:

### Container-Level Egress-Filtering

```yaml
# Kubernetes NetworkPolicy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: mcp-server-egress
spec:
  podSelector:
    matchLabels:
      app: mcp-server
  policyTypes:
    - Egress
  egress:
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
            except:
              - 10.0.0.0/8
              - 172.16.0.0/12
              - 192.168.0.0/16
              - 169.254.0.0/16
              - 127.0.0.0/8
      ports:
        - protocol: TCP
          port: 443
```

### IMDSv2 statt IMDSv1 (AWS-spezifisch)

Falls auf AWS deployed: IMDSv2 mit Hop-Limit 1 erzwingen (verhindert SSRF auch bei Code-Bug).

```bash
aws ec2 modify-instance-metadata-options \
  --instance-id i-xxx \
  --http-tokens required \
  --http-put-response-hop-limit 1
```

### Effort Estimate

Katalog-Richtwert (checks/SEC-004.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

M — 1–3 Tage. Egress-Proxy-Setup + URL-Validation-Layer + Tests.
