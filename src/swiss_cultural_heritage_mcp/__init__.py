"""Swiss Cultural Heritage MCP Server."""

from importlib.metadata import PackageNotFoundError, metadata, version

_DIST = "swiss-cultural-heritage-mcp"

#: Der Bezeichner dieses Servers, in der Schreibweise des Portfolios: klein,
#: mit Bindestrichen, auf `-mcp` endend. Derselbe String ist der PyPI-Name, der
#: Repo-Name, das Konsolen-Skript in `pyproject.toml` und die letzte Stufe des
#: Verzeichniseintrags (`io.github.malkreide/swiss-cultural-heritage-mcp` in
#: `server.json`).
#:
#: Er steht hier und wird nicht je Verwendungsstelle hingeschrieben. Bis zum
#: 20.09.2026 meldete `serverInfo.name` `swiss_cultural_heritage_mcp` — die
#: Schreibweise des Python-MODULS, die es als Server-Bezeichner sonst nirgends
#: gibt. Das ist dieselbe Klasse wie die ruff-Version, die einmal in einer
#: Ueberschrift «an einer Stelle» stand und doch eine Kopie war: Zwei
#: Schreibweisen desselben Namens laufen auseinander, sobald eine davon
#: gepflegt wird.
#:
#: Der Modulpfad bleibt `swiss_cultural_heritage_mcp` — Python erlaubt keine
#: Bindestriche in Paketnamen. `python -m swiss_cultural_heritage_mcp.server`
#: ist deshalb KEIN Fehlstand und wird nicht mitgezogen.
__dist__ = _DIST

try:
    __version__ = version(_DIST)
except PackageNotFoundError:  # not installed (running from source tree)
    __version__ = "0.0.0+local"

try:
    _META = metadata(_DIST)
except PackageNotFoundError:  # not installed (running from source tree)
    _META = None


def _project_url(label: str) -> str | None:
    """Eine `Project-URL`-Zeile der Paket-Metadaten, nach Label gesucht.

    Die Metadaten fuehren jede URL als ``"<Label>, <URL>"``; ``Home-page`` ist
    leer, seit `[project.urls]` die Quelle ist. Deshalb wird hier zerlegt statt
    ein einzelnes Feld gelesen.
    """
    if _META is None:
        return None
    for entry in _META.get_all("Project-URL") or ():
        name, _, url = str(entry).partition(",")
        if name.strip().lower() == label.lower():
            return url.strip() or None
    return None


#: `[project].description` aus `pyproject.toml` — die Kurzbeschreibung, die PyPI
#: zeigt UND die dieser Server als `serverInfo.description` meldet. Eine zweite,
#: von Hand gepflegte Fassung im Auslieferungspfad waere genau die Drift, gegen
#: die `scripts/check_version_sync.py` die Versionsnummer schuetzt.
__summary__: str | None = None if _META is None else _META["Summary"]

#: `[project.urls].Homepage` — Quelle fuer `serverInfo.websiteUrl` und fuer die
#: URL im User-Agent.
__homepage__: str | None = _project_url("Homepage")
