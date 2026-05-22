# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
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
