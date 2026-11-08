## Finding: IDENT-007 — Das veröffentlichte Artefakt startet in einer leeren Umgebung

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `IDENT-007` |
| **PDF-Reference** | Custom (Portfolio-Fundstücke zurich-opendata-mcp 0.5.1, 2026-07-31; swiss-energy-mcp, 2026-08-01) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Das publizierte Artefakt installiert, importiert, startet und liefert. shipped_probe.py nicht verfuegbar, Modus 2 von Hand. Laeufe mit dem Konsolen-Skript (Kommandozeile ohne 'swiss_cultural_heritage_mcp.server') und vollstaendiger Ausgabe — vom parallelen Prozess-Kill nicht betroffen.

### Expected Behavior

Aus dem Katalog (`checks/IDENT-007.md`, Pass Criteria):

- [ ] Das auf dem Index liegende Artefakt **installiert** in eine leere Umgebung (frisches venv, `--no-cache-dir`, kein Lockfile, kein Constraint aus dem Repo)
- [ ] Es **importiert**: das Top-Level-Paket lädt
- [ ] Der Entry Point **startet** und beantwortet ein `initialize`
- [ ] Ein echter `tools/call` liefert eine Antwort, die kein `isError` trägt und nicht leer ist
- [ ] Die veröffentlichte Version ist nicht zurückgezogen (`yanked`)
- [ ] Die tatsächlich aufgelösten Versionen der Kern-Abhängigkeiten sind **protokolliert** — sie sind die Evidenz, wenn dasselbe Paket morgen anders auflöst
- [ ] Ein `TOOL_ERROR` wurde gegen die Egress-Allow-List geprüft, bevor er als Artefakt-Defekt geführt wurde
- [ ] Ein wiederkehrender Lauf prüft dies erneut — nicht nur der Release-Tag (Modus 3)
- [ ] Die Prüfung hat **stattgefunden**: nicht gemessen ist `todo`, nicht Pass

Ein Verstoss ist ein sofortiger Befund auf `high`, unabhängig davon, wie alt der Zustand ist und ob `IDENT-006` grün war.

### Evidence

- Leeres venv (Python 3.14, scratch/verify060), pip install --no-cache-dir --isolated 'swiss-cultural-heritage-mcp==0.6.0' → exit 0; import: 'import ok 0.6.0 ...\verify060\Lib\site-packages\swiss_cultural_heritage_mcp\__init__.py' (aus dem Index, nicht aus dem Checkout)
- Aufgeloest (pip freeze): mcp==2.3.0, mcp-types==2.3.0, httpx==0.28.1, httpx2==2.16.0, pydantic==2.14.3, pydantic-settings==2.16.2, defusedxml==0.7.1, structlog==26.1.0
- Entry Point verify060/Scripts/swiss-cultural-heritage-mcp.exe ueber stdio: initialize → protocolVersion 2025-11-25, serverInfo version 0.6.0; tools/list → 11 Tools
- tools/call list_heritage_collections → isError=False, 1672 Zeichen; tools/call heritage_search_artists {query:'Hodler',limit:2} (echter Upstream-GET) → isError=False, 578 Zeichen, 'Gefunden: 25 Eintraege (zeige 2)'
- PyPI-JSON: 0.6.0 yanked=False
- grep -l 'schedule:' .github/workflows/*.yml → nur nightly-live.yml; dieser installiert den Checkout (pip install -e ".[dev]", Zeile 32), nicht das publizierte Paket

### Gaps

- medium: kein wiederkehrender Lauf im Repo, der das publizierte Artefakt installiert und startet (ob der externe mcp-continuous-auditor es tut, ist hier nicht pruefbar) — die Messung ist ein Zeitpunkt (2026-11-08 ~11:55 UTC)
- medium (Datentreue, nicht Startfaehigkeit): Antwort von heritage_search_artists am 0.6.0-Artefakt rendert den Namen als '## (Unbekannt)' — Live-Schema ohne NAME/HAUPTNR/SIKART_LINK; HEAD 0.7.0 liest dieselben Felder (server.py:1317, 1473, 1527)
- info: 0.7.0 ist nicht auf dem Index; nach dem Publish Modus 2 gegen 0.7.0 wiederholen

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

Alles, was ein Repository über sich weiss, weiss es über sich selbst. Die Tests laufen gegen den Checkout, die Linter gegen den Checkout, das Audit liest den Checkout. Was Nutzende bekommen, ist etwas anderes: ein Artefakt vom Index, aufgelöst gegen die Paketwelt von **heute**, in einer Umgebung, die nichts enthält.

Dieser Check stellt genau eine Frage, und er stellt sie am Artefakt: **Installiert es, importiert es, startet es, antwortet es?**

### Abgrenzung zu `IDENT-006`

`IDENT-006` misst den Abstand zwischen `main` und dem Index — ob jemand vergessen hat zu publizieren. Das ist ein Vergleich von Etiketten und eine berechtigte Frage. Es ist aber nicht diese.

**Der Fall** (`swiss-energy-mcp`): Die Versionsnummern stimmten überein — Repo, Tag und Index einig, keine unveröffentlichten Commits. Der Gap-Check war zufrieden, und zwar zu Recht: Es *gab* keine Lücke. Die Installation war trotzdem tot.

Derselbe Ausgang, vier Wochen früher und vollständig protokolliert, bei `zurich-opendata-mcp` `0.5.1` (2026-07-31):

```
$ uv run --with 'zurich-opendata-mcp==0.5.1' python -c "import zurich_opendata_mcp.app"
installed zurich-opendata-mcp: 0.5.1
installed mcp               : 2.0.0
ModuleNotFoundError: No module named 'mcp.server.fastmcp'
```

Gebrochen hatte in beiden Fällen nichts im Repository. Die Distribution trug `mcp[cli]>=1.28.1` **ohne Obergrenze**; am 2026-07-28 erschien `mcp` 2.0.0 und entfernte `mcp.server.fastmcp` ersatzlos. Von da an löste jede frische Installation eine Major-Version auf, gegen die der Code nicht lief. **Das publizierte Artefakt änderte sich, ohne dass jemand es publizierte.** Die Ursache dieser Klasse trägt `DEP-001`; hier steht die Prüfung, die sie sichtbar macht.

Zwei Konsequenzen, die diesen Check tragen:

1. **Der Befund hängt nicht am Alter.** Ein Artefakt, das *jetzt* nicht startet, ist ein sofortiger Befund — auch bei null unveröffentlichten Commits, auch wenn Repo, Tag und Index dieselbe Nummer tragen. Die Frage ist nicht, wie lange etwas ansteht, sondern ob das, was Nutzende gerade herunterladen, funktioniert. Ein Artefakt, das seit einer Stunde tot ist, ist genauso tot wie eines, das es seit drei Wochen ist; der einzige Unterschied liegt darin, wie viele es schon getroffen hat.
2. **Kein Metadaten-Vergleich kann diese Achse ersetzen.** Die einzige Aussage darüber, ob etwas läuft, entsteht daraus, dass man es installiert und startet.

### Warum «leer» und nicht nur «frisch»

Die Umgebung ist der halbe Check. Drei Umgebungen, die alle plausibel aussehen und die Frage **nicht** beantworten:

| Umgebung | Warum sie nicht zählt |
|---|---|
| Der Checkout mit `pip install -e .` | Prüft den Branch — also genau das, was CI schon prüft. Der blinde Fleck bleibt unberührt |
| Ein venv mit dem Lockfile des Repos | Löst auf, was die Entwicklerin auflöste, nicht was heute aufgelöst wird. Genau die Verschiebung, die den Vorfall ausmachte, ist damit weggepinnt |
| Die eigene Arbeitsumgebung mit `--user`, Cache, vorhandenen Paketen | Ein bereits installiertes `mcp<2` beantwortet die Frage für niemanden ausser die Prüferin selbst |

Leer heisst: neues venv, `--no-cache-dir`, kein Constraint aus dem Repo, Version explizit vom Index. Was der Resolver dann wählt, ist das, was Nutzende heute bekommen — und mehr will dieser Check nicht wissen.

### Remediation

Aus dem Katalog (`checks/IDENT-007.md`, Remediation), auf die Gaps oben anzuwenden:

### Schritt 1: Ersetzen, nicht nachziehen

Ein totes Artefakt auf dem Index ist keine Warteschlangenfrage. Ein Patch-Release, das den Import wieder herstellt, geht allen anderen Findings vor — es ist der einzige Zustand, den jede neue Nutzerin sofort trifft. Ist die Ursache nicht in Minuten zu beheben, ist `yank` der ehrlichere Zwischenschritt als ein Paket, das beim Import stirbt.

### Schritt 2: Die Ursache schliessen, nicht das Symptom

War der Auslöser eine ungedeckelte Dependency-Range, ist das Release die halbe Arbeit. Ohne Obergrenze wiederholt sich derselbe Vorfall beim nächsten Major der Abhängigkeit, wieder ohne Zutun:

```diff
- "mcp[cli]>=1.28.1"
+ "mcp[cli]>=2.0.0,<3"
```

Was gedeckelt gehört und was nicht, steht in `DEP-001`. Ein Lockfile im Repo schützt hier **nicht**: Es gilt für die Entwicklungsumgebung, nicht für die Auflösung beim `pip install` der Nutzenden.

### Schritt 3: Nach dem Release aus dem Index verifizieren

Die vier Schritte aus Modus 2, gegen die soeben publizierte Version. Ein grüner Publish-Job ist ein Zwischenschritt, keine Bestätigung; ein grünes CI erst recht nicht.

### Schritt 4: Wiederkehrend prüfen

Der Zustand kann sich ohne Commit ändern — deshalb ist eine einmalige Messung hier ein Datum, kein Ergebnis. `shipped_probe.py` in einen nächtlichen Lauf, oder ein `schedule`-Workflow, der die vier Schritte fährt.

### Effort Estimate

Katalog-Richtwert (checks/IDENT-007.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — die Probe installiert und startet einmal, das sind Minuten. Ein Patch-Release unter einer Stunde. Der wiederkehrende Lauf ist einmalige Einrichtung; die Obergrenze aus Schritt 2 gehört zu `DEP-001`.
