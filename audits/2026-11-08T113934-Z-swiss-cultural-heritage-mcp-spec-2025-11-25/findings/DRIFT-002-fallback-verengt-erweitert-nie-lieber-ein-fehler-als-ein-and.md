## Finding: DRIFT-002 — Fallback verengt, erweitert nie — lieber ein Fehler als ein anderer Datensatz

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `DRIFT-002` |
| **PDF-Reference** | Custom (Portfolio-Fundstück meteoswiss-mcp#33, 2026-07-30) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Die Fuzzy-Fallbacks sind die zulässige, ausgewiesene Erweiterung (Feld plus Prosa, getestet). Nicht ausgewiesen ist allein der Datumsfilter. JSON trägt je Treffer date:null; das ist ein Indiz, kein Ausweis der Filterabweichung. Kein Fallback tauscht Quelle oder Entität.

### Expected Behavior

Aus dem Katalog (`checks/DRIFT-002.md`, Pass Criteria):

- [ ] Jeder Auswahl-Fallback liefert denselben Datensatz-Typ wie der Primärpfad (gleiche Granularität, gleicher Zeitbezug, gleiche Entität)
- [ ] Fallbacks, die die Semantik ändern, sind entweder entfernt oder in der Antwort ausgewiesen (Feld, nicht nur Prosa)
- [ ] Wo kein semantisch gleichwertiger Kandidat existiert, wird eskaliert statt substituiert
- [ ] Ein Test hält fest, dass der Nicht-Fund ein Fehler ist — nicht nur, dass der Fund funktioniert
- [ ] Die Auswahlfunktion begründet im Docstring, was sie bewusst **nicht** nimmt

### Evidence

- server.py:1418-1427 (heritage_search_artists), 1662-1669 (heritage_search_museum_datasets), 1985-2000 (heritage_search_helveticat, SRU '=' -> ' all ') — der Fuzzy-Retry erweitert die Treffermenge, ist aber als Feld ausgewiesen: match_type='fuzzy' (ResultEnvelope server.py:571) plus Markdown-Hinweis _FUZZY_NOTE (server.py:634-639)
- Mutation M5 (scratchpad/probe/mutate.py auf einer Kopie aus git archive HEAD): match_type nach dem Fuzzy-Retry auf 'exact' gesetzt -> neu rot: TestFuzzyMatch::test_artists_fuzzy_retry und ::test_artists_fuzzy_note_in_markdown
- server.py:2609-2627 _date_passes — bei gesetztem date_from/date_to werden undatierte Objekte AUFGENOMMEN ('lieber ein falsch-positiver Treffer als ein verlorener'); kein Antwortfeld meldet, dass der Filter auf diese Treffer nicht griff; die Feldbeschreibung server.py:2772-2781 sagt 'Nur ab diesem Jahr' ohne Hinweis; grep 'ndatiert' trifft nur den internen Docstring (2614)
- tests/test_server.py:1681 — der Test schreibt die Substitution fest (_date_passes(None,'1800','1899') is True); Mutation M6 (undatierte ausschliessen) -> nur dieser Test wird rot
- server.py:1536-1541 und 2270-2275 — records[0] nur nach einer ID-gepinnten Abfrage (HAUPTNR-Filter bzw. GetRecord-Identifier), das ist eine Drift-Wache, keine Substitution; server.py:329-338 _nb_prefix wählt das Profil je Set aus einer festen Karte, ohne Fallback auf 'irgendeinen Prefix'

### Gaps

- Der clientseitige Datumsfilter in search_heritage lässt undatierte Treffer durch, ohne Feld, das die Abweichung benennt; die Markdown-Ansicht zeigt bei ihnen unter 'Filter: Zeitraum …' gar kein Datum (medium)
- Kein Test hält fest, dass das Zeitfenster ohne passenden Treffer leer bleibt; der vorhandene Test verlangt das Gegenteil (medium)

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

Resilienz-Fallbacks sind Pflicht (Probe-Skill 3.1/3.5): Retry, Dump statt API, Cache statt Live. Alle diese lockern den **Weg** zum selben Datensatz. Es gibt aber eine zweite, verwandt aussehende Sorte, die etwas ganz anderes tut — sie lockert, **welcher Datensatz** geliefert wird:

```python
# gesucht: die 10-Minuten-Werte von heute
if not now_url:
    for _key, asset in assets.items():          # sonst halt irgendein CSV
        if asset["href"].endswith(".csv"):
            now_url = asset["href"]
            break
```

Das ist kein Fallback, sondern eine stille Substitution. Der Aufruf gelingt, die Antwort ist wohlgeformt, die Provenance stimmt formal — und der Inhalt beantwortet eine andere Frage als die gestellte. Für ein Modell ist das nicht erkennbar; es liest Tageswerte als Momentaufnahme.

**Der Fall** (`meteoswiss-mcp`, 2026-07-30): Der Selektor suchte `/now/` im Pfad, doch die Granularität steckt im Dateinamen (`ogd-smn_klo_t_now.csv`) — ein Verzeichnis `/now/` gibt es nicht, die Bedingung war unerfüllbar. Der Fallback nahm daraufhin das *erste* CSV im Item: `d_historical`, Tageswerte zurück bis 1980, ausgegeben unter der Überschrift «Aktuelle Beobachtungen». Verdeckt wurde das nur dadurch, dass ein URL-Fehler den Aufruf ohnehin vorher abbrechen liess (`DRIFT-001`). Ohne diesen zweiten Fehler hätte der Server jahrzehntealte Tageswerte als aktuelle Messung ausgeliefert.

Die Regel, die daraus folgt, ist unbequem, weil sie gegen den Reflex «lieber irgendwas als nichts» steht: **Wo die Semantik nicht mehr stimmt, ist ein Fehler das bessere Ergebnis.** Ein Fehler ist sichtbar und wird gemeldet. Ein semantisch falscher Datensatz wird zitiert.

### Remediation

Aus dem Katalog (`checks/DRIFT-002.md`, Remediation), auf die Gaps oben anzuwenden:

### Schritt 1: Fallbacks klassifizieren

Zwei Spalten: *lockert den Weg* (Retry, Dump, Cache — in Ordnung) und *lockert die Sache* (anderes Asset, andere Periode, andere Entität — prüfen).

### Schritt 2: Substitutionen auflösen

Entweder eskalieren oder ausweisen. Ausweisen heisst: ein Feld in der Antwort, das die Abweichung benennt — nicht ein Satz im Markdown, den ein JSON-Konsument nie sieht.

### Schritt 3: Den Nicht-Fund testen

Der Test, der fehlt, ist fast immer der über den leeren Kandidatensatz.

### Effort Estimate

Katalog-Richtwert (checks/DRIFT-002.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S–M — ein halber Tag pro Server. Das Klassifizieren geht schnell; die Entscheidung «eskalieren oder ausweisen» ist die eigentliche Arbeit.
