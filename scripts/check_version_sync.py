"""
Versions-Synchronität prüfen — und sicherstellen, dass in `src/` keine Version
von Hand gepflegt wird.

`pyproject.toml` ist die einzige Quelle der Wahrheit. Verglichen werden alle
Stellen, die dieselbe Nummer wiederholen:

  - `server.json` (MCP-Registry-Manifest): `version` und jedes
    `packages[*].version`
  - die Versions-Badges der READMEs
  - `generated_for_version` im Tool-Pin (`audits/tool-pins/current.json`)

Hintergrund: `publish.yml` synchronisiert `server.json` beim Veröffentlichen
aus dem Tag-Namen — die *committete* Version wirkt also nie auf das
publizierte Artefakt und fällt deshalb nicht auf, wenn sie veraltet. Die
README-Badges erzwingt überhaupt nichts.

Der Tool-Pin kam am 28.10.2026 dazu, und er bekommt eine eigene Meldung statt
einer Zeile in der Liste oben. Gehalten wurde er bis dahin nur von
`tests/test_server.py::TestToolPins::test_pin_records_the_declared_version` —
das braucht die Projekt-Installation, weil es daneben die *lebenden*
Tool-Definitionen gegen die Hashes stellt. Dieser Check braucht sie nicht und
greift damit auch dort, wo das Paket nicht installiert ist: im pre-commit-Hook
(`.githooks/pre-commit`). Am 0.5.0-Bump war genau das der Fall — die Version
war gehoben, der Pin stand noch auf 0.4.0, und rot wurde es erst in der CI.

Die eigene Meldung ist kein Stil, sondern der Unterschied in der Abhilfe:
`server.json` und die Badges schreibt man von Hand nach, den Pin **nicht**.
Die Hashes neben dem Feld beschreiben die freigegebene Tool-Oberfläche; ein
von Hand nachgetragenes `generated_for_version` behauptete eine Freigabe für
eine Version, gegen die nie geprüft wurde. Ein pauschales «alle Stellen im
selben Commit bumpen» führte also genau in diesen Fehler.

Zweiter Teil: in `src/` darf keine Versionsnummer stehen. Der Laufzeit-Wert
kommt aus den Paket-Metadaten (`importlib.metadata.version()`); ein wieder
eingefügtes Literal wäre der Beginn derselben Drift, die im ganzen Portfolio
falsche User-Agents erzeugt hat.

Verwendung:
    python scripts/check_version_sync.py     # exit 1 bei Abweichung

Bewusst nur Standardbibliothek — der Check braucht keine Projekt-Installation
und läuft damit auch in schlanken CI-Jobs. Auf Python 3.10 (noch keine
`tomllib`) greift ein Minimal-Parser für die zwei benötigten Felder.
"""

import io
import json
import re
import sys
import tokenize
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 — tomllib kam erst mit 3.11
    tomllib = None

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
SERVER_JSON = ROOT / "server.json"
SRC = ROOT / "src"
TOOL_PIN = ROOT / "audits" / "tool-pins" / "current.json"

# Shields.io-Badge: ![Version](https://img.shields.io/badge/version-X.Y.Z-blue)
_BADGE = re.compile(r"img\.shields\.io/badge/[Vv]ersion-([^-\s)]+)-")


def code_lines(text: str) -> list[str]:
    """Zeilen ohne Kommentare.

    Kommentare dokumentieren im Portfolio genau die Drift, die dieser Check
    verhindern soll — etwa «the User-Agent in server.py carried
    "bakom-mcp/1.0"». Sie zu melden wäre ein Fehlalarm, der die CI grundlos
    rot färbt. Ausgeschnitten wird per `tokenize`, nicht per `split("#")`:
    ein `#` in einem String-Literal darf die Zeile nicht abschneiden.
    """
    lines = text.splitlines()
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.COMMENT:
                row, col = tok.start
                lines[row - 1] = lines[row - 1][:col]
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # Nicht parsebare Datei: lieber vollständig prüfen als still übergehen.
        return text.splitlines()
    return lines


def norm(token: str) -> str:
    """Kleingeschrieben und ohne Trennzeichen — zum Vergleich von Produkt-Token
    und Dist-Namen.

    Das Produkt-Token im User-Agent ist nicht immer der Dist-Name:
    `swisstopo-mcp` sendet `SwisstopoMCP/0.1`. Ein wörtlicher Vergleich liess
    dort ein hartkodiertes Literal als sauber durchgehen — genau das Versagen,
    gegen das dieser Check existiert.
    """
    return re.sub(r"[^a-z0-9]", "", token.lower())


# Irgendein Produkt-Token, gefolgt von einer gepunkteten Zahl. Welches davon
# uns gehört, entscheidet der normalisierte Vergleich mit dem Dist-Namen —
# fremde Token (`Mozilla/5.0`, `httpx/0.27`) fallen so heraus.
_UA = re.compile(r"""([A-Za-z][A-Za-z0-9_.+-]*)/(\d+\.\d[^\s"']*)""")


def own_ua_versions(line: str, dist: str) -> list[str]:
    """Versionen aus den User-Agents, deren Produkt-Token uns gehört.

    Eigene Funktion, damit die Zeile auch bei `line-length = 88` passt: im
    Portfolio stehen 88, 100 und 120 nebeneinander, und `ruff format` zieht
    einen Ausdruck zusammen, sobald er in die jeweilige Breite passt. Eine
    mehrzeilige Comprehension waere damit in der einen Haelfte der Repos
    formatgerecht und in der anderen nicht.
    """
    return [m.group(2) for m in _UA.finditer(line) if norm(m.group(1)) == norm(dist)]


def find_hardcoded(dist: str) -> list[tuple[str, int, str]]:
    """Manuell gepflegte Versionen in `src/`.

    Zwei Formen kommen im Portfolio vor: der User-Agent (`<token>/1.2.3`) und
    die `__version__`-Zuweisung. Die Projekt-URL trägt denselben Namen, aber
    keine Ziffer danach — deshalb verlangt das Muster eine gepunktete Zahl.

    Der Fallback im `except PackageNotFoundError`-Zweig (`0.0.0+source`) ist
    ausdrücklich **kein** Treffer: er behauptet gerade keine Version. Erkannt
    wird er am lokalen Segment nach `+`, nicht an der Zahl davor — `0.0.0`
    allein sieht wie eine echte Version aus.
    """
    hits: list[tuple[str, int, str]] = []
    if not SRC.is_dir():
        return hits

    dunder = re.compile(r"""__version__\s*=\s*["']([^"']+)["']""")

    for path in sorted(SRC.rglob("*.py")):
        for lineno, line in enumerate(code_lines(path.read_text(encoding="utf-8")), start=1):
            values = own_ua_versions(line, dist)
            for m in dunder.finditer(line):
                if re.match(r"\d+\.\d", m.group(1)):
                    values.append(m.group(1))
            if any("+" not in v for v in values):
                hits.append((str(path.relative_to(ROOT)), lineno, line.strip()))
    return hits


def collect_declared(expected: str) -> list[tuple[str, str]]:
    """Alle Stellen, die die Version wiederholen — je (Bezeichnung, Wert)."""
    found: list[tuple[str, str]] = []

    if SERVER_JSON.exists():
        server = json.loads(SERVER_JSON.read_text(encoding="utf-8"))
        found.append(("server.json → version", server.get("version", "")))
        for i, pkg in enumerate(server.get("packages", [])):
            found.append((f"server.json → packages[{i}].version", pkg.get("version", "")))

    for readme in sorted(ROOT.glob("README*.md")):
        for match in _BADGE.finditer(readme.read_text(encoding="utf-8")):
            found.append((f"{readme.name} → Versions-Badge", match.group(1)))

    return found


def tool_pin_drift(expected: str) -> str | None:
    """Beschreibt, wie der Tool-Pin von `expected` abweicht — oder None.

    Drei Befunde fallen zusammen, weil sie dieselbe Folge haben: Der Pin sagt
    nicht, zu welchem Release die freigegebene Tool-Oberfläche gehört.

    Eine **fehlende** Datei ist bewusst keiner davon, gleiche Regel wie bei
    `server.json` weiter oben: Dieser Check misst Übereinstimmung, nicht
    Vollständigkeit. Dass es den Pin überhaupt gibt, hält
    `tests/test_server.py::TestToolPins` — und das muss es auch, denn dort
    liegt die Zusicherung über die Hashes selbst.
    """
    if not TOOL_PIN.exists():
        return None
    try:
        recorded = json.loads(TOOL_PIN.read_text(encoding="utf-8")).get("generated_for_version")
    except (OSError, ValueError) as fehler:
        # `json.JSONDecodeError` ist eine `ValueError`-Unterklasse; der weitere
        # Fang nimmt auch einen Pin mit, der kein Objekt ist (dann hat er kein
        # `.get` -> AttributeError). Den braucht es hier mit:
        return f"ist nicht als Pin lesbar ({fehler})"
    except AttributeError:
        return "enthält kein JSON-Objekt"
    if recorded is None:
        return "führt kein Feld `generated_for_version`"
    if recorded != expected:
        return f"ist für {recorded!r} erzeugt"
    return None


def read_project() -> dict:
    """`[project]`-Tabelle aus pyproject.toml.

    Ohne `tomllib` (Python 3.10) genügt hier ein Minimal-Parser: gebraucht
    werden nur `name` und `version`, beides einfache Strings direkt unter
    `[project]`. Eine Abhängigkeit auf `tomli` einzuführen, nur damit ein
    Check laufen kann, wäre unverhältnismässig.
    """
    text = PYPROJECT.read_text(encoding="utf-8")
    if tomllib is not None:
        return tomllib.loads(text)["project"]

    section = re.search(r"^\[project\]\s*$(.*?)(?=^\[)", text, re.MULTILINE | re.DOTALL)
    body = section.group(1) if section else text
    out = {}
    for key in ("name", "version"):
        m = re.search(rf'^{key}\s*=\s*"([^"]+)"', body, re.MULTILINE)
        if m:
            out[key] = m.group(1)
    return out


def main() -> None:
    project = read_project()
    dist = project["name"]
    version = project.get("version")

    if version is None:
        # `dynamic = ["version"]`: die Version entsteht beim Bauen, ein
        # Literal in src/ ist dort die Quelle und kein Fehler.
        print("Versions-Sync übersprungen: pyproject.toml nutzt eine dynamische Version.")
        return

    found = collect_declared(version)
    mismatches = [(where, value) for where, value in found if value != version]
    if mismatches:
        print(
            f"DRIFT: pyproject.toml steht auf {version!r}, folgende Stellen weichen ab:",
            file=sys.stderr,
        )
        for where, value in mismatches:
            print(f"  {where} = {value!r}", file=sys.stderr)
        print(
            "\nAlle Stellen im selben Commit bumpen. Hinweis: publish.yml "
            "überschreibt server.json beim Veröffentlichen ohnehin aus dem Tag — "
            "die committete Version bleibt trotzdem die, die Menschen lesen.",
            file=sys.stderr,
        )
        sys.exit(1)

    drift = tool_pin_drift(version)
    if drift is not None:
        stelle = TOOL_PIN.relative_to(ROOT)
        print(
            f"TOOL-PIN: {stelle} {drift}, pyproject.toml steht auf {version!r}.",
            file=sys.stderr,
        )
        print(
            "\nDas Feld NICHT von Hand nachtragen: Die Hashes daneben "
            "beschreiben die freigegebene Tool-Oberfläche, und ein "
            "nachgeschriebenes `generated_for_version` behauptete eine "
            "Freigabe für eine Version, gegen die nie geprüft wurde. Im "
            "selben Commit wie den Bump neu erzeugen:\n"
            "    PYTHONPATH=src python scripts/pin_tools.py",
            file=sys.stderr,
        )
        sys.exit(1)

    hardcoded = find_hardcoded(dist)
    if hardcoded:
        print("HARDCODED: Versionsnummer in src/ gefunden:", file=sys.stderr)
        for path, lineno, line in hardcoded:
            print(f"  {path}:{lineno}: {line}", file=sys.stderr)
        print(
            "\nDie Laufzeit-Version kommt aus den Paket-Metadaten "
            "(`__version__`, gespeist aus importlib.metadata). Statt eines "
            "Literals von dort lesen — sonst beginnt dieselbe Drift von vorn.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Die Ausgabe nennt jede geprüfte Stelle. Sonst sieht ein grüner Lauf
    # genauso aus, wenn eine Stelle stillschweigend herausfällt — etwa weil
    # eine Datei umbenannt wurde und der Check sie seither überspringt.
    checked = [where for where, _ in found]
    if TOOL_PIN.exists():
        checked.append(f"{TOOL_PIN.relative_to(ROOT)} → generated_for_version")
    stellen = ", ".join(checked) or "keine weiteren Stellen"
    print(f"Versions-Sync OK ({version}; geprüft: {stellen}; keine hartkodierte Version in src/)")


if __name__ == "__main__":
    main()
