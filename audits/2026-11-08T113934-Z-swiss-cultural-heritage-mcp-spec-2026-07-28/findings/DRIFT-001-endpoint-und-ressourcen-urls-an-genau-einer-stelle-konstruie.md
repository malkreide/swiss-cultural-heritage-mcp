## Finding: DRIFT-001 — Endpoint- und Ressourcen-URLs an genau einer Stelle konstruiert

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `DRIFT-001` |
| **PDF-Reference** | Custom (Portfolio-Fundstück meteoswiss-mcp#33, 2026-07-30) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Erfüllt: Basis-Konstanten und die Kopplung der Fehlermeldung an den Abruf. Ein data_source_url-Feld gibt es nicht; die Provenance nennt SOURCE_*.url (Homepage), nicht die abgerufene URL. Befund ist die mehrfache Zusammensetzung derselben Pfade. 2 von 4 Kriterien erfüllt.

### Expected Behavior

Aus dem Katalog (`checks/DRIFT-001.md`, Pass Criteria):

- [ ] Jede Upstream-Ressourcen-URL wird an genau einer Stelle konstruiert (Funktion oder Methode)
- [ ] Fehlermeldung und Provenance rufen dieselbe Konstruktionsstelle wie der Abruf
- [ ] Basis-URLs liegen als Modul-Konstanten vor, nicht als wiederholte Literale
- [ ] Die Konstruktionsfunktion trägt einen Docstring, der die nicht offensichtlichen Regeln nennt (Kleinschreibung, kein Präfix, Encoding)

### Evidence

- src/swiss_cultural_heritage_mcp/server.py:267-273 — Basis-URLs als Modul-Konstanten (CKAN_API, NB_OAI_PMH, NB_SRU, MEMOBASE_API, DODIS_API), gespeist aus Settings server.py:70-91; im Abrufcode keine wiederholten Basis-Literale
- grep -nE '(CKAN_API|NB_OAI_PMH|NB_SRU|MEMOBASE_API|DODIS_API)' server.py — f"{CKAN_API}/datastore_search" an 4 Stellen zusammengesetzt (server.py:1407, 1524, 1796, 2394), f"{CKAN_API}/package_search" an 2 Stellen (1649, 2417); grep 'def _[a-z_]*url' in server.py ohne Treffer, also keine Konstruktionsfunktion
- server.py:2674 vs 3078 — Memobase-Permalink f"https://memobase.ch/de/document/{local}" zweimal als Literal; server.py:2713 vs 3044 — Dodis-Permalink f"https://dodis.ch/{hid}" zweimal; die Kopien weichen schon voneinander ab (Normalisierer mit Fallback `if local else SOURCE_MEMOBASE.url`, Markdown-Ansicht ohne)
- Laufzeit-Probe scratchpad/probe/drift003_probe.py (alle Upstreams 503): die Fehlermeldung nennt die tatsächlich abgerufene URL aus httpx ('Server error 503 ... for url https://ckan.opendata.swiss/api/3/action/datastore_search?resource_id=...'), Meldung und Abruf sind also gekoppelt

### Gaps

- Pfadstruktur datastore_search 4x und package_search 2x inline gebaut statt an einer Konstruktionsstelle (medium)
- Permalinks für Memobase und Dodis je zweimal als Literal, Fallback-Logik bereits auseinandergelaufen; Host wiederholt SOURCE_*.url als Literal (medium)
- Keine Konstruktionsfunktion mit Docstring zu Encoding- und Präfixregeln (low)

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

Die URL einer Upstream-Ressource wird selten nur einmal gebraucht. Typisch sind drei Stellen: der eigentliche Abruf, die Fehlermeldung im Degradationspfad («**STAC-Item:** …») und das `data_source_url`-Feld der Provenance. Wird sie dreimal geschrieben, ist sie dreimal falsch, sobald sie einmal falsch ist — und ein Fix an einer Stelle lässt die anderen stehen.

Der Schaden ist nicht der Tippfehler, sondern die **Widerlegbarkeit**: Die Fehlermeldung zeigt der Nutzerin die URL, die der Server angeblich abgerufen hat. Stimmt die mit der tatsächlich abgerufenen überein, weil beide aus derselben Quelle stammen, ist sie ein Beleg. Sind es Kopien, belegt sie nichts — und im Fehlerfall führt sie die Fehlersuche in die Irre, weil sie plausibel aussieht.

**Der Fall** (`meteoswiss-mcp`, 2026-07-30): Die STAC-Item-URL war an drei Stellen wortgleich ausgeschrieben, alle drei mit demselben Konstruktionsfehler (Collection-ID als Präfix vor der Item-ID). Jede Station lieferte 404. Die Fehlermeldung nannte dabei brav die falsche URL — sie stammte aus derselben Kopie. Im Issue-Report des Nutzers stand sie als vermeintliche Evidenz.

### Remediation

Aus dem Katalog (`checks/DRIFT-001.md`, Remediation), auf die Gaps oben anzuwenden:

### Schritt 1: Konstruktionsfunktion extrahieren

Eine Funktion pro Ressourcentyp, benannt nach ihr (`_smn_stac_item_url`, `_asset_url`). Die Regeln, die man nicht sieht, in den Docstring — Kleinschreibung, Präfixe, Encoding.

### Schritt 2: Alle Aufrufer umstellen

Auch die in Fehlermeldungen und Provenance. Das sind die, die man vergisst, weil sie nicht am Netzverkehr hängen.

### Schritt 3: Kopplung festhalten

Der Test aus Modus 2 kostet fünf Zeilen und hält die Provenance ehrlich.

### Effort Estimate

Katalog-Richtwert (checks/DRIFT-001.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — unter einer Stunde pro Ressourcentyp.
