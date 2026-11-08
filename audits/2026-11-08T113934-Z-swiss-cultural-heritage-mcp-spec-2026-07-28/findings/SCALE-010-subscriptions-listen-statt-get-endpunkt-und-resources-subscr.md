## Finding: SCALE-010 — subscriptions/listen statt GET-Endpunkt und resources/subscribe

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | advisory |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `SCALE-010` |
| **PDF-Reference** | SEP-2575 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Nur 2026-07-28. Die Mechanik stimmt: GET 405, kein resources/subscribe, subscriptions/listen vom SDK mit subscriptionId bestaetigt, Progress laeuft request-gebunden (in-process gemessen, nicht ueber HTTP). Offen ist der Doku-Satz und die Widerspruechlichkeit der beworbenen listChanged-Capability gegenueber statischen Listen.

### Expected Behavior

Aus dem Katalog (`checks/SCALE-010.md`, Pass Criteria):

- [ ] Führt der Server keine Änderungsbenachrichtigungen, ist das belegt und im README festgehalten — mit einem Satz, nicht durch Schweigen
- [ ] Kein `resources/subscribe` / `resources/unsubscribe` mehr im Code
- [ ] Kein GET-Endpunkt für serverinitiierte Nachrichten; ein GET auf den MCP-Pfad antwortet `405`
- [ ] Führt der Server Benachrichtigungen: Der Client trägt sich über `subscriptions/listen` je Typ ein, und der Server bestätigt
- [ ] Jede Benachrichtigung trägt `io.modelcontextprotocol/subscriptionId`
- [ ] `notifications/progress` und `notifications/message` laufen weiter auf dem Antwortstrom ihres Requests, **nicht** auf `subscriptions/listen` — mit einem Test belegt
- [ ] Der Reverse Proxy puffert den langlebigen Strom nicht und schliesst ihn nicht vor dem Server

### Evidence

- grep -rnE 'resources/(un)?subscribe|resource_subscribe|@app.get(.*mcp|handle_get|subscribe_resource' src/ -> 0 Treffer; grep 'subscriptions/listen|subscriptionId|toolsListChanged|resourcesListChanged|subscriptions=' src/ -> 0 Treffer; Negativkontrolle: Muster trifft im SDK in 11 Dateien
- Runtime (lokal gestarteter Server HEAD 9b3a1b4 (editable install), MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT=8765, SDK mcp 2.3.0, 2026-11-08): GET /mcp mit MCP-Protocol-Version: 2026-07-28 -> HTTP 405, `allow: POST`; POST resources/subscribe (2026-07-28) -> HTTP 404 {"code":-32601,"message":"Method not found","data":"resources/subscribe"}
- Runtime: POST subscriptions/listen {toolsListChanged, resourcesListChanged} -> HTTP 200 text/event-stream, erstes Event `notifications/subscriptions/acknowledged` mit `_meta.io.modelcontextprotocol/subscriptionId: 7` — SDK bestaetigt das Opt-in je Typ
- Runtime in-process (scratchpad/probe/sdk003_probe.py, Client(mode='2026-07-28'), respx-Mocks): call_tool heritage_cross_search mit progress_callback -> 2 Progress-Meldungen [(1,2,'SIK-ISEA: Fehler'),(2,2,'SNM: 0 Treffer')] auf dem Aufruf selbst; Code: src/swiss_cultural_heritage_mcp/server.py:2486 und :2864 `ctx.report_progress(...)` im Request-Kontext
- Runtime: server/discover 2026-07-28 meldet capabilities tools/prompts/resources `listChanged: true`, resources `subscribe: true`; initialize 2025-11-25 meldet dieselben als false. Tools/Resources/Prompts werden per Dekorator beim Import registriert (src/swiss_cultural_heritage_mcp/server.py:381 Kommentar, :388-397 CACHE_HINTS), es gibt keinen Code, der eine Aenderung meldet

### Gaps

- low: README sagt nirgends, dass der Server keine Aenderungsbenachrichtigungen fuehrt (git show HEAD:README.md | grep -niE 'notif|listChanged|subscri|benachricht' -> rc=1) — das Kriterium verlangt den Satz
- low: die moderne Aera bewirbt listChanged:true / subscribe:true (SDK-Default), obwohl die Listen statisch sind — Opt-in ohne Wirkung; Abgrenzung zu ARCH-020
- low: Repo-Test fuer Progress prueft nur einen Context-Doppelgaenger (tests/test_server.py:1117-1149 _RecordingCtx), nicht die Zustellung auf dem Antwortstrom des Requests

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

`2026-07-28` ersetzt zwei Mechanismen durch einen. Weg sind der HTTP-GET-Endpunkt für serverinitiierte Nachrichten und das Paar `resources/subscribe` / `resources/unsubscribe`. An ihre Stelle tritt `subscriptions/listen`: ein einzelner langlebiger POST-Antwortstrom, in den sich der Client für bestimmte Benachrichtigungstypen einträgt — `toolsListChanged`, `promptsListChanged`, `resourcesListChanged`, `resourceSubscriptions`. Der Server bestätigt und markiert jede Benachrichtigung mit `io.modelcontextprotocol/subscriptionId`.

**Die Trennlinie, an der die Migration schiefgeht:** Nicht alles, was der Server ungefragt sendet, gehört in diesen Strom. Request-bezogene Benachrichtigungen — `notifications/progress`, `notifications/message` — laufen weiterhin auf dem Antwortstrom **des Requests, zu dem sie gehören**. Nur was keinem Request zugeordnet ist, gehört auf `subscriptions/listen`.

Ein Server, der beim Umbau alles in den neuen Strom schiebt, bricht die Fortschrittsmeldung: Der Client wartet auf dem Antwortstrom seines Tool-Calls auf Fortschritt und bekommt dort nichts, während die Meldungen ohne Request-Bezug daneben eintreffen. Nichts wirft einen Fehler; der Fortschrittsbalken bleibt stehen.

**Bedingt anwendbar.** Ein Server ohne Änderungsbenachrichtigungen — die Mehrheit der Read-only-Wrapper im Portfolio — erfüllt diesen Check dadurch, dass er nichts dergleichen führt. Das ist ein `pass` mit einem Satz Evidenz, kein «nicht anwendbar»: Der Unterschied zwischen «führt keine» und «nicht nachgesehen» ist genau der, den §2.6 einfordert.

### Remediation

Aus dem Katalog (`checks/SCALE-010.md`, Remediation), auf die Gaps oben anzuwenden:

```diff
-@app.get("/mcp")
-async def legacy_notification_stream(request: Request):
-    return EventSourceResponse(_pending_notifications())
-
-@server.subscribe_resource()
-async def subscribe(uri: str) -> None:
-    _SUBSCRIBERS.add(uri)
+@server.subscriptions_listen()
+async def listen(types: list[str]) -> SubscriptionStream:
+    stream = await _subs.open(types)          # Server bestätigt das Opt-in
+    return stream                              # Benachrichtigungen tragen subscriptionId
```

Fortschritt bleibt, wo er war:

```python
@mcp.tool()
async def bulk_export(ctx: Context, year: int) -> dict:
    for i, chunk in enumerate(chunks):
        await ctx.report_progress(i, len(chunks))   # Antwortstrom DIESES Requests
    return complete({"rows": total})
```

### Effort Estimate

Katalog-Richtwert (checks/SCALE-010.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S für Server ohne Benachrichtigungen (Beleg und ein Satz README). M, wenn ein Abonnementpfad umgebaut werden muss — die Zuordnung request-bezogen gegen abonnementbezogen ist der eigentliche Aufwand, nicht der Strom.
