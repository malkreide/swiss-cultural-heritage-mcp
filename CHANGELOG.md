# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
