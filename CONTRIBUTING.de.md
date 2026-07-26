# Beitragen zu swiss-cultural-heritage-mcp

[🇬🇧 English Version](CONTRIBUTING.md)

Vielen Dank für Ihr Interesse an einem Beitrag! Dieser Server ist Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide).

---

## Issues melden

Nutzen Sie [GitHub Issues](https://github.com/malkreide/swiss-cultural-heritage-mcp/issues), um Fehler zu melden oder Funktionen anzufragen.

Bitte geben Sie an:
- Python-Version und Betriebssystem
- Vollständige Fehlermeldung oder Beschreibung des unerwarteten Verhaltens
- Schritte zur Reproduktion

---

## Pull Requests

1. Forken Sie das Repository
2. Erstellen Sie einen Feature-Branch: `git checkout -b feat/mein-feature`
3. Nehmen Sie Ihre Änderungen vor und ergänzen Sie Tests
4. Stellen Sie sicher, dass alle Tests bestehen: `PYTHONPATH=src pytest tests/ -m "not live"`
5. Committen Sie mit [Conventional Commits](https://www.conventionalcommits.org/): `feat: neues Tool ergänzen`
6. Pushen Sie und eröffnen Sie einen Pull Request gegen `main`

---

## Code-Stil

- Python 3.11+
- [Ruff](https://github.com/astral-sh/ruff) für Linting und Formatierung
- Type-Hints für alle öffentlichen Funktionen erforderlich
- Tests für neue Tools erforderlich (`tests/test_server.py`)
- Den bestehenden FastMCP-/Pydantic-v2-Mustern in `server.py` folgen

---

## Datenquellen

Dieser Server nutzt drei offene Schweizer Kulturerbe-APIs — alle ohne Authentifizierung:

| Quelle | Dokumentation |
|--------|--------------|
| SIK-ISEA | [www.sik-isea.ch](https://www.sik-isea.ch/) |
| Nationalmuseum (SNM) | [opendata.swiss](https://opendata.swiss/) |
| Nationalbibliothek (Helveticat) | OAI-PMH-Endpunkt |

Beim Ergänzen neuer Datenquellen gilt das **No-Auth-First**-Prinzip: Phase 1 nutzt ausschliesslich offene, authentifizierungsfreie Endpunkte. Authentifizierte APIs werden in späteren Phasen mit Graceful Degradation eingeführt.

---

## Lizenz

Mit Ihrem Beitrag erklären Sie sich damit einverstanden, dass Ihre Beiträge unter der [MIT-Lizenz](LICENSE) lizenziert werden.
