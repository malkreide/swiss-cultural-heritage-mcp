## Finding: FID-003 — Leermenge von Abwesenheit unterscheidbar — keine Konfabulations-Einladung

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `FID-003` |
| **PDF-Reference** | Custom (Portfolio-Fundstück termdat-mcp#11) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Der Fehlerkanal ist sauber getrennt, und es gibt keine Ausreden-Formulierungen. Die Leermenge selbst ist im strukturierten Modus aber stumm, und an zwei Stellen sind die Kanaele vertauscht (Waechter -> Leermenge, echte Leermenge -> Fehler). MRTR/input_required wird nicht genutzt (rg 'input_required|inputRequests|elicit' -> 0), die Disjunktheits-Kriterien fuer 2026-07-28 entfallen daher fuer beide Protokollstaende.

### Expected Behavior

Aus dem Katalog (`checks/FID-003.md`, Pass Criteria):

- [ ] Ein leeres Result trägt ein maschinenlesbares Feld mit dem nächsten Schritt (`hint`, `next_step` o. ä.), nicht nur `returned: 0`
- [ ] Der Hinweis nennt **konkrete** nächste Versuche (Wildcard, Feld-Erweiterung, andere Sprache), keine Allgemeinplätze
- [ ] Keine Tool-Description enthält eine Formulierung, die eine Leermenge erklärt, entschuldigt oder als wahrscheinlich korrekt darstellt
- [ ] Falls ein Scope-Caveat inhaltlich nötig ist, fordert es zum Nachfassen auf, statt eine Schlussfolgerung zu lizenzieren
- [ ] Die Description sagt explizit, dass keine geratene Antwort an die Stelle eines fehlenden Treffers treten darf
- [ ] `not_found`-Verdikte (z. B. in QA-/Check-Tools) sind als «nicht in dieser Quelle» formuliert, nie als «falsch»
- [ ] Transport- und Autorisierungsfehler (Verbindungsabbruch, Timeout, 401/403, `421 Invalid Host header`, 5xx) enden im Fehlerkanal, nie als Result mit `returned: 0`
- [ ] Der Fehlerpfad trägt seinen eigenen nächsten Schritt — Konfiguration und Credentials prüfen —, nicht den Leermengen-Hinweis dieses Checks
- [ ] Auf `2026-07-28`, sofern das Tool `input_required` zurückgeben kann: Eine Rückfrage trägt **keinen** `hint` — sonst zeigt der nächste Schritt auf die Query, während gar nicht gesucht wurde
- [ ] Auf `2026-07-28`: Eine Rückfrage lässt `entries` **weg** statt es leer zu setzen — ein leeres `entries` ist bereits die Aussage «nichts gefunden»
- [ ] Auf `2026-07-28`: Eine Leermenge trägt **kein** `inputRequests` — sonst beschafft der Client eine Eingabe und retryt ins Leere

### Evidence

- src/swiss_cultural_heritage_mcp/server.py:643-654 — _no_match liefert im JSON-Modus ResultEnvelope(count=0, total=0, results=[], match_type='none') OHNE Hinweisfeld; der Hinweistext existiert nur im Markdown-Modus, und das Envelope (src/swiss_cultural_heritage_mcp/server.py:563-579) hat kein hint-/next_step-Feld. Live 2026-11-08: heritage_search_artists, heritage_search_museum_datasets und heritage_search_helveticat mit 'zzqxjv…' im JSON-Modus liefern keinen Hinweis.
- Live, Markdown: SIKART -> 'Keine Künstler·innen gefunden für die angegebenen Suchkriterien.' (kein naechster Schritt); search_heritage -> '*Keine Treffer für die angegebenen Kriterien.*' (src/swiss_cultural_heritage_mcp/server.py:2939-2941); heritage_cross_search -> '*Keine Treffer*' je Quelle (src/swiss_cultural_heritage_mcp/server.py:2514-2516). Nur Helveticat sagt konkret, was gesucht wurde und wohin man weitergehen kann (src/swiss_cultural_heritage_mcp/server.py:2040-2054).
- src/swiss_cultural_heritage_mcp/server.py:1973-1982 + Live: heritage_search_helveticat ohne query und set_spec (JSON) -> {count: 0, total: 0, match_type: 'none', results: []}. Eine Anfrage, bei der gar nicht gesucht wurde, ist im JSON nicht von einem Null-Treffer zu unterscheiden.
- src/swiss_cultural_heritage_mcp/server.py:990-1012 + Live: set_spec='xrara', from_date='2099-01-01' -> der Upstream antwortet 'noRecordsMatch: ... results in an empty list' (eine echte Leermenge). Das Tool meldet sie als ToolError mit 'Das ist KEIN leeres Ergebnis — es wurde nichts durchsucht.' Die Leermenge ist damit als isError maskiert, und die Aussage ist falsch.
- src/swiss_cultural_heritage_mcp/server.py:922-961, :1483-1484 — Transport- und HTTP-Fehler gehen in den Fehlerkanal (ToolError -> isError) mit eigener Meldung, nicht als Leermenge; src/swiss_cultural_heritage_mcp/server.py:2903-2905: fallen alle Quellen aus -> isError; ein Teilausfall steht in meta.errors bzw. im Warnblock (src/swiss_cultural_heritage_mcp/server.py:2507-2509, :2936).
- rg -n -i -U 'usually\s+means|bedeutet\s+meist|wahrscheinlich\s+nicht|out\s+of\s+scope|not\s+that\s+it\s+is\s+wrong' src/swiss_cultural_heritage_mcp/server.py -> 0 Treffer (rc=1); Kontrolle: 'usually means' trifft FID-003.md 5-mal. Keine Description enthaelt eine entschuldigende Formulierung.
- rg -n -i 'nicht raten|keine geratene|erfund|guess' src/swiss_cultural_heritage_mcp/server.py -> 0 Treffer: Keine Description sagt, dass keine geratene Antwort an die Stelle eines fehlenden Treffers treten darf.
- Live: heritage_cross_search JSON mit 0 Treffern in allen Quellen -> match_type='exact', count=0, meta=None (src/swiss_cultural_heritage_mcp/server.py:2493-2497 setzt match_type nicht).

### Gaps

- Der JSON-Modus (der Modus mit outputSchema) traegt bei einer Leermenge keinen maschinenlesbaren Hinweis, nur match_type='none' (Severity high).
- Die Markdown-Hinweise bei SIKART, SNM, search_heritage und cross_search sind generisch und nennen keinen konkreten naechsten Versuch (Severity medium).
- OAI-noRecordsMatch auf einem Zeitfenster wird als Fehler gemeldet, mit der falschen Aussage 'es wurde nichts durchsucht' (Severity medium).
- Die Validierungs-Waechter in heritage_search_helveticat liefern im JSON-Modus eine Leermenge statt eines Fehlers (Severity medium).
- heritage_cross_search meldet bei 0 Treffern match_type='exact' (Severity low).
- Keine Description verbietet, einen fehlenden Treffer durch eine Vermutung zu ersetzen (Severity medium).
- Im Repo gibt es weder einen Konfabulations-Test (Modus 2) noch einen Test, der einen Fehlschlag am laufenden Server gegen eine Leermenge haelt (Modus 3).

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

Ein leeres Tool-Result ist mehrdeutig. Es kann heissen: der Begriff existiert nicht; die Query war zu eng; der Scope war eingeschränkt; die Syntax passte nicht. Das Modell sieht `[]` und muss raten — und es rät nicht neutral, sondern entlang dessen, was die Tool-Description ihm nahelegt.

Genau dort lag der zweite, schwerwiegendere Teil des Portfolio-Falls. Die `search_terms`-Description von `termdat-mcp` enthielt:

> *«Scope caveat: TERMDAT holds administrative nomenclature, not domain vocabulary. An empty result usually means the term is out of scope, not that it is wrong.»*

Der Satz war als Ehrlichkeit gemeint. Faktisch war er eine vorformulierte Ausrede für das eigene Schweigen. Im gemeldeten Transkript hat das Modell die Leermenge mit diesem Caveat kombiniert und eine plausible, vollständig erfundene Erklärung produziert — die Schweiz verwende auf Bundesebene *Quellenabzug* statt *Quellensteuer* —, für einen Begriff, der die ganze Zeit in der Datenbank stand. Das Modell hat nicht halluziniert, weil es schlecht war. Es hat halluziniert, weil das Werkzeug ihm eine Erklärung mitgeliefert hat und keinen nächsten Schritt.

Daraus folgt eine Regel, die über Fehlerbehandlung hinausgeht: **Tool-Beschreibungen sind eine Halluzinations-Oberfläche.** Eine Formulierung, die eine Leermenge erklärt oder entschuldigt, erzeugt Konfabulation zuverlässiger als eine fehlende Formulierung. Der Unterschied zwischen «X bedeutet meist Y» und «versuche Z, dann melde Abwesenheit» ist der Unterschied zwischen einer erfundenen und einer korrekten Antwort.

Abgrenzung zu OBS-001/OBS-002: Dort geht es um Fehler — laut, sichtbar, mit Status-Code. Hier geht es um den erfolgreichen Aufruf mit leerem Ergebnis. Der ist gefährlicher, weil ihn nichts als Problem markiert.

**Diese Abgrenzung gilt in beide Richtungen.** Ein Transport- oder Autorisierungsfehler ist keine Leermenge und darf nie als solche formatiert werden. Für die aufrufende Schicht sieht ein abgewiesener Request aus wie ein Fehlschlag ohne Daten — wer nur prüft, ob Datensätze da sind, reicht ihn als Leermenge durch. Gemessener Fall: Eine Anfrage mit fremdem Host-Header bekommt `HTTP 421` mit dem Body `Invalid Host header` (zur Ursache siehe `SEC-016` und `SEC-024`). Daraus wird ein Result mit `returned: 0` — und, wenn dieser Check sonst sauber umgesetzt ist, mit genau dem Hinweis von oben: Wildcard versuchen, Felder erweitern. Das Modell bekommt eine Aussage über den Bestand, wo eine über die Konfiguration hingehört, und der nächste Schritt zeigt in die falsche Richtung. Ein Konfigurationsfehler unterläuft damit genau den Check, der das Raten verhindern soll.

Die Regel dahinter ist dieselbe wie bei der Maskierung in der Gegenrichtung: Der Fehlerkanal und die Leermenge beantworten zwei verschiedene Fragen. Null Treffer heisst «die Quelle hat nichts» und setzt voraus, dass die Abfrage angekommen ist. Ist sie das nicht, ist der nächste Schritt ein anderer — Endpoint, Host-Header und Credentials prüfen, nicht die Suche verbreitern.

**Der dritte Ausgang — und er ist der gefährlichste, weil er erfolgreich aussieht.** Auf der Baseline `2026-07-28` beendet MRTR eine Bearbeitung mit einer Rückfrage statt mit einem Ergebnis (`HITL-006`): HTTP 200, wohlgeformtes Result, keine Treffer darin. Damit gibt es drei disjunkte Zustände, die sich an genau **einem** Feld unterscheiden müssen:

| Zustand | Kennzeichen | Nächster Schritt für das Modell |
|---|---|---|
| **Rückfrage** | `resultType: "input_required"`, `inputRequests` gesetzt, `entries` **fehlt** (nicht: ist leer) | Die verlangte Eingabe beschaffen und den Request wiederholen |
| **Null-Treffer** | normales Result, `entries: []`, `hint` nach diesem Check | Query verbreitern — Wildcard, weitere Felder |
| **Fehler** | `isError` | Konfiguration prüfen: Endpoint, Host-Header, Credentials |

`entries` fehlt bei der Rückfrage, statt leer zu sein: Ein leeres `entries` **ist** die Aussage «nichts gefunden», und wer sie neben `input_required` stellt, behauptet zwei Dinge gleichzeitig. Ein Konsument, der nur auf `len(entries)` schaut — und das tun die meisten —, liest die Rückfrage dann als Null-Treffer.

Die beiden Vermischungen kosten in verschiedene Richtungen. Ein `hint` auf einer Rückfrage schickt das Modell zur Wildcard, **während gar nicht gesucht wurde** — der Hinweis dieses Checks wird zur Falschaussage über einen Bestand, den niemand abgefragt hat. Ein `inputRequests` auf einer Leermenge lässt den Client ins Leere retryen: Er beschafft eine Eingabe, wiederholt den Request und bekommt dieselbe Leermenge, weil nie etwas gefehlt hat.

### Remediation

Aus dem Katalog (`checks/FID-003.md`, Remediation), auf die Gaps oben anzuwenden:

```diff
  """Search the database for official designations.
+
+ `search_term` is Lucene syntax: `*`, `?` and `~` work. Matching is on whole
+ words — a compound is not found by its parts. Reach for a wildcard before
+ concluding a term is absent.

- Scope caveat: an empty result usually means the term is out of scope,
- not that it is wrong.
+ Scope caveat: the source holds administrative nomenclature, so a term may
+ genuinely be absent. Establish that with a wildcard retry, not from a single
+ empty result, and never fill the gap with a guessed designation.
  """
-     return SearchResult(returned=len(entries), entries=entries)
+     return SearchResult(
+         returned=len(entries),
+         hint=_EMPTY_HINT if not entries else None,
+         entries=entries,
+     )
```

Und auf dem Fehlerpfad, damit der Hinweis oben nur dann greift, wenn die Abfrage auch angekommen ist:

```diff
      try:
          entries = await client.search(term)
-     except httpx.HTTPError:
-         entries = []          # 421/401/403 wird zu «nichts gefunden»
+     except (httpx.HTTPStatusError, httpx.RequestError) as exc:
+         raise UpstreamUnreachableError(
+             f"Die Quelle hat die Abfrage nicht beantwortet ({exc}). Das ist "
+             "keine Leermenge: Der Request wurde abgewiesen, bevor gesucht "
+             "wurde. Endpoint, Host-Header und Credentials prüfen — eine "
+             "breitere Query hilft hier nicht."
+         ) from exc
      return build_result(entries)
```

### Effort Estimate

Katalog-Richtwert (checks/FID-003.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — Pro Tool 15–30 Minuten. Der Aufwand liegt im Formulieren, nicht im Code.
