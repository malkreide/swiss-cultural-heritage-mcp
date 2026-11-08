## Finding: ARCH-008 — Drei Primitive nutzen: Tools, Resources und Prompts

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `ARCH-008` |
| **PDF-Reference** | Anhang A2 |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Kriterium 1 (>= zwei Primitive) klar erfüllt, Prompts kuratiert (Kriterium 4). Kriterium 3 nur halb (konsistent, nicht dokumentiert), Kriterium 5 nicht belegt -> partial.

### Expected Behavior

Aus dem Katalog (`checks/ARCH-008.md`, Pass Criteria):

- [ ] Server nutzt mindestens zwei der drei Primitive (Tools + Resources oder Tools + Prompts), oder
- [ ] README dokumentiert begründet, warum nur Tools verwendet werden
- [ ] Bei Resources: URI-Schema ist konsistent und dokumentiert
- [ ] Bei Prompts: Template-Liste ist kuratiert, nicht beliebig
- [ ] Tools, die rein read-only sind (idempotent, side-effect-frei, deterministisch), werden auf Resources-Migrations-Potential geprüft

### Evidence

- Laufzeit: `mcp.list_resources()` -> ['heritage://sik-isea/overview', 'heritage://nb/collections']; `mcp.list_prompts()` -> ['heritage_research_artist', 'heritage_find_educational_resources']; dazu 11 Tools, also alle drei Primitive in Gebrauch
- src/swiss_cultural_heritage_mcp/server.py:3283-3284, 3321-3322 — @mcp.resource mit Schema heritage://<quelle>/<thema>; src/swiss_cultural_heritage_mcp/server.py:3383-3384, 3419-3420 — @mcp.prompt, zwei kuratierte Workflows mit Tool-Folge und Ausgabeformat
- `git show HEAD:README.md | grep -nE 'heritage://|[Rr]esource|[Pp]rompt'` -> nur Zählungen (:52 '11 tools, 2 resources, 2 prompts', :58 'Prompt templates', :221-222, :268); keine URI und kein Prompt-Name in README.md oder README.de.md; `git grep heritage:// HEAD -- docs` -> nichts
- src/swiss_cultural_heritage_mcp/server.py:3213-3232 — list_heritage_collections hat openWorldHint=False und keinen Netzaufruf (grep nach _http|await|fetch im Handler-Block -> rc=1): statische, deterministische Daten als Tool, klassischer Resource-Kandidat; heritage_list_nb_collections überschneidet sich inhaltlich mit der Resource heritage://nb/collections

### Gaps

- medium: keine dokumentierte Prüfung, welche read-only Tools Resources sein könnten; list_heritage_collections ist statisch und bleibt ohne Begründung ein Tool
- low: URI-Schema konsistent, aber nirgends in README/docs dokumentiert; die Resource-URIs erfährt man nur über resources/list
- low: sik_isea_overview listet 3 der 11 Tools und spricht von 'allen drei Quellen'; für SNM, Memobase und Dodis gibt es keine Resource, das Inventar ist ungleichmässig

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

MCP definiert drei orthogonale Primitive, von denen die meisten Server nur eines nutzen:

| Primitiv | Zweck | Beispiel | Mentales Modell |
|---|---|---|---|
| **Tools** | Ausführbare Funktionen mit Side-Effects | `search_motions`, `create_invoice` | **Verben** |
| **Resources** | Passive Daten mit URI für Kontext-Lesen | `db://customers/12345`, `report://q3-2024` | **Substantive** |
| **Prompts** | Templates für wiederkehrende Workflows | `summarize_with_swiss_legal_context` | **Kochrezepte** |

Die häufige Anti-Pattern: alles als Tool modellieren. Ein Tool wie `get_document(id)` ist semantisch ein Resource — es hat keine Side-Effects, ist idempotent, dient nur dem Kontext-Lesen. Als Tool kostet es Tokens im Tool-Manifest und konkurriert mit echten aktiven Operationen um die Tool-Budget-Grenze (siehe ARCH-006).

Resources haben drei klare Vorteile gegenüber Read-only-Tools:

1. **Niedrigerer Token-Verbrauch im Tool-Manifest** — Resources werden nicht in jedem LLM-Call gelistet, sie werden vom Client on-demand abgerufen.
2. **Strukturierte URI-Hierarchie** — `school://schulhaus-leutschenbach/2024/luftqualitaet` ist auch ohne LLM-Inferenz navigierbar.
3. **Cache-Freundlichkeit** — Clients können Resources cachen, Tools nicht.

Prompts sind unterausgenutzt. Sie sind besonders wertvoll für wiederkehrende Schulamt-Workflows: «Bildungsbericht für Quartal Q», «Schulhaus-Vergleich nach Standortindex». Statt dass jeder User den Prompt selbst formuliert, bietet der Server geprüfte, kuratierte Templates an.

Für die meisten Server im Schulamt-Portfolio ist die ehrliche Antwort: Tools-only ist okay für Phase-1-Wrapper, aber Resources sollten geprüft werden, sobald der Server reift.

### Remediation

Aus dem Katalog (`checks/ARCH-008.md`, Remediation), auf die Gaps oben anzuwenden:

### Schritt 1: Tools-zu-Resources-Audit

Pro Tool prüfen:

```
- Hat Side-Effects? → Tool bleibt
- Ist deterministisch und idempotent? → Resource-Kandidat
- Liefert primär Kontextdaten zum Lesen? → Resource-Kandidat
```

### Schritt 2: URI-Schema definieren

Pro Resource-Klasse ein konsistentes Schema:

```
school://<school_id>/profile
school://<school_id>/classes/<year>
luftqualitaet://<school_id>/<date>
budget://<school_id>/<year>
```

### Schritt 3: Migration

```diff
- @mcp.tool()
- async def get_school_profile(school_id: str) -> dict:
-     return await db.get_school_profile(school_id).dict()

+ @mcp.resource("school://{school_id}/profile")
+ async def school_profile(school_id: str) -> str:
+     profile = await db.get_school_profile(school_id)
+     return profile.as_markdown()
```

### Schritt 4: Prompts-Inventar

Falls wiederkehrende Workflows existieren: pro Workflow ein Prompt-Template, ins README dokumentieren.

### Effort Estimate

Katalog-Richtwert (checks/ARCH-008.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

M — 1–3 Tage. Audit + Migration einer Handvoll Tools + Doku.
