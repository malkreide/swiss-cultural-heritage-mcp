## Finding: IDENT-005 — Fallback-Version darf nicht wie ein Release aussehen

| Feld | Wert |
|---|---|
| **Severity** | medium |
| **Adoption** | enforced |
| **Check-Status** | partial |
| **Status** | open |
| **Server** | `swiss-cultural-heritage-mcp` |
| **Check-Reference** | `IDENT-005` |
| **PDF-Reference** | Custom (Portfolio-Sweep 2026-07-29, 30 Server) |
| **Audit-Datum** | 2026-11-08 |
| **Run** | `2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25` |
| **Ziel** | `9b3a1b4dde89` auf `claude/release-0.7.0` (Working-Tree dirty: nur `README.md`, fachfremd) |
| **Auditor** | Claude (mcp-audit 2.3.0, Subagent je Kategorie; Ergebnis per verify_raw_outputs geprueft) |

### Observed Behavior

Kein Coverage-Gate (ci.yml ohne --cov) → pragma-Kriterium n/a. Form und strukturelle Erkennung korrekt, Einheitlichkeit und Begruendung fehlen.

### Expected Behavior

Aus dem Katalog (`checks/IDENT-005.md`, Pass Criteria):

- [ ] Der Fallback trägt ein lokales Segment nach `+` (z. B. `0.0.0+source`)
- [ ] Der Marker ist portfolioweit einheitlich
- [ ] Ein Kommentar erklärt, **warum** kein plausibler Platzhalter gewählt wurde
- [ ] Der Drift-Check erkennt Fallbacks am `+`-Segment, nicht am konkreten String
- [ ] Bei Repos mit Coverage-Gate trägt der Zweig `# pragma: no cover` (er ist per Definition nicht abgedeckt)

### Evidence

- grep -rn -A3 'except PackageNotFoundError' src/ → src/swiss_cultural_heritage_mcp/__init__.py:28-29 '__version__ = "0.0.0+local"' (lokales Segment nach '+'); src/swiss_cultural_heritage_mcp/server.py:221-222 svc_version-Fallback ebenfalls '0.0.0+local'
- scripts/check_version_sync.py:find_hardcoded — Fallback-Erkennung strukturell ('if any("+" not in v for v in values)'), nicht am konkreten String

### Gaps

- low: Marker '0.0.0+local' weicht von der Portfolio-Konvention '0.0.0+source' ab (Kriterium 2); das Gate-Docstring nennt selbst '0.0.0+source'
- low: Kommentar am Fallback ('# not installed (running from source tree)') erklaert nicht, warum kein plausibler Platzhalter gewaehlt wurde (Kriterium 3)

### Risk Description

Siehe Gaps; Severity laut Katalog `medium`. Katalogbeschreibung:

Wer `__version__` aus den Paket-Metadaten liest (IDENT-002), braucht einen Zweig für den Fall ohne Installation — den reinen Quell-Checkout. Was dort steht, entscheidet, ob der Umbau die Drift wirklich beseitigt oder sie nur verschiebt.

`swiss-statistics-mcp` hatte:

```python
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"
```

`0.0.0` ist syntaktisch eine gültige Version. In einem Upstream-Log, in einer Fehlermeldung, in einem User-Agent ist sie von einer echten Release-Nummer nicht zu unterscheiden. Damit meldet der Server ohne Installation eine Zahl, die etwas behauptet — genau das, was der Umbau vermeiden sollte.

Die Konvention im Portfolio ist ein **lokales Segment** nach `+`:

```python
    __version__ = "0.0.0+source"
```

Das Segment ist PEP-440-konform, überlebt Versionsvergleiche und ist auf einen Blick als «keine Version bekannt» lesbar.

**Der Fallback kann auch im installierten Paket feuern — und dann ist er ein Befund, kein Fallback.** Dieser Check prüft die *Form* des Markers, eine reine Quell-Eigenschaft, und das ist richtig so. Er sagt aber nichts darüber, ob der Zweig im ausgelieferten Artefakt greift. Sind die Metadaten im publizierten Wheel beschädigt oder fehlt der Distributionsname, den `version()` nachschlägt, dann meldet das installierte Paket `0.0.0+source` auf der Leitung — korrekt geformt, und trotzdem ein kaputtes Artefakt.

Genau dafür ist der Marker gebaut: Er macht diesen Zustand **sichtbar**, statt ihn als plausible Release-Nummer zu tarnen. Gemessen wird er anderswo — `IDENT-001` Modus 3 löst den User-Agent am aus dem Index installierten Paket auf, und `0.0.0+source` dort ist ein Befund gegen `IDENT-002`, nicht gegen diesen Check.

**Der zweite Grund ist maschineller Natur:** Ein Check, der hartkodierte Versionen in `src/` findet (IDENT-002), muss den Fallback ausnehmen — und zwar am Aufbau, nicht am Wert. Das `+`-Segment ist das einzige verlässliche Unterscheidungsmerkmal. Ein Fallback `"0.0.0"` ist von einem echten Literal nicht trennbar und wird korrekt als Befund gemeldet.

Im Sweep war das mehr als Theorie: Meine erste Fassung des Checks nahm `0+unknown` als Marker an (die Form eines einzelnen Servers) und meldete daraufhin **neun Fehlalarme** gegen die Portfolio-Form `0.0.0+source`. Erst die Umstellung auf «enthält `+`» statt «gleicht diesem String» war robust.

### Remediation

Aus dem Katalog (`checks/IDENT-005.md`, Remediation), auf die Gaps oben anzuwenden:

```diff
  except PackageNotFoundError:  # pragma: no cover
-     __version__ = "0.0.0"
+     # Bewusst mit lokalem Segment: "0.0.0" allein sieht wie ein echtes
+     # Release aus. Der Marker macht sichtbar, dass hier keine Version
+     # bekannt ist — Portfolio-Konvention.
+     __version__ = "0.0.0+source"
```

Und im Check die Erkennung am Aufbau festmachen:

```diff
- if value == "0.0.0+source":       # nur diese eine Form
+ if "+" in value:                  # jedes lokale Segment ist ein Fallback
      continue
```

### Effort Estimate

Katalog-Richtwert (checks/IDENT-005.md, Abschnitt Effort), nicht fuer diesen Server nachgeschaetzt:

XS — Minuten pro Server.
