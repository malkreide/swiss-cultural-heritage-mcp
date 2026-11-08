## Finding: DRIFT-003 — Kein Test-Assert wird vom Degradationspfad erfüllt

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | enforced |
| **Check-Status** | fail |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `DRIFT-003` |
| **PDF-Reference** | Custom (Portfolio-Fundstück meteoswiss-mcp#33/#35/#37, 2026-07-30) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Für die meisten Einzelwerkzeuge greift die Absicherung strukturell: ein Upstream-Fehler wirft ToolError, also kann ein Erfolgstest den Fehlerpfad nicht erfüllen. Die Lücke liegt in der Quersuche (Fehler als Prosa) und bei Nicht-Fund- und Leerantworten, die wie Erfolg aussehen. Der Regex-Teil (Modus 3) ist sauber. Beide Gegenproben liefen am 2026-11-08 gegen den committeten Code (src im Arbeitsbaum = HEAD; git status zeigt nur README.md geändert).

### Expected Behavior

Aus dem Katalog (`checks/DRIFT-003.md`, Pass Criteria):

- [ ] Der Degradationspfad ist maschinell erkennbar (Statusfeld, oder ein dokumentierter, eindeutiger Marker)
- [ ] Jeder Test des Erfolgspfads schliesst den Degradationspfad **explizit** aus, bevor er Inhalt prüft
- [ ] Assertions prüfen Werte, die nur im Erfolgsfall vorkommen — keine Stichworte, die auch in der Fehlermeldung stehen
- [ ] Bereichs-Assertions (Koordinaten, Zeitfenster, Grössenordnungen) sind eng genug, dass ein plausibler Fehlgriff sie reisst
- [ ] Für jedes Tool existiert mindestens ein Test des **Erfolgspfads**, nicht nur der Fehlerpfade
- [ ] Prüfmuster, die als Regex ausgewertet werden (`match=`, `assertRaisesRegex`) und **wörtlich gemeint** sind, maskieren ihre Metazeichen — oder benutzen `re.escape`
- [ ] Wo ein Metazeichen **beabsichtigt** ist (Alternative, Gruppe, Quantor), ist die Absicht erkennbar — der Treffer ist dann kein Befund
- [ ] Jedes solche Muster ist einmal gegen eine Zeichenkette gehalten worden, die es ablehnen soll

### Evidence

- Gegenprobe scratchpad/probe/drift003_probe.py: heritage_cross_search mit SIK-ISEA, SNM und NB alle auf HTTP 503 liefert Markdown mit '## SIK-ISEA / ⚠️ Fehler: …' je Quelle, ohne isError. Ausgabe: 'assert SIK-ISEA in result: True | SNM: True | NB: True' — der Totalausfall erfüllt alle drei Assertions von tests/test_server.py:974-976 (test_cross_search_all_sources)
- Gegenprobe: Dodis /solr/full/44755 mit leerem Body -> 'Kein Dodis-Objekt gefunden für ID `44755`.'; Ausgabe "'44755' in result: True | 'doc_att_file_content' not in result: True" — beide Assertions von tests/test_server.py:2077-2081 (test_live_get_dodis_document) bestehen im Nicht-Fund. Live am 2026-11-08 liefert dieselbe ID 'Typ: Bundesratsprotokoll · Datum: 12.8.1921', also Werte, die der Test prüfen könnte
- tests/test_server.py:2055-2075 test_live_search_memobase/_dodis und :1965-1970 test_live_search_by_region prüfen nur isinstance(result, str); :1959-1962 und :1975-1978 prüfen nur 'Fehler' not in result, während server.py:1672-1675 bzw. _no_match (server.py:643-656) bei 0 Treffern 'Keine SNM-Datensätze gefunden…' ohne 'Fehler' liefert — ein leerer Lauf besteht
- server.py:951-961 _raise_tool_error und server.py:2904-2905 — in den Einzelwerkzeugen und in search_heritage ist der Totalausfall maschinell erkennbar (ToolError -> isError). In heritage_cross_search fehlt das: server.py:2504-2506 rendert den Fehler je Quelle als Prosa '⚠️ Fehler', auch wenn alle Quellen ausfallen
- grep -rnE 'match=' tests/*.py — kein Muster mit Metazeichen ('Allow-List', 'HTTPS', 'nicht erreichbar', 'Unbekannter SRU-Index', 'Fehler', 'schon maskiert', 'nicht gefunden'); dass der Metazeichen-Filter greift, zeigen die Treffer auf 'pytest.raises(' selbst

### Gaps

- Die Erfolgstests von heritage_cross_search prüfen Quellennamen, die auch im Degradationspfad stehen; die Gegenprobe zeigt, dass sie beim Totalausfall bestehen (high)
- Mehrere Live-Tests (test_live_get_dodis_document, test_live_search_memobase/_dodis, test_live_search_by_region, test_live_search_snm, test_live_search_hodler) bestehen auf dem Nicht-Fund- bzw. Leerpfad; keiner prüft einen Wert, den nur der Erfolgsfall hat (high)
- heritage_cross_search meldet den Ausfall aller Quellen nicht als isError, nur als Prosa-Marker (medium)
- Im Repo keine Gegenprobe je Tool (Modus 2), die zeigt, dass die Erfolgsassertions im Degradationspfad rot werden (medium)

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

Graceful Degradation ist Pflicht (`ARCH-003`, Probe-Skill 3.5): Fällt die Quelle aus, liefert der Server keine Exception ans Modell, sondern eine wohlgeformte Antwort mit Direktlinks und einem Hinweis. Das ist richtig — und hat einen Preis, den kaum jemand einpreist.

**Die Degradation verwandelt einen Ausfall in eine Antwort, die dem Erfolgsfall ähnelt.** Sie nennt dieselbe Station, denselben Ort, dieselben Stichworte. Jede Assertion, die nur auf solche Stichworte prüft, ist damit gegen genau den Ausfall blind, den sie fangen soll. Der Test läuft grün durch einen Totalausfall.

**Der Fall** (`meteoswiss-mcp`, 2026-07-30): Drei Tools lieferten nichts — `meteo_current` einen 404 für jede Station, `meteo_forecast` und `meteo_school_check` gar keine Daten. Die Testsuite war grün. Drei separate Tests waren so formuliert, dass der Degradationspfad sie erfüllte:

| Test | Assertion | Warum blind |
|---|---|---|
| `test_live_meteo_current_klo` | `"KLO" in result or "Zürich" in result` | Beides steht auch in der Fehlermeldung |
| `test_live_geocode_leutschenbach` | Koordinaten-Box `8.4 < lon < 8.7` | Die *falsche* Gemeinde (Dübendorf, 8.62) liegt darin |
| `meteo_forecast` | — | Der Erfolgspfad war überhaupt nicht getestet, nur Geocoding-Fehlerpfade |

Der zweite ist der lehrreichste: Die Assertion war nicht zu schwach für einen Ausfall, sondern zu schwach für einen **Fehlgriff**. Sie hätte auch dann bestanden, wenn der Server Wetter aus der Nachbargemeinde geliefert hätte.

**Die dritte Ausprägung sitzt eine Ebene tiefer: nicht im Inhalt der Assertion, sondern in ihrer Sprache.** Ein Prüfmuster wird als Text gelesen und als Regex ausgewertet:

```python
with pytest.raises(ReleaseError, match="summary.json not found"):
```

Der Punkt ist ein Metazeichen. Das Muster passt auf `summary.json not found` — und ebenso auf `summaryXjson not found`, auf `summary/json not found`, auf jede Meldung, die an dieser Stelle irgendein Zeichen trägt. Wer die Zeile liest, liest einen Dateinamen; was ausgeführt wird, ist eine Zeichenklasse.

Der Schaden ist derselbe wie bei den beiden Ausprägungen oben: Der Test besteht in Fällen, die er ausschliessen sollte, und sein Wortlaut sagt das Gegenteil. Er ist nur schwerer zu sehen, weil kein Ausfall nötig ist — die Lücke steht in der Assertion selbst. Aufgefallen ist der Fall nicht bei einer Testdurchsicht, sondern beim Anheben eines Lint-Regelsatzes (`RUF043`); vorher hatte ihn niemand als schwach gelesen, weil er sich nicht schwach liest.

Dieselbe Klasse trifft jede Prüfung, deren Argument eine eigene Sprache spricht und als Literal gelesen wird: `match=` in `pytest.raises` und `pytest.warns`, `assertRaisesRegex`, `re.search` auf einer Fehlermeldung, Glob-Muster in Dateizusicherungen. Die Frage ist immer dieselbe — **was von diesem Text ist Zeichen, und was ist Anweisung?**

### Remediation

Aus dem Katalog (`checks/DRIFT-003.md`, Remediation), auf die Gaps oben anzuwenden:

### Schritt 1: Degradation strukturiert machen

Wenn der Ausfall nur an einem Emoji oder einer deutschen Wendung erkennbar ist, zuerst das beheben — sonst hängt jede Testverschärfung an einem Textliteral:

```python
class ServerResponse(BaseModel):
    status: Literal["ok", "degraded", "unavailable"] = "ok"
    degraded_reason: str | None = None
```

### Schritt 2: Assertions umdrehen

Erst ausschliessen, dann prüfen. Der Ausschluss gehört in die **erste** Zeile nach dem Aufruf, nicht ans Ende.

### Schritt 3: Den Test testen

Einmal pro Tool die Gegenprobe aus Modus 2 schreiben. Sie ist der einzige Beleg, dass die Erfolgstests etwas prüfen — und sie kostet je fünf Zeilen.

### Schritt 4: Prüfmuster gegen ihre eigene Sprache halten

Jede Assertion durchgehen, deren Argument als Regex ausgewertet wird, und die Frage stellen, was davon Zeichen ist
und was Anweisung. Maskieren oder `re.escape` benutzen — und das Ergebnis einmal gegen eine Zeichenkette halten, die
es ablehnen soll. `RUF043` im Lint-Regelsatz nimmt den Durchgang künftig ab.

### Effort Estimate

Katalog-Richtwert (checks/DRIFT-003.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S–M — pro Server ein halber Tag. Der Aufwand steckt im Durchgehen der bestehenden Assertions, nicht im Schreiben der neuen.
