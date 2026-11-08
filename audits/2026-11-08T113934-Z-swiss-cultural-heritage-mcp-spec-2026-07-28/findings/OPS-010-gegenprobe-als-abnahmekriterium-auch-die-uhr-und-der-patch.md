## Finding: OPS-010 — Gegenprobe als Abnahmekriterium — auch die Uhr und der Patch

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | advisory |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `OPS-010` |
| **PDF-Reference** | Custom (Katalog-Lücke gegen mcp-transport-hardening-skill Regel 6, 2026-08-07) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Am 2026-11-08 sechs Mutationen gefahren, vier schlagen an, zwei nicht. Die zwei nicht anschlagenden sind das Ergebnis: Wanduhr-Budget und POST-Egress sind ungeprüfte Zusicherungen. Die Mutationen liefen nur auf der Kopie im Scratchpad, das Repo blieb unberührt (Datei danach byte-gleich wiederhergestellt: 'restored identical: True'). Advisory.

### Expected Behavior

Aus dem Katalog (`checks/OPS-010.md`, Pass Criteria):

- [ ] Für jede zentrale Zusicherung des Servers ist **dokumentiert**, welcher Test rot wird, wenn man sie bricht
- [ ] Die Gegenprobe ist **gefahren** worden, nicht nur vorgesehen — mit Datum oder Commit, an dem sie lief
- [ ] Mutationen, die **nicht** anschlagen, stehen im Befund; sie sind das Ergebnis, nicht der Ausschuss
- [ ] Jede Zusicherung über **Wanduhrzeit** hat mindestens einen Test unter **echter** Zeit; eine Uhr, die nur beim Schlafen vorrückt, ist dort kein Beleg
- [ ] Kein Test patcht ein **fremdes** Modul global (`modul.asyncio`, `modul.time`, `modul.random`); gepatcht wird eine eigene Naht (`modul._sleep`)
- [ ] Ein Test bewacht diese Naht — er zeigt, dass das echte `asyncio.sleep` nach der Fixture noch wirkt
- [ ] Der Weg, eine Gegenprobe zu fahren, steht im `CONTRIBUTING`; eine Praxis, die nur einer kennt, überlebt den nächsten Beitrag nicht
- [ ] **Gegenprobe zur Gegenprobe:** Es ist einmal gezeigt worden, dass die Mutations-Methode selbst anschlägt — eine Mutation, von der bekannt ist, dass sie einen Test bricht, bricht ihn auch

### Evidence

- Mutationslauf scratchpad/probe/mutate.py auf einer Kopie aus git archive HEAD (Subset test_server, test_retry_policy, test_response_shape, test_helveticat_zugaenge, test_recorded_fixtures; Baseline '13 failed, 211 passed' = Windows-Altlast): M3 Jitter entfernt -> neu rot test_backoff_is_jittered; M4 Raise bei Totalausfall entfernt -> neu rot test_search_all_sources_down_raises, test_search_timeout_is_handled; M5 Fuzzy-Marker -> 2 neu rot; M6 Datumsfilter -> 1 neu rot (die Methode hat Zähne)
- Nicht anschlagend: M1 'async with asyncio.timeout(remaining):' (server.py:888, Wanduhr-Budget in _fetch_with_retry) durch 'if True:' ersetzt -> 0 neu rot; grep 'retry_total_budget|monotonic|_retry_sleep' tests/ trifft nur tests/test_session_start_hook.py — kein Test unter echter Zeit für das Gesamtbudget
- Nicht anschlagend: M2 _assert_allowed(url) in _http_post (server.py:771) entfernt -> 0 neu rot; die Egress-Tests (tests/test_server.py:534-557) decken nur _http_get, der POST-Pfad (Dodis) ist ungeprüft
- grep -rnE 'monkeypatch.setattr\(\s*[A-Za-z_.]+\.(asyncio|time|random|os|httpx)\s*,' tests/ -> keine Treffer (negative Kontrolle mit 'monkeypatch.setattr(mod.asyncio, "sleep", f)': 1); eigene Naht _retry_sleep (server.py:778), Tests schalten den Backoff über settings.retry_backoff_base=0.0 ab (tests/test_server.py:1669)
- grep -rniE 'gegenprobe|mutation' CONTRIBUTING*.md -> keine Treffer; die Regel steht in CLAUDE.md:37 'Gegenprobe ist Pflicht', gefahrene Gegenproben sind im CHANGELOG [0.7.0] notiert (16 Mutationen test_helveticat_zugaenge)

### Gaps

- Die Wanduhr-Zusicherung (asyncio.timeout als Gesamtbudget, der ARCH-014-Fall) hat keinen Test; ihr Entfernen bleibt grün (high)
- Die Egress-Allow-List im POST-Pfad (_http_post) ist ungeprüft; ihr Entfernen bleibt grün (high)
- Kein Test bewacht die Naht (echtes asyncio.sleep wirkt nach den Fixtures) (low)
- Der Weg, eine Gegenprobe zu fahren, steht nicht in CONTRIBUTING (low)

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

Ein Test, der grün bleibt, wenn man die Implementierung entfernt, prüft nichts. Er kostet Laufzeit, erzeugt eine Zeile im Report und eine Überzeugung, die durch nichts gedeckt ist — die teuerste Form von Testabdeckung, weil sie den Blick von der Stelle wegzieht, an der nichts steht.

Die Gegenprobe ist die einzige Frage, die das entscheidet: **Brich die Zusicherung und sieh nach, ob ein Test rot wird.** Wird keiner rot, ist die Zusicherung ungeprüft, und das gehört in den Befund — nicht in eine Notiz.

**Der Katalog lebt das bereits, aber nur nebenbei.** Einundzwanzig Checks tragen eine Gegenproben-Zeile in ihren Pass Criteria — `ARCH-013`, `ARCH-015`–`ARCH-017`, `ARCH-020`, `DRIFT-003`, `FID-003`, `FID-004`, `FID-006`, `HITL-006`, `IDENT-002`, `IDENT-004`, `OPS-005`–`OPS-008`, `SCALE-007`, `SCALE-009`, `SEC-024`, `SEC-026`. Das ist gute Praxis in Einzelfällen und **kein** Abnahmekriterium: Ein Check ohne eigene Zeile bekommt keine, und die Frage «wurde diese Zusicherung je gebrochen?» wird für den Rest der Suite nie gestellt. Der Skill [`mcp-transport-hardening`](https://github.com/malkreide/mcp-transport-hardening-skill) führt sie als Regel 6; der Katalog hatte sie als Gewohnheit.

Zwei Untervarianten gehören ausdrücklich dazu, **weil beide real aufgetreten sind und beide grün blieben**. Sie stehen hier, weil eine allgemeine Regel sie nicht fängt: In beiden Fällen *gibt* es eine Gegenprobe, und sie ist wirkungslos.

### a) Die Fake-Uhr, die nur beim Schlafen vorrückt

Budget- und Timeout-Tests laufen üblicherweise unter einer Uhr, die nur vorrückt, wenn etwas schläft. Eine solche Uhr kann eine Zusicherung über **echte** Zeit nicht widerlegen: Der Code, der die Wanduhr ignoriert, schläft nicht — also vergeht keine Zeit, also hält er das Budget ein, also ist der Test grün.

Genau dieser blinde Fleck liess einen Budget-Defekt durch **sechs** Server reisen (`ARCH-014`): Ein «Gesamtbudget» aus Per-Operation-`httpx`-Timeouts begrenzt den Aufruf nicht, weil das Read-Timeout mit jedem Chunk von vorn beginnt. Unter der Fake-Uhr sah das sechsmal richtig aus.

```python
async def test_a_slow_response_is_cut_by_the_wall_clock_deadline(real_sleep):
    async def _slow(request):
        await real_sleep(1.0)              # echte Zeit, keine Fake-Uhr
        return httpx.Response(200)
    respx.get(URL).mock(side_effect=_slow)
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        await client.load("data", total_budget=0.05)
    assert time.monotonic() - started < 0.5
```

Die Regel ist eng: Eine Zusicherung über **Wanduhrzeit** braucht mindestens einen Test unter **echter** Zeit. Alles andere darf und soll die schnelle Uhr benutzen — eine Suite, die überall echt schläft, wird nicht ausgeführt und prüft dann gar nichts.

### b) Der globale Monkeypatch auf ein fremdes Modul

```python
monkeypatch.setattr(modul.asyncio, "sleep", _instant)
```

Das sieht lokal aus und ist es nicht. `modul.asyncio` **ist** das stdlib-Modul; der Patch wirkt prozessweit — auf jeden Import, auch auf fremde Tests. Ein Test, der `asyncio.sleep(0)` benutzt, um dem Event-Loop das Wort zu geben, läuft danach weiter und misst nichts. Genau so ist in `srgssr-mcp` eine Parallelitäts-Prüfung eingebrochen, ohne rot zu werden.

Der Ausweg ist eine eigene Naht: Der Backoff geht über `modul._sleep`, und gepatcht wird **die**, nicht das fremde Modul.

```python
# im Produktivcode
_sleep = asyncio.sleep          # die Naht, die der Test fassen darf

# im Test
monkeypatch.setattr(modul, "_sleep", _instant)
```

Und ein Test, der die Naht bewacht — sonst wandert der globale Patch beim nächsten Refactoring zurück:

```python
async def test_the_no_sleep_fixture_leaves_the_global_asyncio_sleep_alone():
    """Die Fixture darf nur die Backoff-Wartezeit abschalten, nicht mehr."""
    started = time.monotonic()
    await asyncio.sleep(0.05)             # das echte, ungepatchte sleep
    assert time.monotonic() - started >= 0.04
```

**Abgrenzung zu `DRIFT-003`.** Der prüft eine bestimmte Fehlerklasse: Assertions, die auch der Degradationspfad erfüllt. Das ist ein Sonderfall dieser Frage mit einer eigenen, engen Antwort. Dieser Check fragt sie für die **ganze Suite** und macht sie zum Abnahmekriterium.

**Abgrenzung zu `OPS-008`.** Der sagt, wo Prüflogik **liegen** muss, damit sie überhaupt mutationstestbar ist (nicht im Workflow-Heredoc). Dieser Check sagt, dass die Mutation dann auch **stattfindet**.

**Abgrenzung zu `OPS-005`.** Der prüft, ob ein Gate überhaupt **läuft**. Dieser prüft, ob es **scheitern kann**. Ein Gate, das läuft und nicht scheitern kann, ist in `OPS-005` grün.

`high`: Eine Suite ohne Gegenprobe liefert keine Sicherheit, sondern das Gefühl davon — und dieses Gefühl entscheidet, wo nicht mehr hingesehen wird.

### Remediation

Aus dem Katalog (`checks/OPS-010.md`, Remediation), auf die Gaps oben anzuwenden:

1. Drei bis fünf zentrale Zusicherungen benennen — die, deren Fehlen etwas kosten würde.
2. Jede einzeln brechen, Suite laufen lassen, notieren welcher Test rot wird. **Und welche keinen roten Test haben.**
3. Für jede ungedeckte Zusicherung entweder einen Test schreiben oder ausdrücklich festhalten, dass sie ungeprüft ist. Beides ist zulässig; stillschweigen nicht.
4. Zeitzusicherungen durchgehen: Läuft der Test unter einer Uhr, die nur beim Schlafen vorrückt? Dann einen unter echter Zeit dazustellen.
5. `grep -rn 'monkeypatch.setattr(' tests/` — jeden Treffer prüfen, ob links vom Komma ein fremdes Modul steht. Wenn ja: eine Naht im Produktivcode anlegen und den Patch dorthin verschieben.
6. Die Naht mit einem Test bewachen, der zeigt, dass das echte `sleep` noch wirkt.
7. Den Weg ins `CONTRIBUTING` schreiben.

### Effort Estimate

Katalog-Richtwert (checks/OPS-010.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

M — Pro Server 1–2 Tage. Schritt 2 ist mechanisch; die Zeit geht in die Tests, die Schritt 3 fordert, und in die Nähte aus Schritt 5.
