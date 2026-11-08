## Finding: FID-001 — Scope-Defaults: Filter-Parameter explizit senden, nie erben

| Feld | Wert |
|---|---|
| **Severity** | critical |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `FID-001` |
| **PDF-Reference** | Custom (Portfolio-Fundstück termdat-mcp#11) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Der Kern des Checks ist erfuellt: Jeder gemessene einschraenkende Default (rows 10, limit 100, maximumRecords 10, size 10, Dodis-rows unbegrenzt) wird explizit uebersteuert, und bewusste Einschraenkungen stehen im Tool-Result. Es fehlen die Matrix als Artefakt, der Regressionstest und die Behandlung von `plain`. Alle Messungen lesend, 2026-11-08 11:45-11:48 UTC, direkt gegen die Upstreams und ueber die Tool-Funktionen.

### Expected Behavior

Aus dem Katalog (`checks/FID-001.md`, Pass Criteria):

- [ ] Default-Matrix existiert und deckt **alle** optionalen Parameter der genutzten Endpoints ab
- [ ] Jeder Parameter mit einschränkendem Default wird vom Server explizit gesetzt
- [ ] Das Recall-Delta (weggelassen vs. explizit maximal) ist für jeden solchen Parameter empirisch gemessen und dokumentiert
- [ ] Eine bewusst gewählte Einschränkung ist im Tool-Result sichtbar (Feld oder `hint`), nicht nur im README
- [ ] Ein Regressionstest hält den vollen Scope fest (siehe FID-002)
- [ ] Scheitert die Ermittlung des vollen Scopes zur Laufzeit (z. B. Vokabular-Endpoint nicht erreichbar), degradiert der Server sauber — die Erweiterung darf die Suche nie brechen

### Evidence

- src/swiss_cultural_heritage_mcp/server.py:1400-1406 — datastore_search (SIKART) sendet limit und offset immer; Upstream-Default ohne limit gemessen 2026-11-08 11:48 UTC: q=Malerin -> 100 Records bei total 1779. Request-Log des Tools: limit=20&offset=0.
- src/swiss_cultural_heritage_mcp/server.py:1648-1651 — package_search sendet rows und start immer (Request-Log: rows=20&start=0); Upstream-Default ohne rows gemessen: 10 Treffer.
- src/swiss_cultural_heritage_mcp/server.py:1284-1293 — SRU sendet maximumRecords=min(limit,50) immer; Upstream-Default ohne maximumRecords gemessen: 10 Records fuer alma.all_for_ui="Volksschule" (numberOfRecords 1990). Der Deckel 50 ist im Tool-Result benannt (src/swiss_cultural_heritage_mcp/server.py:2129-2133) und als has_more im JSON (src/swiss_cultural_heritage_mcp/server.py:2062).
- src/swiss_cultural_heritage_mcp/server.py:2684-2690 und src/swiss_cultural_heritage_mcp/server.py:2723-2729 — Memobase sendet size+offset, Dodis start+rows immer; Upstream-Defaults gemessen: Memobase ohne size 10 Members (total 335 fuer 'Escher'), Dodis ohne rows 963 Treffer (= rows=1000). Beide Defaults werden nie geerbt.
- Recall-Delta datastore_search `language` (weggelassen = english vs german), live 2026-11-08: Hodler 25 vs 0, Bildhauer 1259 vs 0, Malerin 1779 vs 1779. Der Server laesst `language` weg und erbt damit die breitere Variante: kein Befund.
- Recall-Delta datastore_search `plain` (Default true, vom Server nie gesendet): q=Hodler 25, q=Hodl 0, q=Hodl* 0, aber plain=false q='Hodl:*' 26. Der Default schliesst Praefixsuche aus und ist weder gesendet noch im Tool-Result oder in der Description deklariert.
- src/swiss_cultural_heritage_mcp/server.py:2017-2035, src/swiss_cultural_heritage_mcp/server.py:2082-2086, src/swiss_cultural_heritage_mcp/server.py:2047-2053 — die bewusste Einschraenkung (query+set_spec filtert nur die abgerufene OAI-Seite) ist im Tool-Result sichtbar, nicht nur im README; ebenso search_heritage meta.clientside_filters (src/swiss_cultural_heritage_mcp/server.py:2897-2901).
- rg -n -i 'default-matrix|ground.truth|recall|Referenzquer|Web-UI|reality-check' (Repo ohne audits/ und Fixture-Daten) -> keine Default-Matrix; Kontrolle: dasselbe Muster trifft den Katalogtext FID-002.md. PROBE_REPORT_helveticat.md:250-256 dokumentiert nur fuer SRU den maximumRecords-Deckel, :74-76 ListSets ohne resumptionToken (live bestaetigt 2026-11-08: 68 Sets, kein Token).

### Gaps

- Keine Default-Matrix fuer alle optionalen Parameter aller genutzten Endpunkte (CKAN datastore_search/package_search, Memobase, Dodis solr/query); nur Teilbefunde fuer SRU/OAI im Probe-Bericht (Severity medium).
- Kein Regressionstest, der den vollen Scope festhaelt (kein Recall-Floor unter @pytest.mark.live, siehe FID-002) (Severity high).
- datastore_search `plain=true` (Upstream-Default) schliesst Praefix-Matching aus; der Server erbt ihn still und deklariert die Einschraenkung nirgends (Severity medium).
- Dodis/Memobase: weitere serverseitige Defaults (Filter, Typ-Einschraenkungen) nicht spezifiziert und nicht gemessen; keine Spec-Parameterliste im Repo (Severity medium).

### Risk Description

Siehe Gaps; Severity laut Katalog `critical`. Katalogbeschreibung:

Ein optionaler Query-Parameter, dessen Weglassen **nicht** «unbeschränkt» bedeutet, sondern einen willkürlichen Teilausschnitt. Der Server sendet den Parameter nicht, die Upstream-API setzt einen Default, und der Server durchsucht ohne es zu merken einen Bruchteil der Datenbank. Die Antwort ist syntaktisch korrekt, HTTP 200, wohlgeformtes JSON — und inhaltlich falsch.

Der Portfolio-Fall: `termdat-mcp` sendete `ClassificationIds` nur, wenn der Aufrufer sie explizit setzte. Die TERMDAT-API dokumentiert dazu: *«If no ID is given, a default set of classifications will be included (=VARIA)»*. `VARIA` ist eine von 23 Klassifikationen — ausgerechnet die Restkategorie. Jede Default-Suche lief damit gegen ein Dreiundzwanzigstel des Bestands. «Quellensteuer» lieferte null Treffer, obwohl der Begriff in `RECHT` und `FINANZWESEN` mehrfach vorhanden ist. Gefunden hat das ein User mit dem offiziellen Web-UI daneben, nicht die 33 grünen Tests.

Das ist keine Eigenheit einer einzelnen API, sondern eine Fehlerklasse. Verbreitete Vertreter:

| Quelle | Parameter | Default bei Weglassen |
|---|---|---|
| CKAN `package_search` | `rows` | 10 Treffer, nicht alle |
| WFS `GetFeature` | `count` / `maxFeatures` | serverseitiges Limit, oft 1000 |
| SPARQL | `FROM` / Named Graphs | nur der Default-Graph |
| Elasticsearch / OpenSearch | `size` | 10 Hits |
| GraphQL (Relay) | `first` | je nach Schema, oft klein |
| SQL-über-HTTP-Gateways | `LIMIT` | gateway-seitiges Zeilenlimit |
| Solr / Lucene-Fassaden | `fq`, `df` | eingeschränktes Default-Feld |

Der gemeinsame Nenner: der Default steht **ausschliesslich in der Parameterbeschreibung** der Spec. Er ist nicht aus dem Response-Schema ableitbar, nicht aus einem Happy-Path-Test sichtbar, und ein Mock reproduziert ihn nie — weil der Mock genau die Annahme abbildet, die falsch ist.

Dieser Check ist `critical`, weil das Fehlverhalten still ist: Ein Server, der zwei Prozent des Bestands durchsucht und das nicht meldet, produziert falsche Antworten, die niemand als falsch erkennt. Im Bildungs- und Verwaltungskontext ist das gefährlicher als eine offene Bind-Adresse.

### Remediation

Aus dem Katalog (`checks/FID-001.md`, Remediation), auf die Gaps oben anzuwenden:

```diff
+ async def _all_classification_ids(self) -> list[int] | None:
+     """Voller Klassifikationssatz — eine Suche ohne IDs deckt nur VARIA ab.
+
+     Best-effort: Ist das Vokabular nicht erreichbar, läuft die Suche
+     unerweitert weiter. Eine Erweiterung darf nie brechen, was sie erweitert.
+     """
+     try:
+         values, _, _ = await self.vocabulary("Classification", "DE")
+     except Exception:  # noqa: BLE001
+         log.warning("upstream.scope_widening_unavailable")
+         return None
+     return [v["id"] for v in values if isinstance(v.get("id"), int)] or None

  async def search(self, term: str, *, classification_ids: list[int] | None = None):
+     if classification_ids is None:
+         classification_ids = await self._all_classification_ids()
      params = {"SearchTerm": term, ...}
      if classification_ids:
          params["ClassificationIds"] = classification_ids
```

### Effort Estimate

Katalog-Richtwert (checks/FID-001.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — Pro Server 2–4 Stunden: Spec-Parameter durchgehen, Default-Matrix erstellen, Recall-Delta messen, Fix plus Regressionstest.
