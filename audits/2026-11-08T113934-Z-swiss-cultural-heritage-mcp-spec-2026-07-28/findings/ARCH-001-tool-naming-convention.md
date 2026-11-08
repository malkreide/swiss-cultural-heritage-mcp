## Finding: ARCH-001 — Tool Naming Convention

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `ARCH-001` |
| **PDF-Reference** | Sec 2.2 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Kriterien 2 und 3 (snake_case akzeptabel, keine Sonderzeichen) voll erfüllt, an der Laufzeit-Toolliste per Regex samt Negativkontrolle gemessen. Kriterium 1 (einheitliche Convention): Casing einheitlich, Wortstellung gemischt (8 vs. 3). Kriterium 4 für 9/11 erfüllt. Die Toolliste hängt nicht an der Protokollrevision, das Urteil gilt für beide.

### Expected Behavior

Aus dem Katalog (`checks/ARCH-001.md`, Pass Criteria):

- [ ] Eine einheitliche Naming-Convention im ganzen Repo
- [ ] Convention ist `camelCase` (bevorzugt) oder `kebab-case` / `snake_case` (akzeptabel)
- [ ] Keine Spaces, Punkte, Klammern, Sonderzeichen in Tool-Namen
- [ ] Tool-Beschreibungen enthalten Use-Case oder Kontext (nicht nur Funktion)

### Evidence

- Laufzeit `await mcp.list_tools()` (HEAD 9b3a1b4, venv mcp 2.3.0): 11 Tools, alle matchen `^[a-z][a-z0-9]*(_[a-z0-9]+)*$` (snake=True); Negativkontrolle derselben Regex: 'getUserInfo', 'get user', 'client.get' -> False
- src/swiss_cultural_heritage_mcp/server.py:1365,1501,1605,1762,1919,2150,2219,2355 — acht Tools mit Namensraum-Präfix vorn: heritage_search_artists, heritage_get_artist, heritage_search_museum_datasets, heritage_browse_collection, heritage_search_helveticat, heritage_list_nb_collections, heritage_get_publication, heritage_cross_search
- src/swiss_cultural_heritage_mcp/server.py:2798,3091,3214 — drei Tools mit Verb vorn und Namensraum hinten: search_heritage, get_heritage_item, list_heritage_collections; Casing einheitlich, Wortfolge nicht
- src/swiss_cultural_heritage_mcp/server.py:407-411 — INSTRUCTIONS müssen `heritage_cross_search` und `search_heritage` ausdrücklich auseinanderhalten ('Keiner von beiden erreicht die Quellen des anderen'); das verwechselbare Paar entsteht aus der gemischten Wortfolge
- src/swiss_cultural_heritage_mcp/server.py:1512 und src/swiss_cultural_heritage_mcp/server.py:2163 — heritage_get_artist (318 Zeichen) und heritage_list_nb_collections (268 Zeichen): je ein Funktionssatz plus Args/Returns, kein Kontext; die übrigen 9 Beschreibungen haben mehrere Sätze mit Quelle/Kontext (Median 799 Zeichen)

### Gaps

- medium: zwei Namensschemata nebeneinander (heritage_<verb>_<obj> vs. <verb>_heritage[_obj]); das Paar heritage_cross_search / search_heritage ist allein über den Namen nicht unterscheidbar, die Abgrenzung steht nur in INSTRUCTIONS
- low: 2 von 11 Tool-Beschreibungen (heritage_get_artist, heritage_list_nb_collections) nennen nur die Funktion, keinen Use-Case/Kontext

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

LLMs wählen Tools über semantische Entsprechung. Inkonsistente oder maschinenfeindliche Namen führen dazu, dass Tools ignoriert oder fehlerhaft angewandt werden. Die GPT-Tokenizer-Familie parst `camelCase`-Fragmente am effizientesten, gefolgt von `kebab-case` und `snake_case`. Spaces, Punkte und Klammern in Tool-Namen brechen Discovery und Parsing.

### Remediation

Aus dem Katalog (`checks/ARCH-001.md`, Remediation), auf die Gaps oben anzuwenden:

```diff
- @mcp.tool(name="get user info", description="Returns user data.")
+ @mcp.tool(
+     name="getUserInfo",
+     description=(
+         "Liefert Benutzer-Profildaten anhand der User-ID. "
+         "Use-Case: Bei Personalisierung von Antworten oder Audit-Logs. "
+         "Returnt JSON mit Feldern: id, email, role, lastLoginAt."
+     ),
+ )
```

### Effort Estimate

Katalog-Richtwert (checks/ARCH-001.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — Lokale Umbenennung im Code, ggf. Anpassung von Tests und Tool-Dokumentation. Bei publiziertem PyPI-Paket: Breaking Change, Major-Version-Bump.
