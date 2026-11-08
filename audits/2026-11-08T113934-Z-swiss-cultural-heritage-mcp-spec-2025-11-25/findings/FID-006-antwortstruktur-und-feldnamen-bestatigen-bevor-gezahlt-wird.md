## Finding: FID-006 — Antwortstruktur und Feldnamen bestätigen, bevor gezählt wird

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | advisory |
| **Check-Status** | fail |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `FID-006` |
| **PDF-Reference** | Custom (Portfolio-Fundstücke MCP Registry 2026-07 und zh-education-mcp / BISTA 2026-08-03) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Der Belegfall dieses Checks liegt hier in Produktion vor: Unit-Tests und Live-Suite sind gruen, waehrend die SIKART-Werkzeuge keine Namen und keine IDs mehr liefern und der Einzelabruf fuer jede ID scheitert. Die Huellen-Bestaetigung (CKAN, Dodis) ist vorhanden und gut gemacht, die Feld-Ebene darunter fehlt. Wann SIKART das Schema wechselte, ist nicht gemessen; belegt ist das alte Schema am 2026-09-20 (Fixture) und das neue am 2026-11-08.

### Expected Behavior

Aus dem Katalog (`checks/FID-006.md`, Pass Criteria):

- [ ] Der Wurzelpfad der Antwort wird bestätigt, bevor gezählt wird — kein `.get(<Wurzelschlüssel>, [])`, das eine Strukturabweichung in eine Leermenge umschreibt
- [ ] Die vom Code **gelesenen** Felder werden auf dem ersten Eintrag bestätigt, nicht nur die Hülle darum
- [ ] Eine Abweichung endet in einem eigenen Fehlertyp (`UpstreamSchemaError` o. ä.), nicht in einem gültigen leeren Result
- [ ] Die Fehlermeldung nennt die **tatsächlich vorhandenen** Schlüssel — ohne sie ist der nächste Schritt Raten
- [ ] Die Prüfung deckt ausschliesslich, was der Code anfasst; ein zusätzliches optionales Feld upstream lässt sie grün
- [ ] Kein Feldzugriff im Code trägt eine Schreibweise, die die Quelle bereits gewechselt hat, und Endpunkte derselben Quelle mit **unterschiedlicher** Schreibweise werden nicht mit je einem eigenen Literal bedient
- [ ] Hält die Quelle ihre Schreibweise nicht stabil, wird sie an **genau einer** Stelle normalisiert — dort, wo die Rohzeile entsteht, nicht verstreut an den Lesestellen; die Funktion begründet im Docstring, **warum** sie existiert, sonst wird sie beim nächsten Refactoring wegoptimiert
- [ ] Normalisiert wird nur die **Schreibweise**, nicht die Identität des Namens — `anzahl_total` und `anzahlTotal` bleiben verschieden
- [ ] Mindestens ein Test hält Struktur **und** Feldnamen gegen die **echte** Antwort, nicht gegen ein Fixture (`DRIFT-004`, `OPS-009`)
- [ ] **Gegenprobe:** Der Strukturtest ist einmal gegen eine um eine Ebene verschobene Antwort gelaufen und hat dort angeschlagen; wird normalisiert, ist er zusätzlich gegen die jeweils andere Schreibweise gelaufen und hat die Zeile dort gefunden

### Evidence

- Live 2026-11-08 11:46 UTC, datastore_search limit=0 auf der SIKART-Ressource ef3a9fd2-…: fields = _id, NUTZUNGSLIZENZ, ID, PERMALINK, NACHNAME_VORNAME, VORNAME_NACHNAME, PERSONENART, VITAZEILE, LEBENSDATEN, STARTDATUM(_TYP), ENDDATUM(_TYP), STARTORT(_TYP), ENDORT(_TYP), WEBSITE, WIKIDATA, GND, HLS, DOK (total 17665).
- src/swiss_cultural_heritage_mcp/server.py:1315-1332, :1459-1475, :1527, :1550-1567, :2519-2525 — der Code liest NAME, VORNAME, NAMIDENT, HAUPTNR, GEBURTSJAHR, STERBEJAHR, GEBURTSKANTON, STERBEKANTON, SIKART_LINK, GEBURTSDATUM, GEBURTSORT, GEBURTSLAND, STERBEDATUM, STERBEORT, STERBELAND, TYPUS, HLS_ID. 17 von 22 gelesenen Feldern fehlen in der echten Antwort (per Skript abgeglichen; vorhanden sind nur LEBENSDATEN, VITAZEILE, NUTZUNGSLIZENZ, GND, WEBSITE).
- Folge live: heritage_search_artists('Hodler') im Markdown -> '## (Unbekannt)' und '**SIKART-ID:** `—`' fuer jeden Treffer, heritage_cross_search ebenso '(Unbekannt)'; heritage_get_artist(artist_id='5000639' bzw. '4023584') -> ToolError 'API-Anfrage fehlgeschlagen (HTTP 409)'. Direkt: filters={"HAUPTNR":…} -> 409 'invalid value "HAUPTNR"', Positivkontrolle filters={"ID":5000639} -> 200, total 1. Kein eigener Fehlertyp, keine Meldung mit den vorhandenen Schluesseln.
- tests/fixtures/PROVENANCE.md:3 + artists_1.json/artist_detail_1.json/cross_search_1.json — aufgezeichnet 2026-09-20 mit dem alten Schema (HAUPTNR, NAME, VORNAME, …); die Hand-Fixture tests/test_server.py:82-117 ebenso. pytest -m live -> 11 passed: Kein Test haelt die gelesenen Feldnamen gegen die echte Antwort.
- src/swiss_cultural_heritage_mcp/server.py:2691-2693 — Memobase: members = data.get("hydra:member", []) und total = data.get("hydra:totalItems", len(members)) auf dem Wurzelpfad, genau das Fail-Pattern (das rg-Muster mit ':' im Schluessel trifft Zeile 2692; Kontrolle am synthetischen String -> 1).
- src/swiss_cultural_heritage_mcp/server.py:1252-1254, :1153 — SRU-numberOfRecords mit Default '0' und findall('.//srw:record'), OAI findall('.//oai:record'): eine Namensraum- oder Strukturaenderung wird still zu 0 Treffern.
- Positiv: src/swiss_cultural_heritage_mcp/server.py:670-714 UpstreamSchemaError + _ckan_result bestaetigen die CKAN-Wurzel und records/results, mit den vorhandenen Schluesseln in der Meldung; src/swiss_cultural_heritage_mcp/server.py:2736-2746 bestaetigt die Dodis-Wurzel; tests/test_response_shape.py:25-84 enthaelt Gegenproben gegen verschobene Huellen. Eine Bestaetigung der gelesenen Felder auf dem ersten Eintrag gibt es nirgends; rg '_normali[sz]e_keys|casefold\(\)|\.lower\(\)\s*:' -> 0 (Kontrolle am synthetischen String -> 1).

### Gaps

- SIKART-Schemawechsel in Produktion: 17 von 22 gelesenen Feldern fehlen, Namen und IDs verschwinden still, und heritage_get_artist ist fuer jede ID unbrauchbar (Severity critical).
- Die gelesenen Felder werden fuer keine Quelle auf dem ersten Eintrag bestaetigt (Severity high).
- Memobase-Wurzelpfad mit stillem Default .get('hydra:member', []) (Severity high).
- SRU/OAI: eine fehlende Struktur wird zu 0 Treffern statt zu einem UpstreamSchemaError (Severity medium).
- Kein Test haelt Struktur und Feldnamen gegen die echte Antwort; die Fixtures tragen das alte Schema und bestaetigen den Irrtum dauerhaft (Severity high).

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

`FID-003` behandelt die Leermenge bei **korrekter** Abfrage: Die Frage kam an, die Quelle hatte nichts. Dieser Check behandelt den Fall davor — die Abfrage war korrekt, und **der Leser war falsch**. Das Ergebnis sieht identisch aus, und genau darin liegt der Schaden.

**Belegfall (MCP Registry, 2026-07).** Eine Abfrage lieferte konsequent nichts. Die Anfrage war einwandfrei, die Antwort ebenso — nur liegen die gesuchten Felder unter `servers[].server.*`, und gelesen wurde eine Ebene höher. Der Code war syntaktisch fehlerfrei und semantisch blind:

```python
rows = payload.get("servers", [])
for row in rows:
    name = row.get("name")          # liegt in Wahrheit unter row["server"]["name"]
```

`.get(..., [])` macht aus **jeder** Strukturänderung stillschweigend ein gültiges leeres Ergebnis. Für das Modell ist das nicht von «die Quelle kennt das nicht» zu unterscheiden — dieselbe Konfabulations-Einladung wie in `FID-003`, nur mit einer Ursache, die kein Hinweis-Text der Welt behebt: Eine Wildcard hilft nicht gegen einen Pfad, der nirgendwohin zeigt.

**Zweiter Belegfall (`zh-education-mcp` / BISTA, 2026-08-03) — dieselbe Klasse, eine Ebene feiner.** Die Struktur muss sich nicht verschieben, damit der Leser ins Leere zeigt. Es genügt ein Buchstabe. Eine Quelle wechselte die Schreibweise ihrer CSV-Kopfzeile von `Schulgemeinde` auf `schulgemeinde`; der Code hatte die Grossschreibung fest verdrahtet:

```python
rows = [r for r in rows if r["Schulgemeinde"] == gemeinde]
```

Danach fand er nichts mehr und meldete «nicht gefunden» — vier von sechs Datensätzen, acht Tools, **alle Unit-Tests grün**. Ein Ausfall, der wie eine Antwort aussieht, ausgelöst durch einen Grossbuchstaben.

**Und die Schreibweise der Quelle ist nicht einmal in sich einheitlich.** Am selben Tag lieferten vier der sechs genutzten Endpunkte derselben Quelle klein, zwei gross — und zwei mischten **innerhalb einer einzigen Kopfzeile** (`gebiet_Bezeichnung`, `staatsangehoerigkeit_ISO2_Code`). Das ist der Grund, warum «auf die neue Schreibweise umstellen» keine Behebung ist: Es ist dieselbe feste Verdrahtung, nur in die andere Richtung, und beim nächsten Wechsel reisst sie dasselbe Loch. Wer sechs Endpunkte mit sechs verschiedenen Literalen bedient, hat sechs Annahmen, die alle **heute** stimmen.

**Deshalb hat dieser Check zwei Hälften, und sie greifen ineinander.** Bestätigen sagt, dass der Ausfall **auffällt**. Normalisieren sagt, dass er **nicht eintritt**. Wo die Quelle ihre Schreibweise nachweislich nicht stabil hält, reicht die erste Hälfte nicht: Ein Server, der pro Endpunkt streng auf die dort heute geltende Schreibweise prüft, hat sechs korrekte Prüfungen und scheitert beim nächsten Wechsel genauso vollständig wie vorher — nur eben laut statt leise. Die Normalisierung an der Parse-Grenze nimmt die Annahme aus dem Code heraus; die Bestätigung läuft danach gegen die normalisierten Namen weiter und bleibt die Auffanglinie für alles, was sich **nicht** normalisieren lässt: verschobene Ebenen, echte Umbenennungen, weggefallene Felder.

**Warum das kein eigener Check ist.** Es sah zunächst nach einem aus, und im Katalog stand dafür kurz `DRIFT-007`. Die beiden Fundstücke haben aber denselben Satz Ursachen (der Leser nimmt eine Form an, die er nie bestätigt), dieselbe Testgrenze (der Mock trägt die Annahme und bestätigt sie) und dasselbe Prüfobjekt: die Namen, die der Code anfasst. Zwei Checks, deren Pass-Kriterien einander zitieren müssen, sind ein Check mit zwei Abschnitten — und dieselbe Datei zweimal prüfen zu lassen, erzeugt Doppelbefunde, die niemand einzeln abarbeitet. Der Preis dieser Entscheidung steht in den Common Failures: Wer nur die Hülle bestätigt und die Schreibweise fest verdrahtet, ist hier **nicht** grün.

**Abgrenzung zu `DRIFT-002`.** Der liegt daneben, nicht darauf. Dort wird ein **anderer** Datensatz geliefert (stille Substitution), hier **keiner**. Beide sehen erfolgreich aus; die Fehlerbilder sind verschieden, und die Fixes auch.

**Abgrenzung zu `IDENT-001`.** Dort wird ebenfalls normalisiert, aber zum **Vergleich** eines Tokens mit einem Erwartungswert. Hier wird die **gelesene Datenstruktur** normalisiert, bevor irgendjemand sie anfasst.

**Was dieser Check ausdrücklich nicht verlangt.** Keine vollständige Schema-Validierung. Geprüft wird **nur, was der Code tatsächlich anfasst** — die Hülle bis zur gelesenen Ebene und die Felder, die danach ausgelesen werden. Alles darüber hinaus bricht bei jeder harmlosen Erweiterung upstream, und ein Validator, der bei einem neu hinzugekommenen optionalen Feld rot wird, ist nach dem zweiten Fehlalarm abgeschaltet. Ein zu strenger Wächter ist kein strenger Wächter, sondern gar keiner.

**Warum Tests diese Klasse prinzipiell nicht fangen.** Der Mock bildet die **angenommene** Form ab — dieselbe Annahme, die der Produktivcode trifft. Ein Fixture mit `{"servers": [{"name": ...}]}` bestätigt genau den Irrtum, den es widerlegen müsste, und bleibt dabei dauerhaft grün; ein Fixture mit `{"Schulgemeinde": …}` trägt die Schreibweise, die der Autor beim Schreiben des Mocks für richtig hielt, und bestätigt sie ebenso dauerhaft. Die Abweichung fällt nur gegen die echte Antwort auf. Das ist dieselbe Grenze wie in `DRIFT-004`, eine Ebene weiter innen: Dort kann ein Mock das Verschwinden eines Endpoints nicht bemerken, hier nicht die Umformung seiner Antwort. Woher eine Fixture kommen muss, damit sie das überhaupt könnte, steht in `OPS-009`.

### Remediation

Aus dem Katalog (`checks/FID-006.md`, Remediation), auf die Gaps oben anzuwenden:

```diff
+ _READ_FIELDS = ("name", "description", "version")
+
+
+ class UpstreamSchemaError(RuntimeError):
+     """Die Antwort kam an, sieht aber anders aus als der Code sie liest."""
+
+
+ def _rows(payload: dict) -> list[dict]:
+     if "servers" not in payload:
+         raise UpstreamSchemaError(
+             f"Antwort ohne `servers`. Vorhandene Schlüssel: {sorted(payload)}."
+         )
+     rows = payload["servers"]
+     missing = [f for f in _READ_FIELDS if rows and f not in rows[0]]
+     if missing:
+         raise UpstreamSchemaError(
+             f"`servers[0]` trägt {sorted(rows[0])}; es fehlen {missing}. "
+             "Liegen die Felder eine Ebene tiefer (z. B. unter `server`)?"
+         )
+     return rows
+
+
  async def search(query: str) -> SearchResult:
      payload = await client.get(REGISTRY_BASE, params={"search": query})
-     rows = payload.get("servers", [])
+     rows = _rows(payload)
      return build_result(rows)
```

Der Fehler gehört in den Fehlerkanal, nicht in ein Result mit `returned: 0` — dort trüge er den Leermengen-Hinweis aus `FID-003` und zeigte in die falsche Richtung.

Und wo die Quelle ihre Schreibweise wechselt, kommt die Normalisierung davor:

```diff
+ def _normalise_keys(row: dict) -> dict:
+     """Senkt die Spaltennamen einer Zeile auf Kleinschreibung.
+
+     Die Quelle schreibt ihre Kopfzeile nicht einheitlich und hat die
+     Schreibweise am 2026-08-03 gewechselt. Hier ist der einzige Ort, an
+     dem das einmal geschehen muss.
+     """
+     return {(k or "").lower(): v for k, v in row.items()}
+
+
  async def _fetch_csv(endpoint: str) -> list[dict]:
      resp = await _http_get(f"{BASE}/{endpoint}")
      resp.raise_for_status()
-     return list(csv.DictReader(io.StringIO(resp.text)))
+     reader = csv.DictReader(io.StringIO(resp.text))
+     return [_normalise_keys(row) for row in reader]


- hits = [r for r in rows if r["Schulgemeinde"] == gemeinde]
+ hits = [r for r in rows if r["schulgemeinde"] == gemeinde]
```

### Effort Estimate

M (1-3d) — Feldabbildung auf das neue SIKART-Schema (ID, NACHNAME_VORNAME, VORNAME_NACHNAME, PERMALINK, …), Filter von heritage_get_artist auf `ID`, Lizenz auf CC0 korrigieren, Fixtures neu aufzeichnen (mit Datum), Live-Test mit Feld-Assertion. Eingeschaetzt in der Audit-Sitzung, nicht aus dem Katalog.
