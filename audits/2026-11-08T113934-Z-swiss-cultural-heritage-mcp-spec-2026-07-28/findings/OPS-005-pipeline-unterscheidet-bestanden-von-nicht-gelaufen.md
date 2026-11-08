## Finding: OPS-005 — Pipeline unterscheidet «bestanden» von «nicht gelaufen»

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | advisory |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `OPS-005` |
| **PDF-Reference** | Custom (Portfolio-Fundstück mcp-continuous-auditor#29) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Tests laufen, und continue-on-error ist vorbildlich aufgelöst (geprüft per Mutation). Abzüge: Abhängigkeits-Skips und der Geltungsbereich des kopierten Skripts (fünfte Ausprägung des Checks). Advisory.

### Expected Behavior

Aus dem Katalog (`checks/OPS-005.md`, Pass Criteria):

- [ ] Mindestens ein committeter Workflow führt die Testsuite aus, ausgelöst durch `push` und `pull_request` — nicht nur als `.template` für andere Repos
- [ ] Jeder Schritt mit `continue-on-error`, bedingtem `if:` oder `|| true` hat eine **sichtbare Folge**, wenn er ausbleibt: eine Zeile im Bericht, ein Artefakt, eine Annotation
- [ ] Kein Test wird wegen einer fehlenden Abhängigkeit übersprungen, die CI installieren könnte
- [ ] `run:`-Blöcke mit Pipes setzen `pipefail`, sonst maskiert der letzte Befehl den Exit-Code
- [ ] Jedes Gate ist in beide Richtungen verifiziert: Es schlägt an, wenn es soll, und schweigt, wenn es soll
- [ ] Ein Artefakt, das zwischen Repos kopiert wird, ist gegen **jede** dort genutzte Werkzeug-Konfiguration geprüft — nicht nur gegen die lokale
- [ ] Linter und Formatter laufen über **alle** Verzeichnisse mit eigenem Code — insbesondere über `scripts/`, wo die Prüfskripte der übrigen Gates liegen
- [ ] Jeder konfigurierte Regelsatz wird von mindestens einem Workflow auch aufgerufen
- [ ] Kein Gate ist per Kommentar stillgelegt; wo es sein muss, existiert stattdessen ein verfolgbarer Eintrag
- [ ] Der Bericht unterscheidet «kein Befund» von «nicht geprüft»

### Evidence

- .github/workflows/ci.yml:3-7, :28-29 — committeter Workflow, ausgelöst durch push und pull_request auf main, fährt pytest; Lauf 41281505123 (2026-11-01) grün auf 3.11, 3.12 und 3.13
- .github/workflows/nightly-live.yml:36 continue-on-error mit sichtbarer Folge: :54-64 Einordnung clear/finding/unknown, :116-124 exit 1 bei != clear; die Pipe in :38-41 wird über set +e und ${PIPESTATUS[0]} ausgewertet. Mutationsprobe der Einordnung (scratchpad/probe/mutate_classify.py): 5 von 5 Mutationen (alle übersprungen -> clear, 0 Tests -> clear, fehlender Report -> clear, errors ignoriert, Zeilenumbruch nicht geglättet) machen je einen Test rot
- CI-Log 41281505123 — '413 passed, 2 skipped': tests/test_server.py::TestTracing::test_tool_span_records_name_and_is_error und ::test_init_tracing_instruments_httpx; Grund ist pytest.importorskip('opentelemetry.sdk') (test_server.py:1353, :1394), das Extra 'otel' (pyproject.toml:66-69) installiert die CI nicht
- ruff 0.16.9 (Pin) über die Kopie aus git archive HEAD: 'ruff format --check --line-length 88 scripts/' -> 2 Dateien würden umformatiert (scripts/check_version_sync.py:139, scripts/record_fixtures.py:157); bei 100, 110 und 120 formatgerecht. Kein Workflow-Schritt prüft die kopierte Datei gegen andere Breiten
- ci.yml:43, :46 — ruff check/format über src/ tests/ scripts/ (alle Code-Verzeichnisse ausser audits/, das eine historische gen_findings.py enthält); kein auskommentiertes Gate (grep '#.*(ruff|mypy|pytest).*(deaktiviert|disabled|TODO|vorerst|ausstehend)' rc=1)

### Gaps

- 2 Tests werden in der CI wegen einer fehlenden, installierbaren Abhängigkeit (otel-Extra) übersprungen (medium)
- scripts/check_version_sync.py, das portfolioweit kopierte Prüfskript, ist bei line-length 88 nicht formatgerecht, und kein Pipeline-Schritt erzwingt die Formatstabilität über die Breiten (medium)
- publish.yml:69-71 'curl -L … | tar xz' ohne pipefail und ohne curl -f; ein HTTP-Fehler wird nur indirekt über tar sichtbar (low)

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

Ein Check, der nicht gelaufen ist, sieht in jeder Zusammenfassung exakt aus wie einer, der bestanden hat. Grüner Haken, keine Meldung, weiter. Das ist keine Nachlässigkeit im Einzelfall, sondern eine Eigenschaft der Werkzeuge: CI-Oberflächen zeigen Fehlschläge, nicht Abwesenheiten.

`OPS-004` verlangt, dass ein Report Gemessenes von Geschlossenem trennt. Dieser Check zieht dieselbe Linie eine Ebene tiefer, in die Pipeline: **Was nicht gelaufen ist, muss sichtbar sein.**

Sechs Ausprägungen, alle real im Portfolio beobachtet. Die ersten vier sind Abdeckungslücken — etwas lief nicht. Die letzten beiden sind zu eng gefasste Geltungsbereiche: etwas lief, bestand, und belegte trotzdem weniger, als aus ihm gelesen wurde — einmal wegen der Konfiguration, einmal wegen der geprüften Pfade.

**Die ganze Suite lief nie.** `mcp-continuous-auditor` hatte über 150 Tests und keinen committeten Workflow, der sie ausführte — `ci.yml` lag als `.yml.template` für Zielrepos, der einzige aktive Workflow war ein Telegram-Job auf `schedule`. Eine Regression im Budget-Guard oder in der Broker-Pipeline wäre unangefochten nach `main` gelangt. 167 Workflow-Läufe in der Repo-Historie, kein einziger davon ein Test.

**Tests skippen wegen fehlender Abhängigkeit.** Drei Testklassen desselben Repos meldeten `skipped 'fastmcp not installed'`. Die Suite war grün, die Zusammenfassung sagte «OK», und drei Klassen hatten nichts geprüft. Ein Skip, den CI durch eine Installation verhindern könnte, ist kein Skip, sondern eine Lücke.

**`continue-on-error` ohne sichtbare Folge.** Ein Schritt darf scheitern — gut. Aber wenn sein Ausbleiben nirgends im Bericht auftaucht, ist die Abdeckung dieser Woche stillschweigend kleiner als letzte Woche, und niemand erfährt es.

**Der Exit-Code kommt vom falschen Befehl.** GitHub Actions führt `run:`-Blöcke unter Linux mit `bash -e` aus, **ohne** `pipefail`. In `python check.py | tail -4` bestimmt `tail` den Exit-Code; `check.py` darf mit 1 sterben, der Schritt wird grün. Genau das ist in diesem Portfolio passiert, beim Verifizieren eines Gates, das korrekt angeschlagen hatte.

**Der Check lief nur unter der eigenen Konfiguration.** Die vier oben sind Lücken — hier ist der Check gelaufen, hat bestanden und war korrekt. Falsch war, was aus ihm gelesen wurde: `ruff format --check .` belegt «formatgerecht *unter der `line-length` dieses Repos*», gelesen wird es als «formatgerecht». Für eine Datei, die zwischen Repos kopiert wird, ist das zu wenig — die Mechanik dahinter steht in `SKILL.md` unter «Portfolio-Hygiene: ein Commit, 33 Repos». `scripts/check_version_sync.py` hatte eine 99 Zeichen lange Zeile: bei 100 einzeilig und grün, bei 88 mehrzeilig und rot. Der Bruch entstand beim Kopieren, nicht beim Schreiben, und fiel erst im Zielrepo auf, wo er wie ein Fehler am Skript aussah.

Dass die Regel in `SKILL.md` steht, hat sie nicht durchgesetzt: Sie ist Anleitung für den, der ausrollt, und es gibt keinen Zeitpunkt, an dem etwas rot wird, wenn niemand sie liest. Genau diese Lücke schliesst der Check — nicht «kennt jemand die Regel», sondern «erzwingt die Pipeline sie». Dasselbe gilt für jedes Werkzeug mit repo-lokaler Konfiguration: Formatter-Breite, Linter-Regelsatz, `target-version`.

**Das Gate deckt nur einen Teil des Baums.** Ein Linter, der über `src/` läuft, meldet nichts über `tests/` und `scripts/` — und das liest sich in jeder Zusammenfassung wie «sauber». Im Portfolio prüften fast alle Repos nur `src/`. Als das Gate auf den ganzen Baum ausgeweitet wurde, kamen in fünf Repos **112 angesammelte Verstösse** hoch, von einem einzelnen mehrdeutigen Bezeichner bis zu 53 Befunden in einer Datei. Keiner davon war je gemeldet worden, weil nie jemand hingesehen hatte.

Besonders unangenehm ist dabei `scripts/`: Dort liegen im Portfolio genau die Prüfskripte, die in der CI anderer Gates laufen — `check_version_sync.py`, Snapshot-Vergleiche, Pin-Prüfungen. **Die Werkzeuge, die Regeln durchsetzen, waren selbst ungeprüft.** Zwei Sonderformen derselben Lücke traten daneben auf: Ein Repo hatte einen vollständigen Linter-Regelsatz in `pyproject.toml` und das Werkzeug in den dev-Abhängigkeiten, rief es aber in keinem Workflow auf — der Regelsatz galt für den, der lokal daran dachte. Ein anderes trug seinen abgeschalteten Formatcheck als Kommentar im Workflow: `# vorerst deaktiviert (Refactoring ausstehend)`. Eine Absichtserklärung ohne Termin, unsichtbar in jeder Zusammenfassung, und die einzige Spur einer bekannten Lücke.

`high`: Eine Lücke in der Abdeckung ist schlimmer als ein roter Build. Ein roter Build wird bearbeitet; eine Lücke wird geglaubt.

**Adoptionsstufe `advisory`.** Der Check ist neu und trifft mutmasslich einen Teil des Portfolios, das ihn noch nicht erfüllt. Er meldet, blockiert aber nicht, bis ein Portfolio-Durchlauf zeigt, ob er richtig geschnitten ist — der in `SKILL.md` 2.3 dokumentierte Weg.

### Remediation

Aus dem Katalog (`checks/OPS-005.md`, Remediation), auf die Gaps oben anzuwenden:

1. Prüfen, ob ein Workflow die Tests überhaupt ausführt. Wenn nicht, ist das der erste und grösste Fund — alles Weitere ist Feinarbeit daran.
2. Jeden Skip im Testlauf einordnen: Abhängigkeit installieren oder Skip als zulässig begründen.
3. Ein Gate ergänzen, das Abhängigkeits-Skips zum Fehlschlag macht, und es **einmal ohne die Abhängigkeit** laufen lassen, um zu sehen, dass es anschlägt.
4. `shell: bash -euo pipefail {0}` als `defaults.run` setzen.
5. Für jeden `continue-on-error`-Schritt eine Zeile ergänzen, die sein Ausbleiben benennt.
6. Kopierte Artefakte auflisten und hashen. Weichen die Kopien ab, eine kanonische Fassung bestimmen, die unter **allen** genutzten Konfigurationen besteht, und die übrigen daran angleichen. Danach einen Schritt ergänzen, der genau das erzwingt — sonst hält die Angleichung bis zur nächsten Bearbeitung.
7. Die geprüften Pfade auf alle Verzeichnisse mit eigenem Code ausweiten, `scripts/` zuerst. Die dabei hochkommenden Altlasten in einem **eigenen** Commit tilgen, getrennt vom Commit, der das Gate erweitert — sonst ist im Review nicht unterscheidbar, was Aufräumen und was Regeländerung ist. Wo ein Verstoss nicht auflösbar ist (etwa `E402` nach einem `sys.path`-Eingriff im Test), gehört statt einer Codeänderung ein begründeter `per-file-ignore` in die Konfiguration: sichtbar, versioniert und überprüfbar — anders als ein stillgelegter Schritt.

### Effort Estimate

Katalog-Richtwert (checks/OPS-005.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — Pro Repo 1–3 Stunden. Der Workflow ist schnell geschrieben; die Zeit geht in das Einordnen der Skips und die Gegenprobe der Gates.

Die fünfte Ausprägung ist einmalig teurer und danach billig: Die kanonische Fassung zu finden und portfolioweit anzugleichen kostete über 33 Repos rund einen halben Tag, der Workflow-Schritt danach zehn Minuten pro Repo.
