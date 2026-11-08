# Lauf-Notiz — Release-Gate 0.7.0, Baseline 2025-11-25

Dieser Lauf ist **Gate 2** der Abschlusskette vor dem geplanten Release 0.7.0.
Er hat das Gate **nicht** bestanden: `production_ready: false`.
`audit-report.md` daneben ist mit `build_report.py` aus `summary.json`
erzeugt. Diese Notiz ergänzt, was der Generator nicht kennt.

## Zwei Läufe, eine Messung

Der Server spricht zwei Protokollstände: den Legacy-`initialize`-Handshake bis
`2025-11-25` und die Per-Request-Hülle von mcp 2.x bis `2026-07-28`. Weil
`mcp_spec_version` im Profil einen Wert verlangt, gibt es zwei Läufe mit
derselben Ziel-Revision und demselben Katalog:

- dieser Lauf: `2025-11-25`
- Schwesterlauf: `../2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2026-07-28/`

Checks, die für beide Revisionen gelten, wurden **einmal** gemessen. Ihr
Rohergebnis steht in beiden Läufen identisch. Die vollständige Notiz zu
Ausführung, Zwischenfällen und Reproduzierbarkeit steht im Schwesterlauf
(`00-RUN-NOTE.md`) und gilt für diesen Lauf gleichermassen.

**Baseline-Ausfälle in diesem Lauf (§3.3):** elf Checks sind nur für
`2026-07-28` geschrieben. Zehn davon sind im Schwesterlauf gemessen:
ARCH-015, ARCH-016, ARCH-017, ARCH-018, ARCH-020, ARCH-021, HITL-006,
SCALE-008, SCALE-010, SEC-027. Der elfte, SEC-025, ist auch dort nicht
anwendbar (`applies_when`: `no-match`) und wurde in keinem der beiden Läufe
gemessen.

## Ergebnis

25 pass / 41 partial / 17 fail, 1 todo (OPS-004).

Blockierend: DRIFT-003, FID-002, SCALE-002, SCALE-003, SEC-005.
SCALE-002 und SCALE-003 haben eine Ursache: Die Sessions des Legacy-Wegs leben
nur im Prozess, und nichts erzwingt den dokumentierten Betrieb mit genau einer
Instanz.

Ohne Veto, aber dringend: FID-006 (SIKART-Schemawechsel, Produktionsausfall
von `heritage_search_artists` und `heritage_get_artist`), siehe Schwesterlauf.

## Ziel

`9b3a1b4` auf `claude/release-0.7.0`, `verify-target` unverändert.
Working-Tree dirty: nur `README.md` (fachfremd, uncommittet).
