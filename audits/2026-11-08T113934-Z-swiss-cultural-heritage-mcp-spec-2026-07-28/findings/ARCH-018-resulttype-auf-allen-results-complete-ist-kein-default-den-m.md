## Finding: ARCH-018 — resultType auf allen Results — «complete» ist kein Default, den man weglässt

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | advisory |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `ARCH-018` |
| **PDF-Reference** | SEP-2322 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Nur fuer 2026-07-28. Am Draht liegt resultType auf jedem gemessenen Ergebnisweg an, Erfolg und isError, HTTP und stdio. Gesetzt wird es vom SDK, und kein Repo-Test haelt es fest; die SDK-Untergrenze ist fuer das Feld nicht verifiziert. Damit partial.

### Expected Behavior

Aus dem Katalog (`checks/ARCH-018.md`, Pass Criteria):

- [ ] `resultType` liegt auf jedem Result an — Erfolgs- **und** Fehlerpfad
- [ ] Der Wert ist `"complete"`, solange der Server kein MRTR führt
- [ ] Wird MRTR geführt, ist `"input_required"` ausschliesslich dem Zwischenstand vorbehalten (`HITL-006`)
- [ ] Stammt das Feld aus dem SDK, ist dessen Mindestversion im Manifest gepinnt
- [ ] Ein Test prüft das Feld am tatsächlichen Wire-Format, nicht am Rückgabewert der Python-Funktion — dazwischen liegt die Serialisierung, und genau dort geht es verloren

### Evidence

- rg 'resultType|result_type' src tests -> exit 1 (kein eigener Code, kein Test). Negative Kontrolle: dasselbe Muster trifft mcp_types/_types.py, methods.py, _v2026_07_28/__init__.py im venv — das Feld stammt aus dem SDK.
- Laufzeit HTTP 2026-07-28 (scratchpad/probe_modern.out): resultType 'complete' auf server/discover, tools/list, prompts/list, resources/list, resources/templates/list, resources/read, tools/call Erfolg (list_heritage_collections, isError false), tools/call ungueltiges Argument (isError true) und tools/call unbekanntes Tool (isError true).
- Laufzeit stdio (scratchpad/probe_stdio2.py): tools/call does_not_exist -> resultType complete, isError true; tools/call list_heritage_collections -> resultType complete, isError false; server/discover -> resultType complete.
- Kein MRTR im Server (rg 'input_required' src -> kein Treffer im eigenen Code, da resultType gar nicht vorkommt); Wert ist durchgehend 'complete'. SDK: mcp 2.3.0 mit exakt mcp-types==2.3.0; Manifest-Untergrenze pyproject.toml:39 mcp>=2.0.0.

### Gaps

- Kein Test prueft resultType am Wire-Format (Kriterium 5); die Konformitaet haengt ungetestet am SDK. Medium = Check-Severity.
- Ob die Manifest-Untergrenze mcp 2.0.0 das Feld bereits setzt, ist nicht gemessen (nur 2.3.0 installiert); die Untergrenze ist damit nicht als Mindestversion fuer dieses Feld belegt.

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

Seit `2026-07-28` trägt **jedes** Result ein Pflichtfeld `resultType`, mit genau zwei Werten: `"complete"` für ein fertiges Ergebnis und `"input_required"` für den Zwischenstand eines Multi-Round-Trip-Requests (`HITL-006`).

Die Falle steckt im zweiten Satz des Changelog-Eintrags:

> Clients **MUST** treat results from earlier-protocol servers that omit the field as `"complete"`.

Das ist eine Rückwärtskompatibilitäts-Regel für den Client, und sie macht diesen Check leise. Ein Server, der `resultType` schlicht weglässt, funktioniert bei jedem korrekten Client — der ergänzt `"complete"` und macht weiter. Nichts wird rot. Der Server behauptet damit aber, `2026-07-28` zu sprechen, und verlässt sich für seine Korrektheit auf eine Klausel, die es für **ältere** Server gibt.

Teuer wird das erst, wenn der Server irgendwann MRTR braucht: Dann ist `resultType` plötzlich bedeutungstragend, und die Stelle, an der es hätte gesetzt werden müssen, ist über alle Tool-Rückgaben verteilt. Deshalb `medium` statt `high` — es bricht heute nichts, aber es ist Schuld, die verzinst wird.

### Remediation

Aus dem Katalog (`checks/ARCH-018.md`, Remediation), auf die Gaps oben anzuwenden:

```python
def complete(payload: dict) -> dict:
    return {"resultType": "complete", **payload}

@mcp.tool()
async def search_documents(query: str) -> dict:
    try:
        return complete({"content": await _impl.search(query)})
    except UpstreamError as e:
        return complete({"isError": True, "content": [text(mask(e))]})
```

Eine Hilfsfunktion statt eines Feldes an 30 Stellen: Das Feld an jeder Rückgabe von Hand zu setzen ist genau die Sorte Pflicht, die beim 31. Tool vergessen wird.

### Effort Estimate

Katalog-Richtwert (checks/ARCH-018.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — eine Hilfsfunktion und ein Durchgang durch die Tool-Rückgaben. Entfällt ganz, wenn das SDK das Feld setzt.
