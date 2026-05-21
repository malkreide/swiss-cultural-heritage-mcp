# Security Posture

This document records the security controls implemented in `swiss-cultural-heritage-mcp` and the recommended deployment hardening for downstream operators. It maps to the [2026-05-21 audit](../audits/2026-05-21-swiss-cultural-heritage-mcp/report.md).

## Threat model

The server is **read-only** and **anonymous**:

- No authentication surface (all upstream APIs are public open data)
- No write operations (all tools annotated `readOnlyHint: true`)
- No PII processed — only institutional records (artists, museum objects, publications)
- No persistent state (stateless; no database, no cache)

Residual risks the controls below mitigate:
- Server-side request forgery (SSRF) via redirect chains or future user-supplied URLs
- XML attacks (entity expansion / billion laughs) against OAI-PMH responses
- Local-filesystem escalation from a compromised process
- Cross-border data flow non-compliance (revDSG / EDÖB) — see [`data-residency.md`](data-residency.md)

## Controls in code

| Control | Location | Audit ref |
|---|---|---|
| Egress allow-list (`frozenset` of three upstreams) | `server.py:_assert_allowed` | SEC-021 |
| `follow_redirects=False` on the shared httpx client | `server.py:_new_client` | SEC-021 |
| `defusedxml.ElementTree` for OAI-PMH parsing | `server.py` imports | SEC (XML) |
| Pydantic input models with `extra="forbid"`, length caps, regex date patterns | every `*Input` class | input validation |
| Narrow `except ExpectedUpstreamError` (httpx + XML + ValueError) | every tool body | OBS-001 |
| Shared httpx client owned by FastMCP `lifespan` | `server.py:lifespan` | SDK-001 |

See [`network-egress.md`](network-egress.md) for the allow-list contents and the update procedure.

## Container hardening (operators)

A reference `Dockerfile` is shipped at the repo root. Key properties:

- Non-root user, UID `10001`
- Slim Python base image, no build tools in the final layer
- `EXPOSE 8000` for Streamable HTTP mode

When deploying to a Kubernetes-class platform (k8s, Cloud Run, Fly.io, Knative) apply the following `SecurityContext`:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 10001
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop: ["ALL"]
  seccompProfile:
    type: RuntimeDefault
```

For Render.com, Railway, Fly.io: confirm the platform's default sandbox includes seccomp + non-root. None of those platforms grant containers raw socket / `CAP_NET_RAW` access by default.

## stdio mode (Claude Desktop / `uvx`)

When the server runs locally as a stdio child of Claude Desktop, it inherits the user's process privileges. There is no container boundary in this mode. Mitigations:

- The egress allow-list still applies — the server cannot reach hosts other than the three upstreams even if a tool description were poisoned.
- No filesystem-writing tools are exposed.
- No subprocess / shell execution.

If you run this server alongside other MCP servers that *do* touch the filesystem or run subprocesses, sandbox the whole Claude Desktop process accordingly.

## Reporting issues

Open a private security advisory on the repository, or contact the maintainer directly. Do not file public issues for credential leaks or unpatched vulnerabilities.
