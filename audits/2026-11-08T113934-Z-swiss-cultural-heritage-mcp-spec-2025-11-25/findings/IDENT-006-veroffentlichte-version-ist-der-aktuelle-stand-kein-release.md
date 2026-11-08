## Finding: IDENT-006 — Veröffentlichte Version ist der aktuelle Stand — kein Release-Gap

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `IDENT-006` |
| **PDF-Reference** | Custom (Portfolio-Fundstück meteoswiss-mcp#31, 2026-07-30) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Kein fehlgeschlagener Publish, kein Tag ohne Index-Release, [Unreleased] leer. Der Gap ist der Abstand, den 0.7.0 schliessen soll — 'noch nicht released' ist hier korrekt der Zustand vor dem Release, nicht Versions-Drift. shipped_probe.py nicht verfuegbar, von Hand gemessen. IDENT-007 separat beantwortet.

### Expected Behavior

Aus dem Katalog (`checks/IDENT-006.md`, Pass Criteria):

- [ ] Die auf dem Index veröffentlichte Version entspricht dem letzten Release-Tag
- [ ] Kein Release-Tag existiert, den der Index nicht hat (kein fehlgeschlagener Publish)
- [ ] Keine nutzerwirksamen Commits (`fix`, `feat`, `perf`, `revert`) älter als 7 Tage unveröffentlicht
- [ ] `[Unreleased]` im CHANGELOG ist entweder leer oder jünger als die Release-Kadenz — und beschreibt tatsächlich Unveröffentlichtes (`DRIFT-006`)
- [ ] Der Release-Prozess ist im README oder CONTRIBUTING beschrieben, inklusive des manuellen Schritts, falls es einen gibt
- [ ] Der Vergleich hat stattgefunden — Exit `127` der Probe ist `todo`, nicht Pass
- [ ] `IDENT-007` wurde **separat** beantwortet; ein Pass hier wurde nicht als Beleg dafür verbucht

### Evidence

- GET https://pypi.org/pypi/swiss-cultural-heritage-mcp/json → info.version 0.6.0 (Upload 2026-09-19T10:11, nicht yanked); git ls-remote origin: refs/tags/v0.6.0 (→5feed72), kein v0.7.0-Tag; letzter Tag = Index-Version, kein Tag ohne Index-Release
- git show HEAD:pyproject.toml version = '0.7.0' — gebumpt auf Branch claude/release-0.7.0 (HEAD 9b3a1b4, nicht auf origin), nicht getaggt: Release in Vorbereitung, keine Drift
- git log v0.6.0..HEAD --no-merges → 17 Commits, darunter nutzerwirksame und aelter als 7 Tage: 2026-09-20 'Helveticat: marc21 statt oai_dc, und SRU fuer die Volltextsuche', 2026-09-20 'serverInfo.name traegt jetzt den Bezeichner des Portfolios (H3)', 2026-10-28 2x feat (Hooks, Dev-Tooling). Index-Artefakt 0.6.0 meldet tatsaechlich noch serverInfo.name 'swiss_cultural_heritage_mcp' (stdio-initialize am installierten 0.6.0)
- git show HEAD:CHANGELOG.md:8-10 — '## [Unreleased]' leer, darunter '## [0.7.0] - 2026-11-08'
- publish.yml:3-5 — Trigger 'release: published' (manueller Schritt: GitHub-Release erstellen)
- grep -niE 'release|publish|tag|pypi' README.md README.de.md CONTRIBUTING.md CONTRIBUTING.de.md docs/roadmap.md (HEAD) → kein beschriebener Release-Prozess

### Gaps

- high: nutzerwirksame Aenderungen (Helveticat-Fix, serverInfo.name) liegen seit 2026-09-20 (49 Tage) unveroeffentlicht; PyPI liefert sie nicht aus. Wird durch das Release 0.7.0 geschlossen — nach dem Publish am Index erneut messen
- medium: Release-Prozess inkl. manuellem Schritt (GitHub-Release erstellen loest publish.yml aus) weder in README noch CONTRIBUTING dokumentiert

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

`IDENT-001` bis `IDENT-005` prüfen, ob die gemeldete Version **korrekt** ist. Dieser Check prüft, ob sie **aktuell** ist.

Das ist eine eigene Fehlerklasse, und die unbequemste der Kategorie: Ein Repository kann grün, auditiert und vollständig korrigiert sein, während jedes `pip install` weiterhin das kaputte Release ausliefert. Nichts widerspricht dem, denn CI testet den Branch, nie das Artefakt. Der Server ist repariert; die Nutzenden merken nichts davon.

**Der Fall** (`meteoswiss-mcp`, 2026-07-30): Die Migration auf das `mcp`-2.x-SDK war am 29. auf `main` gemergt. PyPI führte weiter `0.4.0`, das `mcp.server.fastmcp` importiert — ein Modul, das `mcp` 2.0.0 am Tag zuvor entfernt hatte. Jede frische Installation starb drei Tage lang beim Import:

```
ModuleNotFoundError: No module named 'mcp.server.fastmcp'
```

Gefunden hat es ein aussenstehender Nutzer, nicht die Testsuite, nicht das Audit. Und es wiederholte sich am selben Nachmittag: `0.5.0` wurde publiziert, drei weitere Fixes landeten auf `main`, und bis zum nächsten Release lieferte PyPI einen Server aus, dessen `meteo_current`, `meteo_forecast` und `meteo_school_check` allesamt nichts zurückgaben — drei von sechs Tools.

Eine schärfere Ausprägung ist nicht «noch nicht released», sondern **ein Tag, den der Index nicht hat**: Dann wurde ein Release geschnitten und ist nie angekommen — ein fehlgeschlagener Workflow, oder eine hängende Environment-Freigabe. Die Maintainerin glaubt bereits, es sei publiziert.

### Was dieser Check nicht sagt: dass das Artefakt läuft

Dieser Check misst einen **Abstand**: zwischen dem, was auf `main` steht, und dem, was auf dem Index liegt. Er vergleicht dafür Etiketten — Versionsnummern in `pyproject.toml`, im letzten Tag und in den Index-Metadaten. Stimmen alle drei überein, heisst das genau eines: **Niemand hat vergessen zu publizieren.**

Es heisst nicht, dass das Publizierte installiert, importiert oder antwortet. Diese Frage ist eine eigene Achse, sie ist unabhängig von jedem Abstand, und sie steht als eigener Check: **[`IDENT-007`](IDENT-007.md) — das veröffentlichte Artefakt startet in einer leeren Umgebung.**

Die Trennung ist nicht formal. Der Fall, der sie erzwungen hat (`zurich-opendata-mcp` `0.5.1`, reproduziert am 2026-07-31), bestand **jedes Kriterium dieses Checks**: Repo, Tag und Index standen alle drei auf `0.5.1`, null unveröffentlichte Commits — und das Artefakt starb beim Import, weil sich eine ungedeckelte Abhängigkeit unter ihm bewegt hatte (`DEP-001`). Ein grünes `IDENT-006` war dort die Wahrheit und trotzdem wertlos.

**Für den Audit heisst das:** Ein Pass hier ist kein Teilbeleg für `IDENT-007`, in keiner Richtung. Beide Checks laufen, beide werden einzeln beantwortet. Der häufigste Irrtum der ganzen Kategorie ist, aus gleichen Etiketten auf ein funktionierendes Paket zu schliessen.

### Remediation

Aus dem Katalog (`checks/IDENT-006.md`, Remediation), auf die Gaps oben anzuwenden:

### Schritt 1: Zuerst `IDENT-007`, dann die Lücke

Wenn das publizierte Artefakt nicht läuft, ist die Lücke eine Nebenfrage: Es gibt dann nichts «nachzuziehen», sondern etwas zu ersetzen, und zwar sofort. Läuft es, ist die Frage nicht «sind wir vorne», sondern «wie lange schon, und was steckt drin» — `fix:` unveröffentlicht ist eine andere Tatsache als `docs:`.

### Schritt 2: Release nachziehen

Version bumpen, CHANGELOG-Abschnitt aus `[Unreleased]` bilden, taggen, Release erstellen. Danach **aus dem Index verifizieren**, nicht aus dem Build-Log — der Ablauf dafür steht in `IDENT-007`, Remediation. Ein grüner Publish-Job ist ein Zwischenschritt, keine Bestätigung. Ein grünes CI erst recht nicht: Es testet den Branch, nie das Artefakt.

### Schritt 3: Die Lücke klein halten

Kein neuer Mechanismus nötig — nur die Reihenfolge umdrehen: Ein Fix, der einen gemeldeten Bug schliesst, wird nicht «beim nächsten Feature» ausgeliefert, sondern zieht sein eigenes Patch-Release. Bei Servern mit seltener Kadenz gehört das explizit ins CONTRIBUTING.

### Effort Estimate

Katalog-Richtwert (checks/IDENT-006.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — Messung Minuten (zwei Requests und etwas Git), Nachziehen eines Releases unter einer Stunde. Der Aufwand liegt in der Disziplin, nicht in der Technik.
