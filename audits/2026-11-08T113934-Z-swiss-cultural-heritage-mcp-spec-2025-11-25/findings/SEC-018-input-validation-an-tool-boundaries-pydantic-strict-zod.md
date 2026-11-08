## Finding: SEC-018 — Input-Validation an Tool-Boundaries (Pydantic strict / Zod)

| Feld | Wert |
|---|---|
| **Severity** | high |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `SEC-018` |
| **PDF-Reference** | Sec 3 / Sec 4 (Defense-in-Depth) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Schema coverage and extra='forbid' are complete, and validation errors come back as isError. Gaps in strictness, bounds and whitelist patterns, the most serious being item_id flowing unencoded into the upstream path. The host stays fixed (see SEC-004), so this is no SSRF, but it is uncontrolled path access on beta.dodis.ch / api.memobase.ch.

### Expected Behavior

Aus dem Katalog (`checks/SEC-018.md`, Pass Criteria):

- [ ] **Alle** Tool-Argumente haben Schema-Validation (Pydantic / Zod / vergleichbar)
- [ ] Numerische Felder haben `ge`/`le`-Constraints (kein unbegrenzter Range)
- [ ] String-Felder haben `min_length`/`max_length` und idealerweise `pattern`
- [ ] Pattern sind Whitelist-basiert, nicht Blacklist
- [ ] Bei Pydantic: `strict=True` und `extra="forbid"` explizit gesetzt
- [ ] Validation-Errors landen als `isError` im Tool-Result, nicht als Server-Crash (siehe OBS-001)
- [ ] Tests decken Edge-Cases ab: zu lange Strings, Out-of-Range-Numbers, unbekannte Felder

### Evidence

- src/swiss_cultural_heritage_mcp/server.py:1338,1490,1587,1748,1875,2144,2208,2324,2760,2966,3157 — all 11 tool input models are pydantic BaseModel with ConfigDict(extra='forbid'); limit fields with ge/le (e.g. :1351-1353 ge=1, le=MAX_LIMIT), date fields with a pattern (:1904, :2775, :2780)
- venv python -I model_validate probe — limit 99999 -> REJECTED less_than_equal; unknown field -> REJECTED extra_forbidden; query 500 chars -> REJECTED string_too_long
- Same probe — limit '5' (string) -> ACCEPTED as int 5 (no strict mode); offset 10**12 -> ACCEPTED (offset only ge=0, no le, :1354/:1599/:1760); ArtistDetailInput.artist_id 10'000 chars -> ACCEPTED (only min_length=1, :1492-1496); CollectionBrowseInput.resource_id 'a\x00b' -> ACCEPTED (:1750-1754); PublicationDetailInput.identifier 10'000 chars -> ACCEPTED (:2210-2214); HeritageItemInput.item_id '../../solr/admin' -> ACCEPTED
- src/swiss_cultural_heritage_mcp/server.py:3135-3137 + httpx.URL probe — item_id flows unencoded into the path: '../../solr/admin' becomes https://beta.dodis.ch/api/solr/admin (path traversal on the allowed host)
- mcp.call_tool('heritage_search_artists', {'params': {'query':'Hodler','limit':99999}}) -> ToolError 'Input should be less than or equal to 100' (comes back as isError, no crash)
- tests/test_server.py:683-735 — tests for limit bounds, blank query, date pattern, invalid sources (with pytest.raises(Exception)); no test for extra fields, overlong strings, or offset

### Gaps

- strict=True is set nowhere: type coercion '5' -> 5 (severity: medium)
- Numeric field offset without an upper bound in 4 models (severity: medium)
- ID strings (artist_id, resource_id, identifier) without max_length or a whitelist pattern; item_id without a pattern, which allows path traversal on the upstream host (severity: high)
- Edge-case tests for extra fields, overlong strings, control characters missing (severity: low)

### Risk Description

Siehe Gaps; Severity laut Katalog `high`. Katalogbeschreibung:

Tool-Argumente kommen vom LLM — einer probabilistischen Quelle, die halluzinieren, formattieren-falsch oder von Prompt-Injection beeinflusst sein kann. Ohne strikte Input-Validation am Tool-Boundary werden invalide oder bösartige Inputs in die Geschäftslogik weitergereicht und können dort:

1. **Unerwartete Exceptions** auslösen → Error-Pfad könnte Information leaken (siehe OBS-002)
2. **Type Confusion** triggern → z.B. `user_id: int` aber LLM schickt String → SQL-Coercion-Bug
3. **Range-Violations** verursachen → z.B. negative Pagination-Limits → DB-Crash oder Memory-Explosion
4. **Encoding-Probleme** propagieren → Unicode-Tricks, Null-Bytes, Control-Characters

Dies ist die universelle Defense-in-Depth-Schicht, die unabhängig von SDK-005 (TypeScript/Zod) für **alle** SDKs gilt: jedes Tool-Argument wird gegen ein striktes Schema geprüft, **bevor** es in Tool-Logik fliesst.

Im Python-Ökosystem ist Pydantic v2 mit `strict=True` der Standard. Im TypeScript-Ökosystem Zod (siehe SDK-005). In Go: validator.v10 oder go-playground/validator. In Rust: serde + validator.

### Remediation

Aus dem Katalog (`checks/SEC-018.md`, Remediation), auf die Gaps oben anzuwenden:

### Schritt 1: Schema pro Tool extrahieren

```diff
+ from typing import Annotated
+ from pydantic import BaseModel, Field, StringConstraints
+
+ class SearchArgs(BaseModel):
+     model_config = {"strict": True, "extra": "forbid"}
+     query: Annotated[str, StringConstraints(min_length=2, max_length=200)]
+     limit: Annotated[int, Field(ge=1, le=100)] = 10

  @mcp.tool()
- async def search(query: str, limit: int = 10) -> dict:
+ async def search(args: SearchArgs, ctx: Context) -> dict:
-     return await db.search(query, limit=limit)
+     return await db.search(args.query, limit=args.limit)
```

### Schritt 2: ValidationError sauber behandeln

```python
from pydantic import ValidationError

@mcp.tool()
async def search(args: SearchArgs, ctx: Context) -> dict:
    try:
        # Pydantic validiert beim Parsing automatisch — kein Aufruf nötig
        # Falls manuell aus dict gebaut: SearchArgs.model_validate(raw_dict)
        return await db.search(args.query, limit=args.limit)
    except ValidationError as e:
        # Wird normal nicht erreicht (FastMCP fängt das ab),
        # aber Defense-in-Depth:
        return {
            "isError": True,
            "content": [TextContent(
                type="text",
                text=f"Invalid arguments: {e.errors()[0]['msg']}"
            )],
        }
```

### Schritt 3: Tests gegen Edge-Cases

```python
@pytest.mark.parametrize("invalid_args,expected_error", [
    ({"query": "a", "limit": 10}, "min_length"),       # zu kurz
    ({"query": "x"*500, "limit": 10}, "max_length"),   # zu lang
    ({"query": "test", "limit": 0}, "greater_than_or_equal"),
    ({"query": "test", "limit": 99999}, "less_than_or_equal"),
    ({"query": "test", "limit": 10, "evil": "field"}, "extra_forbidden"),
])
async def test_search_rejects_invalid(invalid_args, expected_error):
    with pytest.raises(ValidationError) as exc:
        SearchArgs.model_validate(invalid_args)
    assert any(expected_error in err["type"] for err in exc.value.errors())
```

### Effort Estimate

Katalog-Richtwert (checks/SEC-018.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

S — < 1 Tag pro Server bei wenigen Tools, M bei vielen Tools (10+).
