## Finding: ARCH-021 — Extensions deklariert und versioniert — Tasks sind kein Kern-Feature mehr

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | advisory |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `ARCH-021` |
| **PDF-Reference** | SEP-2663 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Nur fuer 2026-07-28. Keine Extension, keine Tasks, keine Anmassung des io.modelcontextprotocol-Namensraums; Deklaration deckt Realitaet. Es fehlt allein der README-Satz, den das erste Kriterium ausdruecklich verlangt -> partial.

### Expected Behavior

Aus dem Katalog (`checks/ARCH-021.md`, Pass Criteria):

- [ ] Führt der Server keine Extension, ist das im README in einem Satz festgehalten — nicht bloss unerwähnt
- [ ] Jede geführte Extension erscheint mit vollständiger, versionierter Kennung (`io.modelcontextprotocol/tasks`) in den Server-Capabilities
- [ ] Die Deklaration deckt sich in **beide** Richtungen mit dem Code
- [ ] Bei Tasks: Der Server spricht die Extension-Fassung (`tasks/get` / `tasks/update`), nicht `tasks/result` oder `tasks/list`
- [ ] Bei Tasks: Das README sagt, ob unaufgeforderte Task-Handles zurückgegeben werden, und die Tool-Descriptions sagen es bei den betroffenen Tools
- [ ] Eigene, nicht-offizielle Erweiterungen laufen unter einem eigenen Namensraum, nie unter `io.modelcontextprotocol/*`

### Evidence

- rg 'io\.modelcontextprotocol/|extensions' src/ -> exit 1; rg 'tasks/(get|update|result|list)|TaskHandle|task_id' src/ -> exit 1. Negative Kontrolle: das erste Muster trifft venv/.../mcp/server/lowlevel/server.py 15-mal.
- Laufzeit server/discover (HTTP und stdio): capabilities = {prompts:{listChanged}, resources:{listChanged, subscribe}, tools:{listChanged}} — kein extensions-Feld, keine Tasks. Deklaration und Code decken sich in beide Richtungen (beides leer).
- README: git show HEAD:README.md | rg -i 'extension' -> exit 1; rg -i 'extension' README.de.md -> exit 1. Der Abschnitt '## MCP Protocol Version' (HEAD:README.md:325-340) sagt nicht, dass keine Extensions gefuehrt werden.

### Gaps

- README haelt nicht in einem Satz fest, dass der Server keine Extensions fuehrt (Kriterium 1; 'keine' und 'nicht dokumentiert' sind ununterscheidbar).
- server/discover laesst das extensions-Feld weg statt {} zu melden (SDK-Verhalten; Remediation: 'Leer ist eine Aussage. Weglassen ist keine.') — low.

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

`2026-07-28` zieht eine Trennlinie zwischen Kernprotokoll und Erweiterungen. `ClientCapabilities` und `ServerCapabilities` bekommen ein `extensions`-Feld; was darüber hinaus geht, läuft als versionierte Extension mit einer Kennung im Namensraum `io.modelcontextprotocol/*`.

Der erste Umzugskandidat ist **Tasks**. In `2025-11-25` waren sie experimenteller Teil des Kerns; jetzt sind sie `io.modelcontextprotocol/tasks` — und die Extension ist nicht dieselbe API:

| `2025-11-25` (Kern, experimentell) | `2026-07-28` (Extension) |
|---|---|
| `tasks/result` blockiert bis fertig | `tasks/get`, aktiv gepollt |
| — | `tasks/update` für Client→Server-Eingaben |
| `tasks/list` | entfernt |
| Task-Handle nur nach Opt-in pro Request | Server darf unaufgefordert einen Handle liefern |

**Der letzte Punkt ist der, der Server bricht, die nichts geändert haben.** Ein Server auf der neuen Baseline darf einen Task-Handle zurückgeben, ohne dass der Client ihn angefordert hat. Ein Client, der das nicht erwartet, liest ihn als Ergebnis. Wer Tasks nutzt, muss deshalb wissen und deklarieren, welche Fassung er spricht — die Deklaration ist hier keine Formalie, sondern der einzige Weg, wie das Gegenüber die Frage beantworten kann.

**Für die Mehrheit des Portfolios ist die korrekte Antwort: keine Extensions.** Dann ist dieser Check in einem Satz erfüllt — und das ist Absicht. Er existiert, damit die Server, die eine führen, sie nicht stillschweigend führen.

### Remediation

Aus dem Katalog (`checks/ARCH-021.md`, Remediation), auf die Gaps oben anzuwenden:

```python
SERVER_CAPABILITIES = {
    "tools": {},
    "resources": {},
    # Leer ist eine Aussage. Weglassen ist keine.
    "extensions": {},
}
```

Mit Tasks:

```python
SERVER_CAPABILITIES = {
    "tools": {},
    "extensions": {
        "io.modelcontextprotocol/tasks": {"version": "1"},
    },
}
```

Im README, Sektion «MCP Protocol Version»:

> Dieser Server spricht `2026-07-28` und führt keine Extensions.

### Effort Estimate

Katalog-Richtwert (checks/ARCH-021.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — für Server ohne Extensions ein Feld und ein Satz. M, wenn Tasks von der Kern-Fassung auf die Extension umzustellen sind: blockierender Abruf wird zu Polling, und das betrifft auch den aufrufenden Agenten.
