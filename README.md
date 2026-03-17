> 🇨🇭 **Part of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide)**

# 🏛️ swiss-cultural-heritage-mcp

![Version](https://img.shields.io/badge/version-0.1.0-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)](https://modelcontextprotocol.io/)
[![No Auth Required](https://img.shields.io/badge/auth-none%20required-brightgreen)](https://github.com/malkreide/swiss-cultural-heritage-mcp)

> MCP Server for Swiss cultural heritage — SIK-ISEA artists, Nationalmuseum collections, and the Nationalbibliothek bibliography

[🇩🇪 Deutsche Version](README.de.md)

---

## Overview

`swiss-cultural-heritage-mcp` provides AI-native access to three major Swiss cultural heritage data sources, all without authentication:

| Source | Data | API |
|--------|------|-----|
| **SIK-ISEA** | 50,000+ Swiss artists (biographies, techniques, cantons) | REST/CSV |
| **Nationalmuseum (SNM)** | Museum collections (numismatics, seals, special collections) | opendata.swiss CKAN |
| **Nationalbibliothek (NB)** | Swiss national bibliography (Helveticat) | OAI-PMH |

This server completes the humanistic dimension of the Swiss public data portfolio — history, literature, and art — alongside existing servers for law ([fedlex-mcp](https://github.com/malkreide/fedlex-mcp)), transport, statistics, and more.

**Anchor demo query:** *"Find works by Zurich-based painters from the 19th century in the Nationalmuseum, and cross-reference with their biography in the SIK-ISEA artist database."*

---

## Features

- 🏛️ **9 tools, 2 resources, 2 prompts** across three data sources
- 🔍 **`heritage_cross_search`** — parallel search across all three sources in a single call
- 🌐 **Bilingual output** (Markdown / JSON)
- 🔓 **No API key required** — all data under open licenses
- ☁️ **Dual transport** — stdio (Claude Desktop) + Streamable HTTP (cloud)
- 📚 **Prompt templates** for art research and finding educational materials

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
3. Set start command: `python -m swiss_cultural_heritage_mcp.server --http --port 8000`
4. In claude.ai under Settings → MCP Servers, add: `https://your-app.onrender.com/sse`

> 💡 *"stdio for the developer laptop, SSE for the browser."*

---

## Available Tools

### SIK-ISEA (Swiss Art Research)

| Tool | Description |
|------|-------------|
| `heritage_search_artists` | Search 50,000+ Swiss artists by name, region, period, technique |
| `heritage_get_artist` | Full artist profile by SIK-ISEA ID |

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

### Example Use Cases

| Query | Tool |
|-------|------|
| *"Who is Ferdinand Hodler?"* | `heritage_get_artist` |
| *"Find 19th-century painters from canton Bern"* | `heritage_search_artists` |
| *"What coins from Zurich does the Nationalmuseum have?"* | `heritage_browse_collection` |
| *"Find publications about Volksschule"* | `heritage_search_helveticat` |
| *"Search for everything about Sophie Taeuber-Arp"* | `heritage_cross_search` |

---

## Architecture

```
┌─────────────────┐     ┌──────────────────────────────┐     ┌──────────────────────────┐
│   Claude / AI   │────▶│  Swiss Cultural Heritage MCP  │────▶│  SIK-ISEA                │
│   (MCP Host)    │◀────│  (MCP Server)                │◀────│  REST/CSV                │
└─────────────────┘     │                              │     ├──────────────────────────┤
                        │  9 Tools · 2 Resources       │────▶│  Nationalmuseum (SNM)    │
                        │  2 Prompts                   │◀────│  opendata.swiss / CKAN   │
                        │  Stdio | SSE                 │     ├──────────────────────────┤
                        │                              │────▶│  Nationalbibliothek (NB) │
                        │  No authentication required  │◀────│  OAI-PMH (Helveticat)    │
                        └──────────────────────────────┘     └──────────────────────────┘
```

### Data Source Characteristics

| Source | Protocol | Coverage | Auth |
|--------|----------|----------|------|
| SIK-ISEA | REST/CSV | 50,000+ Swiss artists | None |
| Nationalmuseum | CKAN DataStore | Museum collections | None |
| Nationalbibliothek | OAI-PMH | Swiss national bibliography | None |

---

## Project Structure

```
swiss-cultural-heritage-mcp/
├── src/swiss_cultural_heritage_mcp/
│   ├── __init__.py              # Package
│   └── server.py                # 9 tools, 2 resources, 2 prompts
├── tests/
│   └── test_server.py           # Unit + integration tests (mocked HTTP)
├── .github/workflows/ci.yml     # GitHub Actions (Python 3.11/3.12/3.13)
├── pyproject.toml
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md                    # This file (English)
└── README.de.md                 # German version
```

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
```

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

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
