## Finding: OPS-009 — Herkunft der Fixture: aufgezeichnet, nicht ausgedacht

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | advisory |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `OPS-009` |
| **PDF-Reference** | Custom (Katalog-Lücke gegen mcp-data-fidelity-skill, 2026-08-07) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Eine starke Grundlage (Recorder, Hash, Schlüssel je Abfrage). Offen sind die Live-Verbindung Aufzeichnung <-> Quelle und die Datierung je Datei. Offene Frage, die das unterscheidet: Erzeugt 'scripts/record_fixtures.py' heute für artists_1.json denselben SHA-256 wie in PROVENANCE? Nicht ausgeführt, weil der Recorder ins Repo schreibt. Advisory.

### Expected Behavior

Aus dem Katalog (`checks/OPS-009.md`, Pass Criteria):

- [ ] Für **jeden** externen Endpunkt liegt mindestens eine Fixture vor, die von der echten Quelle stammt
- [ ] Jede solche Fixture trägt ein **Aufnahmedatum** — im Dateinamen, im Dateikopf oder in einer `PROVENANCE`-Datei daneben
- [ ] Die Herkunft nennt den **Endpunkt**, gegen den aufgenommen wurde, nicht nur «die API»
- [ ] Es gibt einen dokumentierten Weg, die Aufnahme zu **wiederholen** — ein Skript oder ein Befehl, nicht eine Erinnerung
- [ ] Antwort-Literale im Testcode stellen keinen externen Endpunkt dar; wo sie stehen, konstruieren sie einen Grenzfall, den die Quelle nicht liefert
- [ ] Ein Live-Test hält mindestens eine Aufnahme gegen die Quelle — auf der Ebene der Felder, die der Code liest
- [ ] **Gegenprobe:** Eine erfundene Antwort ist einmal danebengehalten worden und hat sich von der Aufnahme unterschieden. Ohne sie belegt der Vergleich nur, dass zwei Dateien gleich sind

### Evidence

- tests/fixtures/PROVENANCE.md:1-25 — 'Aufgezeichnet am 2026-09-20 mit PYTHONPATH=src python scripts/record_fixtures.py'; je Datei Werkzeug, angefragte URL als Schlüssel, Kürzung, Grösse, SHA-256 (z. B. artists_1.json -> https://ckan.opendata.swiss/api/3/action/datastore_search?resource_id=…&q=Giacometti)
- Aufgezeichnete Endpunkte: CKAN datastore_search (artists_1, artist_detail_1, cross_search_1), CKAN package_search (museum_datasets_1, cross_search_3), NB SRU (helveticat_1.xml, cross_search_2.xml), OAI ListSets (nb_collections_1.xml), OAI GetRecord (publication_1.xml), Memobase '/' und '/record/' (memobase_1, item_memobase_1), Dodis solr/query und solr/full (dodis_1, item_dodis_1). Nicht aufgezeichnet: OAI ListRecords (Grund genannt: 345 KB, scripts/record_fixtures.py:38) und heritage_browse_collection (datastore_search mit SNM-Ressource; nur Handmocks in tests/test_server.py)
- tests/test_recorded_fixtures.py:159-456 — Aufnahmedatum, Vollständigkeit der Provenance, SHA-256 und gleiche Aufrufe des Recorders geprüft, jedes Werkzeug liest seine Aufzeichnung (:314); keine Funktion mit @pytest.mark.live (grep 'mark.live' in der Datei ohne Treffer)
- git show --stat b079c99 (2026-09-20) — geändert nur cross_search_2/3, dodis_1, helveticat_1, memobase_1, museum_datasets_1, nb_collections_1, publication_1; artists_1.json, artist_detail_1.json, cross_search_1.json und item_*.json stammen inhaltlich aus 2464623 (2026-08-15), PROVENANCE nennt für alle ein Datum (2026-09-20)

### Gaps

- Kein Live-Test hält eine Aufzeichnung auf Feldebene gegen die heutige Quelle; keine Gegenprobe mit erfundener Antwort (medium)
- Ein Aufnahmedatum für das ganze Verzeichnis; ob die 08-15-Dateien am 09-20 inhaltsgleich neu aufgenommen wurden, lässt sich nicht unterscheiden (medium)
- heritage_browse_collection hat keine Aufzeichnung, nur handgeschriebene Mocks (low)
- Der Erneuerungsweg steht in PROVENANCE.md, nicht in CONTRIBUTING (low)

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

Ein handgeschriebener Mock kodiert die Annahme seines Autors. Er kann sie deshalb **prinzipiell** nicht widerlegen: Produktivcode und Fixture stammen aus demselben Kopf, zur selben Stunde, aus derselben Lektüre der Dokumentation. Wo beide irren, irren beide gleich — und die Suite bleibt dauerhaft grün.

Das ist keine Nachlässigkeit, sondern eine Eigenschaft der Konstruktion. Ein Test kann nur widerlegen, was er nicht selbst behauptet hat.

**Wie oft das schon zugeschlagen hat, steht bereits im Katalog:**

| Check | Was der Mock nicht bemerken konnte |
|---|---|
| `DRIFT-004` | dass der Endpoint verschwunden ist — der Mock antwortet weiter |
| `FID-006` | dass die Felder eine Ebene tiefer liegen — der Mock hat sie oben |
| `FID-006` | dass die Kopfzeile ihre Schreibweise gewechselt hat — der Mock trägt die alte |
| `FID-007` | dass eine Zählspalte `1 bis 5` enthält — der Mock schreibt Zahlen hinein |

Drei Checks, vier Fundstücke, **eine** Ursache. Jeder von ihnen sagt «gegen die echte Antwort prüfen», und keiner sagt, woher die Antwort kommt, die im Repo liegt. Der Skill `mcp-data-fidelity` nennt die Regel zweimal; der Katalog nirgends.

**Was dieser Check verlangt und was nicht.** Er verlangt **nicht**, dass Unit-Tests live gehen — `OPS-001` trennt Unit und Live aus guten Gründen, und die bleiben. Er verlangt, dass die Fixture, gegen die die Unit-Tests laufen, einmal von der **Quelle** kam und dass im Repo steht, **wann**. Danach ist sie ein eingefrorener Zeitpunkt statt einer Vermutung, und der Abstand zwischen Aufnahmedatum und heute ist eine lesbare Zahl statt eines Gefühls.

**Warum das Datum und nicht nur die Herkunft.** «Aufgezeichnet» ohne Zeitpunkt ist nach zwei Jahren von «ausgedacht» nicht mehr zu unterscheiden — die Datei sieht gleich aus, und niemand weiss, ob sie den Stand von gestern oder von vor drei Schema-Wechseln zeigt. Das Datum ist das, was aus einer Datei einen Beleg macht.

**Abgrenzung zu `DRIFT-004`.** Der verlangt, dass die Endpoint-**Konstanten** live verifiziert werden. Dieser Check verlangt, dass die **Antwort**, gegen die im Alltag getestet wird, eine Herkunft hat. Ein Server kann `DRIFT-004` erfüllen — der Live-Test läuft nightly und bestätigt die URL — und trotzdem hundert Unit-Tests gegen einen Mock fahren, den niemand je mit der Quelle verglichen hat.

**Abgrenzung zu `OPS-001`.** Der regelt die **Struktur** der Testlandschaft (Unit gemockt, Live gemarkert, CI-Trennung). Er sagt ausdrücklich «Unit-Tests verwenden `respx` für HTTP-Mocking» — und schweigt darüber, womit `respx` antwortet. Dieser Check füllt genau diese Stelle.

`high`: Er ist die gemeinsame Voraussetzung von vier bestehenden Checks. Wer ihn nicht erfüllt, erfüllt die anderen vier nur dem Wortlaut nach.

### Remediation

Aus dem Katalog (`checks/OPS-009.md`, Remediation), auf die Gaps oben anzuwenden:

1. Ein Aufzeichnungsskript schreiben (`scripts/record_fixtures.py`), das je Endpunkt die echte Antwort holt und mit Datum ablegt.
2. Einmal gegen alle Endpunkte laufen lassen. Die Diffs gegen die bisherigen Handmocks sind der eigentliche Ertrag — sie sind die Liste der Annahmen, die nie stimmten.
3. `PROVENANCE.md` anlegen: Datei, Endpunkt, Datum, Befehl.
4. Vor dem Commit prüfen, was aufgezeichnet wurde — Zugangsdaten und Personendaten gehören nicht ins Repo (`SEC-013`, `CH-002`). Eine Aufnahme wird redigiert, nicht erfunden; was entfernt wurde, gehört in den Dateikopf.
5. Den Weg im `CONTRIBUTING` nennen, damit die nächste Person nicht wieder von Hand schreibt.
6. Gegenprobe: eine erfundene Antwort danebenhalten und zeigen, dass der Vergleich sie verwirft.

### Effort Estimate

Katalog-Richtwert (checks/OPS-009.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

M — Pro Server 1–2 Tage. Das Skript ist schnell; die Zeit geht in die Diffs aus Schritt 2 und in das Redigieren aus Schritt 4.
