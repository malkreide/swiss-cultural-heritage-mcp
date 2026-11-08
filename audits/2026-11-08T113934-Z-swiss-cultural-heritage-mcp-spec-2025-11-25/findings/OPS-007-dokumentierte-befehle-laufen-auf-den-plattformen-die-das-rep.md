## Finding: OPS-007 — Dokumentierte Befehle laufen auf den Plattformen, die das Repo behauptet

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | advisory |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `OPS-007` |
| **PDF-Reference** | Custom (Portfolio-Fundstück mcp-audit-skill#70/#71, 2026-08-02) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Endnutzerpfad (Installation, Start, Claude-Desktop-JSON) ist plattformneutral, der Entwicklerpfad nicht. Laut CLAUDE.md ist PYTHONPATH=src nach pip install -e überflüssig; die einfachste Behebung ist, das Präfix wegzulassen. Advisory.

### Expected Behavior

Aus dem Katalog (`checks/OPS-007.md`, Pass Criteria):

- [ ] Die Plattformen, die das Repo für sich behauptet, sind an **einer** Stelle benannt — nicht aus Testmatrix, Badge und Prosa zusammenzusuchen
- [ ] Jeder dokumentierte Befehl läuft auf jeder dieser Plattformen, oder der Block ist ausdrücklich einer Plattform zugeordnet
- [ ] Keine `&&`/`||`-Verkettung in einem Befehl, der auch für PowerShell gilt — zwei Zeilen kosten nichts und laufen überall
- [ ] Plattformspezifische Blöcke stehen **paarweise** da (PowerShell *und* POSIX), nicht als Fussnote zu einem POSIX-Original
- [ ] Die Suche aus Modus 2 deckt alle Dateien ab, in denen Anleitungen stehen — inklusive der übersetzten Fassungen
- [ ] Die Prüfung ist einmal gegen einen bekannt gebrochenen Befehl gehalten worden

### Evidence

- git show HEAD:README.md:116, :143-144 und README.de.md:117, :144-145 — Plattformzusage macOS und Windows (Claude-Desktop-Konfigurationspfade); CI nur ubuntu-latest (.github/workflows/*.yml); pyproject.toml:24-32 classifiers ohne 'Operating System'. Die Plattformen stehen an keiner Stelle gesammelt
- git show HEAD:README.md:311, README.de.md:312, CONTRIBUTING.md:25, :50, CONTRIBUTING.de.md:27, :53 — dokumentierte Befehle mit POSIX-Präfix 'PYTHONPATH=src pytest …' bzw. 'PYTHONPATH=src python scripts/pin_tools.py', ohne Plattformzuordnung (der Muster-Grep schlägt an 'pip install x && y' an: 1)
- pwsh 7.6.9: 'PYTHONPATH=src python -c "print(1)"' -> 'Der Begriff „PYTHONPATH=src“ wird nicht als Name eines Cmdlets … erkannt', Exit 1
- git show HEAD:README.md:71-104 — Installations- und Quickstart-Befehle (git clone, pip install -e ., uvx …, python -m …) sind shellneutral, ohne &&, export oder $()

### Gaps

- Test- und Beitragsbefehle in README und CONTRIBUTING (EN/DE) laufen in PowerShell nicht, sind aber für Windows nicht als POSIX-only gekennzeichnet (medium)
- Die unterstützten Plattformen sind nicht an einer Stelle benannt (low)

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

`OPS-005` fragt, ob ein Check gelaufen ist. `OPS-006` fragt, ob sein Urteil hält. Dieser Check fragt nach dem Teil des Repos, den **überhaupt nichts ausführt**: die Befehle in README, `CONTRIBUTING` und Setup-Anleitung.

Sie sind Code. Sie werden von Menschen ausgeführt, meist genau einmal, meist von jemandem, der das Repo noch nicht kennt — und in dem Moment, in dem sie brechen, ist niemand da, der die Ursache erkennt. Anders als Code laufen sie in **keiner** Pipeline. Ein Repo kann eine grüne CI über vier Plattform-Matrix-Felder haben und eine Setup-Anleitung, die auf der Hälfte davon nicht startet.

**Der Fundort.** Dieses Repo bekam mit `mcp-audit-skill#70` einen Pre-Commit-Hook, dokumentiert in beiden READMEs mit:

```bash
pip install pre-commit && pre-commit install
```

Das Repo unterstützt Windows ausdrücklich: Die Testmatrix in `test.yml` fährt `windows-latest`, und der Quickstart trägt einen eigenen `powershell`-Block für `PYTHONUTF8`. In **PowerShell 5.1**, der Fassung, die auf Windows ohne Zutun installiert ist, ist `&&` kein Verkettungsoperator, sondern ein Syntaxfehler:

```
Die Verwendung von "&&" ist in dieser Version nicht zulässig.
```

Die CI blieb grün, weil sie den Befehl nie ausführt — auch nicht im `windows-latest`-Feld, das genau diese Plattform abdeckt. Die Anleitung war für einen Teil der behaupteten Zielgruppe schlicht nicht lauffähig, und aufgefallen ist es erst, als jemand beiläufig sagte, er arbeite in PowerShell. Behoben in `mcp-audit-skill#71`, zwei Zeilen statt einer Verkettung.

**Ein zweites Repo war unauffällig — und das ist die Pointe.** `swiss-snb-mcp` bekam denselben Hook am selben Tag, und seine `CONTRIBUTING`-Anleitung stand von Anfang an auf zwei Zeilen. Nicht aus Absicht: Es hat keine Windows-Matrix, niemand hatte die Frage gestellt. Die Plattformtauglichkeit war dort Zufall, nicht Ergebnis — und ein Zufall besteht diesen Check nur, solange er anhält.

**Warum das eine eigene Prüfdimension ist.** Es ist nicht `DRIFT-006` (Prosa widerspricht dem Code) — der Befehl widerspricht nichts, er läuft nur nicht. Es ist nicht `OPS-005` (Check nicht gelaufen) — hier ist gar kein Check vorgesehen. Die Frage lautet: **Deckt sich die Menge der Plattformen, die das Repo für sich behauptet, mit der Menge, auf denen seine eigenen Anweisungen laufen?**

Die Behauptung ist dabei selten explizit. Sie steht in einer Testmatrix, in einer `classifiers`-Zeile, in einem Satz «works on macOS, Linux and Windows», in einem `PYTHONUTF8=1`-Hinweis für Windows-Nutzer. Wer solche Signale setzt, hat die Plattform in seinen Geltungsbereich aufgenommen.

**Die häufigsten Brüche sind nicht exotisch.** `&&` und `||` (PowerShell < 7), `export VAR=…` (PowerShell kennt `$env:VAR`), einfache Anführungszeichen als Literal-Quoting, `/`-Pfade in Kontexten, die keine akzeptieren, `$(…)`-Substitution, `rm -rf`, Heredocs. Jeder davon ist beim Schreiben unsichtbar, weil der Autor in seiner eigenen Shell denkt.

`medium`: Ein gebrochener Setup-Befehl kostet keine Daten und öffnet keine Lücke — er kostet den ersten Kontakt mit dem Repo, und zwar bei genau den Leuten, die am wenigsten in der Lage sind, den Fehler einzuordnen. Für ein Repo, das Beiträge oder Nachnutzung will, ist das teuer; es ist nur nicht gefährlich.

**Adoptionsstufe `advisory`.** Der Check ist neu und trifft absehbar viele Repos, die eine Plattform beiläufig behaupten. Er meldet, blockiert aber nicht, bis ein Portfolio-Durchlauf zeigt, ob er richtig geschnitten ist — der in `SKILL.md` 2.3 dokumentierte Weg.

### Remediation

Aus dem Katalog (`checks/OPS-007.md`, Remediation), auf die Gaps oben anzuwenden:

1. Die behaupteten Plattformen aus allen drei Quellen zusammentragen (Prosa, Testmatrix, Paket-Metadaten) und an einer Stelle im README festschreiben.
2. Alle Code-Blöcke in Anleitungsdateien durchgehen — auch die übersetzten. Die Suchen aus Modus 2 sind der Einstieg, nicht das Ergebnis.
3. Verkettungen auflösen. Zwei Zeilen sind in jeder Shell gültig und lesen sich besser als ein Block mit Plattform-Fussnote.
4. Wo ein Befehl plattformspezifisch bleiben muss, beide Fassungen nebeneinander stellen und die Blöcke entsprechend auszeichnen.
5. Die Prüfung einmal gegen einen bekannt gebrochenen Befehl halten, bevor man sie für aussagekräftig hält.

### Effort Estimate

Katalog-Richtwert (checks/OPS-007.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — Pro Repo 10–30 Minuten. Der Aufwand liegt im Durchgehen der Anleitungsdateien, nicht im Korrigieren; die Korrektur ist meist ein Zeilenumbruch.
