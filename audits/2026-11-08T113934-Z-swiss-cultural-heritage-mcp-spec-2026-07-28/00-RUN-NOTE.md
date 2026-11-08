# Lauf-Notiz — Release-Gate 0.7.0, Baseline 2026-07-28

Dieser Lauf ist **Gate 2** der Abschlusskette vor dem geplanten Release 0.7.0.
Er hat das Gate **nicht** bestanden: `production_ready: false`.
`audit-report.md` daneben ist mit `build_report.py` aus `summary.json`
erzeugt. Diese Notiz ergänzt, was der Generator nicht kennt.

## Zwei Läufe, eine Messung

Der Server spricht zwei Protokollstände: den Legacy-`initialize`-Handshake bis
`2025-11-25` und die Per-Request-Hülle von mcp 2.x bis `2026-07-28`. Weil
`mcp_spec_version` im Profil einen Wert verlangt, gibt es zwei Läufe mit
derselben Ziel-Revision und demselben Katalog:

- dieser Lauf: `2026-07-28`
- Schwesterlauf: `../2026-11-08T113934-Z-swiss-cultural-heritage-mcp-spec-2025-11-25/`

Checks, die für beide Revisionen gelten, wurden **einmal** gemessen. Ihr
Rohergebnis steht in beiden Läufen identisch.

**Baseline-Ausfälle in diesem Lauf (§3.3),** gemessen nur im Schwesterlauf:
SCALE-002, SCALE-003, SCALE-007, SDK-004, SEC-009.

## Ergebnis

30 pass / 44 partial / 14 fail, 1 todo (OPS-004: Prüfobjekt ist dieser
Report, er existierte bei der Messung noch nicht).

Blockierend: DRIFT-003, FID-002, SEC-005.

**Ohne Veto, aber dringend: FID-006.** SIKART hat das Schema seines
Datensatzes geändert. `heritage_search_artists` und `heritage_cross_search`
zeigen jede Person als «(Unbekannt)», und `heritage_get_artist` findet nichts.
Das gilt auch für das publizierte 0.6.0. In der Hauptsession am 2026-11-08 um
11:53 UTC nachgemessen (`datastore_search`, HTTP 200, alte Felder `HAUPTNR`,
`NAME`, `SIKART_LINK` fehlen). Der Check ist `advisory`, deshalb blockiert er
nicht. Ein Produktionsausfall ist es trotzdem. Dazu gehört die Lizenz: live
steht CC0, der Server nennt CC BY (CH-004).

## Ziel und Reproduzierbarkeit

- Ziel: `9b3a1b4` auf `claude/release-0.7.0`. `verify-target`: unverändert.
- Working-Tree dirty: nur `README.md`, eine fachfremde, uncommittete Änderung
  (Überschrift im generierten Install-Block). Die Checks haben das README
  per `git show HEAD:README.md` gelesen.
- Katalog-Hash: `2bbded9079fd…`. Der Report zeigt «Catalog-Version: ?», massgeblich
  ist der Hash in `audit-meta.json`.
- Kein Trendvergleich mit dem Lauf vom 2026-06-02: anderer Katalog,
  `aggregate --previous` hat den Vergleich verweigert.

## Ausführung und Zwischenfälle

Sieben Subagenten, je Kategorie ein Batch; jede Rückgabe über
`verify_raw_outputs.py` geprüft, protokolliert in `audit-meta.json`
(`agent_runs`, Status `ok`). Stichproben der Rohergebnisse (ARCH-003,
SCALE-002, ARCH-019, SEC-018, FID-006) in der Hauptsession nachgelesen bzw.
am Code oder an der Quelle nachgemessen.

- Ein Agent hat während seiner Portprüfung (SEC-006) fremde Python-Prozesse
  beendet. Die betroffenen Startmessungen des OBS-Batches (OBS-004, OBS-008)
  wurden um 11:58 UTC wiederholt, mit gleichem Ergebnis.
- Mehrere Agenten nutzten zeitweise denselben lokalen Port. Log-Einträge aus
  diesem Zeitraum sind nicht als Evidenz verwendet (siehe SCALE-008).
- Kein Docker-Daemon: SCALE-004 (Image-Grösse) und SEC-007 ohne Container-Beleg.
- Nur mcp 2.3.0 installiert; die SDK-Untergrenze 2.0.0 ist ungemessen
  (ARCH-012, ARCH-016, ARCH-018).

## Aufwand in den Findings

Der Aufwand ist, ausser bei FID-006, der Richtwert aus dem Katalog
(`## Effort` des Checks) und nicht für diesen Server nachgeschätzt. FID-006 ist
in der Audit-Sitzung eingeschätzt.

## Beobachtet, nicht als Befund geführt

Im stdio-Betrieb gingen in einer Sitzung die Antworten zweier parallel
gesendeter `tools/call` verloren, als stdin nach 5 s geschlossen wurde.
Einmal beobachtet, von keinem Check abgedeckt, nicht reproduziert.
