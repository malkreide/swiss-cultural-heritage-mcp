## Finding: FID-007 — Eine Zahlenspalte ohne Zahlen

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | advisory |
| **Check-Status** | fail |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `FID-007` |
| **PDF-Reference** | Custom (Portfolio-Fundstück zh-education-mcp / BISTA, 2026-08-03) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Die eigentliche Unterdrueckungsklasse (Marker wie '1 bis 5' in Zaehlspalten) trifft diesen Server nicht, weil er keine Datenzellen summiert. Die einzige Aggregation, die er bildet, zeigt aber genau das Anti-Pattern 'ausnehmen ohne kennzeichnen': eine zu tiefe Gesamtzahl, der man nichts ansieht. Deshalb fail statt pass.

### Expected Behavior

Aus dem Katalog (`checks/FID-007.md`, Pass Criteria):

- [ ] Jede Konvertierung eines Quellwerts in eine Zahl kennt den Fall «keine Zahl» und behandelt ihn ausdrücklich
- [ ] Eine unterdrückte Zelle wird **nicht** zu `0` — weder durch `or 0` noch durch einen `.get(…, 0)`-Default noch durch ein stillschweigendes `except`
- [ ] Eine unterdrückte Zelle bricht den Aufruf **nicht** ab; sie wird ausgenommen
- [ ] Das Tool-Result **nennt** die Zahl der ausgenommenen Zeilen — ohne sie ist die Summe von einer vollständigen nicht zu unterscheiden
- [ ] Der Hinweis sagt, in welche Richtung die Summe abweicht («die echten Werte liegen höher»), nicht nur, dass etwas fehlt
- [ ] Die bekannten Marker der Quelle sind an einer Stelle benannt, nicht über die Lesestellen verstreut
- [ ] Ein Live-Test hält die tatsächlich vorkommenden Nicht-Zahlen gegen diese Liste — welche Marker eine Quelle benutzt, weiss nur die Quelle
- [ ] **Gegenprobe:** Die stille Variante ist einmal danebengestellt worden und liefert dieselbe Zahl. Wer das nicht gezeigt hat, hält den Hinweis für Kosmetik

### Evidence

- src/swiss_cultural_heritage_mcp/server.py:2721-2747 — _search_dodis liefert als Gesamtzahl immer -1; src/swiss_cultural_heritage_mcp/server.py:2876-2885 known_total summiert nur Quellen mit total > 0; src/swiss_cultural_heritage_mcp/server.py:2911 total=known_total or None. Bei collection='all' ist `total` damit nur die Memobase-Zahl, ohne Kennzeichnung.
- Live 2026-11-08: search_heritage(query='Volksschule', collection='all', JSON) -> total=56, has_more=true, meta={'per_source': {'memobase': 5, 'dodis': 5}, 'errors': {}}, ohne Hinweis, dass Dodis nicht mitgezaehlt ist. Direkt: Memobase hydra:totalItems 56, Dodis solr/query mit rows=100 -> 100 Treffer (Seite voll). Das Feld heisst 'Gesamtzahl upstream verfügbar' (src/swiss_cultural_heritage_mcp/server.py:568) und ist eine Untergrenze, die sich als Summe ausgibt (>=156 statt 56).
- src/swiss_cultural_heritage_mcp/server.py:1659 res.get("count", 0), src/swiss_cultural_heritage_mcp/server.py:1807 result.get("total", 0), src/swiss_cultural_heritage_mcp/server.py:1252 int(numberOfRecords … or 0) — stille Null-Defaults auf Zaehlwerten der Quelle (das rg-Muster '\.get\([^)]*,\s*0\s*\)' trifft :1659 und :1807).
- Positiv: Datenzellen der Quellen werden nicht in Zahlen konvertiert. rg '\b(int|float)\(' in src/swiss_cultural_heritage_mcp/server.py trifft nur validierte Eingaben (:2623, :2625, Jahresmuster), Regex-Jahre (:2619), Retry-After (:811) und numberOfRecords (:1252); Datensaetze werden unveraendert durchgereicht (z. B. src/swiss_cultural_heritage_mcp/server.py:1441, :1823).

### Gaps

- search_heritage mit collection='all': `total` schliesst Dodis still aus und ist nicht als Untergrenze gekennzeichnet; eine Richtung wird nicht angegeben (Severity high).
- Stille 0-Defaults auf den Upstream-Zaehlern count/total/numberOfRecords statt eines Fehlers bzw. None (Severity medium).
- Keine Gegenprobe und kein Test zur Kennzeichnung ausgenommener Anteile (Severity medium).

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

Amtliche Quellen unterdrücken kleine Fallzahlen aus Datenschutzgründen. Statt der Zahl steht dann ein Bereich, ein Vergleich oder ein Platzhalter: `1 bis 5`, `<5`, `NULL`, `k.A.`, `*`, die leere Zelle. Die Spalte heisst weiterhin «Anzahl», ihr Typ ist weiterhin «Zahl» — nur ein Teil der Zellen ist keine.

Drei Verhaltensweisen sind möglich, und sie sind **nicht** gleich schlimm:

| Verhalten | Bewertung |
|---|---|
| `int("1 bis 5")` wirft, der Aufruf bricht ab | **laut und schlecht** — der Nutzende sieht «unerwarteter interner Fehler» und weiss nichts |
| als `0` zählen | **still und schlimmer** — die Summe bleibt plausibel, ist zu tief, und durch nichts als falsch erkennbar |
| ausnehmen **und** kennzeichnen | **richtig** |

Der mittlere Fall ist der eigentliche Gegenstand dieses Checks. Ein Absturz ist ein Ärgernis mit Fehlermeldung; eine stille Null erzeugt eine Zahl, die niemand anzweifelt, weil ihr nichts anzusehen ist. Das Modell liest sie als Summe, die Nutzenden lesen sie als Summe, und sie ist eine Untergrenze, die sich als Summe ausgibt.

**Belegfall (`zh-education-mcp` / BISTA, 2026-08-03).** Die Quelle schreibt bei kleinen Fallzahlen `1 bis 5` statt einer Zahl. Gemessen: **18.6 %** der Sek-I-Zeilen und **18.1 %** der Staatsangehörigkeits-Zeilen. Kein Randfall — fast jede fünfte Zeile. `int()` warf, und der Aufrufer sah davon nur «unerwarteter interner Fehler».

**Warum das keine Ausnahmebehandlung ist, sondern Datentreue.** Wer die Zeile ausnimmt, ohne es zu sagen, liefert dieselbe zu tiefe Zahl wie der, der `0` zählt — nur ohne den Umweg. Die Kennzeichnung ist der Check, nicht das Ausnehmen: Erst sie macht aus einer falschen Summe eine richtige Untergrenze.

**Abgrenzung — dieser Check schliesst eine Lücke zwischen zweien.** `FID-003` behandelt die **Leermenge**: Es kam nichts, und das muss von Abwesenheit unterscheidbar sein. `DRIFT-002` behandelt den **Fallback**, der klammheimlich einen anderen Datensatz liefert. Hier kommt der **richtige** Datensatz, vollständig, und ein Fünftel seiner Zellen trägt keinen Wert, der sich addieren lässt. Die Zeile ist da, die Zahl fehlt, und niemand fragt danach.

**Abgrenzung zu `FID-006`.** Der prüft, ob das Feld **am erwarteten Ort** liegt. Hier liegt es dort und trägt etwas anderes, als sein Name verspricht — die Struktur ist in Ordnung, der Inhalt hat eine Klasse, die der Leser nicht kennt.

`high`: Die Wirkung ist eine Zahl, die falsch ist und richtig aussieht. Genau die Klasse, gegen die die `FID`-Kategorie steht.

### Remediation

Aus dem Katalog (`checks/FID-007.md`, Remediation), auf die Gaps oben anzuwenden:

```diff
+ KNOWN_SUPPRESSION_MARKERS = frozenset({"1 bis 5", "<5", "NULL", "k.A.", "*", ""})
+
+
+ def _parse_count(value: object) -> int | None:
+     """Zahl aus einem Zählwert, oder ``None``, wenn keine da ist."""
+     raw = str(value if value is not None else "").strip()
+     return int(raw) if raw.isdigit() else None
+
+
+ def _sum_counts(rows: list[dict], field: str = "anzahl") -> tuple[int, int]:
+     """Summe und Anzahl der ausgenommenen Zeilen — beide, immer."""
+     values = [_parse_count(r.get(field)) for r in rows]
+     return sum(v for v in values if v is not None), sum(v is None for v in values)
+
+
- total = sum(int(r.get("anzahl") or 0) for r in rows)
- return f"Total: {total}"
+ total, suppressed = _sum_counts(rows)
+ note = _suppression_note(suppressed, len(rows))
+ return f"Total: {total}" + (f"\n\n> {note}" if note else "")
```

### Effort Estimate

Katalog-Richtwert (checks/FID-007.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — Pro Server 2–4 Stunden. Die Parse-Funktion ist vier Zeilen; die Zeit geht in das Auffinden aller Summenbildungen und in die Marker-Liste, die nur die Quelle kennt.
