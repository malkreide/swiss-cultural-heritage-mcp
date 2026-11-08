## Finding: SEC-028 — Egress-Guard: Policy-Verstoss und Auflösungsfehler sind unterscheidbar

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `SEC-028` |
| **PDF-Reference** | Custom (Katalog-Lücke, aufgefallen bei zh-education-mcp, 2026-08-03) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Where _fetch_with_retry is used, the distinction at the throw site and in the retry works (measured), and single-source messages are distinguishable. It breaks in the aggregation of search_heritage and through the missing retry layer in the CKAN/NB tools. About half the criteria are met, so partial.

### Expected Behavior

Aus dem Katalog (`checks/SEC-028.md`, Pass Criteria):

- [ ] Policy-Verstoss und Auflösungsfehler verlassen den Guard als **verschiedene Exception-Typen** — oder als ein Typ mit einem Diskriminator, den der Code liest (Attribut, Enum), nicht als Text im Meldungsstring
- [ ] Die Retry-Politik entscheidet an diesem Diskriminator: Policy-Verstoss ohne Wiederholung, Auflösungsfehler mit
- [ ] Die nutzerseitige Meldung nennt im transienten Fall weder die Egress-Policy noch die Allow-List-Konfiguration als Ursache
- [ ] Kein Sammel-`except` und keine Fehlerabbildung, die die beiden Typen vor der Ausgabe wieder zusammenführt
- [ ] Beide Lagen sind getestet — der transiente Fall mit Wiederholung, der deterministische ohne; beide Tests fallen, wenn die Typen zusammengelegt werden

### Evidence

- src/swiss_cultural_heritage_mcp/server.py:726-730 — policy violation (scheme/host) as a plain ValueError; the guard does not resolve DNS itself, so a resolution failure surfaces as httpx.ConnectError (RequestError): two different types
- src/swiss_cultural_heritage_mcp/server.py:883-901 — _fetch_with_retry retries only TimeoutException/RequestError/5xx/429; ValueError propagates without retry. src/swiss_cultural_heritage_mcp/server.py:944-947 _handle_error: ValueError -> 'Fehler: <Policy-Text>', RequestError -> 'Fehler: Netzwerkfehler (...)'
- Runtime (respx, scratch probe taxonomy.py): (a) memobase ConnectError then 200 -> 2 calls, success; (b) emptied ALLOWED_HOSTS via _fetch_with_retry -> 1 attempt, 'Fehler: Host nicht in Allow-List: api.memobase.ch'; (c2) heritage_search_artists with a policy violation -> 'Host nicht in Allow-List: ckan.opendata.swiss'
- Runtime (c): policy violation on both sources, search_heritage -> 'Fehler: Alle angefragten Quellen sind derzeit nicht erreichbar.' (src/swiss_cultural_heritage_mcp/server.py:2903-2905); (a2) persistent ConnectError -> the same message. Both situations collapse into ONE transient-sounding message
- Runtime (d): heritage_search_artists with ConnectError then 200 -> 1 call, ToolError 'Netzwerkfehler (ConnectError): [Errno 11001] getaddrinfo failed': SIKART/SNM/NB tools call _http_get without _fetch_with_retry and never retry resolution failures
- grep -rnE 'ConnectError|gaierror|_fetch_with_retry' tests/*.py -> no match: no test pair for transient vs. deterministic

### Gaps

- search_heritage folds policy violation and outage into 'nicht erreichbar' at the output; a deterministic block reads as a transient outage (severity: high)
- Resolution failures are not retried in 8 of 11 tools (direct _http_get) (severity: medium, overlaps ARCH-014)
- The policy violation is a generic ValueError (shared with UpstreamSchemaError/OaiError/SruError), with no dedicated type or retryable attribute (severity: low)
- No test pair (transient with retry / policy without) and no mutation evidence (severity: medium)

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

`SEC-004` fragt, ob die aufgelöste IP erlaubt ist. `SEC-005` fragt, ob sie auch die benutzte ist. Dieser Check fragt das Dritte: **Sagt der Guard, warum er abgewiesen hat — so, dass die Retry-Politik und der Aufrufer es unterscheiden können?**

Ein Egress-Guard scheitert an zwei grundverschiedenen Lagen, und beide laufen durch dieselbe Funktion:

| | Lage | Eigenschaft | Richtige Behandlung |
|---|---|---|---|
| **(1)** | Der Hostname löst auf eine interne oder nicht-routbare Adresse auf | **Deterministisch.** Wiederholt sich beliebig oft gleich | Kein Retry. Meldung nennt die Policy |
| **(2)** | Die Auflösung selbst scheitert (`socket.gaierror`, Timeout des Resolvers, Ausfall des DNS-Servers) | **Transient.** Beim nächsten Versuch weg | Retry. Meldung nennt die Policy **nicht** |

Die beiden trennt genau eine Eigenschaft, und es ist die, auf die es ankommt: **Reproduzierbarkeit.** Ein Policy-Verstoss ist eine Aussage über die Anfrage; ein Auflösungsfehler ist eine Aussage über den Moment. Ein einziger Exception-Typ für beide behauptet, sie seien dasselbe.

**Der Befund, aus dem dieser Check stammt** (`zh-education-mcp`, `src/zh_education_mcp/http_client.py`, 2026-08-03): `_resolve_and_validate(host)` wirft `PermissionError` in beiden Zweigen. Daraus folgen zwei Schäden, die aussehen wie zwei Bugs und einer sind:

- **Die Retry-Politik kann nicht entscheiden.** Die Schleife überspringt `PermissionError` — *bewusst*, und für Lage (1) ist das richtig. Für Lage (2) heisst es: Ein DNS-Zucken wird nicht wiederholt, obwohl genau die Wiederholung die Lage rettet. Beobachtet: drei aufeinanderfolgende Tool-Aufrufe scheiterten so, der vierte ging durch.
- **Die Fehlerabbildung benennt die falsche Ursache.** Beide Lagen melden «Ausgehende Anfrage durch Egress-Policy blockiert». Bei einem Auflösungsfehler schickt das Nutzende in eine Konfiguration, in der nichts zu finden ist — sie suchen eine Allow-List-Zeile für einen Host, der erlaubt ist.

**Warum `SEC` und nicht `ARCH` oder `OBS`.** Der zweite Schaden hat eine Sicherheitsrichtung, und sie ist der Grund für die Kategorie und für `high`: Wer «Egress-Policy blockiert» dreimal sieht und dreimal feststellt, dass es ein DNS-Zucken war, lernt die Meldung als Rauschen. Der vierte Fall ist dann der echte Policy-Verstoss, und er geht durch denselben Filter im Kopf. Eine Sicherheitskontrolle, die von einer Störung nicht zu unterscheiden ist, wird wie eine Störung behandelt. Der Gegenstand ist der Guard; deshalb steht der Check neben dem Guard und nicht bei der Retry-Politik.

### Abgrenzung zu drei benachbarten Checks

Diese Trennung ist ausgeschrieben, weil sonst ein Server für eine Ursache mehrere Findings erzeugt — derselbe Fehler, den `SEC-004`/`SEC-005` bis v1.3.1 hatten.

| Check | Was er fragt | Warum er diesen Fall nicht sieht |
|---|---|---|
| [`ARCH-014`](./ARCH-014.md) — Retry-Politik | *Was* wiederholt wird, wie schnell, wie lange | ARCH-014 prüft die **Entscheidung** der Retry-Politik; dieser Check, ob sie die **Information** hat, sie zu treffen. Ein Guard, der beide Lagen als einen Typ wirft, macht die Politik nicht falsch — er macht sie blind. Gemessen an dem, was sie sehen kann, ist sie korrekt: Sie überspringt einen Typ, der laut Namen ein Policy-Verstoss ist |
| [`OBS-001`](./OBS-001.md) — Protocol vs. Execution Errors | Auf welchem **Kanal** ein Fehler zurückkommt (JSON-RPC-Error gegen `isError`) | Beide Lagen hier sind Execution Errors und liegen auf demselben Kanal. OBS-001 ist damit erfüllt und die Verwechslung trotzdem da: Sie sitzt eine Ebene tiefer, zwischen zwei Ursachen desselben Typs |
| [`OBS-007`](./OBS-007.md) — Fehler-Details bleiben diagnostizierbar | Ob die Ursache **irgendwo** noch steht (Log, interner Kontext) | OBS-007 ist erfüllbar, während dieser Check scheitert: Der Guard kann `gaierror` sauber ins Log schreiben und trotzdem einen Typ werfen, an dem die Retry-Schleife nicht unterscheiden kann. Ein Log ist für Menschen nach dem Vorfall; ein Diskriminator ist für Code während des Vorfalls |

Kurz: `ARCH-014` prüft die Entscheidung, `OBS-001` den Kanal, `OBS-007` die Nachvollziehbarkeit — dieser Check die **Unterscheidbarkeit am Werfort**.

### Adoptionsstufe: `enforced` — und was daran ungemessen ist

Die Reichweite ist wörtlich die von `SEC-005` und `ARCH-014` (`tools_make_external_requests == true`), also dieselbe Servermenge, für die `SEC-005` die Stufe bereits mit einer Tabelle begründet hat: acht Server, ein Arbeitspaket, kein Aufstand. Der Aufwand hier ist kleiner als dort — eine Exception-Unterklasse und ein Zweig in der Retry-Schleife, keine Transport-Ersetzung.

**Ungemessen ist, wie viele der acht heute bestehen.** Die Vermutung ist: wenige. Ein einziger `PermissionError` ist die naheliegende Art, einen Guard zu schreiben, und der eine gemessene Fall ist ein Beleg dafür, nicht dagegen. Diese Vermutung steht hier als Vermutung, weil ein Portfolio-Durchlauf sie in einer Stunde ersetzen kann und ein hingeschriebener Zahlenwert sie nur plausibel gemacht hätte.

**Was die Stufe umkehren würde:** ein Durchlauf, der zeigt, dass alle acht durchfallen *und* der Rückstand nicht in einem Sprint abbaubar ist. Die Umstellung ist eine Zeile (`adoption: advisory` unter `severity`) plus der Eintrag in `tests/test_adoption_stage.py` und die Zeile in beiden READMEs, die die Advisory-Menge namentlich ausschreibt.

### Remediation

Aus dem Katalog (`checks/SEC-028.md`, Remediation), auf die Gaps oben anzuwenden:

### Schritt 1: Die Typen trennen

Wie im Pass-Pattern oben. Eine gemeinsame Basisklasse ist erwünscht — sie erlaubt weiterhin ein `except EgressError` an der Stelle, wo beide Lagen gleich behandelt werden (etwa beim Abbrechen des Tool-Calls), ohne die Unterscheidung dort aufzugeben, wo sie gebraucht wird.

Das `retryable`-Attribut auf der Klasse ist die kleinere Variante gegenüber einer `isinstance`-Kette in der Schleife: Ein dritter Fall (Resolver-Timeout etwa) bringt seine Antwort selbst mit, statt eine Verzweigung an einer entfernten Stelle zu erfordern.

### Schritt 2: Die Schleife am Diskriminator entscheiden lassen

Siehe Pass-Pattern. Zwei Dinge sind hier leicht zu übersehen:

- **Fail-closed bleibt.** Ein Auflösungsfehler wird wiederholt, aber nicht durchgelassen. Nach dem letzten Versuch scheitert der Aufruf — mit der Meldung des transienten Falls.
- **Das Retry-Budget gehört zu `ARCH-014`.** Wie viele Versuche, mit welcher Streuung und unter welchem Gesamtbudget, entscheidet dieser Check nicht. Er entscheidet nur, dass die eine Lage überhaupt in die Zählung kommt und die andere nicht.

### Schritt 3: Die Meldungen trennen

```python
USER_MESSAGE = {
    EgressPolicyViolation: (
        "Die Zieladresse ist durch die Egress-Policy gesperrt. "
        "Wenn der Host erreichbar sein soll, gehört er in die Allow-List."
    ),
    EgressResolutionError: (
        "Der Zielhost war vorübergehend nicht auflösbar. "
        "Der Aufruf kann wiederholt werden; die Konfiguration ist nicht betroffen."
    ),
}
```

Der letzte Halbsatz ist der eigentliche Fix aus dem Befund: Er sagt ausdrücklich, wo **nicht** zu suchen ist.

### Schritt 4: Tests

Beide Tests aus Modus 3, und die Mutation einmal ausgeführt und protokolliert: die Typen zusammenlegen, beide Tests müssen rot werden.

### Effort Estimate

Katalog-Richtwert (checks/SEC-028.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — wenige Stunden. Zwei Exception-Klassen, ein Zweig in der Retry-Schleife, eine Meldungsabbildung, zwei Tests. Kein Transport-Umbau.
