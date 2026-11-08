## Finding: SEC-005 — DNS-Rebinding **egress**: DNS-Pinning gegen TOCTOU

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | enforced |
| **Check-Status** | fail |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `SEC-005` |
| **PDF-Reference** | Sec 4.4 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

All five pass criteria are unmet; the maintainer documents the deferral on purpose (docs/security.md:46). Real risk is low: attacking it needs control over DNS for one of four federal or institutional hosts, and no tool argument sets the host. The check gives no exemption for that, and the allow-list can be widened by env (MCP_ALLOWED_HOSTS), which moves the deferral's trigger condition into the operator's hands. TLS validation is httpx's default (verify=True, no verify=False in src/), so a rebinding to an internal IP would fail the certificate check against the hostname. That mitigates the vector but does not replace the criterion.

### Expected Behavior

Aus dem Katalog (`checks/SEC-005.md`, Pass Criteria):

- [ ] DNS-Resolution erfolgt **einmalig** vor dem HTTP-Request
- [ ] Resolved IP wird für die TCP-Connection verwendet (gepinnter URL oder Custom-Resolver)
- [ ] Original-Hostname wird via `Host`-Header und SNI für TLS-Handshake erhalten
- [ ] Certificate-Validation läuft gegen Original-Hostname (nicht IP)
- [ ] Tests verifizieren: nur 1 DNS-Call pro Request

### Evidence

- grep -rnE 'getaddrinfo|gethostbyname|dns\.resolve' src/ -> no match (rc=1); control: the pattern matches 'socket.getaddrinfo(h)'. The server never resolves DNS itself
- src/swiss_cultural_heritage_mcp/server.py:347-350 — _new_client(): plain httpx.AsyncClient(timeout, follow_redirects=False, headers=UA) with no custom transport or resolver; hostname resolution happens inside httpcore at connect time
- grep -rnE 'sni_hostname|SSLContext|verify_hostname|replace\(.*hostname' src/ -> no match; there is no pinned-IP URL and no Host/SNI override
- docs/security.md:46 — 'DNS pinning ... Deferred', with the trigger 'any tool starts accepting a user-supplied URL/host, or the allow-list grows beyond trusted fixed hosts'
- tests/: grep -rnE 'getaddrinfo|gaierror|pinning' tests/*.py -> no test asserts a single DNS call per request

### Gaps

- No single resolution plus pinned IP for the TCP connection (severity: high)
- No test that checks for exactly one DNS lookup per request (severity: medium)

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

**Richtung: ausgehend.** Dieser Check betrifft ausschliesslich Hostnamen, die der **Server selbst auflöst** — er ist hier das Werkzeug, nicht das Ziel. Der gleichnamige Angriff in der eingehenden Richtung, bei dem eine fremde Seite ihren Hostnamen auf die Adresse dieses Servers auflöst und ihn aus dem Browser anspricht, ist eine andere Kontrolle: **`SEC-024`** (Inbound Host/Origin-Allow-List). Zwei Angriffe, ein Name — wer «DNS-Rebinding» ohne Richtungsangabe zitiert, meint mit einiger Wahrscheinlichkeit den anderen.

SEC-004 (SSRF-Prevention) verlangt: Resolved IP wird gegen Blocklist geprüft, dann Request mit dieser IP. DNS-Rebinding ist ein verfeinerter Angriff, der diese Defense umgeht — durch zwei verschiedene DNS-Antworten für denselben Hostnamen mit kurzem TTL:

**Ablauf des Angriffs (TOCTOU = Time-Of-Check-Time-Of-Use):**

1. Angreifer kontrolliert `evil.attacker.com` mit DNS-TTL = 1 Sekunde
2. Erste Auflösung: `evil.attacker.com` → `198.51.100.42` (öffentliche IP, passiert SSRF-Check)
3. Server validiert: IP ist nicht in Blocklist → Pass
4. Server macht zweiten DNS-Lookup für eigentlichen Request (typisch in `requests`/`httpx`-Default-Setup)
5. Zweite Auflösung: `evil.attacker.com` → `169.254.169.254` (Cloud-Metadata-IP)
6. Request geht an Cloud-Metadata-Endpoint → Credential-Leak

Mitigation: **DNS-Pinning** — die einmal aufgelöste IP wird für den eigentlichen HTTP-Request verwendet, nicht der Hostname. Das eliminiert die zweite DNS-Auflösung und damit das Rebinding-Fenster.

Im Pass-Pattern von SEC-004 ist DNS-Pinning bereits enthalten (resolved IP → in URL ersetzt) — echter Code macht Blocklisting und Pinning in derselben Funktion. **Bewertet wird das Pinning aber ausschliesslich hier.** Bis v1.3.1 trug `SEC-004` das Kriterium «DNS-Resolution erfolgt einmal» wortgleich mit; ein Server, der es vergisst, erzeugte damit zwei Findings für eine Ursache, und nach dem Fix wäre eines davon rot geblieben. `SEC-004` prüft jetzt, ob die aufgelöste IP *erlaubt* ist; dieser Check, ob sie auch die *benutzte* ist.

**Reichweite: ausgehende Requests, nicht der eigene Transport.** Die Klausel verlangte früher zusätzlich `transport != "stdio-only"`. Das war falsch gefasst: Der hier beschriebene Angriff läuft vollständig auf der **ausgehenden** Seite — zwei DNS-Antworten für einen Hostnamen, den der Server selbst abruft. Wie der Server angesprochen wird, kommt darin nicht vor. Ein stdio-only-Server, der URLs fetcht, ist exakt gleich angreifbar; die Cloud-Metadata-IP aus Schritt 5 ist erreichbar, sobald der Prozess in einer Cloud-Umgebung läuft, unabhängig davon, ob er über eine Pipe oder über HTTP bedient wird.

Nicht zu verwechseln mit **eingehendem** DNS-Rebinding — dem Angriff, bei dem eine Webseite den Browser des Opfers dazu bringt, einen lokal lauschenden Server anzusprechen. Der ist tatsächlich transportabhängig und hat eigene Checks: `SEC-016` (0.0.0.0-Binding) und `SDK-004` (CORS). Beide tragen ihre Transport-Bedingung zu Recht. Dieser Check hat sie nur geerbt.

### Adoptionsstufe: `enforced` — geprüft und so entschieden

Die Erweiterung der Reichweite hat die Frage aufgeworfen, ob dieser Check den in `SKILL.md` 2.3 dokumentierten Weg über `adoption: advisory` gehen sollte. **Er tut es nicht, und das ist eine Entscheidung, keine Unterlassung.**

Portfolio-Stand zum Zeitpunkt der Erweiterung (v1.3.0):

| | Server |
|---|---|
| Bisher erfasst (`dual` / `HTTP/SSE` mit ausgehenden Requests) | 3 |
| **Neu erfasst** (`stdio-only` mit ausgehenden Requests) | **5** |
| Reichweite gesamt | 3 → 8 |

Relativ ist das fast eine Verdreifachung. Absolut sind es fünf Server — und darauf kommt es an: 2.3 begründet die Stufe damit, dass ein neuer Check «am Tag des Merges 30+ Server als rote Pipeline» trifft und deshalb *zurückgenommen statt übernommen* wird. Fünf Server sind kein Aufstand, sondern ein Arbeitspaket von je 1–3 Tagen.

**Ausschlaggebend war die Asymmetrie der beiden Kosten.** Die Adoptionsstufe wirkt pro Check, nicht pro Profilsegment: `advisory` hätte die Blockierung auch bei den drei Servern aufgehoben, wo sie heute schon greift. Dieser Preis ist **gewiss und unsichtbar** — er fällt an, sobald die Stufe gesetzt ist, und taucht in keinem Report auf. Der Preis von `enforced` ist **ungewiss und laut**: Vielleicht bestehen die fünf ohnehin; falls nicht, steht es rot in der Pipeline und niemand kann es übersehen.

Ein Tausch, bei dem drei Server ihre Blockierung verlieren, damit fünf andere geschont werden, hat ausserdem niemand verlangt.

**Was die Entscheidung umkehren würde:** Ein Portfolio-Durchlauf, der zeigt, dass alle fünf durchfallen *und* der Rückstand nicht in einem Sprint abbaubar ist. Die Umstellung ist eine Zeile (`adoption: advisory` unter `severity`) plus die gepinnte Advisory-Menge in `tests/test_adoption_stage.py` und die Zeile in `README.md`, die sie namentlich ausschreibt.

**Was sie nicht umkehrt:** dass die fünf Server den Check heute nicht erfüllen. Das wäre ein Befund über das Portfolio, kein Argument gegen den Check. Und eine `advisory`-Stufe, die nie promoviert wird — den Schritt, den 2.3 als dritten nennt —, ist eine stillgelegte Regel mit gutem Gewissen.

### Remediation

Aus dem Katalog (`checks/SEC-005.md`, Remediation), auf die Gaps oben anzuwenden:

### Schritt 1: HTTP-Client mit Custom Transport

```python
import httpx
import socket
import ipaddress

class PinnedTransport(httpx.AsyncHTTPTransport):
    """HTTPX Transport mit DNS-Pinning."""

    async def handle_async_request(self, request):
        url = request.url
        if url.scheme != "https":
            raise httpx.RequestError("Only HTTPS allowed")

        # Resolve einmalig
        loop = asyncio.get_event_loop()
        addrinfo = await loop.getaddrinfo(
            url.host, url.port, type=socket.SOCK_STREAM
        )
        resolved_ip = addrinfo[0][4][0]

        # Range-Check
        ip = ipaddress.ip_address(resolved_ip)
        for blocked in BLOCKED_NETWORKS:
            if ip in blocked:
                raise httpx.RequestError(f"Blocked IP: {ip}")

        # URL mit gepinnter IP, aber Host-Header bleibt
        pinned_url = httpx.URL(str(url).replace(url.host, resolved_ip, 1))
        new_request = httpx.Request(
            method=request.method,
            url=pinned_url,
            headers=httpx.Headers(request.headers),
            content=request.content,
            extensions=request.extensions,
        )
        new_request.headers["Host"] = url.host
        # SNI bleibt durch URL-Hostname (httpx interner default)
        return await super().handle_async_request(new_request)


# Verwendung
async with httpx.AsyncClient(transport=PinnedTransport()) as client:
    response = await client.get("https://api.external.com/data")
```

### Schritt 2: Alternative — Egress-Proxy

Wenn Custom-Transport zu komplex: Stripe Smokescreen als Sidecar erledigt DNS-Pinning automatisch.

```yaml
# docker-compose.yml
services:
  smokescreen:
    image: stripe/smokescreen:latest
    command: ["--listen-ip", "127.0.0.1", "--listen-port", "4750"]

  mcp-server:
    image: malkreide/mcp-server
    environment:
      HTTPS_PROXY: http://smokescreen:4750
```

```python
# Im Code: einfach Proxy nutzen
async with httpx.AsyncClient(proxy="http://localhost:4750") as client:
    return await client.get(url)
```

### Schritt 3: Tests

Wie im Mock-Beispiel oben. Plus Integration-Test, der nachweist dass die SSRF-Test-Suite (SEC-004 Modus 3) auch mit Rebinding-Versuchen besteht.

### Effort Estimate

Katalog-Richtwert (checks/SEC-005.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

M — 1–3 Tage. Custom-Transport oder Egress-Proxy-Setup + Tests.
