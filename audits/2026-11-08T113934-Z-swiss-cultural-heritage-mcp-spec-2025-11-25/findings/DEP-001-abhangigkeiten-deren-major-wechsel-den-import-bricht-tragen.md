## Finding: DEP-001 — Abhängigkeiten, deren Major-Wechsel den Import bricht, tragen eine Obergrenze

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `DEP-001` |
| **PDF-Reference** | Custom (Portfolio-Fundstücke zurich-opendata-mcp 0.5.1 / swiss-energy-mcp; mcp 2.0.0 vom 2026-07-28) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Laufzeit-Distribution sauber begrenzt und gemessen. Abzug nur fuer das ungedeckelte otel-Extra. SDK-006 nicht vermischt: der mcp-Bound ist am 2er-Major verankert, das ist hier nur als Existenz des zweiten Bounds gewertet. Bezieht sich auf 0.6.0 (publiziert) und HEAD 0.7.0 (identische Ranges laut PyPI requires_dist vs pyproject.toml).

### Expected Behavior

Aus dem Katalog (`checks/DEP-001.md`, Pass Criteria):

- [ ] Jede Abhängigkeit, aus deren Modulpfaden der Server importiert, trägt eine Obergrenze (`<N+1` oder enger)
- [ ] Das SDK bzw. Server-Framework ist gedeckelt — ausnahmslos
- [ ] Ungedeckelte Ranges sind auf Abhängigkeiten beschränkt, die hinter einer eigenen Schnittstelle liegen, und diese Entscheidung ist irgendwo aufgeschrieben
- [ ] Keine exakte Pinnung (`==`) in den Laufzeit-Abhängigkeiten der publizierten Distribution — Bereiche mit beiden Enden
- [ ] Jede Obergrenze ist **gemessen**: Die höchste vom Cap erlaubte Version wurde installiert, importiert und gegen die Suite gefahren (Modus 4a) — nicht auf die nächste runde Zahl gesetzt
- [ ] Für jede Obergrenze wurde der **Gegenversuch** geführt: Cap entfernt, gegen den Index aufgelöst, der nächste Major kommt herein (Modus 4b). Tut er das nicht, steht das als «Wirkung ungeprüft» im Report
- [ ] Die Abgrenzung zu `SDK-006` ist gewahrt: Ein Befund dort («Bound hält den alten Major fest») wurde nicht als Befund hier verbucht und umgekehrt
- [ ] Ein Prozess hebt Obergrenzen an (Dependabot / Renovate / dokumentierter Quartals-Durchgang); ein Deckel ohne diesen Prozess ist nur eine Verzögerung ohne Ende
- [ ] Die Auflösung wurde einmal **leer** durchgeführt und gegen das Lockfile gehalten (Modus 3) — nicht nur die Range gelesen
- [ ] Für jede offene Range steht im Report, ob sie geprüft und für vertretbar befunden wurde, oder ob niemand hingesehen hat. Beides ist ein Ergebnis, aber nicht dasselbe

### Evidence

- git show HEAD:pyproject.toml [project].dependencies — alle sechs Laufzeit-Abhaengigkeiten mit beiden Enden: mcp[cli]>=2.0.0,<3; httpx>=0.27.0,<1.0.0; pydantic>=2.0.0,<3.0.0; pydantic-settings>=2.0.0,<3.0.0; defusedxml>=0.7.1,<1.0.0; structlog>=24.1.0,<27.0.0; kein == in Laufzeit-Deps (ruff==0.16.9 nur im dev-Extra)
- src/swiss_cultural_heritage_mcp/server.py:38-44 + src/swiss_cultural_heritage_mcp/__init__.py:3 — Top-Level-Imports aus mcp.server.mcpserver, httpx, pydantic, pydantic_settings, structlog, defusedxml; alle gedeckelt. SDK gedeckelt (<3), Kommentar pyproject.toml begruendet Floor und Cap
- pyproject.toml [project.optional-dependencies].otel — opentelemetry-sdk>=1.20.0, opentelemetry-exporter-otlp-proto-http>=1.20.0, opentelemetry-instrumentation-httpx>=0.40b0: OHNE Obergrenze; importiert aus Modulpfaden in server.py:205-209 (im try/except ImportError) und server.py:233 (OTLPSpanExporter, ausserhalb des try → ImportError dort bricht den Start, sobald OTEL_EXPORTER_OTLP_ENDPOINT gesetzt ist). Keine aufgeschriebene Begruendung fuer die offene Range
- Modus 3 (leer aufgeloest): neues venv (Python 3.14), pip install --no-cache-dir --isolated swiss-cultural-heritage-mcp==0.6.0 → mcp 2.3.0, mcp-types 2.3.0, httpx 0.28.1, httpx2 2.16.0, pydantic 2.14.3, pydantic-settings 2.16.2, defusedxml 0.7.1, structlog 26.1.0. Kein Lockfile im Repo (ls uv.lock poetry.lock requirements*.txt → nicht vorhanden); Majors identisch mit dem Dev-venv
- Modus 4a: PyPI-JSON 2026-11-08: hoechste stabile Versionen mcp 2.3.0, httpx 0.28.1, pydantic 2.14.3, pydantic-settings 2.16.2, defusedxml 0.7.1, structlog 26.1.0 = hoechste vom Cap erlaubte; installiert im Audit-venv, importiert, Suite: 375 passed, 40 failed (die bekannten Windows-only-Fehler), 2 skipped; publiziertes 0.6.0 mit diesen Versionen importiert und tools/call beantwortet
- Modus 4b: pip install --dry-run --no-cache-dir --isolated ohne Caps ("mcp[cli]>=2.0.0" "httpx>=0.27.0" ... "structlog>=24.1.0" + otel) → mcp 2.3.0, httpx 0.28.1, pydantic 2.14.3, pydantic-settings 2.16.2, defusedxml 0.7.1, structlog 26.1.0, opentelemetry-sdk 1.45.2, instrumentation-httpx 0.66b2. pip config list leer. Negative Kontrolle unabhaengig: PyPI-JSON fuehrt fuer keine der sechs einen naechsten Major → Ergebnis ist kein Aufbaufehler
- git show HEAD:.github/dependabot.yml — package-ecosystem pip, monatlich, gruppiert: Anhebungsprozess vorhanden

### Gaps

- medium: otel-Extra (3 Pakete) ohne Obergrenze, obwohl aus deren Modulpfaden importiert wird; nicht dokumentiert als bewusste Ausnahme. Wirkung beschraenkt auf Deployments mit [otel] und gesetztem Endpoint
- info: Wirkung aller sechs Caps ungeprueft — Gegenversuch 4b fuehrt fuer keine Abhaengigkeit einen hoeheren Major herein, weil auf dem Index keiner existiert (kein Fehler, aber kein Beleg; bei naechstem Major erneut fragen)

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

`mcp[cli]>=1.28.1` sieht aus wie eine Mindestanforderung. Es ist eine Vollmacht: Wer immer als Nächstes eine Version dieses Pakets publiziert, entscheidet mit, welchen Code der eigene Server importiert — rückwirkend, für jede Installation, die von da an stattfindet.

**Der Fall** (2026-07-28): `mcp` 2.0.0 erschien und entfernte `mcp.server.fastmcp` ersatzlos. `swiss-energy-mcp` `0.3.3` deklarierte `mcp` ohne Obergrenze. Ab diesem Tag löste jedes frische `pip install` auf die 2er-Linie auf, und das Konsolen-Skript starb beim Start:

```
ModuleNotFoundError: No module named 'mcp.server.fastmcp'
```

Kein Commit ging dem voraus. Kein Test wurde rot. Kein Release wurde geschnitten.

> Das Artefakt hat sich nicht geändert. Die Antwort des Resolvers hat sich geändert.

Das ist der ganze Mechanismus, und die einzige Stelle, die ihn erlaubte, war ein fehlendes `<3`.

**Der Sweep** (2026-08-02) suchte danach im gesamten Portfolio: **28 Befunde über 24 Server**, alle behoben. Die Zahl gedeckelter Abhängigkeiten stieg dabei von **61 auf 89**. Der Vorfall war also kein Einzelfall in zwei Repos, sondern die Voreinstellung überall dort, wo eine Range beim Anlegen nie zu Ende gedacht wurde.

**Drei Mechanismen, die hier nicht helfen** — jeder davon wird regelmässig dafür gehalten:

| Mechanismus | Warum er nicht greift |
|---|---|
| Lockfile im Repo (`uv.lock`, `poetry.lock`) | Gilt für die Entwicklungsumgebung. `pip install <dist>` bei Nutzenden liest ihn nie |
| Grüne CI | Installiert aus dem Lock oder aus dem Checkout, meist mit Cache. Sie löst nicht auf, was heute aufgelöst würde |
| Ein gerade erst geschnittenes Release | Der Vorfall entstand **nach** einem korrekten Release. Die Range ist im Artefakt eingebacken; sie wirkt zum Zeitpunkt der Installation, nicht zum Zeitpunkt des Publizierens |

Der Check misst deshalb etwas, das keinem Repo-Zustand ansieht: den **Auflösungsraum**, den das publizierte Artefakt offenlässt.

### Nicht «alles deckeln»

Eine Obergrenze auf jede Abhängigkeit ist die andere Sorte Schaden. Sie hält Sicherheitspatches zurück, macht den Server mit anderen Paketen in derselben Umgebung unvereinbar und erzeugt Arbeit, die niemand tut, bis sie weh tut. Das Kriterium ist enger:

> **Gedeckelt gehört, was den Server beim Major-Wechsel bricht, ohne dass es jemandem auffällt.**

Die praktische Frage dazu, in dieser Reihenfolge:

1. **Importiere ich aus ihren Modulpfaden?** `from mcp.server.fastmcp import FastMCP` bindet an eine Struktur, die ein Major umbauen darf. Ein Umbau schlägt beim **Import** zu — also sofort, bei jedem Start, für alle. Deckeln.
2. **Leite ich von ihren Typen ab, oder implementiere ich ihre Protokolle?** Basisklassen, Pydantic-Modelle, ABCs — dieselbe Bindung, dieselbe Antwort.
3. **Ist sie das Framework, in dem der Server läuft?** SDK, Server-Framework, Validierungsbibliothek. Ihr Major ist der eigene Major. Deckeln.
4. **Berühre ich sie nur hinter einer eigenen Schnittstelle, an einer Stelle, mit einem stabilen Aufruf?** Dann ist eine offene Range vertretbar — der Bruch ist lokal und sichtbar.

Für Punkt 4 gilt trotzdem: Vertretbar heisst «bewusst entschieden», nicht «nie hingesehen». Der Unterschied zeigt sich daran, ob es jemand begründen kann.

**Der Gegenfehler ist die exakte Pinnung.** `mcp==1.28.1` deckelt nicht, es friert ein. Ein Server, der so publiziert wird, lässt sich mit keinem anderen Paket in derselben Umgebung kombinieren, das eine andere Patch-Version braucht — und bekommt keine Sicherheitsfixes. Die richtige Form ist ein Bereich mit beiden Enden: `>=2.0.0,<3`.

### Die Obergrenze wird gemessen, nicht geraten

Steht fest, *dass* gedeckelt wird, folgt die Frage, *worauf*. Die bequeme Antwort ist die nächste runde Zahl — sie ist auch die falsche, in beide Richtungen: zu tief gesetzt sperrt sie eine Major-Version aus, die längst funktioniert; zu hoch gesetzt lässt sie genau die herein, die den Import bricht.

> Der Deckel wird gegen das gemessen, was heute nachweislich installiert **und importiert** wird — nicht gegen die nächste runde Zahl.

`structlog>=24.1,<27` ist deshalb kein Tippfehler und keine Nachlässigkeit. `<27` steht dort, weil `26.1.0` **belegt** funktioniert: installiert, importiert, Testsuite gelaufen. Ein `<25`, das jemand aus Vorsicht gesetzt hätte, wäre ebenso unbelegt gewesen wie ein `<30` aus Bequemlichkeit — der einzige Unterschied liegt in der Richtung des Schadens.

Zwei Teile gehören zusammen, und beide sind Messungen:

1. **Die obere Schranke ist die höchste Major-Version, die läuft.** «Läuft» heisst: in einer leeren Umgebung installiert, der Server importiert, die Suite grün. Nicht «steht im Changelog als kompatibel».
2. **Die untere Schranke ist die tiefste, die noch gebraucht wird.** Sie ist keine Zierde: Sie hält die Spanne so weit, dass der Server mit anderen Paketen in derselben Umgebung koexistiert.

**Der Nachweis, dass der Deckel überhaupt etwas tut.** Eine Obergrenze, die ohnehin nie erreicht wird, ist Text ohne Wirkung — und sie sieht im Diff genauso aus wie eine wirksame. Der Beleg ist ein Gegenversuch:

> Cap entfernen, gegen den Index auflösen. **Der nächste Major muss hereinkommen.**

Kommt er nicht, deckelt die Range nichts, was der Resolver heute ohnehin tun würde: Entweder ist die Abhängigkeit dort noch gar nicht, oder eine andere Constraint hält sie bereits. Das ist kein Pass — es ist ein Deckel, dessen Wirkung ungeprüft ist, und beim nächsten Release der Abhängigkeit stellt sich die Frage neu. Genau dieser Gegenversuch trennt einen gemessenen Deckel von einem abgeschriebenen.

### Abgrenzung zu SDK-006 — zwei verschiedene Fragen an dieselbe Zeile

`SDK-006` sieht denselben Text an wie dieser Check und fragt etwas anderes. Die Verwechslung ist naheliegend genug, dass sie hier benannt gehört:

| | `SDK-006` | `DEP-001` (dieser Check) |
|---|---|---|
| **Frage** | Ist die Migration `mcp` 1.x → 2.x **abgeschlossen**? | Ist der **Auflösungsraum** jeder Abhängigkeit begrenzt? |
| **Gegenstand** | ausschliesslich das Python-SDK `mcp` | jede Abhängigkeit der publizierten Distribution |
| **Was ein Cap dort bedeutet** | `<2` ist ein **Befund**: Er hält den alten Major fest, also ist nicht migriert worden | `<3` ist die **Erfüllung**: Die Range hat beide Enden |
| **Wann erledigt** | einmalig, mit der Migration | dauerhaft, bei jeder Abhängigkeit und jedem Release |
| **`applies_when`** | `sdk_language == "Python"` | `always` |

Der Unterschied in einem Satz: **`SDK-006` prüft, an welchem Major der Bound verankert ist. Dieser Check prüft, dass es überhaupt einen zweiten Bound gibt.**

Daraus folgt, dass beide Checks an derselben Zeile gleichzeitig fehlschlagen können — `mcp>=1.28.1` ist für `SDK-006` der alte Major und für `DEP-001` die offene Range —, und dass sie sich nicht gegenseitig erfüllen: Ein migriertes `mcp>=2.0.0` ohne Obergrenze besteht `SDK-006` nicht (dort ist die obere Schranke ebenfalls gefordert) und ist für diesen Check der Ausgangsfall. Umgekehrt sagt ein sauberes `mcp>=2.0.0,<3` nichts über `httpx`, `pydantic` oder `structlog` — die dieser Check mitprüft und `SDK-006` nie ansieht.

### Eine Obergrenze ohne Anhebungsprozess verrottet

Das ist der ehrliche Preis dieses Checks, und er gehört dazu. Ein `<3`, das drei Jahre steht, ist irgendwann kein Schutz mehr, sondern der Grund, warum der Server auf einer nicht mehr gepflegten Major-Version festsitzt. Eine Obergrenze ist eine **Verzögerung**, damit der Wechsel eine Entscheidung wird — kein Verzicht auf den Wechsel.

Deshalb sind Deckel und automatisierter Anhebungs-PR ein Paar. Wer den einen einführt, führt den anderen mit ein.

### Remediation

Aus dem Katalog (`checks/DEP-001.md`, Remediation), auf die Gaps oben anzuwenden:

### Schritt 1: Deckeln, was den Import trägt

```diff
  dependencies = [
-     "mcp[cli]>=1.28.1",
+     "mcp[cli]>=2.0.0,<3",
      "httpx>=0.27",
-     "structlog>=24.1",
+     # <27, weil 26.1.0 installiert, importiert und getestet ist (Modus 4a).
+     "structlog>=24.1,<27",
  ]
```

`httpx` bleibt offen, wenn der Server es hinter einem eigenen Client-Modul verwendet — das ist Frage 4, und die Antwort gehört als Kommentar oder in die Doku, nicht in den Kopf einer Person.

Die Zahl hinter dem `<` ist dabei kein Rundungsergebnis: `<27` steht dort, weil `26.1.0` gemessen läuft. Wer sie ohne diesen Lauf setzt, hat den Vorfall nur verschoben — von «der nächste Major bricht den Import» zu «eine funktionierende Version ist ausgesperrt, und niemand weiss warum».

### Schritt 2: Neu publizieren

Die Range wirkt nur in dem Artefakt, das sie trägt. Ein Deckel auf `main` schützt keine einzige Installation, solange der Index die alte Distribution führt (`IDENT-006`) — und die nächste frische Installation prüft `IDENT-007`.

### Schritt 3: Den Anhebungsprozess mitliefern

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule: { interval: "weekly" }
```

Der PR ist der Ort, an dem der Major-Wechsel eine Entscheidung wird: Die Testsuite läuft gegen die neue Linie, und wer den Deckel anhebt, hat die Migration vor sich statt hinter sich. Genau das war im Vorfall nicht gegeben — dort geschah der Wechsel ohne PR, ohne Test und ohne Entscheidung.

### Effort Estimate

Katalog-Richtwert (checks/DEP-001.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — Ranges anpassen und neu publizieren ist eine halbe Stunde. Der Anhebungsprozess ist einmalige Einrichtung. Teuer ist nur der Fall, in dem der Deckel schon zu lange fehlte und die Migration gleich mit ansteht.
