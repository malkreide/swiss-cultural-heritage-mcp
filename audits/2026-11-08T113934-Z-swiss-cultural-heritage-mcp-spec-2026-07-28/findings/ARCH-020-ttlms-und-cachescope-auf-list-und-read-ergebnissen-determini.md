## Finding: ARCH-020 — ttlMs und cacheScope auf List- und Read-Ergebnissen, deterministische Reihenfolge

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | advisory |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `ARCH-020` |
| **PDF-Reference** | SEP-2549 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Nur fuer 2026-07-28. Felder auf allen fuenf Methoden, Werte im zulaessigen Vorrat, public nur ueber aufruferunabhaengigen Listen (Public Open Data) — am Draht belegt. Reihenfolge ueber Prozessgrenzen stabil, aber nicht sortiert und nicht getestet; der Pagination-Schnitt ist ungesichert. Rund die Haelfte der anwendbaren Kriterien erfuellt -> partial.

### Expected Behavior

Aus dem Katalog (`checks/ARCH-020.md`, Pass Criteria):

- [ ] `ttlMs` und `cacheScope` liegen auf allen fünf Methoden an, sofern der Server sie bedient
- [ ] `ttlMs` ist begründet gewählt, nicht 0 und nicht willkürlich gross — ein Wert oberhalb der Änderungsfrequenz der Quelle liefert veraltete Werkzeuglisten
- [ ] Jeder gesetzte `cacheScope` trägt **einen der zwei Werte aus SEP-2549** — `"public"` oder `"private"`. Erhoben am ausgelieferten Result (Modus 2), nicht nur am Quelltext: Ein Literal kann auf dem Weg nach draussen noch durch ein Mapping laufen
- [ ] `cacheScope: "public"` steht ausschliesslich über aufruferunabhängigen Inhalten
- [ ] Bei `data_class != "Public Open Data"`: `resources/read` liefert `"private"`, und ein Test hält das fest
- [ ] `tools/list` liefert eine deterministische Reihenfolge, über **Prozessgrenzen** hinweg geprüft
- [ ] Die Reihenfolge stammt aus einer expliziten Sortierung, nicht aus der Registrierungsreihenfolge — letztere ändert sich mit jedem Refactoring des Imports
- [ ] Sofern der Server Query-Resultate paginiert: Der Sortierschlüssel ist **total** — bei Gleichstand entscheidet ein eindeutiger Zusatzschlüssel, nicht die Quelle
- [ ] Sofern paginiert: Ein Test über zwei aufeinanderfolgende Seiten belegt leere Schnittmenge **und** vollständige Vereinigung, gegen einen Bestand grösser als eine Seite
- [ ] Sofern der Server Datenresultate mit `ttlMs` versieht: Der Wert ist aus `source_freshness` abgeleitet (publizierte Kadenz, `Last-Modified`, `Cache-Control`) und auf die nächste Publikation gedeckelt — bei unbekannter Kadenz kurz, nicht komfortabel
- [ ] **Gegenprobe:** Der Reihenfolgetest ist einmal gegen eine Fassung mit `set`-Iteration gelaufen und hat dort angeschlagen; wo paginiert wird, ist der Seitentest einmal gegen einen nicht-totalen Sortierschlüssel gelaufen und hat dort angeschlagen; und die Werteprüfung ist einmal gegen ein Result mit `cacheScope: "session"` gelaufen und hat dort angeschlagen

### Evidence

- server.py:390-396 CACHE_HINTS: tools/list, resources/list, resources/templates/list, prompts/list, server/discover je CacheHint(ttl_ms=300_000, scope='public'); Begruendung server.py:374-388 (Listen beim Import fest, keine Filterung nach Aufrufer; resources/read bewusst ohne Hinweis).
- Laufzeit HTTP 2026-07-28 (scratchpad/probe_modern.out): tools/list, prompts/list, resources/list, resources/templates/list, server/discover -> ttlMs 300000, cacheScope 'public'; resources/read heritage://sik-isea/overview -> ttlMs 0, cacheScope 'private'. Alle Werte im Vorrat {public, private}. stdio: tools/list und server/discover ebenfalls ttlMs 300000/public.
- tests/test_cache_hints.py:24-76 — ueber echte Client(mcp)-Session: tools/list, resources/list, prompts/list = LIST_CACHE_TTL_MS/public; resources/read = 0/private; Negativkontrolle MCPServer('kontrolle') ohne Hinweise -> 0/private.
- Reihenfolge: 4 frische Prozesse mit PYTHONHASHSEED=random, random, 1, 12345 -> identischer Hash cc65e045d4cf1603 der 11 Tool-Namen; Negativkontrolle: ein set derselben Namen wechselt die Ordnung zwischen Seeds 1/2/3. names == sorted(names) -> False: die Ordnung ist Registrierungsreihenfolge (heritage_search_artists ... list_heritage_collections), keine explizite Sortierung.
- Paginierung: offset/limit an die Quelle (server.py:1403, 1650 'start', 1791, 2687, 2726) ohne Sortierparameter; rg 'sort' server.py trifft nur sorted()-Aufrufe in Fehlermeldungen/Allow-List (700, 711, 2744, 3529-3530), kein sort=/order_by im Request — die Muster-Negativkontrolle schlaegt an (sorted(...) gefunden).
- Datenresultate tragen kein ttlMs (CacheHints nur auf Protokollmethoden; tools/call-Ergebnis ohne ttlMs) — Kriterium zu source_freshness gegenstandslos.

### Gaps

- tools/list-Reihenfolge stammt aus der Registrierungsreihenfolge, nicht aus einer expliziten Sortierung; kein Test ueber Prozessgrenzen und keine Gegenprobe gegen set-Iteration im Repo (stabil nur gemessen, nicht gebunden).
- Paginierte Query-Tools (SIKART, SNM, Memobase, Dodis, Helveticat-SRU) senden keinen totalen Sortierschluessel; bei Gleichstand (Relevanz-Score) entscheidet die Quelle je Abruf — Risiko doppelter/verlorener Datensaetze beim Blaettern. Kein Zwei-Seiten-Test (Schnittmenge + Vereinigung).
- resources/read liefert ttlMs 0 (Common Failure 'ttlMs: 0 als sicherer Wert'); die Ressourcen sind statische Uebersichtstexte. Bewusst begruendet (server.py:385-387), aber ohne Frischehinweis.
- Keine Gegenprobe der Werteprufung gegen cacheScope 'session' im Repo.

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

Zwei Änderungen, die dieselbe Sache betreffen — was ein Client mit einer Antwort tun darf, nachdem er sie erhalten hat.

**`CacheableResult` (SEP-2549, Pflicht).** Fünf Methoden tragen neu zwei Felder: `tools/list`, `prompts/list`, `resources/list`, `resources/read` und `resources/templates/list`. `ttlMs` ist ein Frischehinweis in Millisekunden; `cacheScope` ist `"public"` oder `"private"` und entscheidet, ob eine zwischengeschaltete Instanz mitcachen darf. Die beiden ersetzen `listChanged` nicht, sie ergänzen es.

**Deterministische Reihenfolge (Minor #3, SHOULD).** `tools/list` soll eine stabile Reihenfolge liefern, damit clientseitiges Caching und Prompt-Caching greifen.

**Warum das zusammen einen Check bildet und nicht zwei.** Beide Anforderungen sind wertlos, solange die andere fehlt: Ein `ttlMs` von 300 000 über einer Liste, die bei jedem Aufruf anders sortiert ist, veranlasst den Client, fünf Minuten lang eine Reihenfolge zu behalten, die keine Aussage trägt — und das Prompt-Caching bricht bei jedem Aufruf trotzdem. Umgekehrt nützt eine stabile Reihenfolge wenig, wenn kein Frischehinweis das Nachfragen bremst. Der Fix ist derselbe Handgriff an derselben Stelle, und §2.5 verlangt, dass ein Check in **einem** Schritt behebbar bleibt.

**Der stille Fehler ist ein dritter Wert.** `cacheScope` ist ein geschlossener Vorrat aus zwei Einträgen. Wer `"session"`, `"caller"` oder `"none"` sendet, meint meistens etwas Vernünftiges — «enger als öffentlich» — und liefert trotzdem etwas Schemawidriges: Eine Zwischeninstanz kennt den Wert nicht und behandelt ihn wie ein fehlendes Feld. Der vorsichtig gemeinte Wert ist damit **weiter** als `"private"`, nicht enger. Ein erfundener Wert ist kein vorsichtiger Wert.

Bis v2.1.0 hat dieser Check das nicht gesehen: Seine Kriterien fragten, ob `"public"` an der richtigen Stelle steht — ein Wert, der weder `"public"` noch `"private"` ist, bestand sie deshalb ohne Weiteres, und zwar auf allen fünf Methoden. **Belegfall (Portfolio, 2026-08):** `mcp-data-fidelity-skill` lieferte in `reference/patterns.py` einen Copy-Paste-Baustein mit `Literal["public", "session"]` aus, samt Testrezept `assert result.cache_scope == "session"`. Dieser Baustein ist für die datenabfragenden Server des Portfolios der Einstieg; dort korrigiert in PR #10. Kein Kriterium dieses Katalogs hätte einen Server gemeldet, der ihm gefolgt ist — das ist die Lücke, die diese Fassung schliesst.

**Der teure Fehler ist `cacheScope: "public"` an der falschen Stelle.** Bei einem Server mit `data_class != "Public Open Data"` erlaubt `"public"` einer Zwischeninstanz, die Antwort für andere Aufrufer aufzubewahren. Wenn `resources/read` mandantenbezogene Inhalte liefert, ist das kein Performance-Detail, sondern eine Freigabe. Das ist der Grund, warum dieser Check trotz `medium` eine `critical`-Nachbarschaft hat: Der Schaden liegt nicht in der Kategorie Caching, sondern in `CH-001` und `SEC-023`.

### Dieselben zwei Grössen auf Datenresultaten — und dort schärfer

Beide Anforderungen sind oben an den Protokoll-Methoden formuliert. Dieselben zwei Grössen — **ein totaler Sortierschlüssel** und **ein begründeter `ttlMs`** — entscheiden bei Query-Resultaten über die Vollständigkeit der Antwort, und dort kostet ihr Fehlen mehr als einen kalten Cache. Das ist keine zweite Regel, sondern derselbe Handgriff an derselben Stelle mit grösserer Wirkung; deshalb steht es hier und nicht in einem eigenen Check.

**Der Pagination-Schnitt.** Bei instabiler Ordnung wechselt ein Datensatz zwischen dem Abruf von Seite 1 und dem von Seite 2 seine Position — und erscheint dadurch **doppelt oder gar nicht**. Das ist Recall-Verlust: dieselbe stille Unvollständigkeit wie in `FID-001`, nur beim Blättern statt beim Filtern, und sie tritt bei **korrekt gesendeten Parametern** auf. Kein Fehler wird gemeldet, keine Zahl sieht falsch aus; der fehlende Datensatz hinterlässt keine Spur. Ein Sortierschlüssel, der nicht total ist (`ORDER BY datum` bei mehreren Einträgen pro Tag), genügt dafür bereits — bei Gleichstand entscheidet die Quelle je Abruf neu.

**`ttlMs` aus der Quellen-Frische.** Für Datenresultate reicht «kein Wert oberhalb der Änderungsfrequenz» nicht als Begründung, weil die Frequenz hier nicht geschätzt, sondern erhoben wird: aus `source_freshness` — publizierte Kadenz, `Last-Modified`, `Cache-Control` —, gedeckelt auf die **nächste Publikation**. Eine Quelle, die dienstags um 09:00 publiziert, verträgt am Montag einen langen und am Dienstag um 08:55 einen sehr kurzen Wert; ein fester Mittelwert ist an beiden Tagen falsch. **Unbekannte Kadenz heisst kurzer Wert, nicht komfortabler** — die andere Richtung liefert veraltete Daten unter dem Anschein von Frische.

**Bekannte Lücke, ausdrücklich benannt.** Dieser Check trägt `spec_baseline: 2026-07-28`. Der Pagination-Verlust existiert aber auch auf `2025-11-25`: Er hängt an der Quelle und am Sortierschlüssel, nicht am Protokollstand. Ein Server der alten Baseline wird deshalb **nicht** dagegen gemessen, obwohl der Fehler dort auftreten kann. Die Lücke bleibt bewusst offen, statt sie durch `spec_baseline: beide` zu schliessen: Das Feld gilt pro Datei, nicht pro Kriterium — der ganze Check auf `beide` würde `ttlMs` und `cacheScope` gegen Server messen, deren Protokoll diese Felder nicht kennt, und dort einen Falsch-Fail erzeugen, genau wo der Check schweigen soll. Wenn die Reihenfolge-Hälfte eine eigene Reichweite verdient, wird sie ein eigener Check — beim Abschluss von Migrations-Welle D, wenn ohnehin über den Verbleib der Kohorte entschieden wird, und nicht als stille Ausweitung heute.

### Remediation

Aus dem Katalog (`checks/ARCH-020.md`, Remediation), auf die Gaps oben anzuwenden:

```python
TOOLS_TTL_MS = 300_000          # 5 min: Werkzeugliste ändert sich mit Releases

@server.list_tools()
async def list_tools() -> ToolsListResult:
    return ToolsListResult(
        tools=sorted(REGISTRY.values(), key=lambda t: t.name),   # explizit
        ttlMs=TOOLS_TTL_MS,
        cacheScope="public",     # Werkzeugliste ist für alle Aufrufer gleich
    )

@server.read_resource()
async def read_resource(uri: str) -> ResourceReadResult:
    return ResourceReadResult(
        contents=await _impl.read(uri),
        ttlMs=60_000,
        # Inhalte sind aufruferbezogen — keine geteilte Zwischenspeicherung
        cacheScope="private",
    )
```

```python
def test_tool_order_survives_a_restart(run_in_fresh_process):
    a = run_in_fresh_process("tools/list", env={"PYTHONHASHSEED": "random"})
    b = run_in_fresh_process("tools/list", env={"PYTHONHASHSEED": "random"})
    assert [t["name"] for t in a] == [t["name"] for t in b]
```

Und dieselben zwei Grössen auf dem Datenpfad — ein totaler Schlüssel, ein aus der Quelle abgeleiteter Frischewert:

```python
# Total: der fachliche Schlüssel plus ein eindeutiger Zusatz für den Gleichstand.
ORDER = ("publiziert_am", "id")


async def search(query: str, offset: int, limit: int) -> QueryResult:
    rows = await _impl.search(query, order_by=ORDER, offset=offset, limit=limit)
    return QueryResult(
        rows=rows,
        # Aus source_freshness abgeleitet, nicht geschätzt: gedeckelt auf die
        # nächste Publikation, bei unbekannter Kadenz bewusst kurz.
        ttlMs=ttl_until_next_publication(SOURCE_FRESHNESS, fallback_ms=60_000),
        cacheScope="public",     # Open Data, aufruferunabhängig
    )
```

### Effort Estimate

Katalog-Richtwert (checks/ARCH-020.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S für die fünf Protokoll-Methoden — eine Sortierung und zwei Felder je Methode. Die Entscheidung über `cacheScope` je Ressource kostet mehr Nachdenken als Code.

Auf dem Datenpfad ebenfalls S, solange die Quelle einen eindeutigen Schlüssel anbietet und ihre Kadenz publiziert. Bietet sie keinen, wird es M: Dann muss ein stabiler Zusatzschlüssel erst hergestellt werden, und das ist eine Entscheidung über die Abfrage, nicht über die Ausgabe.
