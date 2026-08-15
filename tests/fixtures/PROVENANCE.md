# Herkunft der Fixtures

Aufgezeichnet am **2026-08-15** mit `PYTHONPATH=src python scripts/record_fixtures.py`.

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
- **Auswahl:** ungekuerzt
- **Groesse:** 2034 Bytes
- **SHA-256:** `4a35dabd274d69a1ef64491580223d65f1e89e97bb4baa4efce70c907403c08f`

## `artists_1.json`

- **Werkzeuge:** `heritage_search_artists`
- **Schluessel:** `https://ckan.opendata.swiss/api/3/action/datastore_search?resource_id=ef3a9fd2-2fb3-49ee-bfba-75d58e40b2ea&limit=5&offset=0&q=Giacometti`
- **Auswahl:** ungekuerzt
- **Groesse:** 4280 Bytes
- **SHA-256:** `38eb506eafef927440daf564c14c643f07f81889e878bac8fc31648f3b76ee44`

## `cross_search_1.json`

- **Werkzeuge:** `heritage_cross_search`
- **Schluessel:** `https://ckan.opendata.swiss/api/3/action/datastore_search?resource_id=ef3a9fd2-2fb3-49ee-bfba-75d58e40b2ea&q=Sammlung&limit=3`
- **Auswahl:** ungekuerzt
- **Groesse:** 4486 Bytes
- **SHA-256:** `2eeec5b3e9be0987b8a0e4391dbf1a66bc74c49b88de4a9ab34c3b97c1c26367`

## `cross_search_2.json`

- **Werkzeuge:** `heritage_cross_search`
- **Schluessel:** `https://ckan.opendata.swiss/api/3/action/package_search?q=Sammlung+organization%3Aschweizerisches-nationalmuseum-snm&rows=3`
- **Auswahl:** ungekuerzt
- **Groesse:** 43596 Bytes
- **SHA-256:** `8b70419ee6a5df7be7e9997ed1a405ec17b08a8dac562a212e1936a49c4d0d0d`

## `dodis_1.json`

- **Werkzeuge:** `search_heritage`
- **Schluessel:** `https://beta.dodis.ch/api/solr/query`
- **Auswahl:** ungekuerzt
- **Groesse:** 1247 Bytes
- **SHA-256:** `2909afd922012a9f95471f7a381a969f265380a41e14e2aa0dad429a794c65cb`

## `item_dodis_1.json`

- **Werkzeuge:** `get_heritage_item`
- **Schluessel:** `https://beta.dodis.ch/api/solr/full/G27`
- **Auswahl:** ungekuerzt
- **Groesse:** 989 Bytes
- **SHA-256:** `c8490a549f138c750096010292dc8c9da206cd33380c6f9a363de1fac9626e4d`

## `item_memobase_1.json`

- **Werkzeuge:** `get_heritage_item`
- **Schluessel:** `https://api.memobase.ch/record/abb-001-1603_39_Foto_St`
- **Auswahl:** ungekuerzt
- **Groesse:** 9603 Bytes
- **SHA-256:** `c363de23d1117d22b911819ea27bb8680ea0b595a487f799063f02124cf7200c`

## `memobase_1.json`

- **Werkzeuge:** `search_heritage`
- **Schluessel:** `https://api.memobase.ch/?q=Z%C3%BCrich&size=5&offset=0`
- **Auswahl:** ungekuerzt
- **Groesse:** 40774 Bytes
- **SHA-256:** `d244b53746a2f72f06ebaafcf7fcd9cba9da7169108f27d9f440f903279cfd2c`

## `museum_datasets_1.json`

- **Werkzeuge:** `heritage_search_museum_datasets`
- **Schluessel:** `https://ckan.opendata.swiss/api/3/action/package_search?q=Museum+organization%3Aschweizerisches-nationalmuseum-snm&rows=5&start=0`
- **Auswahl:** ungekuerzt
- **Groesse:** 46549 Bytes
- **SHA-256:** `349e8c5fa480488405df662ed8c33df4fa0c91490abd7071924032245d606e66`

## `nb_collections_1.xml`

- **Werkzeuge:** `heritage_list_nb_collections`
- **Schluessel:** `https://helveticat.nb.admin.ch/view/oai/41SNL_51_INST/request?verb=ListSets`
- **Auswahl:** ungekuerzt — der Server liest diese Liste ganz, ein Schnitt behauptete einen kleineren Bestand
- **Groesse:** 4855 Bytes
- **SHA-256:** `769c7f1e2f9418a62ab869ad617f87cba27d29cfdd917dda8bd072eef17c6892`
