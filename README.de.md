[🇬🇧 English Version](README.md)

# swiss-cultural-heritage-mcp

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![Lizenz](https://img.shields.io/badge/Lizenz-MIT-green)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Kein API-Schlüssel](https://img.shields.io/badge/Auth-keiner%20erforderlich-brightgreen)

> MCP-Server für Schweizer Kulturerbe — SIK-ISEA Künstler·innen, Nationalmuseum-Sammlungen und Nationalbibliothek-Bibliografie

## Übersicht

`swiss-cultural-heritage-mcp` ermöglicht KI-Assistenten den direkten Zugang zu drei grossen Schweizer Kulturerbe-Quellen — alle ohne Authentifizierung:

| Quelle | Daten | API |
|--------|-------|-----|
| **SIK-ISEA** | 50'000+ Schweizer Künstler·innen (Biografien, Techniken, Kantone) | REST/CSV |
| **Nationalmuseum (SNM)** | Sammlungsdaten (Numismatik, Siegel, Spezialsammlungen) | opendata.swiss CKAN |
| **Nationalbibliothek (NB)** | Schweizerische Nationalbibliografie (Helveticat) | OAI-PMH |

Dieser Server ergänzt das Schweizer Open-Data-Portfolio um die geisteswissenschaftliche Dimension — Geschichte, Literatur und Kunst — neben bestehenden Servern für Recht, Verkehr, Statistik und mehr.

## Funktionen

- 9 Tools, 2 Resources, 2 Prompts über drei Datenquellen
- `heritage_cross_search` — parallele Suche über alle drei Quellen in einem Aufruf
- Zweisprachige Ausgabe (Markdown / JSON)
- Kein API-Schlüssel erforderlich — alle Daten unter offenen Lizenzen
- Dualer Transport: stdio (Claude Desktop) + Streamable HTTP (Cloud)
- Prompt-Vorlagen für Künstler-Recherche und Bildungsressourcen

## Tools

### SIK-ISEA (Schweizer Kunstwissenschaft)
| Tool | Beschreibung |
|------|-------------|
| `heritage_search_artists` | 50'000+ Künstler·innen nach Name, Region, Epoche, Technik suchen |
| `heritage_get_artist` | Vollständiges Künstler·innen-Profil nach SIK-ISEA-ID |

### Nationalmuseum (SNM)
| Tool | Beschreibung |
|------|-------------|
| `heritage_search_museum_datasets` | SNM-Datensätze auf opendata.swiss suchen |
| `heritage_browse_collection` | Objekte in einer Sammlung via CKAN DataStore durchsuchen |

### Nationalbibliothek (NB)
| Tool | Beschreibung |
|------|-------------|
| `heritage_search_helveticat` | Schweizerische Nationalbibliografie via OAI-PMH durchsuchen |
| `heritage_list_nb_collections` | Verfügbare OAI-PMH-Sets auflisten |
| `heritage_get_publication` | Vollständige Dublin-Core-Metadaten einer Publikation |

### Quellenübergreifend
| Tool | Beschreibung |
|------|-------------|
| `heritage_cross_search` | Parallele Suche über SIK-ISEA + SNM + NB |

## Voraussetzungen

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (empfohlen) oder pip

## Installation

```bash
# Klonen
git clone https://github.com/malkreide/swiss-cultural-heritage-mcp.git
cd swiss-cultural-heritage-mcp

# Installieren
pip install -e .
# oder mit uv:
uv pip install -e .
```

## Verwendung

```bash
# stdio (für Claude Desktop)
python -m swiss_cultural_heritage_mcp.server

# Streamable HTTP (Port 8000)
python -m swiss_cultural_heritage_mcp.server --http --port 8000

# via uvx (ohne Installation)
uvx swiss-cultural-heritage-mcp
```

## Konfiguration

### Claude Desktop

Editiere `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) bzw. `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

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

Danach kannst du in Claude fragen:
- *«Wer ist Ferdinand Hodler?»*
- *«Welche Münzen aus Zürich hat das Nationalmuseum?»*
- *«Finde Publikationen zur Volksschule in der Nationalbibliothek»*
- *«Zeige mir Schweizer Künstlerinnen des 19. Jahrhunderts aus dem Kanton Bern»*

## Projektstruktur

```
swiss-cultural-heritage-mcp/
├── src/swiss_cultural_heritage_mcp/
│   ├── __init__.py          # Package
│   └── server.py            # 9 Tools, 2 Resources, 2 Prompts
├── tests/
│   └── test_server.py       # Unit + Integrationstests (gemockt)
├── .github/workflows/ci.yml # GitHub Actions (Python 3.11/3.12/3.13)
├── pyproject.toml
├── README.md / README.de.md
└── CHANGELOG.md
```

## Portfolio-Integration

Dieser Server ergänzt optimal:

| Server | Synergie |
|--------|---------|
| [eth-library-mcp](https://github.com/malkreide/eth-library-mcp) | Vollständige Bibliotheksabdeckung: ETH = Naturwiss., NB = Geisteswiss. |
| [fedlex-mcp](https://github.com/malkreide/fedlex-mcp) | Kulturgüterrecht + Primärgesetzgebung |
| [zurich-opendata-mcp](https://github.com/malkreide/zurich-opendata-mcp) | Räumlich-historisch: Museumsobjekte + Zürich-Geodaten |
| [swiss-statistics-mcp](https://github.com/malkreide/swiss-statistics-mcp) | Statistischer Kontext für Kulturforschung |

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md)

## Lizenz

MIT-Lizenz — siehe [LICENSE](LICENSE)

## Autor·in

Hayal Oezkan · [malkreide](https://github.com/malkreide)

*Teil des Schweizer Open-Data-Portfolios für öffentliche KI-Infrastruktur.*
