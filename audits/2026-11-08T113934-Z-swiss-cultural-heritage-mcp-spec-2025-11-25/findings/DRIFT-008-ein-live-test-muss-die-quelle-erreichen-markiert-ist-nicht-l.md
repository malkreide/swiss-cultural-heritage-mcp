## Finding: DRIFT-008 — Ein Live-Test muss die Quelle erreichen — «markiert» ist nicht «live»

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | advisory |
| **Check-Status** | fail |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `DRIFT-008` |
| **PDF-Reference** | Custom (Portfolio-Fundstück zh-education-mcp, 2026-08-08) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Die Kernfrage, ob die Live-Suite die Quelle erreicht, ist heute positiv belegt: kein Stub im Geltungsbereich, dazu Spuren echten Netzverkehrs. Erfüllt ist Kriterium 1 von 6; die übrigen verlangen den vorbeugenden Wächter samt Gegenprobe, und den gibt es nicht. Nach der 50-%-Regel daher fail, bei derzeit null Exposition. Advisory.

### Expected Behavior

Aus dem Katalog (`checks/DRIFT-008.md`, Pass Criteria):

- [ ] Jede `autouse`-Fixture, die Auflösung, Transport, Zeit oder Umgebung ersetzt, nimmt Live-Tests aus — oder in ihrem Geltungsbereich existiert nachweislich kein Live-Test
- [ ] Ein Wächter bricht Live-Tests ab, deren Aussenwelt ersetzt wurde, und zwar **suiteweit**, nicht je Datei
- [ ] Der Wächter läuft zwischen Fixture-Aufbau und Testkörper (Hook), nicht als Fixture
- [ ] Der echte Referenzwert wird beim Import festgehalten, vor jeder Fixture
- [ ] Die Gegenprobe ist geführt und in beide Richtungen belegt: Rückfall fällt, ehrlicher Live-Test bleibt grün
- [ ] Die Fehlermeldung nennt die Behebung, nicht nur den Zustand — wer sie liest, sucht sonst zuerst bei der Quelle

### Evidence

- grep -rn -A12 'autouse=True' tests/*.py — nur zwei autouse-Fixtures: tests/conftest.py:14-20 (_reset_http_client, schliesst nach jedem Test den Client und ersetzt nichts) und tests/test_transport_security.py:45-49 (patcht settings.inbound_allowed_hosts/cors_origins, die Datei hat keinen Live-Test). grep 'getaddrinfo|create_connection|freeze_time|AsyncHTTPTransport' tests/ ohne Treffer; alle Live-Tests liegen in tests/test_server.py:1956-2081
- gh run view 39233988544 --log (2026-10-19) — httpx.ReadTimeout aus echtem Netzverkehr in test_live_search_hodler; Lauf 42475229230 (2026-11-08): 11 Live-Tests PASSED, je 1-2 s; lokale Probe am 2026-11-08: socket.getaddrinfo('beta.dodis.ch') -> 83.228.234.53, die Antwort trägt einen echten Datensatz (Bundesratsprotokoll vom 12.8.1921)
- grep -rn 'request.keywords|item.keywords|pytest_runtest' tests/*.py — keine Treffer: kein suiteweiter Wächter-Hook, keine Live-Ausnahme in Fixtures, keine Gegenprobe

### Gaps

- Kein suiteweiter Wächter (pytest_runtest_call-Hook mit einem beim Import festgehaltenen Referenzwert), der Live-Tests mit ersetzter Aussenwelt abbricht (medium, derzeit latent)
- Keine Gegenprobe in beide Richtungen (synthetischer Live-Test mit stubbender autouse-Fixture) (medium)

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

Ein Live-Test ist im Katalog kein gewöhnlicher Test. Er ist der **Beleg**: die einzige Stelle, an der eine Annahme über eine fremde Quelle widerlegt werden kann. Jeder andere Test prüft gegen eine Fixture, und die Fixture ist aus derselben Annahme geschrieben wie der Code — sie bestätigt sie, so lange es sie gibt. Deshalb verlangt [`SKILL.md` §2.6](../SKILL.md), dass ein Live-Test, der **nicht gelaufen** ist, `todo` ergibt und nicht `pass`.

Dieser Check ergänzt den zweiten Fall, der genauso aussieht und schlimmer ist: **Der Live-Test ist gelaufen — nur nicht gegen die Quelle.**

Eine Testsuite hält die Unit-Tests hermetisch, und das ist richtig. Sie stubbt Namensauflösung, Zeit, Zufall, Umgebung. Wird auch nur einer dieser Stubs für Live-Tests nicht ausgenommen, prüft der Beleg nichts mehr — und er sagt es nicht. Er wird rot oder grün aus Gründen, die mit der Quelle nichts zu tun haben.

### Der Belegfall

`zh-education-mcp`, 2026-08-08. `tests/test_server.py` trug:

```python
@pytest.fixture(autouse=True)
def _stub_dns(monkeypatch):
    """… damit Unit-Tests hermetisch bleiben (kein echtes DNS) …"""
    monkeypatch.setattr("zh_education_mcp.http_client.socket.getaddrinfo", fake_getaddrinfo)
```

`fake_getaddrinfo` liefert `8.8.8.8`. Die Fixture ist `autouse` für die ganze Datei und nimmt Live-Tests **nicht** aus — die Fixtures in `conftest.py` tun das, diese eine nicht. Der einzige Live-Test jener Datei verband sich also nach `8.8.8.8:443` und sandte SNI `www.bista.zh.ch`. Google antwortet mit einem Zertifikat für `dns.google`:

```
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
Hostname mismatch, certificate is not valid for 'www.bista.zh.ch'
```

**Fünf Läufe lang sah das aus wie ein Befund über die Quelle.** Erst wie ein falsches Zertifikat des Kantons Zürich, dann wie ein flatternder Knoten in einem Pool, dann wie eine Reihenfolge-Abhängigkeit in der Suite. Es kostete einen Diagnoseschritt im Workflow, drei Sonden und zwei Korrekturen an einem bereits veröffentlichten Katalogeintrag, bis der Ausschluss vollständig war. Der Fehler war eine fehlende Zeile:

```python
if "live" in request.keywords:
    return
```

Verschärfend, und der Grund für die Reichweite: Der Stub sieht lokal aus und ist global. `http_client` macht `import socket`, also **ist** `http_client.socket` das stdlib-Modulobjekt. Wer dessen `getaddrinfo` ersetzt, ersetzt es prozessweit — auch für `anyio`, über das `httpx` verbindet. Gemessen:

```
http_client.socket is socket   ->  True
socket.getaddrinfo("www.bista.zh.ch", 443)  ->  ('8.8.8.8', 443)
anyio sieht dieselbe Funktion  ->  True
```

### Warum das ein eigener Check ist

Der **Mechanismus** steht bereits in `OPS-010 b)` — der globale Monkeypatch auf ein fremdes Modul, mit `modul.asyncio` als Belegfall. Das **Kriterium** dort ist ein anderes: `OPS-010` fragt, ob das Brechen einer Zusicherung einen Test rot macht. Diese Frage war hier grün beantwortet. Die Mutationstests von `_confirm_shape` fallen sauber; der Stub hatte mit Mutationsabdeckung nichts zu tun.

Und `DRIFT-005` fragt, ob die Live-Suite **läuft**. Sie lief — fünfmal, mit Issue und Benachrichtigung, genau wie verlangt.

Was keiner der beiden fragt: **ob dabei die Quelle angesprochen wurde.** Genau dort fällt dieser Fall hindurch, und deshalb steht er hier statt als Absatz in `OPS-010`.

`high`: Ein Live-Test, der gegen einen Stub läuft, prüft nichts und behauptet alles. Läuft er grün, ist der Vertrag mit der Quelle ungeprüft und gilt als geprüft. Läuft er rot, erzeugt er einen **Befund über einen Dritten**, den niemand verschuldet hat — im Belegfall beinahe eine Meldung an den Kanton Zürich über ein Zertifikat, das in Ordnung war.

**Zur Nummer:** `DRIFT-007` ist vergeben und zurückgezogen (2026-08-07, aufgegangen in `FID-006`). Die Nummer bleibt verbrannt, damit der Audit-Trail eindeutig bleibt.

### Remediation

Aus dem Katalog (`checks/DRIFT-008.md`, Remediation), auf die Gaps oben anzuwenden:

Die Ausnahme in jede betroffene Fixture, auch vorsorglich in Dateien ohne heutigen Live-Test:

```diff
 @pytest.fixture(autouse=True)
-def _stub_dns(monkeypatch):
+def _stub_dns(request, monkeypatch):
+    if "live" in request.keywords:
+        return
+
     monkeypatch.setattr("paket.http_client.socket.getaddrinfo", fake_getaddrinfo)
```

Dann der Wächter aus Modus 2. Die Ausnahme behebt den bekannten Fall, der Wächter den nächsten — und der nächste kommt aus einer Datei, die es heute noch nicht gibt.

### Effort Estimate

Katalog-Richtwert (checks/DRIFT-008.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

**S–M.** Die Ausnahme ist eine Zeile je Fixture. Der Wächter samt Gegenprobe ist eine halbe Stunde. Teuer ist ausschliesslich die Diagnose, wenn er fehlt: Im Belegfall fünf Läufe, drei Sonden und zwei Korrekturen an einem veröffentlichten Eintrag.
