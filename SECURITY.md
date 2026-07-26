# Security Policy & Posture

[🇩🇪 Deutsche Version](SECURITY.de.md)

`swiss-cultural-heritage-mcp` is a **read-only**, **no-PII**, **public-open-data**
MCP server in the [Swiss Public Data MCP Portfolio](https://github.com/malkreide).
It exposes three open Swiss cultural-heritage sources — SIK-ISEA, the Swiss
National Museum (SNM), and the National Library (Helveticat) — none of which
require authentication.

## Reporting a vulnerability

Please open a private security advisory on the GitHub repository, or contact the
maintainer listed in `README.md`. Do not file public issues for exploitable
vulnerabilities.

## Posture summary

All tools only **query** the three public upstream sources — there is no write
path, no authentication, and no personal data.

| Area | Control |
|---|---|
| Egress | HTTPS to the public SIK-ISEA / SNM / Helveticat endpoints |
| TLS | Certificate verification on by default (httpx default; never disabled) |
| Transport | stdio-first — stdout reserved for the JSON-RPC stream |
| Input | Pydantic v2 validation on tool inputs |
| Secrets | No API keys or credentials — all three sources are public, so there is nothing to store or leak |
| Write | None — read-only access |
| Tests | respx-mocked unit suite on every PR; live tests gated to a nightly job |

## Audit status

This server has been audited against the internal MCP best-practice catalogue
(v0.5.0, 68 checks) using the `mcp-audit` methodology. The audit runs — including
the pass/partial/fail scorecards and the tracked open findings — live under
[`audits/`](audits/); the latest run is
`audits/2026-06-02T041532-Z-swiss-cultural-heritage-mcp/`. Consult those reports
for the current finding set and remediation status; this document is the
vulnerability-reporting policy and posture summary, not the scorecard.

## Re-evaluation triggers

The posture should be re-evaluated if the server ever:

- gains **write** capability or starts processing **PII**, or
- registers tools **dynamically** / from remote sources, or
- is moved to a **cloud / SSE** deployment, or
- is aggregated behind a shared MCP gateway (then implement gateway-level tool
  allow-listing and poisoning detection there).
