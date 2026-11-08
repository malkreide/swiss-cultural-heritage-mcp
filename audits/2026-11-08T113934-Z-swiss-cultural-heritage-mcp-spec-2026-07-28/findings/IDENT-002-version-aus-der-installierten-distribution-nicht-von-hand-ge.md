## Finding: IDENT-002 — __version__ aus der installierten Distribution, nicht von Hand gepflegt

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `IDENT-002` |
| **PDF-Reference** | Custom (Portfolio-Sweep 2026-07-29, 30 Server) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Kern (Ableitung aus Metadaten, kein Literal in src/ und tests/) erfuellt. Aus diesem Check wird nichts ueber das publizierte Paket geschlossen (dafuer IDENT-001/006).

### Expected Behavior

Aus dem Katalog (`checks/IDENT-002.md`, Pass Criteria):

- [ ] `__version__` wird über `importlib.metadata.version()` (bzw. das Sprach-Äquivalent) gelesen
- [ ] Kein Versionsliteral unter `src/` ausser dem Fallback-Marker (IDENT-005)
- [ ] **Kein Versionsliteral unter `tests/`** — ein Test, der die Nummer festnagelt, ist selbst eine Versions-Stelle
- [ ] Der Versions-Test vergleicht eine **Invariante** zwischen zwei unabhängig gepflegten Stellen (`__version__` gegen `server.json`), nicht `__version__` gegen eine aufgeschriebene Zahl
- [ ] Dieser Test wurde durch **Verstimmen von `server.json`** einmal rot gesehen — sonst ist unbelegt, dass er greift
- [ ] Ein Test vergleicht die installierten Metadaten gegen `pyproject.toml`
- [ ] Die Fehlermeldung dieses Tests nennt den Editable-Install-Fall
- [ ] Der Test wird ohne Installation **übersprungen**, nicht rot (sonst scheitert er im reinen Quell-Checkout)
- [ ] Bei Submodul-Importen in `__init__.py`: Versionsblock steht **vor** ihnen (Zirkelimport)
- [ ] Aus dem Bestehen dieses Checks wurde **nicht** auf die Identität des publizierten Pakets geschlossen — dafür sind `IDENT-001` (Modus 3) und `IDENT-006` zuständig

### Evidence

- src/swiss_cultural_heritage_mcp/__init__.py:3,26-29 — __version__ = version('swiss-cultural-heritage-mcp'), except PackageNotFoundError → '0.0.0+local'; Versionsblock steht vor jedem Submodul-Import (__init__ importiert kein Submodul)
- grep -rnE '__version__\s*=\s*"[0-9]+\.[0-9]' src/ → nur __init__.py:29 '0.0.0+local' (Fallback mit '+'); kein Literal sonst
- grep -rnE '__version__\s*==\s*"[0-9]+\.[0-9]|==\s*"v?[0-9]+\.[0-9]+\.[0-9]+"' tests/ → exit 1; negative Kontrolle 'assert __version__ == "0.3.0"' trifft (exit 0)
- tests/test_server_identity.py:197-202 — vergleicht die gemeldete serverInfo.version (aus den installierten Metadaten) gegen pyproject.toml; Fehlermeldung nennt 'pip install -e ".[dev]"' (Editable-Fall). Lauf: 33 passed (test_server_identity.py + TestPackageMetadata)
- Invariante gegen server.json: scripts/check_version_sync.py vergleicht pyproject ↔ server.json (version, packages[*]); verstimmt in Kopie (packages[0]=0.6.0) → 'DRIFT ... server.json -> packages[0].version = 0.6.0' exit 1
- Laufzeit: Audit-venv (editable) meldet __version__ 0.7.0 = pyproject 0.7.0; Index-Artefakt meldet 0.6.0 = installierte 0.6.0

### Gaps

- low: kein Test, der __version__ direkt gegen server.json haelt; die Invariante liegt im Gate-Skript (pyproject ↔ server.json), nicht im Test
- low: tests/test_server_identity.py wird ohne Installation nicht uebersprungen — im reinen Quell-Checkout faellt __version__ auf 0.0.0+local und der Test waere rot statt skip
- tests/test_server.py:463-467 (TestPackageMetadata) prueft nur 'nicht leer' — wirkungslos, aber harmlos

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

`__version__` im Paket-Root ist die naheliegende Quelle für jede Integration, die wissen will, welche Serverversion läuft. Wird der Wert von Hand gepflegt, driftet er — und zwar unbemerkter als der User-Agent, weil er oft nirgends ausgewertet wird und deshalb nie auffällt.

Der Portfolio-Sweep vom 2026-07-29 fand **20 von 30 Servern** mit abgedriftetem `__version__`:

| Server | `__version__` | Paket |
|---|---|---|
| `bag-epl-mcp` | 0.2.0 | **1.0.1** (volle Major-Version) |
| `zurich-opendata-mcp` | 0.2.0 | 0.5.1 (drei Minor-Bumps) |
| `swiss-efv-mcp` | 0.1.0 | 0.3.0 |
| `swiss-environment-mcp` | 0.1.0 | 0.5.1 (seit dem Initial-Release nie mitgezogen) |

Der letzte Fall ist der aufschlussreichste: Der Wert stand seit dem ersten Release unverändert auf `0.1.0`, während das Paket bei `0.5.1` lag. Niemand hatte ihn je ausgewertet — was ihn nicht harmlos macht, sondern nur unentdeckt.

`pyproject.toml` ist die einzige Quelle der Wahrheit. Alles andere liest von dort, statt sie zu wiederholen.

### Ein Test mit Versions-Literal ist selbst eine Versions-Stelle

Wer die Versions-Stellen eines Servers zählt, zählt `pyproject.toml`, `server.json`, `__init__.py`, vielleicht ein `Dockerfile` — und hört bei den Dateien auf, die nach Konfiguration aussehen. `tests/` steht auf keiner dieser Listen.

**Der Fall** (`hn-tech-signal-mcp`): Der Release-Durchgang zog vier gezählte Stellen mit. Rot wurde die CI trotzdem:

```python
# tests/test_version.py
assert __version__ == "0.3.0"
```

Das war die fünfte, und sie war nirgends erfasst. Ein Testfile ist Code, also sucht dort niemand nach Konfigurationswerten — aber ein Literal ist ein Literal, unabhängig davon, in welchem Verzeichnis es steht.

> Ein Test, der ein Versions-Literal festnagelt, ist keine Prüfung der Version. Er ist eine weitere Kopie davon, mit dem Zusatz, dass er beim nächsten Bump die Pipeline anhält.

**Die Behebung ist nicht, das Literal mitzuziehen.** Ein fünfter Ort in der Release-Checkliste macht die Liste länger und das Problem nicht kleiner — beim nächsten Mal ist es der sechste. Der Test muss stattdessen auf die **Invariante** zeigen, die wirklich brechen kann:

```python
# Nicht: stimmt __version__ mit einer aufgeschriebenen Zahl überein?
# Sondern: stimmen zwei unabhängig gepflegte Stellen überein?
assert __version__ == json.loads(Path("server.json").read_text())["version"]
```

Der Unterschied ist nicht kosmetisch. Ein Literal-Vergleich bricht bei **jedem** Bump — also genau dann, wenn alles richtig läuft. Der Vergleich gegen `server.json` bricht nur, wenn zwei Stellen auseinanderlaufen, die zusammengehören — also genau dann, wenn etwas falsch ist. Und dass sie auseinanderlaufen, ist belegt: `IDENT-003` fand vier Server mit genau dieser Drift.

**Der Nachweis, dass der neue Test überhaupt greift, gehört dazu.** Ein Vergleich zweier Werte, die aus derselben Quelle stammen, kann nicht widersprechen und ist grün, ohne etwas zu prüfen — dieselbe Falle, die weiter unten unter «Reichweite» steht. Deshalb einmal **`server.json` verstimmen** und beobachten, dass der Test rot wird:

```bash
python - <<'EOF'
import json, pathlib
p = pathlib.Path("server.json"); d = json.loads(p.read_text())
d["version"] = "0.0.0-verstimmt"
p.write_text(json.dumps(d, indent=2))
EOF
python -m pytest tests/test_version.py -q     # MUSS fehlschlagen
git checkout server.json                       # zurücknehmen
```

Bleibt er grün, prüft er nicht, was er zu prüfen vorgibt — er liest womöglich eine Datei, die es nicht gibt, oder vergleicht zwei Ableitungen von `pyproject.toml` miteinander.

### Remediation

Aus dem Katalog (`checks/IDENT-002.md`, Remediation), auf die Gaps oben anzuwenden:

```diff
  """<Server> MCP Server."""
+
+ from importlib.metadata import PackageNotFoundError
+ from importlib.metadata import version as _distribution_version

- __version__ = "0.2.0"
+ try:
+     __version__ = _distribution_version("<dist-name>")
+ except PackageNotFoundError:
+     # Quell-Checkout ohne Installation. Bewusst kein plausibel aussehender
+     # Platzhalter — siehe IDENT-005.
+     __version__ = "0.0.0+source"
```

Ein bestehender Test, der das Literal festnagelt, muss mitgeändert werden — und zwar auf eine Invariante, nicht auf eine zweite Ableitung derselben Quelle:

```diff
- assert __version__ == "0.3.0"
+ import json
+ from pathlib import Path
+
+ # Zwei unabhängig gepflegte Stellen. `server.json` wird von Hand
+ # gepflegt und driftet belegt (IDENT-003, vier Server) — genau deshalb
+ # kann dieser Vergleich brechen, und genau deshalb prüft er etwas.
+ manifest = json.loads(Path("server.json").read_text(encoding="utf-8"))
+ assert __version__ == manifest["version"], (
+     f"__version__ meldet {__version__}, server.json steht auf "
+     f"{manifest['version']} — eine der beiden Stellen wurde beim "
+     "Release nicht mitgezogen."
+ )
```

`assert __version__ == version("<dist-name>")` wäre **nicht** die Behebung: Beide Seiten kommen aus denselben Metadaten, der Vergleich kann nicht widersprechen und ist grün, ohne etwas zu prüfen.

Danach einmal belegen, dass der Test greift — `server.json` verstimmen, Suite laufen lassen, Änderung zurücknehmen (Befehle oben im Description-Teil). Ein Versions-Test, der nie rot war, ist von einem wirkungslosen nicht zu unterscheiden.

### Effort Estimate

Katalog-Richtwert (checks/IDENT-002.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — Pro Server 10 Minuten. Der Testumbau ist der grössere Teil.
