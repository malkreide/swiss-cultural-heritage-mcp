# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security
- Audit finding `OBS-002`: unhandled (programming) errors no longer leak their internal exception text to the client/LLM. The official `mcp.server.fastmcp` SDK has no `mask_error_details` flag (that exists only in the standalone `fastmcp` package) and otherwise wraps every tool exception as `ToolError(f"Error executing tool {name}: {e}")`. A new `mask_unexpected_errors` decorator on every tool logs the full exception to stderr (server-side) and re-raises a generic `ToolError`, so the error is still surfaced as an error result (`OBS-001`) but with internals masked.
- Audit finding `SDK-004`: Streamable-HTTP transport now mounts CORS middleware that exposes `Mcp-Session-Id` (so browser clients can read/continue the session) with an explicit, non-wildcard origin allow-list via `MCP_CORS_ORIGINS`.
- Audit finding `SEC-016`: the HTTP host now defaults to `127.0.0.1`; only the container image sets `MCP_HOST=0.0.0.0`, preventing accidental all-interface binding outside a container.

### Added
- Audit finding `OBS-006`: optional OpenTelemetry distributed tracing. New `_init_tracing()` sets up an OTLP exporter, a resource (`service.name`/`service.version`/`deployment.environment`), and httpx auto-instrumentation; `mask_unexpected_errors` opens one span per call (`mcp.tool.<name>` with `mcp.tool.name` + `is_error` attributes — no payloads/PII), so each upstream request (SIKART/SNM/NB) appears as a child span and cross-search fan-out latency is observable. It is **gated behind `OTEL_EXPORTER_OTLP_ENDPOINT`** and packaged as an optional `otel` extra (`pip install '.[otel]'`), so stdio/local runs have zero overhead and no extra dependency; if the env var is set but the packages are missing, it logs a warning and continues without tracing. Endpoint/headers follow the standard `OTEL_*` env vars; `DEPLOYMENT_ENV` sets the environment label.
- Audit finding `OBS-003`: structured logging. Added `structlog` (new runtime dependency) configured to emit **JSON to stderr** — stdout stays reserved for the MCP stdio protocol (`OBS-004`). Every tool call is logged via `mask_unexpected_errors` with bound context (`tool` name + best-effort MCP `request_id`, propagated through `contextvars` so deep logs inherit it): an `info` `tool.call` per invocation, an `error` `tool.unexpected_error` (with `exc_info`) on masked failures, and a `warning` `upstream.error` (error class + HTTP status only — no payloads/PII) for each handled upstream failure in `_handle_error`. Level is configurable via `MCP_LOG_LEVEL`; the prior stdlib `logging` last-resort logger is replaced.
- Audit finding `ARCH-003`: "not found" heuristics. The `ResultEnvelope` gained a `match_type` field (`Literal["exact","fuzzy","none"]`). The two free-text CKAN search tools now retry on zero exact hits with a loosened query and label the result `fuzzy` — `heritage_search_artists` re-queries with the most specific (longest) term, `heritage_search_museum_datasets` re-queries with OR-joined Solr prefix wildcards. Markdown responses show a fuzzy notice; JSON `none` results are now a structured envelope (`count: 0`, `match_type: "none"`) instead of a bare string, while keeping the existing actionable hint text. NB/Helveticat has no server-side search, so it stays exact-only (documented in the tool + the empty-result hint).
- Audit finding `SDK-003`: context injection for progress + logging. `heritage_cross_search` (which fans out to three upstreams, typically > 2 s) now accepts an SDK-injected `ctx: Context` and calls `ctx.report_progress()` after each completed source and `ctx.warning()` for each failing source — so clients get an incremental progress signal and a *structured* warning instead of the per-source error being silently folded into the result text. The fan-out switched from `asyncio.gather` to `as_completed` for incremental reporting (requested source order is preserved in the output). `ctx` is excluded from the public input schema and defaults to `None`, so direct/test calls without a request still work.
- Audit finding `CH-004`: OGD-CH licence/attribution compliance. Every markdown response now ends with a **"Datenquelle & Lizenz"** footer (source name, licence, URL), and `heritage_cross_search` tags each result line with its own source (`` `[SIK-ISEA]` ``/`` `[SNM]` ``/`` `[NB]` ``) so provenance survives when a single item is copied out of an aggregated answer; its JSON sections now carry `license`/`url` per source. Builds on the `ResultEnvelope.source` block from `SDK-002`. The SIK-ISEA source-level licence was also corrected to `CC BY` to match the project's own documented OGD terms (`heritage://sik-isea/overview`, README).
- Audit finding `SDK-002`: typed structured output. Search/list tools now return a consistent `ResultEnvelope` Pydantic model (`source` + licence, `count`, `total`, `offset`, `has_more`, `results`, optional `meta`) in `response_format="json"` mode, so the official SDK emits real MCP structured content plus an `outputSchema`. Markdown remains the default human-readable view over the same data (return type is `ResultEnvelope | str`). `heritage_cross_search` gained a `response_format` parameter and returns multi-source provenance in its envelope.
- Audit finding `ARCH-012`: `.github/dependabot.yml` (monthly pip / GitHub Actions / Docker update PRs) and a "MCP Protocol Version" section in both READMEs documenting the supported version (`2025-11-25`) and SDK-pin update policy.
- Audit finding `OPS-003`: `docs/roadmap.md` declaring the read-only Phase 1 scope and the Phase 1 → 2 gate; the phase is now stated in both READMEs.
- Audit findings `SEC-019` / `SEC-013` / `SCALE-006`: lethal-trifecta assessment, secret-management note, and recommended container resource limits added to `docs/security.md`.

### Changed
- **Breaking (JSON consumers):** `response_format="json"` now returns the typed `ResultEnvelope` (fields `source`/`count`/`total`/`offset`/`has_more`/`results`/`meta`) instead of the previous ad-hoc keys (`artists`/`datasets`/`records`/`sets`). Record lists moved under `results`; provenance and licence are under `source`. Markdown output is unchanged.

### Fixed
- HTTP entry point: `--http` mode previously called `mcp.run(transport="streamable-http", port=port)`, but the official SDK's `run()` takes no `port` argument — the server now configures host/port on `mcp.settings` and serves the CORS-wrapped app via uvicorn (`SDK-004` / `SCALE-001`).
- Documentation drift: both READMEs said "9 tools"; the server registers 8 (`OPS-002`).
- Test isolation: the shared `httpx.AsyncClient` is now reset between tests, fixing `RuntimeError: Event loop is closed` when live tests run in pytest's per-test event loops
- HTTP redirects are followed again — a `302` from opendata.swiss previously surfaced to users as `Fehler: API-Anfrage fehlgeschlagen (HTTP 302)`
- SIK-ISEA module pointed at a non-existent host (`api.sik-isea.ch`); it now uses the real SIKART artist dataset (~17'000 records) on opendata.swiss
- Nationalbibliothek module pointed at a non-existent OAI-PMH endpoint (`www.nb.admin.ch/oai/oai-provider`); it now uses the real Helveticat OAI-PMH provider

### Changed
- `_http_get` follows redirects manually and re-checks the egress allow-list (`ALLOWED_HOSTS`) on every hop; the client keeps `follow_redirects=False` so per-hop validation still closes the redirect-chain SSRF vector
- `nightly-live.yml` no longer hard-fails on upstream API breakage — it opens or updates a `nightly-live-failure` GitHub issue instead, matching the workflow's documented intent
- SIK-ISEA: `heritage_search_artists` / `heritage_get_artist` now query the CKAN DataStore API (`datastore_search` on the SIKART resource) with server-side full-text search and pagination
- Nationalbibliothek: `NB_OAI_PMH` now targets `helveticat.nb.admin.ch/view/oai/41SNL_51_INST/request`; the OAI-PMH (`oai_dc`) design is unchanged
- CKAN base URL switched to the canonical `ckan.opendata.swiss` host (avoids the `302` from `opendata.swiss`)
- Egress allow-list reduced to the hosts actually used: `ckan.opendata.swiss`, `helveticat.nb.admin.ch`
- Documentation (`README.md`, `README.de.md`, `EXAMPLES.md`, `docs/`) updated to match the rebuilt SIK-ISEA / NB data sources

### Removed
- `heritage_search_artists` parameters `period` and `technique` — the SIKART dataset has no structured fields for them; `query` covers professions via the biography line
- Unused `_paginate` helper (artist search now paginates server-side via CKAN)

## [0.2.0] - 2026-05-21

### Added
- `/health` endpoint for Render / Kubernetes / Cloud Run liveness probes
- Hardened `Dockerfile` (non-root UID 10001, slim Python base)
- `docs/security.md`, `docs/network-egress.md`, `docs/data-residency.md`
- Nightly live-test CI workflow (`.github/workflows/nightly-live.yml`)
- `NbCollectionsInput` Pydantic model for `heritage_list_nb_collections`
- `.gitignore`
- Reproducible audit deliverables under `audits/` (baseline + re-run reports, per-finding files)

### Changed
- HTTP client now owned by FastMCP `lifespan`; a single `httpx.AsyncClient` is reused across all requests
- All tools catch the narrow `ExpectedUpstreamError` tuple instead of bare `Exception`
- Dependency upper bounds tightened (`<2.0.0` on `mcp`, `<1.0.0` on `httpx`, `<3.0.0` on `pydantic`, `<1.0.0` on `defusedxml`)
- `__version__` derived from `importlib.metadata.version()` (single source of truth)
- `heritage_cross_search.idempotentHint` corrected from `False` to `True`
- README (EN + DE): Render section now requires the Frankfurt region for Swiss public-sector deployments

### Security
- Egress allow-list (`ALLOWED_HOSTS` frozenset) enforced on every HTTP request
- `follow_redirects=False` on the shared httpx client to close the redirect-chain SSRF vector
- Swapped `xml.etree.ElementTree` → `defusedxml.ElementTree` for OAI-PMH parsing
- Programming bugs now propagate to the framework layer instead of being hidden in user-facing strings

## [0.1.0] - 2026-03-13

### Added
- Initial release with Phase 1 implementation (no authentication required)
- **SIK-ISEA module**: `heritage_search_artists`, `heritage_get_artist`
- **SNM module**: `heritage_search_museum_datasets`, `heritage_browse_collection`
- **NB module**: `heritage_search_helveticat`, `heritage_list_nb_collections`, `heritage_get_publication`
- **Cross-source**: `heritage_cross_search` — parallel search across all three sources
- 2 Resources: `heritage://sik-isea/overview`, `heritage://nb/collections`
- 2 Prompts: `heritage_research_artist`, `heritage_find_educational_resources`
- Dual transport: stdio (Claude Desktop) + Streamable HTTP (cloud/Render.com)
- GitHub Actions CI (Python 3.11, 3.12, 3.13)
- Bilingual documentation (DE/EN)
- 36 unit and integration tests (mocked HTTP via respx)
