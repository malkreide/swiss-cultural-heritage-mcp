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
3. Installieren Sie die Dev-Abhängigkeiten: `pip install -e ".[dev]"` — damit kommt auch die ruff-Version, die die CI verwendet (siehe [Code-Stil](#code-stil))
4. Nehmen Sie Ihre Änderungen vor und ergänzen Sie Tests
5. Stellen Sie sicher, dass alle Tests bestehen: `PYTHONPATH=src pytest tests/ -m "not live"`
6. Committen Sie mit [Conventional Commits](https://www.conventionalcommits.org/): `feat: neues Tool ergänzen`
7. Pushen Sie und eröffnen Sie einen Pull Request gegen `main`

---

## Code-Stil

- Python 3.11+
- [Ruff](https://github.com/astral-sh/ruff) für Linting und Formatierung
- Type-Hints für alle öffentlichen Funktionen erforderlich
- Tests für neue Tools erforderlich (`tests/test_server.py`)
- Den bestehenden FastMCP-/Pydantic-v2-Mustern in `server.py` folgen

**Ruff ist exakt gepinnt**, in `pyproject.toml` unter
`[project.optional-dependencies] dev` — diese eine Zeile ist die einzige
Stelle, an der die Version steht, und die CI installiert kein eigenes ruff.
Fahren Sie die Lint-Gates deshalb aus derselben `pip install -e ".[dev]"`-
Umgebung und setzen Sie kein `pip install -U ruff` darüber: Ein neueres ruff
ändert Regelsatz und Formatter und meldet dann auf unberührtem Code
Abweichungen, die niemand verursacht hat. Die zwei Gates, wörtlich wie in der
CI:

```bash
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
```

Für einen ruff-Wechsel diese eine Zeile in `pyproject.toml` ändern und im
selben Pull Request neu formatieren — so zeigt der Diff, was die neue Version
tatsächlich geändert hat.

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

## Die Live-Suite: wann sie läuft, und wer ein rotes Ergebnis sieht

**Kadenz:** täglich um 04:17 UTC, dazu jederzeit von Hand über *Actions → Nightly Live Tests → Run
workflow*. Siehe [`.github/workflows/nightly-live.yml`](.github/workflows/nightly-live.yml).

**Wer es sieht:** Ein roter Lauf öffnet ein Issue mit dem Label `nightly-live-failure` (Titel: «Nightly live tests failing against upstream APIs»). Ein zweiter roter Lauf erkennt das offene Issue **am Label**, nicht am Titel, und hängt sich an denselben Thread. Wer das Label von Hand entfernt, bekommt beim nächsten roten Lauf ein zweites Issue. Ein grüner Lauf schliesst das Issue **nicht** von selbst — nach einem behobenen Ausfall gehört es von Hand zugemacht, sonst hält der nächste Blick den alten Ausfall für den neuen.

**Ein roter Live-Lauf heisst nicht zwingend «unser Fehler».** Er heisst: Der
Vertrag mit der Quelle hat sich geändert, oder die Quelle ist gerade aus. Beides
gehört gesehen, nur das Erste gehört gefixt. Bitte den Lauf lesen, bevor der Job
deaktiviert wird — so stirbt dieser Check, und er ist der einzige im Repo, der
einer falschen Grundannahme über die Upstream-APIs (Memobase, Dodis, Helveticat) widersprechen kann. Jeder andere Test
prüft gegen eine Fixture, und die Fixture ist aus derselben Annahme geschrieben
wie der Code.

## Lizenz

Mit Ihrem Beitrag erklären Sie sich damit einverstanden, dass Ihre Beiträge unter der [MIT-Lizenz](LICENSE) lizenziert werden.
