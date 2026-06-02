# Audit Re-Run — swiss-cultural-heritage-mcp

**Date:** 2026-06-02 (re-run, same day after the remediation series)
**Auditor:** Claude (Opus) following [`mcp-audit-skill`](https://github.com/malkreide/mcp-audit-skill) methodology
**Baseline:** [`../2026-06-02T041532-Z-swiss-cultural-heritage-mcp/audit-report.md`](../2026-06-02T041532-Z-swiss-cultural-heritage-mcp/audit-report.md)
**Branch / commit audited:** `main` @ `e9ee21b` (post-merge of PRs #19–#25)

---

## Executive Summary

Re-applied the audit against the codebase after the remediation series landed (13 PRs). Of the **21 baseline findings**, **16 are now closed**, **2 are accepted-risk / documented-deferred** (the heavier SSRF defense-in-depth), and **3 remain open** — all of them medium-effort engineering choices rather than live exposures.

No regressions were introduced. The unit suite grew from the baseline to **95 passing** (4 live-gated), ruff clean. Two findings the baseline marked `partial` (SCALE-004 multistage Dockerfile/HEALTHCHECK, ARCH-011 single-file justification) were found already satisfied in current `main`.

**Verdict:** all `critical`/`high`/`medium` *code-conformance, observability, compliance, and search-quality* findings are resolved. The residual open items are an architectural refactor (`ARCH-004`), an error-surface change (`OBS-001`), and a supply-chain hardening option (`SEC-022`).

---

## Score-Card Diff

| ID | Category | Sev | Baseline | Re-Run | Δ |
|---|---|---|---|---|---|
| SEC-004 | SEC | critical | partial | **partial (mitigated + documented)** | ✅ HTTPS-only enforced; IP-blocklist/DNS-pin deferred w/ rationale |
| SEC-019 | SEC | critical | partial | **PASS** | ✅ lethal-trifecta assessment documented |
| ARCH-004 | ARCH | high | partial | partial | — still module-level config, no `BaseSettings` |
| OBS-001 | OBS | high | partial | partial | — handled errors still returned as plain strings, not `isError` |
| OBS-002 | OBS | high | fail | **PASS** | ✅ `mask_unexpected_errors` |
| OPS-003 | OPS | high | partial | **PASS** | ✅ `docs/roadmap.md` + phase declared |
| SCALE-002 | SCALE | high | partial | **PASS (documented)** | ✅ single-instance constraint in `docs/scaling.md` |
| SCALE-003 | SCALE | high | partial | **PASS (documented)** | ✅ edge-routing / affinity path documented |
| SDK-004 | SDK | high | partial | **PASS** | ✅ CORS exposes `Mcp-Session-Id` |
| SEC-005 | SEC | high | partial | **partial (documented)** | ⚠️ DNS-pinning deferred w/ trigger |
| SEC-022 | SEC | high | partial | partial | — `heritage_` prefix kept; no hash-pin |
| ARCH-003 | ARCH | medium | partial | **PASS** | ✅ `match_type` + fuzzy fallback |
| ARCH-011 | ARCH | medium | partial | **PASS** | ✅ README "Single-file server" justification |
| ARCH-012 | ARCH | medium | fail | **PASS** | ✅ dependabot + protocol-version docs |
| CH-004 | CH | medium | partial | **PASS** | ✅ per-response source + licence footer |
| OBS-003 | OBS | medium | fail | **PASS** | ✅ structlog JSON to stderr |
| OBS-006 | OBS | medium | fail | **PASS** | ✅ optional OpenTelemetry tracing |
| SCALE-004 | SCALE | medium | partial | **PASS** | ✅ multistage Dockerfile + HEALTHCHECK |
| SCALE-006 | SCALE | medium | partial | **PASS (documented)** | ✅ resource-limit guidance |
| SDK-002 | SDK | medium | partial | **PASS** | ✅ typed `ResultEnvelope` + `outputSchema` |
| SDK-003 | SDK | medium | partial | **PASS** | ✅ `ctx` progress + structured warnings |

**Totals:** 16 PASS · 2 PARTIAL (accepted-risk/documented) · 3 PARTIAL (open) · 0 FAIL
**Baseline was:** 0 PASS · 17 PARTIAL · 4 FAIL.

---

## Closed Findings — Verification Evidence

| Finding | Evidence in current code (`main` @ `e9ee21b`) |
|---|---|
| SEC-019 | `docs/security.md` "Lethal Trifecta assessment" — at most one leg present |
| OBS-002 | `server.py:mask_unexpected_errors` — full detail to stderr, generic `ToolError` to client |
| OPS-003 | `docs/roadmap.md`; "Phase 1 — read-only" stated in both READMEs |
| SCALE-002/003 | `docs/scaling.md` — single-instance constraint, `Mcp-Session-Id` session model, Variant A/B scaling path |
| SDK-004 | `server.py:build_http_app` — CORS exposes `Mcp-Session-Id`, non-wildcard origin allow-list |
| ARCH-003 | `ResultEnvelope.match_type` (`exact`/`fuzzy`/`none`); loosened-query retry in artists + datasets tools |
| ARCH-011 | `README.md` "Project Structure" → "Single-file server" justification |
| ARCH-012 | `.github/dependabot.yml`; "MCP Protocol Version" section in both READMEs |
| CH-004 | `server.py:_attribution` footer on every markdown response; per-source provenance in `cross_search` |
| OBS-003 | `server.py:_configure_logging` — structlog JSON→stderr; per-call `tool`/`request_id` binding |
| OBS-006 | `server.py:_init_tracing` — gated OTLP + httpx instrumentation; `mcp.tool.*` span per call |
| SCALE-004 | `Dockerfile` — `AS builder`/`AS runtime` + `HEALTHCHECK` on `/health` |
| SCALE-006 | `docs/security.md` "Resource limits" table |
| SDK-002 | `ResultEnvelope` returned in JSON mode → real structured content + `outputSchema` |
| SDK-003 | `heritage_cross_search(ctx: Context)` — `report_progress()` per source, `warning()` on failure |
| SEC-004 (HTTPS leg) | `server.py:_assert_allowed` — `scheme != "https"` rejected; `test_assert_allowed_rejects_non_https_scheme` |

Unit-test suite at re-run time: **95 passed, 4 deselected** · ruff clean.

---

## Accepted-Risk / Documented-Deferred

| Finding | Decision | Rationale & trigger |
|---|---|---|
| SEC-004 (IP blocklist) | Deferred | The closed two-host egress allow-list + no user-controlled host already block metadata IPs; resolved-IP blocklisting is belt-and-suspenders. **Trigger:** a tool accepts a user-supplied host, or the allow-list widens. Documented in `docs/security.md` (SSRF & DNS rebinding). |
| SEC-005 (DNS pinning) | Deferred | Theoretical TOCTOU only; an attacker would need to control DNS for a Swiss-federal host. **Trigger:** same as above. Documented alongside SEC-004. |

---

## Remaining Open Findings (recommended backlog, in priority order)

1. **OBS-001 (high)** — Handled upstream failures are still returned as plain `Fehler: …` strings (7 call sites: `return _handle_error(e)`), not flagged `isError: true`. The LLM cannot distinguish an error result from content. *Fix:* wrap handled errors in an error-flagged result (or raise via the FastMCP error path), add a test asserting the flag. Smallest of the three; highest correctness value.
2. **ARCH-004 (high)** — Configuration is still module-level constants (`CKAN_API`, `HTTP_TIMEOUT`, `ALLOWED_HOSTS`, host/port) and transport is selected via `sys.argv`. *Fix:* a `Settings(BaseSettings)` (env-prefixed) instantiated once; `MCP_TRANSPORT`/`MCP_HOST`/`MCP_PORT`. Partial progress already exists (`MCP_HOST`/`MCP_PORT`/`MCP_LOG_LEVEL`/`MCP_CORS_ORIGINS` are read from env), so this is a consolidation, not net-new behaviour.
3. **SEC-022 (high)** — Tools use the consistent `heritage_` prefix rather than the `<server>__<tool>` server-identity form, and there is no release-time tool-definition hash for rug-pull detection. *Fix (optional/breaking):* adopt `<server>__<tool>` (major bump) and/or add a release step writing a tool name+description+schema hash to `audits/tool-pins/<version>.json`.

None of the three is a live exposure; all are engineering/process choices appropriate to schedule rather than hotfix.

---

## Conclusion

The remediation series closed every `fail` and the great majority of `partial` findings. The server is in a strong posture for a read-only, anonymous, closed-allow-list Phase 1 deployment: structured + traceable, licence-compliant, with graceful search degradation and masked internal errors. The remaining three open items are documented above as a prioritised backlog.
