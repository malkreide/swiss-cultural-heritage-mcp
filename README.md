# swiss-cultural-heritage-mcp

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![No Auth Required](https://img.shields.io/badge/auth-none%20required-brightgreen)

> MCP Server for Swiss cultural heritage — SIK-ISEA artists, Nationalmuseum collections, and the Nationalbibliothek bibliography

[🇩🇪 Deutsche Version](README.de.md)

## Overview

`swiss-cultural-heritage-mcp` provides AI-native access to three major Swiss cultural heritage data sources, all without authentication:

| Source | Data | API |
|--------|------|-----|
| **SIK-ISEA** | 50,000+ Swiss artists (biographies, techniques, cantons) | REST/CSV |
| **Nationalmuseum (SNM)** | Museum collections (numismatics, seals, special collections) | opendata.swiss CKAN |
| **Nationalbibliothek (NB)** | Swiss national bibliography (Helveticat) | OAI-PMH |

This server completes the humanistic dimension of the Swiss public data portfolio — history, literature, and art — alongside existing servers for law ([fedlex-mcp](https://github.com/malkreide/fedlex-mcp)), transport, statistics, and more.

## Features

- 9 tools, 2 resources, 2 prompts across three data sources
- `heritage_cross_search` — parallel search across all three sources in a single call
- Bilingual output (Markdown / JSON)
- No API key required — all data under open licenses
- Dual transport: stdio (Claude Desktop) + Streamable HTTP (cloud)
- Prompt templates for art research and finding educational materials

## Tools

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

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Installation

```bash
# Clone
git clone https://github.com/malkreide/swiss-cultural-heritage-mcp.git
cd swiss-cultural-heritage-mcp

# Install
pip install -e .
# or with uv:
uv pip install -e .
```

## Usage / Quickstart

```bash
# stdio (for Claude Desktop)
python -m swiss_cultural_heritage_mcp.server

# Streamable HTTP (port 8000)
python -m swiss_cultural_heritage_mcp.server --http --port 8000

# via uvx (no installation required)
uvx swiss-cultural-heritage-mcp
```

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

Or with uvx:

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

Then ask Claude:
- *"Who is Ferdinand Hodler?"*
- *"What coins does the Nationalmuseum have from Zurich?"*
- *"Find publications about Volksschule in the Swiss national bibliography"*

## Project Structure

```
swiss-cultural-heritage-mcp/
├── src/swiss_cultural_heritage_mcp/
│   ├── __init__.py          # Package
│   └── server.py            # 9 tools, 2 resources, 2 prompts
├── tests/
│   └── test_server.py       # Unit + integration tests (mocked HTTP)
├── .github/workflows/ci.yml # GitHub Actions (Python 3.11/3.12/3.13)
├── pyproject.toml
├── README.md / README.de.md
└── CHANGELOG.md
```

## Portfolio Integration

This server pairs well with:

| Server | Synergy |
|--------|---------|
| [eth-library-mcp](https://github.com/malkreide/eth-library-mcp) | Full Swiss library coverage: ETH = science, NB = humanities |
| [fedlex-mcp](https://github.com/malkreide/fedlex-mcp) | Cultural heritage law + primary legislation |
| [zurich-opendata-mcp](https://github.com/malkreide/zurich-opendata-mcp) | Spatial-historical: museum objects + Zurich geodata |
| [swiss-statistics-mcp](https://github.com/malkreide/swiss-statistics-mcp) | Statistical context for cultural research |

## Changelog

See [CHANGELOG.md](CHANGELOG.md)

## License

MIT License — see [LICENSE](LICENSE)

## Author

Hayal Oezkan · [malkreide](https://github.com/malkreide)

*Part of the Swiss public-sector AI infrastructure portfolio.*
