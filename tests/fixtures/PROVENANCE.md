# Herkunft der Fixtures

Aufgezeichnet am **2026-09-20** mit `PYTHONPATH=src python scripts/record_fixtures.py`.

Eine Antwort je **Abfrage**, nicht je Endpunkt: vier Quellen — SIKART/CKAN,
Memobase, Dodis, Nationalbibliothek —, aber mehr Abfrageformen als Hosts.
Vier Dateien wuerden die Portfolio-Regel erfuellen und fast nichts belegen.

Der **Schluessel** unten ist die angefragte URL; danach ordnet der Test zu und
nicht nach Reihenfolge. `heritage_cross_search` und `search_heritage` fragen
mehrere Quellen in einem Aufruf ab, und eine Zuordnung nach Reihenfolge waere
im gruenen Fall bloss zufaellig richtig.

Die Antworten stammen aus dem geteilten Client (gleicher User-Agent, gleiches
Timeout, gleiche Egress-Allow-List wie im Betrieb), abgegriffen ueber einen
httpx-Response-Hook. Ausgeloest hat sie jeweils das Werkzeug selbst — so belegt
die Aufzeichnung auch, dass das Werkzeug genau diese Anfrage schickt.
Redirect-Hops sind nicht aufgezeichnet: sie sind Zwischenschritte, keine
Antworten auf eine Abfrage.

Neu gesetzt ist die Einrueckung; gekuerzt ist allein die **Zahl** der
Listeneintraege. Kein Feld eines behaltenen Eintrags ist angetastet, und
Zaehlfelder daneben (`total`, `count`, `numFound`) stehen wie geliefert — die
Quelle meint damit die Gesamtzahl der Treffer.

Die Fehlerpfade — Timeout, 5xx, leere Trefferliste — bleiben handgeschrieben.
Sie lassen sich nicht auf Zuruf aufzeichnen und sind als Erfindung in Ordnung.

## `artist_detail_1.json`

- **Werkzeuge:** `heritage_get_artist`
- **Schluessel:** `https://ckan.opendata.swiss/api/3/action/datastore_search?resource_id=ef3a9fd2-2fb3-49ee-bfba-75d58e40b2ea&filters=%7B%22HAUPTNR%22%3A+%224005571%22%7D&limit=1`
- **Auswahl:** 4 von 28 Listeneintraegen (je Liste die ersten 3), aus 2453 Bytes Rohantwort
- **Groesse:** 2034 Bytes
- **SHA-256:** `4a35dabd274d69a1ef64491580223d65f1e89e97bb4baa4efce70c907403c08f`

## `artists_1.json`

- **Werkzeuge:** `heritage_search_artists`
- **Schluessel:** `https://ckan.opendata.swiss/api/3/action/datastore_search?resource_id=ef3a9fd2-2fb3-49ee-bfba-75d58e40b2ea&limit=5&offset=0&q=Giacometti`
- **Auswahl:** 6 von 33 Listeneintraegen (je Liste die ersten 3), aus 5730 Bytes Rohantwort
- **Groesse:** 4280 Bytes
- **SHA-256:** `38eb506eafef927440daf564c14c643f07f81889e878bac8fc31648f3b76ee44`

## `cross_search_1.json`

- **Werkzeuge:** `heritage_cross_search`
- **Schluessel:** `https://ckan.opendata.swiss/api/3/action/datastore_search?resource_id=ef3a9fd2-2fb3-49ee-bfba-75d58e40b2ea&q=Sammlung&limit=3`
- **Auswahl:** 6 von 31 Listeneintraegen (je Liste die ersten 3), aus 4352 Bytes Rohantwort
- **Groesse:** 4486 Bytes
- **SHA-256:** `2eeec5b3e9be0987b8a0e4391dbf1a66bc74c49b88de4a9ab34c3b97c1c26367`

## `cross_search_2.xml`

- **Werkzeuge:** `heritage_cross_search`
- **Schluessel:** `https://helveticat.nb.admin.ch/view/sru/41SNL_51_INST?version=1.2&operation=searchRetrieve&recordSchema=dc&query=alma.all_for_ui%3D%22Sammlung%22&maximumRecords=3`
- **Auswahl:** ungekuerzt
- **Groesse:** 5224 Bytes
- **SHA-256:** `6aa761bbc07726e48c606f6ac1a591b2007d20d58cab17bb5440796364009658`

## `cross_search_3.json`

- **Werkzeuge:** `heritage_cross_search`
- **Schluessel:** `https://ckan.opendata.swiss/api/3/action/package_search?q=Sammlung+organization%3Aschweizerisches-nationalmuseum-snm&rows=3`
- **Auswahl:** 62 von 104 Listeneintraegen (je Liste die ersten 3), aus 40993 Bytes Rohantwort
- **Groesse:** 43622 Bytes
- **SHA-256:** `984439c1beebbe2e2e41392b6fbf8e544d47085ebc09b8f03de89d4e28eec585`

## `dodis_1.json`

- **Werkzeuge:** `search_heritage`
- **Schluessel:** `https://beta.dodis.ch/api/solr/query`
- **Auswahl:** 3 von 5 Listeneintraegen (je Liste die ersten 3), aus 1557 Bytes Rohantwort
- **Groesse:** 1247 Bytes
- **SHA-256:** `329ed69c45558570e502694ce1621106850f3da049d32dfc55e36b6c2eee48ea`

## `helveticat_1.xml`

- **Werkzeuge:** `heritage_search_helveticat`
- **Schluessel:** `https://helveticat.nb.admin.ch/view/sru/41SNL_51_INST?version=1.2&operation=searchRetrieve&recordSchema=dc&query=alma.all_for_ui%3D%22Volksschule+Z%C3%BCrich%22&maximumRecords=5`
- **Auswahl:** ungekuerzt
- **Groesse:** 7674 Bytes
- **SHA-256:** `7d83c3da00cc86956afb4782a8dba752366fef621b6f84643d3a31d4a632a37a`

## `item_dodis_1.json`

- **Werkzeuge:** `get_heritage_item`
- **Schluessel:** `https://beta.dodis.ch/api/solr/full/G27`
- **Auswahl:** 6 von 21 Listeneintraegen (je Liste die ersten 3), aus 1796 Bytes Rohantwort
- **Groesse:** 989 Bytes
- **SHA-256:** `c8490a549f138c750096010292dc8c9da206cd33380c6f9a363de1fac9626e4d`

## `item_memobase_1.json`

- **Werkzeuge:** `get_heritage_item`
- **Schluessel:** `https://api.memobase.ch/record/abb-001-1603_39_Foto_St`
- **Auswahl:** 41 von 48 Listeneintraegen (je Liste die ersten 3), aus 7086 Bytes Rohantwort
- **Groesse:** 9603 Bytes
- **SHA-256:** `c363de23d1117d22b911819ea27bb8680ea0b595a487f799063f02124cf7200c`

## `memobase_1.json`

- **Werkzeuge:** `search_heritage`
- **Schluessel:** `https://api.memobase.ch/?q=Z%C3%BCrich&size=5&offset=0`
- **Auswahl:** 159 von 192 Listeneintraegen (je Liste die ersten 3), aus 48226 Bytes Rohantwort
- **Groesse:** 40774 Bytes
- **SHA-256:** `83dcbd777e87f09ae186b88e0d79f1997305ad6f32a13e5040e2b240c3940d97`

## `museum_datasets_1.json`

- **Werkzeuge:** `heritage_search_museum_datasets`
- **Schluessel:** `https://ckan.opendata.swiss/api/3/action/package_search?q=Museum+organization%3Aschweizerisches-nationalmuseum-snm&rows=5&start=0`
- **Auswahl:** 64 von 116 Listeneintraegen (je Liste die ersten 3), aus 70355 Bytes Rohantwort
- **Groesse:** 46575 Bytes
- **SHA-256:** `1acf02349182d3fd24446241e56fa6b9521e33662892c7e0f0f8afe88eac747a`

## `nb_collections_1.xml`

- **Werkzeuge:** `heritage_list_nb_collections`
- **Schluessel:** `https://helveticat.nb.admin.ch/view/oai/41SNL_51_INST/request?verb=ListSets`
- **Auswahl:** ungekuerzt — der Server liest diese Liste ganz, ein Schnitt behauptete einen kleineren Bestand
- **Groesse:** 4855 Bytes
- **SHA-256:** `2dc8bfec02754b50da8fd9baa3c81bd3fe9e6a76facd8fcf422ded81630b8ecb`

## `publication_1.xml`

- **Werkzeuge:** `heritage_get_publication`
- **Schluessel:** `https://helveticat.nb.admin.ch/view/oai/41SNL_51_INST/request?verb=GetRecord&identifier=oai%3Ahelveticat.nb.admin.ch%3A991016034239703976&metadataPrefix=marc21`
- **Auswahl:** ungekuerzt
- **Groesse:** 4588 Bytes
- **SHA-256:** `5f7ce25cfb7ead2f7efaa79a04f47ea14130f795e2c3038337a99a1c1654e7f8`
