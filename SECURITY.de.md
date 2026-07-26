# Sicherheitsrichtlinie & Sicherheitslage

[🇬🇧 English Version](SECURITY.md)

`swiss-cultural-heritage-mcp` ist ein **rein lesender**, **PII-freier** MCP-Server
für **öffentliche Open Data** im [Swiss Public Data MCP Portfolio](https://github.com/malkreide).
Er stellt drei offene Schweizer Kulturerbe-Quellen bereit — SIK-ISEA, das
Schweizerische Nationalmuseum (SNM) und die Nationalbibliothek (Helveticat) —
von denen keine eine Authentifizierung erfordert.

## Schwachstelle melden

Bitte eröffnen Sie ein privates Security Advisory im GitHub-Repository oder
kontaktieren Sie die in `README.md` genannte verantwortliche Person. Erstellen Sie
für ausnutzbare Schwachstellen **keine** öffentlichen Issues.

## Zusammenfassung der Sicherheitslage

Alle Tools **fragen** die drei öffentlichen Upstream-Quellen nur ab — kein
Schreibpfad, keine Authentifizierung, keine Personendaten.

| Bereich | Kontrolle |
|---|---|
| Egress | HTTPS zu den öffentlichen SIK-ISEA-/SNM-/Helveticat-Endpunkten |
| TLS | Zertifikatsprüfung standardmässig aktiv (httpx-Standard; nie deaktiviert) |
| Transport | stdio-first — stdout für den JSON-RPC-Stream reserviert |
| Input | Pydantic-v2-Validierung der Tool-Inputs |
| Secrets | Keine API-Keys oder Zugangsdaten — alle drei Quellen sind öffentlich, es gibt nichts zu speichern oder zu leaken |
| Schreiben | Keines — rein lesender Zugriff |
| Tests | respx-mockierte Unit-Suite bei jedem PR; Live-Tests auf einen Nightly-Job beschränkt |

## Audit-Status

Dieser Server wurde gegen den internen MCP-Best-Practice-Katalog (v0.5.0,
68 Checks) mit der `mcp-audit`-Methodik geprüft. Die Audit-Läufe — inklusive der
pass/partial/fail-Scorecards und der erfassten offenen Findings — liegen unter
[`audits/`](audits/); der jüngste Lauf ist
`audits/2026-06-02T041532-Z-swiss-cultural-heritage-mcp/`. Der aktuelle
Finding-Stand und der Remediation-Status sind diesen Berichten zu entnehmen;
dieses Dokument ist die Meldepolitik für Schwachstellen und die Zusammenfassung
der Sicherheitslage, nicht das Scorecard.

## Re-Evaluierungs-Auslöser

Die Sicherheitslage sollte neu bewertet werden, falls der Server jemals:

- **Schreib**-Funktionalität erhält oder beginnt, **PII** zu verarbeiten, oder
- Tools **dynamisch** / aus entfernten Quellen registriert, oder
- auf ein **Cloud-/SSE**-Deployment verschoben wird, oder
- hinter einem gemeinsamen MCP-Gateway aggregiert wird (dann Tool-Allow-Listing
  und Poisoning-Erkennung auf Gateway-Ebene umsetzen).
