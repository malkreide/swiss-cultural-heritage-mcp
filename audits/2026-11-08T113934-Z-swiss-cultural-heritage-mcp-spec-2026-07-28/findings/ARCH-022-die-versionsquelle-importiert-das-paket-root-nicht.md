## Finding: ARCH-022 — Die Versionsquelle importiert das Paket-Root nicht

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | advisory |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `ARCH-022` |
| **PDF-Reference** | Custom (Portfolio-Fundstücke i14y-mcp / bag-health-mcp, 2026-08-03) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Doppelmessung in je frischen Interpretern: beide gelingen, das Konsolen-Skript (kalter Pfad) startet mit korrekter Version. Statisch kein Zyklus, weil der Root ein Blatt ist. Die verlangte Struktur (_version.py, kein Rueckgriff auf den Root) fehlt aber, und damit ist die Zyklusfreiheit eine Eigenschaft des heutigen __init__.py, nicht der Architektur -> partial.

### Expected Behavior

Aus dem Katalog (`checks/ARCH-022.md`, Pass Criteria):

- [ ] Die Version steht in einem eigenen Modul (`_version.py` o. ä.), das **nichts** aus dem eigenen Paket importiert
- [ ] Kein Submodul liest `__version__` aus dem Paket-Root
- [ ] Das Paket-Root liest die Version ebenfalls aus diesem Modul, statt sie selbst zu ermitteln
- [ ] Die Korrektheit hängt **nicht** an der Reihenfolge der Zeilen in `__init__.py`
- [ ] KALT (Submodul zuerst) und WARM (Root zuerst) wurden in je **frischen** Interpretern gemessen, und **beide** Ergebnisse stehen in der Evidenz
- [ ] Der Pfad des deklarierten Konsolen-Skripts wurde bestimmt und mitgemessen — er ist der kalte
- [ ] Ein einzelner Lauf wurde **nicht** als Beleg für «kein Zyklus» gewertet
- [ ] Sofern ein Test die Eigenschaft hält: Er importiert in einem eigenen Prozess, nicht innerhalb der laufenden Suite

### Evidence

- src/swiss_cultural_heritage_mcp/__init__.py:3,26-29 — Root ermittelt __version__ selbst via importlib.metadata.version; rg '^\s*(from \.|import \.|from swiss_cultural_heritage_mcp)' __init__.py -> exit 1: der Root importiert nichts aus dem eigenen Paket (Negativkontrolle: dasselbe Muster trifft server.py:46).
- server.py:46 'from . import __dist__, __homepage__, __summary__, __version__' — ein Submodul liest die Version aus dem Paket-Root; _version.py existiert nicht (ls: No such file).
- KALT (frischer Interpreter, Submodul zuerst): python -c 'import swiss_cultural_heritage_mcp.server as m; print(m.__version__, m.USER_AGENT)' -> 'KALT ok: 0.7.0 swiss-cultural-heritage-mcp/0.7.0 (+https://github.com/malkreide/swiss-cultural-heritage-mcp)', kalt_exit=0.
- WARM (frischer Interpreter, Root zuerst): python -c 'import swiss_cultural_heritage_mcp as p; import swiss_cultural_heritage_mcp.server as m; ...' -> 'WARM ok: 0.7.0 0.7.0', warm_exit=0. Zusaetzlich _toolpins kalt -> exit 0.
- Konsolen-Skript-Pfad: pyproject.toml [project.scripts] swiss-cultural-heritage-mcp = 'swiss_cultural_heritage_mcp.server:mcp.run' (kalter Pfad); gemessen ueber swiss-cultural-heritage-mcp.exe (stdio-Probe) -> serverInfo.version 0.7.0.

### Gaps

- Kein eigenes Blatt-Modul fuer die Version; server.py liest __version__ aus dem Root (Kriterien 1-3 woertlich verfehlt). Heute kein Zyklus, weil __init__.py keine Submodule importiert — sobald jemand das uebliche 'from .server import mcp' in den Root setzt, haengt die Korrektheit an der Zeilenreihenfolge.
- Kein Test haelt den kalten Importpfad in einem eigenen Prozess fest (konditionales Kriterium; nicht vorhanden).

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

`IDENT-002` sagt, **woher** die Version kommt: aus den Paket-Metadaten, nicht aus einem Literal. Dieser Check betrifft die Frage danach — **wo** dieser Wert steht und wer ihn holen darf, ohne einen Zyklus zu bauen.

**Der Fall** (`i14y-mcp`): Das Submodul `client` braucht die Version für seinen User-Agent (`IDENT-001`). Es holt sie so:

```python
# src/i14y_mcp/client.py
from i14y_mcp import __version__          # aus dem Paket-Root
```

Das Paket-Root sieht so aus:

```python
# src/i14y_mcp/__init__.py
__version__ = _distribution_version("i14y-mcp")
from .server import mcp                   # und server importiert client
```

Damit läuft der Import im Kreis: Root → `server` → `client` → Root. Dass es trotzdem funktioniert, hängt an einer einzigen Eigenschaft dieser Datei — dass `__version__` **oberhalb** von `from .server import mcp` steht. Beim Rückgriff aus `client` ist das Root-Modul erst halb initialisiert; gefunden wird nur, was bis dahin zugewiesen wurde.

> Die Version aus einem halb initialisierten Root zu ziehen hält, bis jemand zwei Zeilen umsortiert.

Und das Umsortieren ist genau die Art Änderung, die durch jedes Review geht: Importe nach oben, Zuweisungen nach unten — die Konvention, die fast jeder Formatierer und fast jede Stilfibel nahelegt. Der Zyklus bricht dann sofort und vollständig, mit einem `ImportError`, der auf `client.py` zeigt und nichts über seine Ursache sagt.

`bag-health-mcp` trägt dieselbe Form. Beide sind bestätigt.

### Die Lösung ist ein eigenes Modul

```python
# src/i14y_mcp/_version.py — importiert nichts aus dem eigenen Paket
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _distribution_version

try:
    __version__ = _distribution_version("i14y-mcp")
except PackageNotFoundError:
    __version__ = "0.0.0+source"
```

Root und Submodule lesen beide von dort:

```python
# src/i14y_mcp/__init__.py
from ._version import __version__

# src/i14y_mcp/client.py
from ._version import __version__
```

`_version.py` ist ein **Blatt** im Importgraphen: Es importiert nichts aus dem eigenen Paket, also kann kein Pfad durch es hindurch zurückführen. Damit ist die Reihenfolge der Zeilen im Root keine tragende Eigenschaft mehr, sondern wieder das, wonach sie aussieht — Formatierung.

Das ist auch der Unterschied zu `IDENT-002`. Dessen Kriterium «Versionsblock steht **vor** den Submodul-Importen» beschreibt, wie man mit dem Zyklus lebt. Dieser Check entfernt ihn.

### Die Doppelmessung — und warum sie in den Check gehört

Ein Zyklus ist keine Eigenschaft, die man einem Importfehler ansieht. Ein einzelner Lauf, der scheitert, kann auch ein Artefakt der Reihenfolge sein: falsches Arbeitsverzeichnis, unvollständige Installation, ein `sys.path`, der ein anderes Paket zuerst findet. Und ein einzelner Lauf, der **gelingt**, sagt noch weniger — er hat womöglich nur den günstigen Pfad genommen.

Deshalb wird zweimal gemessen, jedes Mal in einem **frischen Interpreter**:

| Messung | Was importiert wird | Was sie zeigt |
|---|---|---|
| **KALT** | das Submodul zuerst (`import pkg.client`) | Der Root wird erst durch diesen Import initialisiert. Der Rückgriff aus `client` trifft ihn halb fertig — hier schlägt ein echter Zyklus zu |
| **WARM** | das Root zuerst (`import pkg`, dann `pkg.client`) | Der Root ist vollständig, `__version__` liegt vor. Ein echter Zyklus ist hier **unsichtbar** |

Erst der Vergleich trägt die Aussage:

- **KALT scheitert, WARM gelingt** → echter Zyklus. Das Ergebnis hängt daran, wer zuerst importiert — also an der Aufrufreihenfolge des Konsolen-Skripts, die kein Test festhält.
- **Beide scheitern** → kein Zyklus, sondern ein kaputter Aufbau. Der Befund liegt woanders (Installation, Pfad, Paketname).
- **Beide gelingen** → kein Befund aus dieser Messung. Der statische Pfad in Modus 2 kann trotzdem einen Zyklus zeigen, der heute nur nicht getroffen wird.

**Diese Unterscheidung ist der Grund, warum der Check existiert, und ich habe sie zuerst nicht gemacht.** Der `bag-health-mcp`-Befund wurde beim ersten Durchgang als Reihenfolge-Artefakt abgetan — auf Basis eines einzigen warmen Laufs, der erwartungsgemäss grün war. Erst der kalte Lauf im frischen Interpreter zeigte den Zyklus. Ein einzelner Lauf beantwortet diese Frage nicht, egal wie er ausgeht.

### Positivbeispiel

```
src/pkg/
├── __init__.py     from ._version import __version__
│                   from .server import mcp
├── _version.py     importiert nur importlib.metadata      ← Blatt
├── server.py       from ._version import __version__
└── client.py       from ._version import __version__
```

KALT und WARM liefern beide dieselbe Version; die Zeilenreihenfolge im Root trägt nichts.

### Negativbeispiel

```
src/pkg/
├── __init__.py     __version__ = _distribution_version("pkg")   ← muss oben stehen
│                   from .server import mcp
├── server.py       from .client import Client
└── client.py       from pkg import __version__                  ← zurück ins Root
```

KALT scheitert, sobald die beiden Zeilen im Root tauschen:

```
ImportError: cannot import name '__version__' from partially initialized
module 'pkg' (most likely due to a circular import)
```

WARM gelingt weiterhin — deshalb findet ein Test, der irgendwo vorher `import pkg` gemacht hat, diesen Fehler nie.

### Remediation

Aus dem Katalog (`checks/ARCH-022.md`, Remediation), auf die Gaps oben anzuwenden:

```diff
+ # src/pkg/_version.py  (neu — Blatt im Importgraphen)
+ from importlib.metadata import PackageNotFoundError
+ from importlib.metadata import version as _distribution_version
+
+ try:
+     __version__ = _distribution_version("<dist-name>")
+ except PackageNotFoundError:
+     __version__ = "0.0.0+source"
```

```diff
  # src/pkg/__init__.py
- __version__ = _distribution_version("<dist-name>")
+ from ._version import __version__
  from .server import mcp
```

```diff
  # src/pkg/client.py
- from pkg import __version__
+ from ._version import __version__
```

Danach die Doppelmessung erneut, in frischen Interpretern — und diesmal muss KALT ebenso gelingen wie WARM. Ein Fix, der nur warm belegt ist, ist nicht belegt.

### Effort Estimate

Katalog-Richtwert (checks/ARCH-022.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — Eine neue Datei und zwei geänderte Importzeilen. Die Zeit geht in die Doppelmessung und darin, den Pfad des Konsolen-Skripts tatsächlich zu bestimmen statt anzunehmen.
