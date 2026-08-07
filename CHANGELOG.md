# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **Eine unerwartete Dodis-Antwort wurde zu null Treffern.** `_search_dodis`
  las `data if isinstance(data, list) else data.get("results", [])`.

  Zwei Formen sind hier wirklich gültig — Dodis antwortet als nackte
  Trefferliste **und** als Objekt mit `results`. Der stille Rest war der dritte
  Fall: ein Objekt **ohne** `results` — eine Fehlerseite mit HTTP 200, eine
  umgebaute Antwort — wurde zu null Treffern, und das liest sich wie «Dodis
  kennt dazu nichts».

  Der dritte Fall wirft jetzt `UpstreamSchemaError` mit den tatsächlich
  vorhandenen Schlüsseln. Beide gültigen Formen gehen unverändert durch; eine
  Bestätigung, die die Listenform mitgefangen hätte, hätte die Quelle
  kaputtgemacht statt sie zu prüfen.

  Nachtrag zum Portfolio-Durchlauf
  ([`FID-006`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-006.md)):
  Der CKAN-Sweep reparierte die sechs CKAN-Stellen dieses Servers, Dodis ist
  die siebte Quelle.

### Fixed

- **Sechs CKAN-Stellen schrieben eine Strukturänderung in eine Leermenge um.**
  Dreimal auf `records` (DataStore), zweimal auf `results` (`package_search`),
  einmal auf beides im Mehrquellen-Werkzeug — alle nach dem Muster
  `data.get("result", {}).get(<feld>, [])`.

  Fällt `result` weg, war die Trefferliste leer, und das Werkzeug antwortete
  «Keine Daten gefunden»: für das Modell nicht davon zu unterscheiden, dass
  SIK-ISEA oder das SNM nichts haben. **Zwei der sechs** lasen die Hülle sogar
  direkt aus `resp.json()`, ohne das `success`-Envelope überhaupt anzusehen —
  die beiden waren am leichtesten zu übersehen.

  Alle sechs laufen jetzt über `_ckan_result()`, das `result` **und** das
  gelesene Feld bestätigt und sonst `UpstreamSchemaError` wirft, mit den
  tatsächlich vorhandenen Schlüsseln in der Meldung.

  Der Typ erbt von `ValueError` und ist damit automatisch Teil von
  `ExpectedUpstreamError` — das ist hier tragend: Die Formänderung wird zur
  handlungsorientierten Meldung statt zu einem maskierten «Interner Fehler»,
  und im Mehrquellen-Werkzeug fällt nur *diese* Quelle aus, während die anderen
  weiter antworten.

  `records: []` bleibt ein normales Ergebnis: Bestätigt wird die **Anwesenheit**
  des Schlüssels, nicht sein Inhalt. CKAN liefert `records` bzw. `results` auch
  bei null Treffern.

  **Unverändert:** Eine Antwort, die statt eines Objekts eine nackte Liste ist,
  scheitert weiterhin an `data.get("success")` und wird als «Interner Fehler»
  maskiert — eine bewusste Entscheidung dieses Repos mit eigenem Test.

  Gefunden im Portfolio-Durchlauf zu
  [`FID-006`](https://github.com/malkreide/mcp-audit-skill/blob/main/checks/FID-006.md)
  am 2026-08-07: Acht Server im Portfolio sprechen mit CKAN, alle acht prüfen
  das `success`-Envelope, sieben defaulteten `result` danach.

### Fixed

- **The retry had six defects, all inherited from the shared template.** This
  server copied its retry from `reference/retry_backoff.py` in
  [mcp-data-source-probe-skill](https://github.com/malkreide/mcp-data-source-probe-skill),
  and the template shipped these until 2026-08-07. A sweep across eleven
  servers found that none read `Retry-After` and none jittered — one template,
  eleven copies, not eleven independent omissions.
  1. **No jitter.** The ladder was deterministic, so every client that hit the
     same outage retried in lockstep and the load returned as a wave exactly
     when the source recovered — the retry storm extending the outage it was
     meant to bridge. Now spread into `[0.5x, 1.5x]`.
  2. **`Retry-After` was never read.** A 429 or 503 answers the very question
     the backoff curve guesses at. Both RFC 9110 §10.2.3 forms are now read
     (delta-seconds and HTTP-date); an unparseable header yields `None` and
     falls back to the curve — it must never crash on the error path. The
     jitter on top is one-sided `[1.0x, 1.25x]`: the source said *when*, so
     later is polite and earlier ignores the value just read.
  3. **No cap on a single wait**, and the cap now binds *after* the jitter.
     `min(cap, base) * jitter` and `min(cap, base * jitter)` both contain a cap
     and a jitter; only the second is bounded — 20s times 1.5 is 30s.
  4. **The budget counted attempts, not seconds.** Four attempts against an
     upstream that takes 30s to time out is two minutes inside one tool call,
     and an attempt count never says so. Now 25s for the whole call, anchored
     on the MCP SDK's `MCP_DEFAULT_TIMEOUT = 30.0`.
  5. **Nothing held that budget.** It is now an `asyncio.timeout` wall-clock
     deadline rather than an httpx timeout: httpx bounds each *operation*, and
     its read timeout restarts with every chunk, so a slowly trickling response
     outlived the budget without any single read expiring.
  6. **Point six did not apply here.** `_fetch_with_retry` already ended in
     `raise last_error` rather than wrapping — the caller keeps the exception
     type and `.response`. A structured `upstream_unreachable` warning now
     records the type and which of the two limits ran out; the raise is
     unchanged. `UpstreamUnavailableError` covers the one case with no original
     exception.

  The new knobs are settings fields, matching how `retry_attempts` and
  `retry_backoff_base` are already configured: `retry_total_budget`,
  `retry_max_delay`, `retry_jitter_spread`, `retry_after_jitter`.

  New `tests/test_retry_policy.py`: `Retry-After` in both forms plus the
  refusal cases, the jitter spread, that the cap binds after jittering, and the
  one-sided `Retry-After` jitter.

## [0.5.0] - 2026-07-31

### Hinzugefuegt

- **Der Server nennt jetzt seinen Namen.** Bisher ging gegenueber jedem
  Upstream der httpx-Default hinaus: der Betreiber der Datenquelle sah
  eine Bibliothek, nicht uns, und hatte keinen Weg, uns bei Fehlverhalten
  zu erreichen. Neu traegt den HTTP-Client
  `swiss-cultural-heritage-mcp/<version> (+github.com/malkreide/swiss-cultural-heritage-mcp)`.

  Die Version stammt aus `importlib.metadata` und kann nicht getrennt vom
  Paket driften.

### Fixed

- **HTTP-Modus wies unter jedem echten Hostnamen mit 421 ab (SEC-005).**
  `build_http_app()` rief `mcp.streamable_http_app()` ohne `host` auf. Unter
  mcp 2.x ist das kein neutraler Default: das SDK leitet daraus seine
  Host-Allow-List ab und aktiviert bei loopback-artigem Wert automatisch
  `127.0.0.1:*`. Da das Argument selbst auf `127.0.0.1` defaultet, traf das jeden
  Container mit `MCP_HOST=0.0.0.0` — also den dokumentierten Deployment-Fall.
  Vor der Migration ging `host` an den `FastMCP`-Konstruktor, wo dieselbe Logik
  den echten Bind sah und den Schutz korrekt ausliess.

  Der Bind reist jetzt in die App, und eine echte Allow-List wird aus dem neuen
  `MCP_INBOUND_ALLOWED_HOSTS` gebaut. Ohne diese Variable bleibt der Schutz auf
  einem Nicht-Loopback-Bind bewusst aus und der Aufrufer warnt — eine geratene
  Liste wäre genau der 421-Fall.

  Die Einstellung heisst bewusst `inbound_allowed_hosts` und nicht
  `allowed_hosts`: letzteres ist in diesem Server die **Egress**-Allow-List
  (SEC-021) und meint die Gegenrichtung. Ein Test hält fest, dass ein Upstream
  wie `ckan.opendata.swiss` nicht in die eingehende Liste gerät.

  13 neue Tests, darunter der tragende Fall „richtiger Hostname, falscher Port"
  — nur er unterscheidet eine portgenaue Allow-List von einer, die alles
  durchlässt. Mutationsgetestet: nimmt man den `host`-Kwarg wieder weg,
  reproduziert der Test das 421.

  Geprüft mit dem wörtlichen CI-Kommando: 137 passed, 2 skipped, 7 deselected;
  `ruff check src/ tests/` clean.

- **The tool pin recorded the wrong release, and could not have recorded the
  right one (SEC-022).** `audits/tool-pins/current.json` said
  `generated_for_version: 0.3.3` while the package was at `0.4.0`, so the pin
  documented *which* tool surface was approved but not *for which* release.

  The cause was in the generator, not the file: `scripts/pin_tools.py` read
  `importlib.metadata.version()`, which returns `0.0.0+local` under the
  documented `PYTHONPATH=src` invocation. The value therefore depended on
  whatever happened to be installed in the caller's environment — which is why
  the pin test carried the comment *"version is environment-dependent and
  intentionally not compared"*. Uncomparable meant unchecked, and it drifted.

  The generator now reads the version from `pyproject.toml`. That makes the
  output deterministic — correct even with nothing installed, which the old
  code could not manage — and makes the field safe to assert. Two tests do:
  one compares the pin against `pyproject.toml`, one pins the generator's own
  version source so a regression there cannot make the first test fail for the
  wrong reason. Both are mutation-tested.

  **No tool contract moved:** `manifest_sha256` stays `fc22092d79e4…` and every
  per-tool hash is byte-identical; the version line is the whole diff.
  Regeneration is idempotent.

### Changed

- **Migrated to the `mcp` 2.x server API.** Pin `>=1.28.1,<2` → `>=2.0.0,<3`;
  `FastMCP` → `MCPServer` (`mcp.server.mcpserver`). The floor is hard: 2.0.0
  removed `mcp.server.fastmcp` with no compatibility shim, so this code cannot
  run on 1.x, and a `>=1.x` range would let a resolver pick a version that
  fails at import.

  Existing clients see no difference — the legacy `initialize` handshake still
  caps at 2025-11-25. mcp 2.x does additionally serve a "modern" per-request
  envelope era that reaches 2026-07-28, so a 2.x-aware client negotiates the
  newer revision. Not a break, but not a protocol no-op either.

- **The OBS-001 error-flag test now goes through the real protocol path.** It
  reached into `mcp._mcp_server.request_handlers[CallToolRequest]`, a mapping
  2.x no longer has. The replacement uses the in-process `mcp.client.Client`,
  which is closer to what a real client does: `is_error` is set by the server's
  CallTool handler, not by the tool function, so `MCPServer.call_tool()` alone
  would not have exercised it.

  Verified: 2 failed / 122 passed / 7 deselected — identical to the 1.x
  baseline, and the two failures are the pre-existing `TestTracing` ones
  (missing optional OpenTelemetry packages), confirmed to fail the same way
  under mcp 1.x. `ruff check src/ tests/` clean, fresh-venv install clean.

  **No tool contract moved:** `scripts/pin_tools.py` regenerates a
  byte-identical `manifest_sha256` (`fc22092d79e4…`, 11 tools). Unrelated
  observation, left alone: `generated_for_version` in the committed pin still
  reads `0.3.3` while the package is at `0.4.0`.

## [0.4.0] - 2026-07-19

Adds a **federated memory-institution facade** over two newly probed Swiss sources —
**Memoriav / Memobase** and **Dodis** (Diplomatic Documents of Switzerland) — bringing
the server to **11 tools across five data sources**. The server stays in **Phase 1
(read-only)**: all three new tools are annotated `readOnlyHint: true` and only issue
HTTP GET/POST reads against public, no-auth upstreams.

### Added
- **Three federated tools** (`MODUL 5` in `server.py`), following the task's requested
  signatures:
  - `search_heritage(query, collection, date_from, date_to, media_type)` — `collection`
    is an enum (`memobase | dodis | all`). For `all`, both sources are queried in
    parallel with per-source progress/warnings via the injected `Context`; if one
    source fails the other still returns (surfaced in `meta.errors`), and only a
    total outage raises `isError`.
  - `get_heritage_item(collection, item_id)` — full metadata for one object.
  - `list_heritage_collections()` — discovery tool listing each source's protocol,
    auth and licence, **including the probed-but-not-connected sources** (Bundesarchiv,
    Landesmuseum) and the reason each is excluded.
- **Provenance + split licence in every result.** Each hit carries `source`, a
  `permalink`, and the licence reported **separately for metadata and for the digitised
  object** — they diverge (metadata is open Linked Open Data; a Memobase digitised
  object may be `In Copyright` / access `onsite`, exposed from
  `rightsstatements.org`). Only metadata and links are returned; **copyright-protected
  full texts are never reproduced** — Dodis transcription/fulltext fields
  (`doc_att_file_content`, `doc_att_xmlTranscription_ids`) are excluded from both the
  markdown view and the JSON envelope, and the Dodis regest is length-capped.
- **Resilience: retry with exponential backoff.** New `_fetch_with_retry` wraps the
  memory-institution fetches (5xx / 429 / network / timeout → up to `retry_attempts`
  tries with `retry_backoff_base * 2**(n-1)` waits, default 2s/4s/8s; 4xx except 429
  never retried). `_http_post` (JSON) and an optional `headers` argument on `_http_get`
  were added (Memobase requires `Accept: application/ld+json` content-negotiation).
- Egress allow-list extended with `api.memobase.ch` and `beta.dodis.ch` (see
  `docs/network-egress.md`); permalink hosts are linked but never fetched, so they are
  deliberately not allow-listed.
- Architecture-decision section (bilingual READMEs) documenting the **live probe of
  2026-07-19**: why Memobase and Dodis are connected and why Bundesarchiv (eIAM +
  reCAPTCHA) and Landesmuseum (no public API) are not.
- New unit tests (happy path, single/all collection, client-side date & media-type
  filters, partial failure, retry-on-503, timeout, fulltext-non-leak, discovery) and
  `@pytest.mark.live` tests against the real Memobase and Dodis APIs.

### Security
- **`SEC-022` tool-pin re-approval note:** `audits/tool-pins/current.json` was
  regenerated (8 → 11 tools) to record the three new tools `search_heritage`,
  `get_heritage_item`, `list_heritage_collections`. No existing tool's name,
  description, or schema changed; the pin update reflects only the added tools.

## [0.3.0] - 2026-06-02

This release lands the full **mcp-audit-skill** remediation series (PRs #19–#30) on top of the SIK-ISEA / NB data-source rebuild: typed structured output, optional distributed tracing, structured JSON logging, OGD licence attribution, fuzzy search fallback, `isError` error flagging, a single env-driven configuration object, and tool-prompt drift pinning. The audit board moves from `0 PASS / 17 PARTIAL / 4 FAIL` to **19 PASS / 2 accepted-risk / 0 open** — see [`audits/2026-06-02-swiss-cultural-heritage-mcp-rerun/report.md`](audits/2026-06-02-swiss-cultural-heritage-mcp-rerun/report.md).

> **⚠️ Breaking for JSON consumers** (`response_format="json"`): see the Changed section. Markdown output (the default) is unchanged.

### Security
- Audit finding `SEC-022`: tool-definition pinning for rug-pull / drift detection. `audits/tool-pins/current.json` now commits a SHA-256 of every tool's `name` + cleaned docstring (the LLM-facing `description`, plus a manifest hash); `scripts/pin_tools.py` regenerates it and a new `TestToolPins` fails CI on any silent change, forcing a conscious update + a CHANGELOG re-approval note. The pin intentionally excludes the pydantic/SDK-generated JSON schema, whose serialised form varies across dependency versions (so it stays stable across benign dependency bumps); the schema/IO contract is covered by the structured-output and input-validation tests. The `<server>__<tool>` namespacing half is breaking (every tool id changes → major bump) and is documented as a deferred Phase-2 decision in `docs/security.md`; the consistent `heritage_` prefix is retained. **Re-approval note:** this change does not alter any tool's name, description, or schema — the pin records the existing definitions, so no client re-approval is required.
- Audit finding `OBS-001`: handled upstream failures (HTTP error, timeout, network, XML-parse, CKAN `success:false`) are now **raised as `ToolError`** via a new `_raise_tool_error` helper instead of being returned as plain `Fehler: …` strings. The masking decorator passes `ToolError` through and the MCP SDK wraps it in a `CallToolResult` with `isError: true`, so the client/LLM can distinguish a failure from a successful (or empty) result. Genuine empty results ("Keine … gefunden") remain normal, non-error responses. The structured `upstream.error` warning (`OBS-003`) is still logged on the way out.
- Audit finding `SEC-004`: `_assert_allowed` now also enforces an **HTTPS-only scheme** (rejects `http://`/`file://` and other schemes even for an allow-listed host, e.g. a redirect downgrade) — defense-in-depth on top of the two-host egress allow-list. The heavier IP-blocklist and DNS-pinning (`SEC-005`) measures are documented as deliberately deferred (low real risk given the closed allow-list and no user-controlled host), with the explicit trigger that would make them required — see `docs/security.md` (SSRF & DNS rebinding).
- Audit findings `SCALE-002` / `SCALE-003`: documented the **single-instance constraint** for the Streamable-HTTP deployment and the path to safe horizontal scaling (edge sticky-sessions on `Mcp-Session-Id` with failover testing, or a shared Redis/Durable-Objects session backend) in a new `docs/scaling.md`, linked from both READMEs. The transport session is in-process; the tool logic itself remains stateless.
- Audit finding `OBS-002`: unhandled (programming) errors no longer leak their internal exception text to the client/LLM. The official `mcp.server.fastmcp` SDK has no `mask_error_details` flag (that exists only in the standalone `fastmcp` package) and otherwise wraps every tool exception as `ToolError(f"Error executing tool {name}: {e}")`. A new `mask_unexpected_errors` decorator on every tool logs the full exception to stderr (server-side) and re-raises a generic `ToolError`, so the error is still surfaced as an error result (`OBS-001`) but with internals masked.
- Audit finding `SDK-004`: Streamable-HTTP transport now mounts CORS middleware that exposes `Mcp-Session-Id` (so browser clients can read/continue the session) with an explicit, non-wildcard origin allow-list via `MCP_CORS_ORIGINS`.
- Audit finding `SEC-016`: the HTTP host now defaults to `127.0.0.1`; only the container image sets `MCP_HOST=0.0.0.0`, preventing accidental all-interface binding outside a container.

### Added
- Audit finding `ARCH-004`: a single `Settings(BaseSettings)` object (env prefix `MCP_`, via `pydantic-settings`) is now the source of truth for all configuration — upstream endpoints, the SIKART resource id, HTTP timeout/limits/redirects, the egress allow-list, and transport/host/port/log-level/CORS-origins. Every field is overridable per environment via `MCP_*` env vars (e.g. `MCP_HTTP_TIMEOUT=10`, `MCP_TRANSPORT=http`) **without editing code**, removing the previous reliance on global module constants. The public module constants (`CKAN_API`, `ALLOWED_HOSTS`, …) remain as stable aliases derived from `settings`. The entry point selects the transport from `MCP_TRANSPORT` (with `--http` kept as a CLI alias) instead of parsing `sys.argv` for host/port.
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

### Fixed
- HTTP entry point: `--http` mode previously called `mcp.run(transport="streamable-http", port=port)`, but the official SDK's `run()` takes no `port` argument — the server now configures host/port on `mcp.settings` and serves the CORS-wrapped app via uvicorn (`SDK-004` / `SCALE-001`).
- Documentation drift: both READMEs said "9 tools"; the server registers 8 (`OPS-002`).
- Test isolation: the shared `httpx.AsyncClient` is now reset between tests, fixing `RuntimeError: Event loop is closed` when live tests run in pytest's per-test event loops
- HTTP redirects are followed again — a `302` from opendata.swiss previously surfaced to users as `Fehler: API-Anfrage fehlgeschlagen (HTTP 302)`
- SIK-ISEA module pointed at a non-existent host (`api.sik-isea.ch`); it now uses the real SIKART artist dataset (~17'000 records) on opendata.swiss
- Nationalbibliothek module pointed at a non-existent OAI-PMH endpoint (`www.nb.admin.ch/oai/oai-provider`); it now uses the real Helveticat OAI-PMH provider

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
