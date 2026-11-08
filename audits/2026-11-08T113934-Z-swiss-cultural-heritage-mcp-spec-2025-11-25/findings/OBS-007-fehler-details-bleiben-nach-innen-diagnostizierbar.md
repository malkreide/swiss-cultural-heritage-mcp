## Finding: OBS-007 — Fehler-Details bleiben nach innen diagnostizierbar

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | enforced |
| **Check-Status** | fail |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `OBS-007` |
| **PDF-Reference** | Custom (Portfolio-Fundstück swiss-efv-mcp#16) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Der Retry-Pfad ist vorbildlich (Durchreichen, Typ, Versuche), deckt aber nur Memobase/Dodis/get_heritage_item. Die Einzelquellen-Tools loggen den Typ ohne Ziel, die foederierte Suche gar nichts. Weniger als die Haelfte der Kriterien erfuellt.

### Expected Behavior

Aus dem Katalog (`checks/OBS-007.md`, Pass Criteria):

- [ ] Meldungen, die der Server für sich behält (Log **und** intern geworfene Exceptions), nennen den **Exception-Typ**, nicht nur `str(exc)`
- [ ] Bei leerem `str(exc)` bleibt ein vollständiger Satz stehen — ein Fallback wie `or "no further detail"` oder ein Format, das ohne die Message auskommt
- [ ] Das **Ziel** ist benannt (Host, Endpoint, Datensatz-Key) — ohne Query-String, Header oder Credentials
- [ ] Nach erschöpften Retries steht die **Anzahl Versuche** in der Meldung — «nach Retries» allein sagt nicht, ob zwei oder zwanzig
- [ ] `raise ... from exc` verkettet die Ursache, damit der ursprüngliche Traceback nicht verloren geht
- [ ] Richtung nach aussen bleibt maskiert: Der Detailtext taucht **nicht** im Tool-Result auf (`OBS-002` gilt unverändert)
- [ ] Mindestens ein Test prüft den Meldungsinhalt für den Fall `str(exc) == ""` — ohne ihn verfällt der Text beim nächsten Refactoring unbemerkt

### Evidence

- src/swiss_cultural_heritage_mcp/server.py:888-920 — _fetch_with_retry reicht die Original-Exception durch ('raise last_error', Kommentar 913-917) und loggt upstream_unreachable mit attempts, limit, error_type (Pass-Muster) — aber ohne Ziel/Host
- src/swiss_cultural_heritage_mcp/server.py:922-930 — _handle_error loggt upstream.error mit error_kind und status, ohne Ziel/Host; Laufzeit: '{"error_kind": "ConnectError", "status": null, "event": "upstream.error", "tool": "heritage_search_artists", ...}' — welcher Endpunkt, steht nirgends
- Laufzeit heritage_cross_search mit ConnectError('') auf allen Quellen (httpx.MockTransport): einziges Log-Event ist tool.call — KEIN Fehler-Log, kein Typ; im Ergebnis 'error': '' je Quelle ({SV}:2407-2412, 2430-2435, 2460-2465)
- grep -rnE 'f".*\{(exc|e|err|error|last_error)...\}' src/ → src/swiss_cultural_heritage_mcp/server.py:945, 947, 948, 2870; grep 'str\((exc|e|...)\)' → src/swiss_cultural_heritage_mcp/server.py:2411, 2434, 2464 (negative Kontrolle 'f"Fehler: {e}"' trifft). Laufzeit 947: 'Fehler: Netzwerkfehler (ConnectError): ' — endet auf ': '
- grep -rnE 'ConnectTimeout\(""\)|ConnectError\(""\)|upstream_unreachable' tests/ → keine Treffer: kein Test fuer den Fall str(exc) == ''

### Gaps

- medium: heritage_cross_search verschluckt Upstream-Fehler ohne jedes Log (Typ, Ziel, Versuche fehlen) und liefert bei Netzfehlern ein leeres error-Feld
- medium: kein Log-Event nennt das Ziel (Host/Endpoint/Datensatz) — bei fuenf Quellen ist die Stoerung nicht zuordenbar
- low: Meldungen mit '{e}' ohne Fallback fuer leeres str() (947 endet auf ': ')
- medium: kein Test, der den Meldungsinhalt fuer str(exc) == '' festhaelt

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

`OBS-002` verlangt, dass Fehler-Details das LLM nicht erreichen, und verweist sie dorthin, wo sie hingehören: ins Server-Log. Was dort ankommt, prüft der Katalog bisher nicht. Die Maskierung kann vorbildlich sein und der Text dahinter trotzdem leer.

Genau das ist der Fall, sobald eine Exception in eine eigene Meldung interpoliert wird:

```python
raise RuntimeError(f"Upstream unreachable after retries: {last_error}")
```

Für `httpx` ist das Ergebnis reproduzierbar nichts:

```python
>>> import httpx
>>> for e in (httpx.ConnectTimeout(""), httpx.ReadTimeout(""), httpx.ConnectError("")):
...     print(type(e).__name__, "->", repr(str(e)))
ConnectTimeout -> ''
ReadTimeout -> ''
ConnectError -> ''
```

Timeout- und Verbindungsfehler tragen keine Message. `{last_error}` expandiert zu einem leeren String, und übrig bleibt eine Meldung, die nach einem Doppelpunkt aufhört. Sie nennt weder den Fehlermodus noch das Ziel noch wie oft es versucht wurde — also keine der drei Angaben, wegen derer man sie liest. Das sind ausgerechnet die Fehler, die im Betrieb auftreten: Ein 404 hat eine Message, ein Netzausfall nicht.

**Der Fundort.** Bei `swiss-efv-mcp` scheiterte die nächtliche Live-Suite am 2026-08-01 an einer vorübergehenden Netzstörung. Vier Tests, Meldung jeweils `RuntimeError: Upstream unreachable after retries:` — Satzende. Der Server erfüllte `OBS-002` mustergültig (`mask_error_details=True`, Original nur ins Log); die Maske sass, dahinter stand nichts. Ob die Leitung tot war, die URL rotiert hatte oder der Egress-Filter griff, war der Meldung nicht zu entnehmen — drei Ursachen mit drei verschiedenen Reaktionen.

**Warum das die Nebenwirkung des eigenen Rats ist.** Ein Text, der nach aussen maskiert wird, hat im Normalbetrieb keinen Leser. Niemand sieht ihn beim Entwickeln, kein Test liest ihn, keine Antwort enthält ihn. Er wird genau einmal gebraucht — im Störungsfall, unter Zeitdruck — und bis dahin bemerkt niemand, dass er nichts sagt. Maskierung ohne diesen Check verlagert das Problem, statt es zu lösen.

**Abgrenzung.** Die drei bestehenden OBS-Checks fragen etwas anderes:

| | Frage | Richtung |
|---|---|---|
| `OBS-001` | Ist es Protocol- oder Execution-Error? | Klassifikation zum Client |
| `OBS-002` | Verlässt der Detailtext den Server? | nach aussen — **nicht** verlassen |
| `OBS-003` | Ist das Log strukturiert und richtig gestuft? | Form des Logs |
| `OBS-007` | Steht im Detailtext etwas Brauchbares? | nach innen — **Gehalt** |

`OBS-002` und `OBS-007` widersprechen einander nicht, sie zeigen in verschiedene Richtungen: nach aussen maskiert, nach innen vollständig. Ein Server kann beide erfüllen, und wer nur den ersten erfüllt, hat den Fehler nicht behoben, sondern unsichtbar gemacht.

`medium`: Der Server funktioniert, die Daten stimmen, kein Leck. Der Schaden ist Zeit — die Störung wird länger diagnostiziert als sie dauert, und im Wiederholungsfall beginnt die Diagnose von vorn.

**Adoptionsstufe `enforced` seit dem Portfolio-Durchlauf.** Der Check startete `advisory`, weil das `f"...: {exc}"`-Muster die naheliegende Schreibweise ist und breite Teile des Portfolios zu treffen schien. Ein Durchlauf über zehn Server hat das widerlegt: **Zwei von acht** mit Retry-Pfad verletzen ihn, und der Grund ist präzise. Wer die ursprüngliche Exception mit `raise last_exc` weiterreicht, erfüllt den Check automatisch — Typ und Traceback bleiben erhalten. Verletzt wird er nur beim **Einpacken** in eine neue Meldung, die den Typ verschluckt. Der Check ist damit eng geschnitten, ohne falsche Positive im Sample, und blockiert ab sofort (Details im CHANGELOG).

Der auffälligere der beiden Befunde zeigt, warum der Check nicht kosmetisch ist. `lindas-mcp` setzt hinter das leere `{last_error}` eine Diagnose:

```python
f"LINDAS unreachable after {MAX_ATTEMPTS} attempts. "
f"Last error: {last_error}. This often means the query was too broad "
f"and the store timed out — anchor it on a known class such as ..."
```

Bei einem `ConnectError` steht dort «Last error: .» und darunter eine selbstbewusste Ursachenbehauptung, die mit dem tatsächlichen Fehler nichts zu tun hat. Eine leere Meldung sagt nichts; eine leere Meldung mit angehängter Vermutung sagt etwas Falsches.

### Remediation

Aus dem Katalog (`checks/OBS-007.md`, Remediation), auf die Gaps oben anzuwenden:

```diff
      except (httpx.HTTPStatusError, httpx.RequestError) as exc:
          last_error = exc
  ...
- raise RuntimeError(f"Upstream unreachable after retries: {last_error}")
+ # httpx-Timeouts tragen ein leeres str() — Typ und Ziel müssen das überleben.
+ detail = str(last_error) or "no further detail"
+ raise RuntimeError(
+     f"Upstream unreachable after {attempts} attempts: "
+     f"{type(last_error).__name__}: {detail} "
+     f"(host={urlsplit(url).hostname})"
+ ) from last_error
```

Und den Text festnageln, sonst verfällt er wieder:

```python
@respx.mock
async def test_retry_exhaustion_message_names_type_and_host():
    respx.get(URL).mock(side_effect=httpx.ConnectTimeout(""))   # leere Message
    with pytest.raises(RuntimeError) as exc_info:
        await client.load("headline")
    msg = str(exc_info.value)
    assert "ConnectTimeout" in msg
    assert "upstream.example" in msg
    assert not msg.rstrip().endswith(":")
    assert isinstance(exc_info.value.__cause__, httpx.ConnectTimeout)
```

### Effort Estimate

Katalog-Richtwert (checks/OBS-007.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — Pro Server 1–2 Stunden. Die Stellen sind mit zwei greps gefunden; die Zeit geht in den Test, der den Text hält.
