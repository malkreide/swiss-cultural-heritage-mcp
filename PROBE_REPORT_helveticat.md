# PROBE-Report Helveticat (Nationalbibliothek)

**Phase 0 — Messung, keine Codeänderung.**
Gemessen am **20.09.2026, 12:38–12:45 UTC**, live gegen den Endpunkt, mit
`httpx` aus dem Projekt-venv (`httpx 0.28.1`), eigener User-Agent, ohne
Zugangsdaten. Rohausgaben im Scratchpad der Session; jede Zahl unten stammt
aus einem der Läufe und nicht aus einer Herleitung.

---

## 0. Kernbefund in einem Satz

**Die Quelle ist nicht kaputt — der `metadataPrefix` ist falsch.** Der
Endpunkt liefert `ListRecords` für **66 der 68 Sets** aus, sobald man
`metadataPrefix=marc21` statt des im Code verdrahteten `oai_dc` schickt.
Zusätzlich bietet dieselbe Domain einen **SRU-Endpunkt mit echter
serverseitiger Volltextsuche**, der die heutige clientseitige Filterung
ersetzt, ohne die Tool-Fläche anzufassen.

Damit ist **H1 in seiner Deutung falsch**, in seinen Beobachtungen aber
richtig: Die beiden gemeldeten Fehler treten genau so auf — sie sind bloss
keine Absage der Quelle, sondern die Antwort auf eine Anfrage, die es so
nicht gibt.

Das ist derselbe Fehlschluss, den `CLAUDE.md` unter **«Ein 4xx ist kein
Nein»** am `lotId`-Fall festhält: Die Spec führt fünf `metadataPrefix`
auf, und daraus wurde gelesen, dass alle fünf für alle Sets gelten.
Bemerkenswert ist, dass die Diagnose im Repo bereits halb geschrieben
steht — der Docstring von `_raise_if_oai_error` nennt wörtlich «ohne das
verlangte `set` und mit einem **nicht publizierten** `metadataPrefix`».
Der publizierte wurde nie gesucht.

---

## 1. Der Endpunkt

Aus dem Code, `Settings.nb_oai_pmh` (`server.py:78`):

```
https://helveticat.nb.admin.ch/view/oai/41SNL_51_INST/request
```

`Identify` (HTTP 200) zeigt, was der Code nicht weiss:

| Feld | Wert |
|---|---|
| `repositoryName` | Helveticat |
| `baseURL` | `https://nb-helveticat.alma.exlibrisgroup.com/view/oai/41SNL_51_INST/request` |
| `protocolVersion` | 2.0 |
| `adminEmail` | bibsys@nb.admin.ch |
| `earliestDatestamp` | 2001-01-01T00:00:00Z |
| `deletedRecord` | transient |
| `granularity` | YYYY-MM-DDThh:mm:ssZ |
| `repositoryIdentifier` | helveticat.nb.admin.ch |
| `sampleIdentifier` | `oai:helveticat.nb.admin.ch:12345678` |

Die `baseURL` nennt **Ex Libris Alma**. Das ist keine Randnotiz, sondern
die Erklärung für alles Folgende: In Alma ist ein `metadataPrefix` nicht
eine Eigenschaft des Repositoriums, sondern eines **Publishing Profile**
je Set. `ListMetadataFormats` beschreibt daher, was die Software *kann*,
nicht, was dieses Haus *publiziert*.

## 2. `ListMetadataFormats` — fünf Formate, und die Falle darin

HTTP 200, fünf `metadataPrefix`:

`mods` · `oai_dc` · `oai_qdc` · `marc21` · `etdms`

Ohne `identifier`-Argument ist das die **repositoriumsweite** Liste. Sie
ist die «optional»-Falle aus `CLAUDE.md` in Formatgestalt: Sie führt
`oai_dc` auf, und `oai_dc` ist für 67 von 68 Sets trotzdem nicht
abrufbar.

## 3. `ListSets` — 68 Sets, eine Seite

`ListSets` liefert **68 Sets** ohne `resumptionToken`. Grössere Gruppen:
`xwas-*` (34 Sets, Kantone plus Sonderbestände), `xediss-*` (11,
Hochschuldissertationen), dazu `helveticat`, `helveticat4slsp`,
`swissbook`, `xehelv`, `xdigicoll`, `xrara`, `maps`, `xpop1`, `RFN`,
`RFN2` u. a.

Bei `xwas-ag` weicht `setName` (`xaws-ag`) vom `setSpec` (`xwas-ag`) ab —
ein Tippfehler der Quelle. Das Tool gibt beide aus und muss nichts tun;
wer je nach `setName` auflöst, greift daneben.

## 4. Die Profilkarte — vollständig gemessen

`ListIdentifiers` über **alle 68 Sets × alle 5 `metadataPrefix`** (340
Abfragen, 12:41–12:44 UTC):

| `metadataPrefix` | Sets mit Publishing Profile | welche |
|---|---:|---|
| **`marc21`** | **66 / 68** | alle ausser `RFN`, `RFN2` |
| `oai_dc` | 1 / 68 | nur `RFN` (57 Records) |
| `oai_qdc` | 1 / 68 | nur `RFN2` (57 Records) |
| `mods` | 0 / 68 | — |
| `etdms` | 0 / 68 | — |

Diese Tabelle ist der Bericht. Sie liefert zugleich die **Positivkontrolle**,
die `CLAUDE.md` bei einem «nicht gefunden» verlangt: `oai_dc` existiert —
für genau ein Set. Die Quelle verweigert das Format also nicht, sie
publiziert es nur fast nirgends. Ohne diese Gegenprobe wäre «`oai_dc` geht
nicht» wieder nur eine Vermutung mit vielen Belegen.

**Ohne `set` bleibt es bei `badArgument`** — geprüft für alle fünf Prefixe.
Dieser Teil von H1 hält: `set` ist Pflicht, für jedes Format.

## 5. Zeitfenster, Paginierung, `GetRecord`

Alles mit `marc21` gegen `set=helveticat`:

| Probe | Ergebnis |
|---|---|
| `from=2026-09-01&until=2026-09-10` | **OK**, 100 Records + `resumptionToken` |
| `from`/`until` als vollständiger Zeitstempel (`…T00:00:00Z`) | **OK**, 100 Records |
| `from=2001-01-01&until=2001-01-02` | `noRecordsMatch` — *anderer Text*: «The combination of the values of the from, until, set and metadataPrefix arguments results in an empty list.» |
| dasselbe Fenster mit `oai_dc` | `noRecordsMatch` — «No Publishing profile exists…» |
| `ListIdentifiers` | **OK**, 100 IDs |
| `resumptionToken` Folgeseite | **OK**, weitere 100 Records |
| `GetRecord` + `marc21` + bekannte ID | **OK**, 1 Record |
| `GetRecord` + `oai_dc`/`mods`/`oai_qdc` + **dieselbe** ID | `idDoesNotExist` |

Drei Dinge daran sind wichtig:

**Der `noRecordsMatch`-Code trägt zwei gegensätzliche Bedeutungen.** Einmal
«dein Fenster ist leer» — eine echte Auskunft. Einmal «diese Kombination
gibt es nicht» — eine Absage. Nur der Text trennt sie. Die Lehre ist
dieselbe wie bei jedem mehrdeutigen Statuscode: *den Text lesen, nicht
den Code*.

**`GetRecord` mit `oai_dc` lügt.** Es meldet `idDoesNotExist` für einen
Datensatz, den dasselbe Repositorium eine Sekunde vorher mit `marc21`
ausgeliefert hat. Die Meldung spricht über den Identifier und meint das
Profil. Wer ihr folgt, sucht den Fehler in der ID.

**`from`/`until` sind Änderungsstempel, keine Erscheinungsjahre.** Der
geprüfte Datensatz trägt `datestamp` 2025-08-21 bei Erscheinungsjahr 2000;
das Fenster 2001-01-01/02 ist leer, obwohl `earliestDatestamp` dort liegt.
Die heutige Parameterbeschreibung im Code — «Publikationen ab diesem
Datum» — ist damit **sachlich falsch**, unabhängig von allem anderen.

## 6. Was der ausgelieferte Code heute tut

Die drei NB-Werkzeuge, in-process gegen die Live-Quelle (12:43 UTC):

| Aufruf | Ergebnis heute |
|---|---|
| `heritage_search_helveticat(query="Volksschule")` | **ToolError** `badArgument` |
| `heritage_search_helveticat(set_spec="helveticat")` | **ToolError** `noRecordsMatch` |
| `heritage_search_helveticat(set_spec="RFN")` | **OK** — der einzige funktionierende Pfad |
| `heritage_get_publication(<gültige OAI-ID>)` | **ToolError** `idDoesNotExist` |
| `heritage_list_nb_collections()` | **OK** — 68 Sets |
| `heritage_cross_search(query=…)` (Standard) | NB-Block: `⚠️ Fehler: … badArgument` |

Der Schadensradius ist also grösser als H1/H2 beschreiben: Es fällt nicht
nur die Suche aus, sondern auch `heritage_get_publication` — **jeder**
Detailabruf, für jede ID. Von drei NB-Werkzeugen arbeitet eines
(`heritage_list_nb_collections`, weil `ListSets` kein Profil braucht).

`set_spec="RFN"` ist dabei die Positivkontrolle im eigenen Haus: Derselbe
Code, derselbe Client, dieselbe Allow-List — und ein Ergebnis. Die
Fehlermeldungen sagen nichts über die Erreichbarkeit der Quelle.

H2 stimmt in der Folge: Solange das so ist, trägt jede Quersuche mit dem
Standard-`sources` einen NB-Fehlerblock. Der Block ist gut gebaut (er sagt
ausdrücklich «Das ist KEIN leeres Ergebnis») — er steht bloss unter einem
vermeidbaren Fehler.

---

## 7. Der SRU-Endpunkt — der eigentliche Fund

Auf **derselben Domain**, damit **innerhalb der bestehenden
Egress-Allow-List** (`helveticat.nb.admin.ch`, `server.py:124`):

```
https://helveticat.nb.admin.ch/view/sru/41SNL_51_INST
```

`operation=explain` antwortet mit HTTP 200 und 149 KB Katalog.

**Indexe:** 327, darunter alles, was die Werkzeuge brauchen —
`all_for_ui` (Alles-Index der Oberfläche), `title`, `creator`, `subjects`,
`main_pub_date`, `date_of_publication`, `publisher`, `language`, `isbn`,
`issn`, `mms_id`.

**`recordSchema`:** `marcxml`, **`dc`**, `mods`, `dcx`, `unimarcxml`,
`kormarcxml`, `cnmarcxml`, `isohold`.

Das `dc` darin ist der Grund, warum diese Option billig ist: SRU liefert
Dublin Core in genau der Feldform, die `_parse_oai_records` heute schon
erzeugt (`dc:title`, `dc:date`, `dc:subject`, `dc:language`,
`dc:description`, `dc:identifier`, `dc:coverage`, `dc:type`).

**Gemessene Suchen:**

| CQL | `numberOfRecords` |
|---|---:|
| `alma.all_for_ui="Volksschule Zürich"` | 4 |
| `alma.all_for_ui all "Volksschule Zürich"` | 346 |
| `alma.title="Volksschule"` | 960 |
| `alma.creator="Keller, Gottfried"` | 1 721 |
| `alma.subjects="Schulwesen"` | 1 894 |
| `alma.all_for_ui="Volksschule" and alma.main_pub_date="1960"` | 5 |
| `alma.mms_id="991016034239703976"` | 1 |
| `alma.all_for_ui="kjhfgkjsdhfgkjsdhfg"` | **0** |

Der Nulltreffer ist so wichtig wie die Treffer: Die Suche ist
unterscheidungsfähig, sie gibt nicht immer irgendetwas zurück.

**Latenz:** 0,19 / 0,16 / 0,17 s für 20 Records — schneller als die
100-Record-OAI-Seite, die das Tool heute holt.

**Die Identifier-Brücke ist geprüft.** SRU gibt je Record ein
`<recordIdentifier>` (= MARC `001`, die Alma-MMS-ID) aus. Roundtrip:

```
SRU recordIdentifier   991016034239703976
  → oai:helveticat.nb.admin.ch:991016034239703976
  → OAI GetRecord/marc21  →  OK, setSpec = helveticat, helveticat4slsp
```

Das heisst: `heritage_search_helveticat` kann über SRU suchen und trotzdem
Identifier ausgeben, die `heritage_get_publication` unverändert frisst.
**Keine neue Tool-Fläche, kein neuer Parameter, keine neue Domain.**

### 7.1 Drei Fallen im SRU, die man beim Bauen kennen muss

**Ein unbekannter Index ergibt keinen Fehler, sondern den ganzen Katalog.**

```
alma.unknown_index="x"   →  numberOfRecords = 2 244 233
dc.title="Volksschule"   →  numberOfRecords = 2 244 233
alma.title="Volksschule" →  numberOfRecords = 960
```

Der zweite Fall ist der gefährliche: `dc.` sieht neben `recordSchema=dc`
völlig plausibel aus und liefert stillschweigend 2,3 Millionen statt 960.
Kein `diagnostic`, HTTP 200. Das ist dieselbe Klasse wie der CKAN-`q` mit
falschem `organization:` im Kommentar bei `snm_org` — nur andersherum:
dort still null, hier still alles. **Konsequenz für eine Umsetzung: nur
eine geprüfte Index-Whitelist in die CQL einsetzen, nie einen Wert aus der
Eingabe.**

**Fehlerhafte CQL meldet sich sauber** (HTTP 200 + `diag:uri 200812`,
«Invalid query») — für unbalancierte Klammern, leeren Term und einen
blossen String. Die Diagnostik ist also vorhanden, sie greift nur beim
Index nicht.

**`maximumRecords` ist bei 50 gedeckelt, und zwar lautlos.**
`explain` sagt `<setting type="maximumRecords">50</setting>`; die Anfrage
mit 100 oder 200 liefert ohne Warnung 50 Records bei
`nextRecordPosition=51`. `startRecord` funktioniert (Position 101 → 10
Records, `nextRecordPosition=111`). Das heutige `limit` reicht bis 50 und
passt damit exakt — aber der Deckel gehört in einen Kommentar, sonst
findet ihn der Nächste über eine stille Kürzung.

### 7.2 Zwei Grenzen des SRU

**SRU kennt die OAI-Sets nicht.** Geprüft:
`… and alma.mms_memberOf="helveticat"` → 0, `… and alma.bib_labels="swissbook"`
→ 0. Ein `set_spec`-Filter ist über SRU **nicht** abbildbar. Daraus folgt
die Arbeitsteilung in der Empfehlung: `query` → SRU, `set_spec` /
`from_date` / `until_date` → OAI `marc21`.

**`dc:creator` bleibt leer.** In allen **9** geprüften Datensätzen (drei
Abfragen) war `dc:creator` nicht vorhanden; Verfasser·innen und
Körperschaften standen ausnahmslos in `dc:contributor` — Alma bildet MARC
100/110/700/710 gemeinsam dorthin ab. Der heutige Markdown-Renderer liest
`rec.get("creator")`, würde also **jede** Autorenangabe verschweigen. Das
ist kein Ausschlussgrund, aber eine Zeile Arbeit, die man nicht sieht,
wenn man nur auf Trefferzahlen schaut. (Neun Records sind kein Beweis,
dass Alma nie `dc:creator` sendet — sie reichen, um den Fallback
`creator or contributor` zur Pflicht zu machen.)

---

## 8. Funktionierende Kombinationen — die Kurzfassung

| Zweck | Aufruf | Status |
|---|---|---|
| Sammlungen auflisten | `verb=ListSets` | ✅ heute schon |
| Records je Sammlung | `verb=ListRecords&set=<66 Sets>&metadataPrefix=marc21` | ✅ |
| Records Sets `RFN` / `RFN2` | `…&set=RFN&metadataPrefix=oai_dc` / `…&set=RFN2&metadataPrefix=oai_qdc` | ✅ |
| Zeitfenster | `…&metadataPrefix=marc21&set=…&from=YYYY-MM-DD&until=YYYY-MM-DD` | ✅ (Änderungs-, nicht Erscheinungsdatum) |
| Paginierung | `verb=ListRecords&resumptionToken=…` | ✅ |
| Einzelabruf | `verb=GetRecord&identifier=oai:helveticat.nb.admin.ch:<mms_id>&metadataPrefix=marc21` | ✅ |
| **Volltextsuche** | `sru/41SNL_51_INST?version=1.2&operation=searchRetrieve&recordSchema=dc&query=alma.all_for_ui="…"&maximumRecords=≤50` | ✅ |
| Treffer-Gesamtzahl | SRU `<numberOfRecords>` | ✅ (füllt `total`/`has_more` erstmals ehrlich) |
| **Nicht** möglich | `metadataPrefix=oai_dc` ausser Set `RFN` · `mods`/`etdms` überhaupt · `ListRecords` ohne `set` · Set-Filter im SRU | ❌ |

---

## 9. Optionen mit Aufwand

### Option A — nur den Prefix tauschen

`oai_dc` → `marc21` in den drei NB-Aufrufen, plus ein MARCXML-Parser, der
in dieselben Dict-Schlüssel schreibt wie heute (245$a → `title`,
100/110/700/710$a → `creator`/`contributor`, 260/264$b$c → `publisher`/`date`,
650/651/653$a → `subject`, 041$a → `language`, 024$a → `identifier`,
500/520$a → `description`, 506/540$a → `rights`).

*Aufwand:* ~80 Zeilen Parser, ~4 Aufrufstellen, Fixtures neu aufnehmen.
**Klein.**

*Was es löst:* `heritage_get_publication` und `heritage_list_nb_collections`
funktionieren vollständig; `heritage_search_helveticat` mit `set_spec`
ebenfalls; der Fehlerblock in `heritage_cross_search` verschwindet.

*Was es **nicht** löst:* `query`. Die clientseitige Filterung sieht weiter
nur die ersten 100 Records eines Sets — bei `helveticat` sind das 100 von
Millionen, in einer Reihenfolge, die niemand kontrolliert. «Volksschule
Zürich» findet dort praktisch nie etwas, und das Werkzeug meldet dann
«Keine Publikationen gefunden». Das ist ein *stiller* Negativbefund und
damit schlechter als der heutige laute Fehler. Genau davor warnt der
Skill `mcp-data-fidelity`, und `CLAUDE.md` nennt dieselbe Klasse beim
CKAN-`organization:`-Term.

### Option B — A plus SRU für die Volltextsuche **(empfohlen)**

Zusätzlich zu A, in `heritage_search_helveticat`:

* `query` gesetzt **und** kein `set_spec`/`from_date`/`until_date` → **SRU**
  (`recordSchema=dc`, `alma.all_for_ui`, `maximumRecords=limit`),
  `total` aus `numberOfRecords`, Identifier aus `recordIdentifier` in die
  OAI-Form gebracht;
* `set_spec`/`from_date`/`until_date` gesetzt → **OAI `marc21`** wie in A,
  `query` filtert wie bisher clientseitig, und der Hinweistext sagt das;
* `heritage_cross_search._nb` → **SRU** (das ist per Definition ein
  Suchbegriff ohne Set — der Fall, für den SRU gebaut ist).

Dazu: `nb_sru` als zweites Settings-Feld (gleiche Domain, Allow-List
unverändert), eine Index-Whitelist als Modulkonstante, ein CQL-Quoting,
das `"` im Suchbegriff neutralisiert.

*Aufwand:* Option A **plus** ~120 Zeilen (SRU-Aufruf, DC-Parser,
CQL-Bau, Whitelist), ~2 neue Fixtures, Offline-Tests für den
Nulltreffer, die `diag`-Antwort und den Index-Schutz.
**Mittel** — ein Arbeitstag, nicht eine Woche.

*Grenzen:* keine neuen Tools (bleibt bei 11 von 15), keine
Architekturänderung, keine neue Domain, `readOnlyHint` unberührt, die
Tool-Signaturen bleiben Zeichen für Zeichen gleich. Die Verzweigung
`query` vs. `set_spec` muss im Docstring stehen, sonst ist sie eine
unsichtbare Verhaltensänderung.

### Option C — verwerfen

Siehe Abschnitt 11.

---

## 10. Empfehlung

**Option B.**

Die Begründung ist nicht, dass sie mehr kann, sondern dass **A allein den
Fehler nur leiser macht**. Der heutige Zustand ist unangenehm, aber
ehrlich: Das Werkzeug sagt, dass es nichts durchsucht hat. Option A
ersetzt diese Meldung durch «Keine Publikationen gefunden» zu Anfragen,
die es nie ernsthaft gestellt hat. Ein Modell kann das nicht
unterscheiden — und die Antwort, die es der nutzenden Person daraus baut,
ist dann falsch statt bloss leer.

Der Zusatzaufwand von B gegenüber A ist überschaubar und hat drei
Eigenschaften, die selten zusammenkommen: gleiche Domain (keine
Allow-List-Änderung), gleiche Identifier (keine Tool-Fläche), gleiches
DC-Feldschema (kein zweiter Renderer). Wenn B je fällt, fällt es auf A
zurück, nicht auf null.

Was in jedem Fall und unabhängig vom Entscheid mit muss:

1. **Die `from`/`until`-Beschreibung korrigieren** — «Publikationen ab
   diesem Datum» ist falsch; es sind Änderungsstempel des Katalogsatzes.
2. **Die Profilkarte aus Abschnitt 4 in den Code**, als Kommentar neben
   dem Prefix. Sonst steht dort in einem Jahr wieder `oai_dc`, weil
   `ListMetadataFormats` es ja aufführt.
3. **Beide Antworten aufzeichnen**, mit funktionierendem und mit
   nicht-publiziertem Prefix. `CLAUDE.md` nennt das beim `lotId`-Fall als
   den Grund, warum der Fehlbefund damals nicht auffiel: «Eine
   Aufzeichnung nur des Fehlschlags kann nicht zeigen, dass er vermeidbar
   war.» Hier wäre es die zweite Auflage desselben Versäumnisses.

---

## 11. Verwerfen-Option (falls der Entscheid gegen die Umsetzung fällt)

Vollständig beschrieben, damit sie eine echte Wahl ist:

* `heritage_cross_search.sources` Standard auf `["sik_isea","snm"]`; `nb`
  bleibt explizit wählbar, der Validator bleibt unverändert.
* Der Docstring nennt den Grund und das Datum: Der OAI-Endpunkt liefert
  unter dem verwendeten `metadataPrefix` nichts aus.
* `heritage_search_helveticat` fängt `badArgument` und `noRecordsMatch` ab
  und gibt eine **Degraded-Antwort** statt einer Exception — mit dem
  OAI-Fehlercode, dem Verweis auf `heritage_list_nb_collections` und auf
  `helveticat.ch`.
* Offline-Tests mit `respx` für beide Fehlerfälle.

**Was diese Option kostet, offen gesagt:** Sie schreibt einen Zustand
fest, von dem jetzt gemessen ist, dass er an einem Parameter hängt. Die
Degraded-Meldung müsste, um nicht zu täuschen, sinngemäss sagen: *«Diese
Quelle ist erreichbar; dieser Server fragt sie falsch.»* — und das ist
eine Formulierung, die man nicht lange stehen lässt.

Zudem bliebe `heritage_get_publication` kaputt. Die Verwerfen-Option, wie
in der Aufgabe umrissen, adressiert Suche und Quersuche; der Detailabruf
ist erst durch diese Probe als betroffen bekannt. Er müsste dieselbe
Degraded-Behandlung bekommen — ein Werkzeug, das unter allen Eingaben
degradiert antwortet, ist allerdings ein Werkzeug, das man streicht, und
Streichen wäre eine Änderung der Tool-Fläche.

**Der ehrliche Mittelweg, falls der Aufwand von B nicht jetzt da ist:**
Option A umsetzen (klein, repariert `heritage_get_publication` und
`heritage_cross_search` vollständig) **und** `query` in
`heritage_search_helveticat` ohne `set_spec` ausdrücklich als
nicht-unterstützt melden, statt still zu filtern. Das ist nicht schön,
aber es lügt an keiner Stelle.

---

## 12. Was diese Probe **nicht** hergibt

* **Ein Zeitpunkt, keine Reihe.** Alles oben ist vom 20.09.2026,
  12:38–12:45 UTC. Publishing Profiles sind eine Konfiguration des Hauses
  und können sich ändern. Dass `marc21` heute 66 Sets trägt, sagt nichts
  über morgen — der Nightly-Live-Lauf (`nightly-live.yml`, 04:17 UTC) ist
  der Ort, an dem eine Drift auffiele.
* **Die Herkunft der Profilkarte ist ungemessen.** Warum ausgerechnet
  `RFN` `oai_dc` trägt und `RFN2` `oai_qdc`, ist nicht bekannt. Plausibel
  ist eine Altlast; belegt ist nichts.
* **Keine Nutzungsbedingungen geprüft.** Ob die NB für den SRU-Endpunkt
  ein Rate-Limit, eine Registrierungspflicht oder eine abweichende Lizenz
  vorsieht, wurde nicht gemessen; es kam in ~380 Abfragen keine
  Drosselung, aber das ist kein Freibrief. Vor einer Umsetzung von B
  gehört das geklärt — notfalls per Mail an `bibsys@nb.admin.ch` aus dem
  `Identify`.
* **Die SRU-Abdeckung ist nicht mit den OAI-Sets verglichen.** SRU meldet
  2 244 233 Records im Alles-Index; ob das der Vereinigung der 68 Sets
  entspricht, wurde nicht geprüft. Für die Suche ist es unerheblich, für
  eine Aussage über Vollständigkeit nicht.
* **Die MARC→DC-Abbildung ist an wenigen Records beurteilt.** Zwei
  MARCXML-Records im Volltext gelesen, neun DC-Records in den Feldnamen
  geprüft. Für die Feldauswahl reicht das; für eine Zusicherung über alle
  Materialarten (Karten, Zeitschriften, Digitalisate) nicht.
* **Deutungen, nicht Messungen:** Dass `noRecordsMatch` mit zwei
  Bedeutungen ein Risiko ist, dass `dc.` ein plausibler Tippfehler ist,
  dass A den Fehler «leiser» macht — das sind Einschätzungen. Die Zahlen
  darunter sind gemessen; die Schlüsse daraus sind meine.

---

**HARTER STOPP.** Keine Codeänderung vorgenommen. Phase 1 erst nach
«Weiter» und Entscheid.
