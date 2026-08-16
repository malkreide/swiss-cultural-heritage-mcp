# Contributing to swiss-cultural-heritage-mcp

Thank you for your interest in contributing! This server is part of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide).

---

## Reporting Issues

Use [GitHub Issues](https://github.com/malkreide/swiss-cultural-heritage-mcp/issues) to report bugs or request features.

Please include:
- Python version and OS
- Full error message or description of unexpected behaviour
- Steps to reproduce

---

## Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Install the dev dependencies: `pip install -e ".[dev]"` — this is also what pins ruff to the version CI uses (see [Code Style](#code-style))
4. Make your changes and add tests
5. Ensure all tests pass: `PYTHONPATH=src pytest tests/ -m "not live"`
6. Commit using [Conventional Commits](https://www.conventionalcommits.org/): `feat: add new tool`
7. Push and open a Pull Request against `main`

---

## Code Style

- Python 3.11+
- [Ruff](https://github.com/astral-sh/ruff) for linting and formatting
- Type hints required for all public functions
- Tests required for new tools (`tests/test_server.py`)
- Follow the existing FastMCP / Pydantic v2 patterns in `server.py`

**Ruff is pinned to an exact version**, in `pyproject.toml` under
`[project.optional-dependencies] dev` — that one line is the only place the
version is written down, and CI installs no ruff of its own. So run the lint
gates from the same `pip install -e ".[dev]"` environment, and do not
`pip install -U ruff` on top of it: a newer ruff changes the rule set and the
formatter, and will report differences on untouched code that nobody
introduced. The two gates, exactly as CI runs them:

```bash
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
```

To bump ruff, change that one line in `pyproject.toml` and reformat in the same
pull request, so the diff shows what the new version actually changed.

---

## Data Sources

This server uses three open Swiss cultural heritage APIs — all without authentication:

| Source | Documentation |
|--------|--------------|
| SIK-ISEA | [www.sik-isea.ch](https://www.sik-isea.ch/) |
| Nationalmuseum (SNM) | [opendata.swiss](https://opendata.swiss/) |
| Nationalbibliothek (Helveticat) | OAI-PMH endpoint |

When adding new data sources, follow the **No-Auth-First** principle: Phase 1 uses only open, authentication-free endpoints. Authenticated APIs are introduced in later phases with graceful degradation.

---

## The live suite: when it runs, and who sees a red result

**Cadence:** daily at 04:17 UTC, plus on demand via *Actions → Nightly Live Tests → Run
workflow*. See [`.github/workflows/nightly-live.yml`](.github/workflows/nightly-live.yml).

**Who sees it:** A red run opens an issue labelled `nightly-live-failure` (title: “Nightly live tests failing against upstream APIs”). A second red run recognises the open issue **by its label**, not by its title, and appends to that same thread. Remove the label by hand and the next red run opens a second issue. A green run does **not** close the issue by itself — once the failure is fixed it needs closing by hand, otherwise the next reader mistakes the old failure for the new one.

**A red live run does not necessarily mean *our* bug.** It means the contract
with the source has changed, or the source is down. Both belong seen; only the
first belongs fixed. Please read the run before disabling the job — that is how
this check dies, and it is the only one in the repository that can contradict a
wrong assumption about the upstream APIs (Memobase, Dodis, Helveticat). Every other test asserts against a fixture, and
the fixture was written from the same assumption as the code.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
