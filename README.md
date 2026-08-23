> 🇨🇭 **Part of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide)**

# 🏛️ swiss-cultural-heritage-mcp

![Version](https://img.shields.io/badge/version-0.5.0-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)](https://modelcontextprotocol.io/)
[![No Auth Required](https://img.shields.io/badge/auth-none%20required-brightgreen)](https://github.com/malkreide/swiss-cultural-heritage-mcp)
![CI](https://github.com/malkreide/swiss-cultural-heritage-mcp/actions/workflows/ci.yml/badge.svg)

> MCP Server for Swiss cultural heritage — SIK-ISEA artists, Nationalmuseum collections, and the Nationalbibliothek bibliography

[🇩🇪 Deutsche Version](README.de.md)

---

## Overview

`swiss-cultural-heritage-mcp` provides AI-native access to Swiss cultural heritage data sources, all without authentication:

| Source | Data | API |
|--------|------|-----|
| **SIK-ISEA (SIKART)** | ~17,000 Swiss artists — SIKART biographical data | opendata.swiss CKAN |
| **Nationalmuseum (SNM)** | Museum collections (numismatics, seals, special collections) | opendata.swiss CKAN |
| **Nationalbibliothek (NB)** | Swiss national bibliography (Helveticat) | OAI-PMH |
| **Memoriav / Memobase** | Audiovisual heritage (photo, audio, video) | Linked Open Data (JSON-LD / Hydra) |
| **Dodis** | Diplomatic Documents of Switzerland (documents, persons, organisations) | JSON-REST (Solr) + permalinks |

This server completes the humanistic dimension of the Swiss public data portfolio — history, literature, and art — alongside existing servers for law ([fedlex-mcp](https://github.com/malkreide/fedlex-mcp)), transport, statistics, and more.

The **memory-institution facade** (Memobase + Dodis) is exposed through three
federated tools — `search_heritage`, `get_heritage_item`, `list_heritage_collections` —
rather than one tool-family per source. Every result carries **source, permalink and
licence**, and the licence is reported **separately for metadata and for the
digitised object** (they diverge: metadata is open Linked Open Data, but a
digitised object may be *In Copyright*). Only metadata and links are returned —
copyright-protected full texts (e.g. Dodis transcriptions) are never reproduced.

**Anchor demo query (art):** *"Find works by Zurich-based painters from the 19th century in the Nationalmuseum, and cross-reference with their biography in the SIK-ISEA artist database."*

**Anchor demo query (memory institutions):** *"Which sources on the development of the Zurich Volksschule in the 19th century can be found in the Swiss memory institutions?"* → `search_heritage(query="Volksschule Zürich", collection="all", date_from="1800", date_to="1899")`.

### Demo

![Demo: Claude using heritage_cross_search](docs/assets/demo.svg)

---

## Features

- 🏛️ **11 tools, 2 resources, 2 prompts** across five data sources
- 🔍 **`heritage_cross_search`** — parallel search across SIK-ISEA + SNM + NB in a single call
- 🏛️ **`search_heritage`** — federated facade over Memobase + Dodis with per-result source, permalink and split metadata/digitised-object licence
- 🌐 **Bilingual output** (Markdown / JSON)
- 🔓 **No API key required** — all data under open licenses
- ☁️ **Dual transport** — stdio (Claude Desktop) + Streamable HTTP (cloud)
- 📚 **Prompt templates** for art research and finding educational materials

**Project phase:** **Phase 1 — read-only.** Every tool is annotated `readOnlyHint: true`; there are no write or destructive operations. Moving to Phase 2 (write-capable) requires the prerequisites in [`docs/roadmap.md`](docs/roadmap.md).

---

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

---

## Installation

```bash
# Clone the repository
git clone https://github.com/malkreide/swiss-cultural-heritage-mcp.git
cd swiss-cultural-heritage-mcp

# Install
pip install -e .
# or with uv:
uv pip install -e .
```

Or with `uvx` (no permanent installation):

```bash
uvx swiss-cultural-heritage-mcp
```

---

## Quickstart

```bash
# stdio (for Claude Desktop)
python -m swiss_cultural_heritage_mcp.server

# Streamable HTTP (port 8000)
python -m swiss_cultural_heritage_mcp.server --http --port 8000
```

Try it immediately in Claude Desktop:

> *"Who is Ferdinand Hodler?"*
> *"What coins does the Nationalmuseum have from Zurich?"*
> *"Find publications about Volksschule in the Swiss national bibliography"*

[→ More use cases by audience →](EXAMPLES.md)

---

## Configuration

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "swiss-cultural-heritage": {
      "command": "python",
      "args": ["-m", "swiss_cultural_heritage_mcp.server"]
    }
  }
}
```

Or with `uvx`:

```json
{
  "mcpServers": {
    "swiss-cultural-heritage": {
      "command": "uvx",
      "args": ["swiss-cultural-heritage-mcp"]
    }
  }
}
```

**Config file locations:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

### Cloud Deployment (SSE for browser access)

For use via **claude.ai in the browser** (e.g. on managed workstations without local software):

**Render.com (recommended):**
1. Push/fork the repository to GitHub
2. On [render.com](https://render.com): New Web Service → connect GitHub repo
3. **Select region `Frankfurt` (EU)** — required for Swiss public-sector use under revDSG / EDÖB. See [`docs/data-residency.md`](docs/data-residency.md).
4. Set start command: `python -m swiss_cultural_heritage_mcp.server --http --port 8000`
5. In claude.ai under Settings → MCP Servers, add: `https://your-app.onrender.com/sse`

> 💡 *"stdio for the developer laptop, SSE for the browser."*

For container deployments (Docker / Kubernetes / Cloud Run): the repository ships a hardened `Dockerfile` (non-root UID 10001). See [`docs/security.md`](docs/security.md) for recommended `SecurityContext` and [`docs/network-egress.md`](docs/network-egress.md) for egress policy. The service runs **single-instance** by default; before scaling horizontally, see [`docs/scaling.md`](docs/scaling.md) for the session-affinity prerequisites.

---

## Available Tools

### SIK-ISEA (Swiss Art Research)

| Tool | Description |
|------|-------------|
| `heritage_search_artists` | Search ~17,000 Swiss artists (SIKART) by name or place |
| `heritage_get_artist` | Full artist profile by SIKART ID (HAUPTNR) |

### Nationalmuseum (SNM)

| Tool | Description |
|------|-------------|
| `heritage_search_museum_datasets` | Search SNM datasets on opendata.swiss |
| `heritage_browse_collection` | Browse objects within a collection via CKAN DataStore |

### Nationalbibliothek (NB)

| Tool | Description |
|------|-------------|
| `heritage_search_helveticat` | Search Swiss national bibliography via OAI-PMH |
| `heritage_list_nb_collections` | List available OAI-PMH sets |
| `heritage_get_publication` | Full Dublin Core metadata for a publication |

### Cross-Source

| Tool | Description |
|------|-------------|
| `heritage_cross_search` | Parallel search across SIK-ISEA + SNM + NB |

### Memory institutions (Memobase + Dodis) — federated facade

| Tool | Description |
|------|-------------|
| `search_heritage` | Federated search over Memobase + Dodis (`collection = memobase \| dodis \| all`), with `date_from` / `date_to` / `media_type` filters. Every result carries source, permalink and a split metadata/digitised-object licence |
| `get_heritage_item` | Full metadata for one object (`collection`, `item_id`). Metadata + links only — protected full texts are never reproduced |
| `list_heritage_collections` | Discovery: which collections exist, their protocol, auth and licences — including the probed-but-not-connected sources (Bundesarchiv, Landesmuseum) and *why* |

### Example Use Cases

| Query | Tool |
|-------|------|
| *"Who is Ferdinand Hodler?"* | `heritage_get_artist` |
| *"Find Swiss artists born in Basel"* | `heritage_search_artists` |
| *"What coins from Zurich does the Nationalmuseum have?"* | `heritage_browse_collection` |
| *"Find publications about Volksschule"* | `heritage_search_helveticat` |
| *"Search for everything about Sophie Taeuber-Arp"* | `heritage_cross_search` |
| *"Sources on the 19th-c. Zurich Volksschule in Swiss memory institutions"* | `search_heritage` |

---

## Architecture

```
┌─────────────────┐     ┌──────────────────────────────┐     ┌──────────────────────────┐
│   Claude / AI   │────▶│  Swiss Cultural Heritage MCP  │────▶│  SIK-ISEA                │
│   (MCP Host)    │◀────│  (MCP Server)                │◀────│  opendata.swiss / CKAN   │
└─────────────────┘     │                              │     ├──────────────────────────┤
                        │  11 Tools · 2 Resources      │────▶│  Nationalmuseum (SNM)    │
                        │  2 Prompts                   │◀────│  opendata.swiss / CKAN   │
                        │  Stdio | SSE                 │     ├──────────────────────────┤
                        │                              │────▶│  Nationalbibliothek (NB) │
                        │  No authentication required  │◀────│  OAI-PMH (Helveticat)    │
                        │                              │     ├──────────────────────────┤
                        │  search_heritage facade      │────▶│  Memobase (JSON-LD/Hydra)│
                        │                              │◀────│  Dodis (JSON-REST/Solr)  │
                        └──────────────────────────────┘     └──────────────────────────┘
```

### Data Source Characteristics

| Source | Protocol | Coverage | Auth |
|--------|----------|----------|------|
| SIK-ISEA (SIKART) | CKAN DataStore | ~17,000 Swiss artists | None |
| Nationalmuseum | CKAN DataStore | Museum collections | None |
| Nationalbibliothek | OAI-PMH | Swiss national bibliography | None |
| Memoriav / Memobase | Linked Open Data (JSON-LD / Hydra, RiC-O) | Audiovisual heritage (~460k records) | None |
| Dodis | JSON-REST (Solr) + stable permalinks | Diplomatic documents, persons, organisations | None |

### Architecture decision — memory-institution facade

Verified by a live probe on **2026-07-19** (methodology: *mcp-data-source-probe*).
Four memory institutions were evaluated; only two expose a clean, no-auth,
standardised interface and are connected:

| Source | Result | Why |
|--------|--------|-----|
| **Memobase** | ✅ connected | Linked-Open-Data API (`api.memobase.ch`, JSON-LD/Hydra); full-text search via `?q=`, single record via `/record/<id>`; pagination via `offset`/`size`. Metadata open; digitised objects carry per-object `rightsstatements.org` rights ("In Copyright", access "onsite"). |
| **Dodis** | ✅ connected | JSON-REST/Solr (`beta.dodis.ch/api`): search via `POST /api/solr/query`, item via `GET /api/solr/full/<id>`; stable permalinks `dodis.ch/<id>`. Metadata open (citation required); documents carry per-document rights (TEI/PDF behind the permalink). |
| **Bundesarchiv** | ⛔ not connected | The `recherche.bar.admin.ch` backend (CMI AIS) sits behind **eIAM** login and **Google reCAPTCHA** — not machine-accessible without emulating a session, which is fragile and against the operator's intent. |
| **Landesmuseum** | ⛔ not connected | `sammlung.nationalmuseum.ch` has **no public API** (only an internal, undocumented Ajax/HTML surface) — connecting it would require scraping, which violates the resilience guardrails. |

Consequences: three federated tools instead of four tool-families; every result
carries source + permalink + a **split** metadata/digitised-object licence; no
copyright-protected full text is reproduced (metadata + links only); `bar` and
`landesmuseum` are documented as gated via `list_heritage_collections`, not scraped.

---

## Project Structure

```
swiss-cultural-heritage-mcp/
├── src/swiss_cultural_heritage_mcp/
│   ├── __init__.py              # Package
│   └── server.py                # 11 tools, 2 resources, 2 prompts
├── tests/
│   └── test_server.py           # Unit + integration tests (mocked HTTP)
├── .github/workflows/ci.yml     # GitHub Actions (Python 3.11/3.12/3.13)
├── .github/dependabot.yml       # Monthly dependency + SDK update PRs
├── Dockerfile                   # Multi-stage, non-root, HEALTHCHECK
├── docs/                        # security, network-egress, scaling, data-residency, roadmap
├── pyproject.toml
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md                    # This file (English)
└── README.de.md                 # German version
```

> **Single-file server:** the 11 tools live in one `server.py` rather than a `tools/` package. At this size a single, linear module is easier to read and review than a split; if the tool count grows materially, the SIK-ISEA / SNM / NB / cross-search blocks are the natural split points.

---

## Safety & Limits

- **Read-only:** All tools perform HTTP GET requests only — no data is written, modified, or deleted.
- **No personal data:** The APIs return institutional records (artworks, publications, artists). No personally identifiable information (PII) is processed or stored by this server.
- **Rate limits:** The opendata.swiss and OAI-PMH endpoints are not rate-limit-documented; use `limit` parameters conservatively. The server enforces a 30s timeout per request.
- **Data freshness:** Records reflect the upstream source at query time. No caching is performed by this server.
- **Terms of service:** Data is subject to the ToS of each source — [SIK-ISEA](https://www.sik-isea.ch), [opendata.swiss](https://opendata.swiss/terms-of-use), [Nationalbibliothek OAI-PMH](https://www.nb.admin.ch/). All data is published under open licenses (CC0 / CC BY).
- **No guarantees:** This server is a community project, not affiliated with SIK-ISEA, SNM, or NB. Availability depends on upstream APIs.

---

## Known Limitations

- **SIK-ISEA:** Artist data is updated periodically; very recent acquisitions may not yet be reflected
- **Nationalmuseum:** Only datasets published on opendata.swiss are accessible; not all SNM collections are available
- **Nationalbibliothek:** OAI-PMH harvesting is rate-limited; large result sets require pagination
- **Cross-search:** Response time depends on the slowest of the three sources

---

## Testing

```bash
# Unit tests (no API key required)
PYTHONPATH=src pytest tests/ -m "not live"

# Integration tests (live API calls)
pytest tests/ -m "live"

# Lint and format, as CI runs them
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
```

Ruff is pinned to an exact version in `pyproject.toml` (`[project.optional-dependencies] dev`), so `pip install -e ".[dev]"` gives you the version CI uses and the lint gates agree with it. Installing a newer ruff on top changes the rule set and the formatter, and reports differences on code nobody touched. See [CONTRIBUTING.md](CONTRIBUTING.md#code-style).

---

## MCP Protocol Version

| Item | Value |
|---|---|
| SDK | `mcp[cli]>=2.0.0,<3` (pinned in `pyproject.toml`) |
| Served via the `initialize` handshake | `2024-11-05` … `2025-11-25` — the handshake ceiling |
| Served via the per-request envelope | `2026-07-28` |
| Who picks | The client's first request, once per connection: a request carrying the `2026-07-28` `_meta` envelope opens a modern connection, anything else opens a handshake connection. A later claim from the other era is refused. |
| Update policy | The SDK pin is the source of truth for the protocol version. [Dependabot](.github/dependabot.yml) opens monthly `mcp` update PRs; protocol-version bumps are reviewed there and recorded in [CHANGELOG.md](CHANGELOG.md). |

This server does not override the negotiation — the official `mcp` SDK decides, and both eras are reachable over either transport (stdio and HTTP alike). Pin the SDK, not a hand-rolled version string, to control which protocol versions are spoken. The numbers above are the pinned SDK's own registry (`mcp_types.version`: `HANDSHAKE_PROTOCOL_VERSIONS`, `MODERN_PROTOCOL_VERSIONS`) — read them there rather than from this table if the pin has moved.

Both revisions are pinned in
[`tests/test_protocol_version.py`](tests/test_protocol_version.py) and asserted
against the installed SDK — including the handshake ceiling, measured against a
live `initialize` through the assembled ASGI stack. A Dependabot bump of `mcp`
can no longer move either number without this table going stale unnoticed.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

---

## Security

See [SECURITY.md](SECURITY.md) ([Deutsch](SECURITY.de.md)) for the security
posture and how to report a vulnerability.

---

## License

MIT License — see [LICENSE](LICENSE)

---

## Author

Hayal Oezkan · [malkreide](https://github.com/malkreide)

---

## Credits & Related Projects

- **SIK-ISEA:** [www.sik-isea.ch](https://www.sik-isea.ch/) — Swiss Institute for Art Research
- **Nationalmuseum:** [www.nationalmuseum.ch](https://www.nationalmuseum.ch/) / [opendata.swiss](https://opendata.swiss/)
- **Nationalbibliothek:** [www.nb.admin.ch](https://www.nb.admin.ch/) — Swiss National Library
- **Protocol:** [Model Context Protocol](https://modelcontextprotocol.io/) — Anthropic / Linux Foundation
- **Related:** [eth-library-mcp](https://github.com/malkreide/eth-library-mcp) — ETH Library: full Swiss library coverage (ETH = science, NB = humanities)
- **Related:** [fedlex-mcp](https://github.com/malkreide/fedlex-mcp) — Cultural heritage law + primary legislation
- **Related:** [zurich-opendata-mcp](https://github.com/malkreide/zurich-opendata-mcp) — Spatial-historical: museum objects + Zurich geodata
- **Portfolio:** [Swiss Public Data MCP Portfolio](https://github.com/malkreide)

<!-- mcp-name: io.github.malkreide/swiss-cultural-heritage-mcp -->

<!-- BEGIN GENERATED: install -->
## Installation

Run via [`uv`](https://docs.astral.sh/uv/)'s `uvx` — no clone or manual install needed. Add to your MCP client config (`mcpServers` for Claude Desktop, Cursor and Windsurf; use a top-level `servers` key for VS Code in `.vscode/mcp.json`):

```json
{
  "mcpServers": {
    "swiss-cultural-heritage-mcp": {
      "command": "uvx",
      "args": [
        "swiss-cultural-heritage-mcp"
      ]
    }
  }
}
```
<!-- END GENERATED: install -->
