## Finding: ARCH-003 — «Not Found» Anti-Pattern: Heuristiken statt leerer Antworten

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | enforced |
| **Check-Status** | fail |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `ARCH-003` |
| **PDF-Reference** | Sec 2.2 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Erfüllt: match_type-Feld vorhanden (Kriterium 2), Markdown-Leermenge mit Hinweistext (Kriterium 3 teilweise), keine sensiblen Daten (Kriterium 4 n/a). Verfehlt: Kriterien 5 bis 11. Unter 50 % -> fail. Das ist genau der Belegfall der Check-Definition ('Der Vorschlag wird gleich mitgesucht, seine Treffer landen unter results'). Die Docstrings dokumentieren das Verhalten offen ('wird automatisch breiter ... gesucht'), Dokumentation heilt den Befund aber nicht.

### Expected Behavior

Aus dem Katalog (`checks/ARCH-003.md`, Pass Criteria):

- [ ] Bei nicht-sensiblen Such-Tools: leere Ergebnisse triggern Fuzzy-Match oder Suggestion-Mechanismus
- [ ] Response enthält `match_type`-Feld oder ähnlich (exact / fuzzy / none)
- [ ] Bei `match_type == "none"`: ein actionable Hinweis (Vorschläge, andere Tools, Term-Verfeinerung)
- [ ] Bei sensiblen Tools: ausschliesslich exakte Lookups, kein Fuzzy-Fallback (dokumentiert)
- [ ] Pro Tool-Aufruf geht **genau ein** Upstream-Request raus, und sein Suchbegriff ist der des Aufrufers, **unverändert** — erhoben am Zähler der Route (Modus 3), nicht am Rückgabewert
- [ ] Vorschläge sind aus der Eingabe **abgeleitet** (Kürzung, Präfix), nicht aus einem Korpus-Vokabular geholt — letzteres ist eine zweite Abfrage in anderer Verpackung, mit eigenem Recall-Risiko
- [ ] Vorschläge unterhalb weniger Zeichen werden verworfen — ein Präfix, das den halben Bestand matcht, ist kein nächster Schritt («AG» ist kein Suchbegriff)
- [ ] Heuristische Treffer stehen in einem **eigenen** Feld, zusammen mit dem Begriff, der sie erzeugt hat — nie in derselben Liste wie die exakten
- [ ] Die Antwort **sagt**, dass nicht verbreitert wurde; ohne diesen Satz schliesst das Modell aus dem Schweigen, es sei schon alles versucht
- [ ] Das Testpaar aus Modus 3 ist **vollständig** vorhanden — eine Hälfte belegt, dass Vorschläge erscheinen, die andere, dass keiner davon abgefragt wurde
- [ ] **Gegenprobe:** Der Zähler ist einmal gegen eine Fassung gelaufen, die ihre Vorschläge selbst absucht, und hat dort angeschlagen. Ein Modus, der nur am korrigierten Server grün wird, prüft die Fixture

### Evidence

- Modus 3, Zähler auf der respx-Route (scratchpad/probe/arch003_counter.py): heritage_search_artists(query='Xyzzyqq', region='Nirgendwo') gegen leere Antwort -> route.call_count=2, gesendete q-Werte ['Xyzzyqq Nirgendwo', 'Nirgendwo']; Kontrolle mit Treffer-Antwort ('Hodler','Bern') -> call_count=1, ['Hodler Bern'], match_type exact. Der Zähler schlägt also an
- Modus 3, heritage_search_museum_datasets(query='Xyzzyqq Plonk') gegen leere Antwort -> call_count=2, zweite Abfrage '(Xyzzyqq* OR Plonk*) organization:schweizerisches-nationalmuseum-snm', ein Begriff, den der Aufrufer nie geschickt hat
- src/swiss_cultural_heritage_mcp/server.py:1420-1425 — Fuzzy-Retry ruft `_query(max(q_terms, key=len))` erneut ab; src/swiss_cultural_heritage_mcp/server.py:1436-1444 — die Treffer daraus landen unter `results` desselben Envelopes, nur `match_type='fuzzy'` daneben
- src/swiss_cultural_heritage_mcp/server.py:1664-1668 (SNM: OR-Präfix-Wildcards) und src/swiss_cultural_heritage_mcp/server.py:1993-1999 (Helveticat SRU: relation ' all ') — dasselbe Selbst-Verbreitern in zwei weiteren Tools
- src/swiss_cultural_heritage_mcp/server.py:643-656 — `_no_match` liefert im JSON-Modus `ResultEnvelope(count=0, results=[], match_type='none')` ohne `suggestions` und ohne Hinweis, ob verbreitert wurde; gemessene Leer-Antwort: {'count': 0, 'total': 0, 'match_type': 'none', 'results': [], 'meta': None}
- tests/test_server.py:1200-1221 und 1253-1268 — die Tests sichern das Selbst-Verbreitern ab (Handler liefert Treffer nur für den zweiten, veränderten Begriff und erwartet match_type 'fuzzy'); das Testpaar 'Vorschläge erscheinen' + 'genau ein Request mit unverändertem Begriff' fehlt

### Gaps

- medium: bei Leermenge gehen pro Tool-Aufruf zwei Upstream-Requests raus, der zweite mit verändertem Begriff (heritage_search_artists, heritage_search_museum_datasets, heritage_search_helveticat)
- medium: heuristische Treffer stehen unter `results`, nicht in einem eigenen Feld mit dem erzeugenden Begriff; das Modell kann sie nicht von exakten Treffern trennen
- medium: keine aus der Eingabe abgeleiteten `suggestions`; der JSON-Leer-Envelope ist ohne handlungsfähigen Hinweis
- low: die Antwort sagt nie, mit welchem Begriff verbreitert wurde; _FUZZY_NOTE (src/swiss_cultural_heritage_mcp/server.py:635-640) nennt den Ersatzbegriff nicht
- medium: Testpaar aus Modus 3 und Gegenprobe gegen eine selbst-suchende Fassung fehlen; die vorhandenen Tests zementieren das Anti-Pattern

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

LLMs reagieren empirisch nachweisbar empfindlich auf negativ-framing in Tool-Responses. Eine Antwort wie `"No results found"` oder `[]` ohne Kontext führt häufig zu einer von zwei Failure-Modes:

1. **Halluzination:** Das Modell konstruiert eine Antwort aus Trainingsdaten, statt zuzugeben, dass es keine Information hat.
2. **Sackgasse:** Das Modell bricht die Aufgabe ab, statt mit alternativen Strategien (verwandte Begriffe, andere Tools) weiterzumachen.

Der Best-Practice-Standard fordert: Wenn ein Tool keine exakten Treffer findet, soll es **partielle / heuristische / verwandte Ergebnisse** zurückgeben, gepaart mit explizitem Hinweis auf die fehlende Exaktheit. Damit kann das Modell:

- Verwandte Resultate dem User anbieten
- Den Suchbegriff verfeinern
- Ein anderes Tool wählen

**Ausnahme:** Bei hochsensiblen Daten (Personendaten, Zugriffskontrollen) ist «not found» korrekt — Heuristiken könnten Information leaken, die das Modell sonst nicht hätte. Beispiel: `getUserMedicalRecord("nonexistent")` darf NICHT «hier ist ein ähnlicher Datensatz» liefern.

### Vorschlagen ist nicht Erweitern — und bis v2.1.0 hat dieser Check nur das eine geprüft

Die Forderung oben lässt offen, **wie** das Tool zu seinen Vorschlägen kommt. Der bequeme Weg ist, die kürzere Variante des Begriffs gleich selbst abzufragen und ihre Treffer zurückzugeben. Die Antwort sieht dann besser aus, und sie beantwortet einen Begriff, den der Aufrufer nie gewählt hat.

**Die Eigenschaft, die dabei bricht:** *Keine Zeile im Resultat darf einem Begriff zuzuschreiben sein, den der Aufrufer nicht geschickt hat.* Für das Modell ist ein so entstandener Treffer von einem echten nicht zu unterscheiden — `match_type: "fuzzy"` steht daneben, aber es sagt *dass* geraten wurde, nicht *welche Zeile zu welchem Begriff gehört*. Liegen beide Sorten in derselben Liste, fehlt die Zuordnung, und der Hinweis daneben ändert daran nichts.

Dieselbe Fehlerform wie in `DRIFT-002` («Fallback verengt, erweitert nie»), eine Ebene weiter: dort wird ein anderer **Datensatz** substituiert, hier eine andere **Abfrage**.

**Beide Modi dieses Checks lasen bis v2.1.0 die Antwort** — Empty-Result-Pattern im Quelltext, `match_type`-Feld, handlungsfähiger Hinweis. Keiner mass, was **rausgegangen** ist. Ein Server, der seine eigenen Vorschläge still selbst absucht, bestand den Check; das Pass-Pattern von Modus 1 führte es sogar vor, indem es `fuzzy` unter `results` mischte und Vorschläge über `popular_terms_starting_with(query[:3])` aus einem Korpus holte — eine zweite Abfrage, die niemand angefordert hatte. Beides ist unten korrigiert.

**Belegfall (Portfolio, 2026-08):** [`amtsblatt-mcp`](https://github.com/malkreide/amtsblatt-mcp), beide Hälften desselben Vorgangs. **0.20.0** lehnte Kriterium 1 ausdrücklich ab und begründete das mit «bankruptcy notices, debt-collection summonses, estate calls, construction objections» — Rubriken, die die Allow-Liste `GREEN_RUBRICS` des Servers gerade ausschliesst und die über kein Tool erreichbar sind. Die Ausnahme aus Kriterium 4 wurde damit für genau die Menge beansprucht, auf die Kriterium 1 anzuwenden gewesen wäre. Die Begründung stand in beiden `SECURITY`-Dateien, im CHANGELOG und im abschliessenden PR; gefangen hat sie erst das [Re-Audit vom 2026-07-30](https://github.com/malkreide/amtsblatt-mcp/blob/main/audits/2026-07-30T105205-Z-amtsblatt-mcp/findings/ARCH-003.md), und zwar nicht durch einen Modus, sondern durch Lesen der Rubrik-Listen. **0.22.0** hat es umgesetzt — Vorschläge sind Kürzungen des eigenen Begriffs, der Server fragt keine davon ab.

**Bemerkenswert an der Reihenfolge dort:** Der Test «es geht genau ein Request mit dem unveränderten Begriff raus» existierte **lange vor** dem Vorschlagsmechanismus. Der Server war damit nachweislich unschädlich und nachweislich nutzlos. Eine Hälfte allein liest sich wie Disziplin und ist keine — deshalb verlangt Modus 3 unten beide, sonst prämiert der Check den Zustand, der Kriterium 1 gerade verfehlt.

**Abgrenzung.** `FID-003` prüft, ob die Leermenge **eindeutig und handlungsfähig** ist; dort ist Verbreitern der ausdrücklich empfohlene nächste Schritt — nur trifft die Entscheidung darüber der Aufrufer. Dieser Check prüft, ob der Server sie ihm abnimmt. `DRIFT-004` warnt umgekehrt davor, mit einem Mock die eigene Annahme über die Quelle festzuschreiben; das gilt hier nicht, denn Prüfgegenstand ist das Verhalten des Servers, nicht die Quelle — siehe die Begründung unter Modus 3.

### Remediation

Aus dem Katalog (`checks/ARCH-003.md`, Remediation), auf die Gaps oben anzuwenden:

```diff
  @mcp.tool()
  async def find_school(name: str) -> list:
      results = await db.find(name)
-     if not results:
-         return []
+     if not results:
+         # Vorschläge sind Kürzungen des eigenen Begriffs — abgeleitet, nicht
+         # abgefragt. Es geht genau ein Request raus, und der trug `name`.
+         suggestions = [v for v in shorter_variants(name) if len(v) >= 4]
+         return {
+             "results": [],
+             "match_type": "none",
+             "suggestions": suggestions,
+             "note": (
+                 f"Keine exakten Treffer für '{name}'. Es wurde nicht "
+                 f"selbstständig verbreitert — gesucht wurde nur '{name}'. "
+                 f"Die Vorschläge sind Kürzungen davon und ungeprüft."
+             ),
+         }
      return {"results": results, "match_type": "exact"}
```

Wer statt des Vorschlags-Arms den **Fuzzy-Arm** nimmt, hält die Eigenschaft nur mit einem getrennten Feld:

```diff
- return {"results": fuzzy[:5], "match_type": "fuzzy"}
+ return {
+     "results": [],                       # leer: nichts beantwortet `name`
+     "match_type": "fuzzy",
+     "heuristic": {"produced_by": fuzzy.term, "entries": fuzzy.entries[:5]},
+ }
```

Verboten ist die Vermischung, nicht die Hilfe.

### Effort Estimate

Katalog-Richtwert (checks/ARCH-003.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — Pro Tool ~30 Minuten. Bei 10 Such-Tools: 1 Tag.

Modus 3 kostet einmalig mehr, wenn der Server noch keinen Mock-Layer für seinen Upstream-Client hat: Dann ist der Zähler nicht zwei Assertions, sondern erst eine Testverdrahtung. Existiert der Layer, sind es zwei Tests von je zehn Zeilen — und ohne sie ist der Rest dieses Checks am Rückgabewert erhoben, also an der Seite, die der Fehler nicht berührt.
