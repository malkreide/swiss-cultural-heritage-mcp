#!/usr/bin/env python3
"""
Swiss Cultural Heritage MCP Server — v0.1.0

AI-nativer Zugang zu drei Schweizer Kulturerbe-Quellen:
  · SIK-ISEA:          Schweizerisches Institut für Kunstwissenschaft (50'000+ Künstler·innen)
  · Nationalmuseum:    Sammlungsdaten via opendata.swiss CKAN API
  · Nationalbibliothek: Schweizerische Nationalbibliografie via OAI-PMH

Kein API-Schlüssel erforderlich. Alle Daten öffentlich zugänglich unter offenen Lizenzen.
"""

import asyncio
import csv
import io
import json
import xml.etree.ElementTree as ET
from enum import Enum
from typing import List, Optional

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ─────────────────────────── Server ────────────────────────────────────────────
mcp = FastMCP("swiss_cultural_heritage_mcp")

# ─────────────────────────── Konstanten ────────────────────────────────────────
SIK_ISEA_API  = "https://api.sik-isea.ch"
CKAN_API      = "https://opendata.swiss/api/3/action"
NB_OAI_PMH    = "https://www.nb.admin.ch/oai/oai-provider"
SNM_ORG       = "schweizerisches-nationalmuseum"
HTTP_TIMEOUT  = 30.0
DEFAULT_LIMIT = 20
MAX_LIMIT     = 100

# OAI-PMH XML-Namespaces
OAI_NS = {
    "oai":    "http://www.openarchives.org/OAI/2.0/",
    "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
    "dc":     "http://purl.org/dc/elements/1.1/",
}


# ─────────────────────────── Enum ──────────────────────────────────────────────
class ResponseFormat(str, Enum):
    """Ausgabeformat für Tool-Antworten."""
    MARKDOWN = "markdown"
    JSON     = "json"


# ─────────────────────────── Shared Utilities ──────────────────────────────────
async def _http_get(url: str, params: Optional[dict] = None) -> httpx.Response:
    """Wiederverwendbare HTTP-GET-Funktion mit einheitlichem Timeout."""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        return await client.get(url, params=params, timeout=HTTP_TIMEOUT)


def _handle_error(e: Exception) -> str:
    """Einheitliche, handlungsorientierte Fehlermeldungen (auf Deutsch)."""
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        if code == 404:
            return "Fehler: Ressource nicht gefunden. Bitte ID oder Parameter prüfen."
        if code == 429:
            return "Fehler: Rate-Limit erreicht. Bitte kurz warten und erneut versuchen."
        if code in (503, 502):
            return "Fehler: Dienst vorübergehend nicht verfügbar. Bitte erneut versuchen."
        return f"Fehler: API-Anfrage fehlgeschlagen (HTTP {code})."
    if isinstance(e, httpx.TimeoutException):
        return "Fehler: Zeitüberschreitung. Der Dienst antwortet nicht. Bitte erneut versuchen."
    if isinstance(e, ET.ParseError):
        return "Fehler: XML-Antwort konnte nicht verarbeitet werden. Möglicherweise vorübergehend."
    return f"Fehler: Unerwarteter Fehler ({type(e).__name__}): {e}"


def _paginate(items: list, limit: int, offset: int) -> dict:
    """Standard-Pagination-Hilfsfunktion."""
    total  = len(items)
    sliced = items[offset : offset + limit]
    return {
        "total":       total,
        "count":       len(sliced),
        "offset":      offset,
        "has_more":    (offset + len(sliced)) < total,
        "next_offset": (offset + len(sliced)) if (offset + len(sliced)) < total else None,
        "items":       sliced,
    }


def _parse_oai_records(xml_text: str) -> List[dict]:
    """Parsed OAI-PMH ListRecords/GetRecord-Antwort in eine Liste von Dicts."""
    root = ET.fromstring(xml_text)
    records = []
    for record in root.findall(".//oai:record", OAI_NS):
        header = record.find("oai:header", OAI_NS)
        if header is not None and header.get("status") == "deleted":
            continue
        identifier_el = record.find("oai:header/oai:identifier", OAI_NS)
        datestamp_el  = record.find("oai:header/oai:datestamp",  OAI_NS)
        metadata_el   = record.find("oai:metadata/oai_dc:dc",    OAI_NS)

        rec: dict = {
            "oai_identifier": identifier_el.text if identifier_el is not None else "",
            "datestamp":      datestamp_el.text  if datestamp_el  is not None else "",
        }

        if metadata_el is not None:
            for child in metadata_el:
                tag = child.tag.split("}")[-1]  # Namespace entfernen
                val = (child.text or "").strip()
                if not val:
                    continue
                if tag in rec:
                    existing = rec[tag]
                    if isinstance(existing, list):
                        existing.append(val)
                    else:
                        rec[tag] = [existing, val]
                else:
                    rec[tag] = val

        records.append(rec)
    return records


def _extract_resumption_token(xml_text: str) -> Optional[str]:
    """Extrahiert OAI-PMH Resumption Token für Paginierung."""
    root    = ET.fromstring(xml_text)
    token_el = root.find(".//oai:resumptionToken", OAI_NS)
    if token_el is not None and token_el.text and token_el.text.strip():
        return token_el.text.strip()
    return None


def _normalize_ckan_title(title) -> str:
    """Normalisiert CKAN-Titel (dict mit Sprachschlüsseln oder String)."""
    if isinstance(title, dict):
        return title.get("de") or title.get("fr") or title.get("en") or next(iter(title.values()), "—")
    return str(title) if title else "—"


# ══════════════════════════════════════════════════════════════════════════════
#  MODUL 1 — SIK-ISEA  (Schweizerisches Institut für Kunstwissenschaft)
# ══════════════════════════════════════════════════════════════════════════════

class ArtistSearchInput(BaseModel):
    """Input für die SIK-ISEA Künstler·innen-Suche."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    query:     Optional[str] = Field(
        default=None, max_length=200,
        description="Name oder Namensteil (z. B. 'Hodler', 'Sophie Taeuber-Arp', 'Giacometti')"
    )
    region:    Optional[str] = Field(
        default=None, max_length=100,
        description="Schweizer Kanton oder Region (z. B. 'Zürich', 'Bern', 'Ticino', 'Genf')"
    )
    period:    Optional[str] = Field(
        default=None, max_length=100,
        description="Epoche oder Zeitraum (z. B. '19. Jahrhundert', 'Moderne', '1880-1950')"
    )
    technique: Optional[str] = Field(
        default=None, max_length=100,
        description="Technik oder Medium (z. B. 'Ölmalerei', 'Grafik', 'Skulptur', 'Fotografie')"
    )
    limit:  int = Field(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Max. Ergebnisse (1–100)")
    offset: int = Field(default=0, ge=0, description="Offset für Paginierung")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

    @field_validator("query", "region", "technique", "period")
    @classmethod
    def not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Darf nicht leer sein.")
        return v


@mcp.tool(
    name="heritage_search_artists",
    annotations={
        "title": "Schweizer Künstler·innen suchen (SIK-ISEA)",
        "readOnlyHint":    True,
        "destructiveHint": False,
        "idempotentHint":  True,
        "openWorldHint":   True,
    },
)
async def heritage_search_artists(params: ArtistSearchInput) -> str:
    """Sucht Schweizer Künstler·innen in der SIK-ISEA-Datenbank (50'000+ Einträge).

    SIK-ISEA (Schweizerisches Institut für Kunstwissenschaft) pflegt das umfassendste
    Verzeichnis Schweizer Künstler·innen mit biografischen Angaben, Technik, Herkunft.

    Args:
        params (ArtistSearchInput):
            - query (Optional[str]):     Namenssuche (z. B. 'Hodler', 'Taeuber')
            - region (Optional[str]):    Kanton/Region (z. B. 'Zürich', 'Wallis')
            - period (Optional[str]):    Epoche (z. B. '19. Jahrhundert', '1880-1920')
            - technique (Optional[str]): Technik (z. B. 'Ölmalerei', 'Skulptur')
            - limit (int):               Max. Ergebnisse (Standard: 20)
            - offset (int):              Paginierungs-Offset
            - response_format:           'markdown' oder 'json'

    Returns:
        str: Liste gefundener Künstler·innen mit Name, Lebensdaten, Kanton, Technik.

        Erfolg (Markdown):
            ## [Name] | SIK-ID: …
            Lebensdaten: … | Kanton: … | Technik: …

        Fehler: "Fehler: …"
    """
    try:
        api_params: dict = {"format": "json"}
        if params.query:
            api_params["q"] = params.query
        if params.region:
            api_params["kanton"] = params.region
        if params.technique:
            api_params["technik"] = params.technique
        if params.period:
            api_params["epoche"] = params.period

        resp = await _http_get(f"{SIK_ISEA_API}/personendaten", params=api_params)
        resp.raise_for_status()

        # SIK-ISEA kann JSON oder CSV zurückgeben
        content_type = resp.headers.get("content-type", "")
        text = resp.text.strip()
        if "csv" in content_type or (text and not text.startswith("{") and not text.startswith("[")):
            reader  = csv.DictReader(io.StringIO(text))
            artists = list(reader)
        else:
            data    = resp.json()
            artists = data if isinstance(data, list) else data.get("results", data.get("data", []))

        if not artists:
            return "Keine Künstler·innen gefunden für die angegebenen Suchkriterien."

        paged = _paginate(artists, params.limit, params.offset)

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(paged, ensure_ascii=False, indent=2)

        filters = []
        if params.query:     filters.append(f"Name: *{params.query}*")
        if params.region:    filters.append(f"Kanton: *{params.region}*")
        if params.technique: filters.append(f"Technik: *{params.technique}*")
        if params.period:    filters.append(f"Epoche: *{params.period}*")

        lines = ["# SIK-ISEA Künstler·innen-Suche\n"]
        if filters:
            lines.append("**Filter:** " + " · ".join(filters))
        lines.append(f"\nGefunden: {paged['total']} Einträge (zeige {paged['count']})\n")
        lines.append("---\n")

        for artist in paged["items"]:
            name       = artist.get("Name") or artist.get("name") or artist.get("Nachname", "")
            vorname    = artist.get("Vorname") or artist.get("vorname", "")
            full_name  = f"{vorname} {name}".strip() if vorname else name
            artist_id  = artist.get("ID") or artist.get("id") or artist.get("PersonID", "—")
            birth      = artist.get("Geburtsjahr") or artist.get("birth_year", "")
            death      = artist.get("Todesjahr")   or artist.get("death_year", "")
            canton     = artist.get("Kanton")      or artist.get("kanton") or ""
            tech       = artist.get("Technik")     or artist.get("technik") or ""
            beruf      = artist.get("Beruf")       or ""

            lines.append(f"## {full_name or '(Unbekannt)'}")
            meta: list = []
            if birth or death:
                meta.append(f"**Lebensdaten:** {birth or '?'}–{death or 'heute'}")
            if canton:
                meta.append(f"**Kanton:** {canton}")
            if tech:
                meta.append(f"**Technik:** {tech}")
            elif beruf:
                meta.append(f"**Beruf:** {beruf}")
            meta.append(f"**SIK-ID:** `{artist_id}`")
            lines.append("  ·  ".join(meta))
            lines.append("")

        if paged["has_more"]:
            lines.append(f"*Weitere Ergebnisse verfügbar — Offset: {paged['next_offset']}*")

        return "\n".join(lines)

    except Exception as e:
        return _handle_error(e)


class ArtistDetailInput(BaseModel):
    """Input für SIK-ISEA Künstler·in-Detailabfrage."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    artist_id: str = Field(
        ..., min_length=1,
        description="SIK-ISEA Personen-ID (aus heritage_search_artists, z. B. '12345')"
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


@mcp.tool(
    name="heritage_get_artist",
    annotations={
        "title": "Künstler·in-Details abrufen (SIK-ISEA)",
        "readOnlyHint":    True,
        "destructiveHint": False,
        "idempotentHint":  True,
        "openWorldHint":   True,
    },
)
async def heritage_get_artist(params: ArtistDetailInput) -> str:
    """Ruft vollständige Daten zu einer Künstler·in aus SIK-ISEA ab.

    Args:
        params (ArtistDetailInput):
            - artist_id (str): SIK-ISEA Personen-ID (aus heritage_search_artists)
            - response_format: 'markdown' oder 'json'

    Returns:
        str: Vollständiges Profil mit Lebensdaten, Technik, Biografie, Kanton und Links.
    """
    try:
        resp = await _http_get(
            f"{SIK_ISEA_API}/personendaten/{params.artist_id}",
            params={"format": "json"},
        )
        resp.raise_for_status()

        data   = resp.json()
        artist = (data[0] if isinstance(data, list) and data else data) or {}

        if not artist:
            return f"Keine Daten gefunden für SIK-ISEA ID `{params.artist_id}`."

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(artist, ensure_ascii=False, indent=2)

        name      = artist.get("Name") or artist.get("name", "")
        vorname   = artist.get("Vorname") or artist.get("vorname", "")
        full_name = f"{vorname} {name}".strip() if vorname else name

        lines = [f"# {full_name or 'Unbekannt'}\n", f"**SIK-ISEA ID:** `{params.artist_id}`\n"]

        dc_map = [
            ("Geburtsjahr",  "Geburtsjahr"),
            ("Geburtsort",   "Geburtsort"),
            ("Todesjahr",    "Todesjahr"),
            ("Todesort",     "Todesort"),
            ("Kanton",       "Kanton"),
            ("Technik",      "Technik"),
            ("Beruf",        "Beruf"),
            ("Epoche",       "Epoche"),
            ("Kommentar",    "Kommentar"),
            ("Beschreibung", "Beschreibung"),
            ("URL",          "Mehr Infos"),
        ]
        for field, label in dc_map:
            val = artist.get(field) or artist.get(field.lower())
            if val:
                lines.append(f"**{label}:** {val}")

        return "\n".join(lines)

    except Exception as e:
        return _handle_error(e)


# ══════════════════════════════════════════════════════════════════════════════
#  MODUL 2 — NATIONALMUSEUM (SNM) via opendata.swiss CKAN API
# ══════════════════════════════════════════════════════════════════════════════

class MuseumSearchInput(BaseModel):
    """Input für SNM-Datensatzsuche."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    query:      Optional[str] = Field(
        default=None, max_length=200,
        description="Suchbegriff (z. B. 'Münzen', 'Siegel', 'Mittelalter', 'Waffen', 'Textil')"
    )
    collection: Optional[str] = Field(
        default=None, max_length=100,
        description="Sammlungsfilter (z. B. 'numismatik', 'siegelsammlung', 'spezialsammlungen')"
    )
    limit:  int = Field(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)
    offset: int = Field(default=0, ge=0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


@mcp.tool(
    name="heritage_search_museum_datasets",
    annotations={
        "title": "SNM-Datensätze suchen (opendata.swiss)",
        "readOnlyHint":    True,
        "destructiveHint": False,
        "idempotentHint":  True,
        "openWorldHint":   True,
    },
)
async def heritage_search_museum_datasets(params: MuseumSearchInput) -> str:
    """Sucht Datensätze des Schweizerischen Nationalmuseums (SNM) auf opendata.swiss.

    Das SNM publiziert Sammlungsdaten als Open Data: Numismatik (~100'000 Münzen),
    Siegelsammlung (~80'000 Objekte), Spezialsammlungen und weitere.

    Args:
        params (MuseumSearchInput):
            - query (Optional[str]):      Suchbegriff über Titel/Beschreibung
            - collection (Optional[str]): Sammlungsfilter (z. B. 'numismatik')
            - limit / offset:             Paginierung
            - response_format:            'markdown' oder 'json'

    Returns:
        str: Liste verfügbarer SNM-Datensätze mit Titel, Beschreibung und
             Download-URLs (CSV, XLSX, JSON).

        Schema:
            {
              "total": int,
              "datasets": [
                {
                  "name": str,       # CKAN Package-ID
                  "title": str,
                  "description": str,
                  "resources": [{"name": str, "format": str, "url": str}]
                }
              ]
            }
    """
    try:
        search_q = f"organization:{SNM_ORG}"
        if params.query:
            search_q = f"{params.query} {search_q}"
        if params.collection:
            search_q += f" {params.collection}"

        resp = await _http_get(
            f"{CKAN_API}/package_search",
            params={"q": search_q, "rows": params.limit, "start": params.offset},
        )
        resp.raise_for_status()
        data = resp.json()

        if not data.get("success"):
            return f"Fehler: CKAN-API-Anfrage fehlgeschlagen — {data.get('error', 'Unbekannt')}"

        result   = data.get("result", {})
        packages = result.get("results", [])
        total    = result.get("count", 0)

        if not packages:
            return "Keine SNM-Datensätze gefunden für die angegebenen Kriterien."

        if params.response_format == ResponseFormat.JSON:
            simplified = [
                {
                    "name":  pkg.get("name", ""),
                    "title": _normalize_ckan_title(pkg.get("title")),
                    "description": _normalize_ckan_title(pkg.get("notes")) if pkg.get("notes") else "",
                    "resources": [
                        {
                            "name":   r.get("name") or r.get("title") or "Unbenannt",
                            "format": r.get("format") or r.get("media_type", ""),
                            "url":    r.get("download_url") or r.get("url") or "",
                        }
                        for r in pkg.get("resources", [])
                    ],
                }
                for pkg in packages
            ]
            return json.dumps({"total": total, "count": len(packages), "datasets": simplified}, ensure_ascii=False, indent=2)

        lines = ["# Schweizerisches Nationalmuseum (SNM) — Open Data\n"]
        if params.query:
            lines.append(f"**Suche:** *{params.query}*\n")
        lines.append(f"Gefunden: {total} Datensätze (zeige {len(packages)})\n")
        lines.append("---\n")

        for pkg in packages:
            title    = _normalize_ckan_title(pkg.get("title"))
            pkg_name = pkg.get("name", "")
            notes    = pkg.get("notes")
            desc     = _normalize_ckan_title(notes) if notes else ""
            if desc and len(desc) > 200:
                desc = desc[:200] + "…"
            resources = pkg.get("resources", [])

            lines.append(f"## {title}")
            lines.append(f"**Paket-ID:** `{pkg_name}`")
            if desc:
                lines.append(f"{desc}")
            if resources:
                lines.append(f"**{len(resources)} Ressource(n):**")
                for r in resources[:4]:
                    r_name   = r.get("name") or r.get("title") or "Unbenannt"
                    r_format = r.get("format") or r.get("media_type", "?")
                    r_url    = r.get("download_url") or r.get("url") or ""
                    lines.append(f"  - [{r_name}]({r_url}) `{r_format}`")
            lines.append("")

        if total > params.offset + len(packages):
            lines.append(f"*Weitere Datensätze ab Offset {params.offset + len(packages)}*")

        return "\n".join(lines)

    except Exception as e:
        return _handle_error(e)


class CollectionBrowseInput(BaseModel):
    """Input für SNM-Sammlungsobjekt-Suche via CKAN DataStore."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    resource_id: str = Field(
        ..., min_length=1,
        description="CKAN Resource-ID (aus heritage_search_museum_datasets, z. B. 'abc123-...')"
    )
    query:  Optional[str] = Field(default=None, max_length=200, description="Suchbegriff im Datensatz")
    limit:  int = Field(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)
    offset: int = Field(default=0, ge=0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


@mcp.tool(
    name="heritage_browse_collection",
    annotations={
        "title": "SNM-Sammlungsobjekte durchsuchen (CKAN DataStore)",
        "readOnlyHint":    True,
        "destructiveHint": False,
        "idempotentHint":  True,
        "openWorldHint":   True,
    },
)
async def heritage_browse_collection(params: CollectionBrowseInput) -> str:
    """Durchsucht Objekte innerhalb eines SNM-Sammlungsdatensatzes via CKAN DataStore.

    Voraussetzung: Resource-ID aus `heritage_search_museum_datasets`.
    Geeignet für Objekte in der Numismatik-, Siegel- oder Spezialsammlung.

    Args:
        params (CollectionBrowseInput):
            - resource_id (str): CKAN Resource-ID (aus heritage_search_museum_datasets)
            - query (Optional[str]): Suchbegriff (z. B. 'Zürich', 'Karl der Grosse', 'Gold')
            - limit / offset: Paginierung
            - response_format: 'markdown' oder 'json'

    Returns:
        str: Liste von Sammlungsobjekten mit verfügbaren Feldern.

        Schema:
            {
              "total": int,
              "fields": [str],
              "records": [dict]  # Struktur abhängig vom Datensatz
            }
    """
    try:
        api_params: dict = {
            "resource_id": params.resource_id,
            "limit":       params.limit,
            "offset":      params.offset,
        }
        if params.query:
            api_params["q"] = params.query

        resp = await _http_get(f"{CKAN_API}/datastore_search", params=api_params)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("success"):
            return f"Fehler: DataStore-Anfrage fehlgeschlagen — {data.get('error', 'Unbekannt')}"

        result  = data.get("result", {})
        records = result.get("records", [])
        total   = result.get("total", 0)
        fields  = [f["id"] for f in result.get("fields", []) if f["id"] != "_id"]

        if not records:
            return (
                f"Keine Objekte gefunden in Ressource `{params.resource_id}`.\n\n"
                "Tipp: Prüfe mit `heritage_search_museum_datasets` die verfügbaren Resource-IDs."
            )

        if params.response_format == ResponseFormat.JSON:
            return json.dumps({
                "total":       total,
                "count":       len(records),
                "offset":      params.offset,
                "resource_id": params.resource_id,
                "fields":      fields,
                "records":     records,
            }, ensure_ascii=False, indent=2)

        # Titelfeld ermitteln (erste sinnvolle Spalte)
        title_field = next(
            (f for f in ["Titel", "Title", "Bezeichnung", "Name", "Objekt", "Beschriftung"] if f in fields),
            fields[0] if fields else None,
        )

        lines = [f"# SNM-Sammlung: Objekte\n"]
        lines.append(f"**Ressource:** `{params.resource_id}`")
        if params.query:
            lines.append(f"**Suche:** *{params.query}*")
        lines.append(f"Gefunden: {total} Objekte (zeige {len(records)})\n")
        lines.append("---\n")

        display_fields = [f for f in fields if f != title_field][:7]

        for rec in records:
            title = rec.get(title_field, f"Objekt #{rec.get('_id', '?')}") if title_field else f"#{rec.get('_id', '?')}"
            lines.append(f"## {title}")
            for f in display_fields:
                if rec.get(f):
                    lines.append(f"**{f}:** {rec[f]}")
            lines.append("")

        if (params.offset + len(records)) < total:
            lines.append(f"*Weitere Objekte ab Offset {params.offset + len(records)}*")

        return "\n".join(lines)

    except Exception as e:
        return _handle_error(e)


# ══════════════════════════════════════════════════════════════════════════════
#  MODUL 3 — NATIONALBIBLIOTHEK (NB) via OAI-PMH
# ══════════════════════════════════════════════════════════════════════════════

class HelvticatSearchInput(BaseModel):
    """Input für die OAI-PMH-Suche in der Nationalbibliothek."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    query:      Optional[str] = Field(
        default=None, max_length=300,
        description=(
            "Suchbegriff für clientseitige Filterung (Titel, Autor, Schlagwort) — "
            "z. B. 'Volksschule Zürich', 'Gottfried Keller', 'Bildungspolitik'. "
            "Hinweis: OAI-PMH unterstützt keine serverseitige Volltextsuche."
        )
    )
    set_spec:   Optional[str] = Field(
        default=None, max_length=100,
        description="OAI-Set-Bezeichner (aus heritage_list_nb_collections) — z. B. 'helveticat'"
    )
    from_date:  Optional[str] = Field(
        default=None,
        description="Publikationen ab diesem Datum (YYYY oder YYYY-MM-DD)",
        pattern=r"^\d{4}(-\d{2}(-\d{2})?)?$",
    )
    until_date: Optional[str] = Field(
        default=None,
        description="Publikationen bis zu diesem Datum (YYYY oder YYYY-MM-DD)",
        pattern=r"^\d{4}(-\d{2}(-\d{2})?)?$",
    )
    limit: int = Field(default=10, ge=1, le=50, description="Max. Ergebnisse (1–50, Standard: 10)")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


@mcp.tool(
    name="heritage_search_helveticat",
    annotations={
        "title": "Helveticat durchsuchen (Nationalbibliothek OAI-PMH)",
        "readOnlyHint":    True,
        "destructiveHint": False,
        "idempotentHint":  True,
        "openWorldHint":   True,
    },
)
async def heritage_search_helveticat(params: HelvticatSearchInput) -> str:
    """Durchsucht die Schweizerische Nationalbibliothek (Helveticat) via OAI-PMH.

    Helveticat ist die Nationalbibliografie der Schweiz und verzeichnet alle
    in der Schweiz erschienenen Publikationen (Pflichtexemplargesetz).

    Hinweis: OAI-PMH unterstützt keine serverseitige Volltextsuche. Datum- und
    Set-Filter sind am effektivsten; query-Parameter filtert clientseitig.

    Args:
        params (HelvticatSearchInput):
            - query (Optional[str]):      Clientseitige Filterung (Titel, Autor)
            - set_spec (Optional[str]):   OAI-Set-ID (aus heritage_list_nb_collections)
            - from_date (Optional[str]):  Datum von (YYYY oder YYYY-MM-DD)
            - until_date (Optional[str]): Datum bis (YYYY oder YYYY-MM-DD)
            - limit (int):                Max. Ergebnisse 1–50 (Standard: 10)
            - response_format:            'markdown' oder 'json'

    Returns:
        str: Liste von Publikationen mit Titel, Autor, Jahr, Schlagwörtern und Identifier.

        Schema:
            {
              "count": int,
              "has_more": bool,
              "records": [
                {
                  "identifier": str,
                  "title": str | [str],
                  "creator": str | [str],
                  "date": str,
                  "subject": str | [str],
                  "description": str,
                  "language": str
                }
              ]
            }
    """
    try:
        oai_params: dict = {"verb": "ListRecords", "metadataPrefix": "oai_dc"}
        if params.set_spec:
            oai_params["set"] = params.set_spec
        if params.from_date:
            oai_params["from"] = params.from_date
        if params.until_date:
            oai_params["until"] = params.until_date

        resp = await _http_get(NB_OAI_PMH, params=oai_params)
        resp.raise_for_status()

        records    = _parse_oai_records(resp.text)
        resumption = _extract_resumption_token(resp.text)

        # Clientseitige Filterung nach query
        if params.query:
            q_lower = params.query.lower()
            def _matches(r: dict) -> bool:
                blob = " ".join([
                    str(r.get("title", "")),
                    str(r.get("creator", "")),
                    str(r.get("subject", "")),
                    str(r.get("description", "")),
                ]).lower()
                return q_lower in blob
            records = [r for r in records if _matches(r)]

        records = records[:params.limit]

        if not records:
            return (
                "Keine Publikationen gefunden für die angegebenen Kriterien.\n\n"
                "**Tipp:** OAI-PMH unterstützt keine Volltextsuche. "
                "Für komplexe Abfragen: [helveticat.ch](https://www.helveticat.ch)"
            )

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(
                {"count": len(records), "has_more": bool(resumption), "records": records},
                ensure_ascii=False, indent=2,
            )

        lines = ["# Nationalbibliothek — Helveticat\n"]
        if params.query:
            lines.append(f"**Suche:** *{params.query}*")
        if params.from_date or params.until_date:
            lines.append(f"**Zeitraum:** {params.from_date or '—'} bis {params.until_date or 'heute'}")
        if params.set_spec:
            lines.append(f"**Sammlung:** `{params.set_spec}`")
        lines.append(f"\nGefunden: {len(records)} Einträge\n")
        lines.append("---\n")

        for rec in records:
            title = rec.get("title") or "Ohne Titel"
            if isinstance(title, list):
                title = title[0]
            creator = rec.get("creator", "")
            if isinstance(creator, list):
                creator = " / ".join(creator)
            date        = rec.get("date", "")
            description = rec.get("description", "")
            if isinstance(description, list):
                description = description[0]
            subject = rec.get("subject", "")
            if isinstance(subject, list):
                subject = " | ".join(subject[:4])
            identifier = rec.get("oai_identifier", "") or rec.get("identifier", "")
            language   = rec.get("language", "")

            lines.append(f"## {title}")
            if creator:
                lines.append(f"**Autor·in:** {creator}")
            if date:
                lines.append(f"**Jahr:** {date}")
            if language:
                lines.append(f"**Sprache:** {language}")
            if subject:
                lines.append(f"**Schlagwörter:** {subject}")
            if description:
                short = str(description)[:280] + "…" if len(str(description)) > 280 else str(description)
                lines.append(f"*{short}*")
            if identifier:
                lines.append(f"**OAI-ID:** `{identifier}`")
            lines.append("")

        if resumption:
            lines.append(f"*Weitere Ergebnisse verfügbar (OAI Resumption Token vorhanden).*")

        return "\n".join(lines)

    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="heritage_list_nb_collections",
    annotations={
        "title": "NB-Sammlungen auflisten (OAI-PMH ListSets)",
        "readOnlyHint":    True,
        "destructiveHint": False,
        "idempotentHint":  True,
        "openWorldHint":   True,
    },
)
async def heritage_list_nb_collections(response_format: str = "markdown") -> str:
    """Listet verfügbare Sammlungen/Sets der Nationalbibliothek auf (OAI-PMH ListSets).

    Liefert die OAI-Set-Bezeichner (`set_spec`) für die gezielte Suche in
    spezifischen NB-Teilbeständen via `heritage_search_helveticat`.

    Args:
        response_format (str): 'markdown' oder 'json'

    Returns:
        str: Liste aller OAI-PMH Sets mit Bezeichner (setSpec) und Name.

        Schema:
            {"sets": [{"spec": str, "name": str}]}
    """
    try:
        resp = await _http_get(NB_OAI_PMH, params={"verb": "ListSets"})
        resp.raise_for_status()

        root = ET.fromstring(resp.text)
        sets = []
        for s in root.findall(".//oai:set", OAI_NS):
            spec_el = s.find("oai:setSpec", OAI_NS)
            name_el = s.find("oai:setName", OAI_NS)
            sets.append({
                "spec": spec_el.text if spec_el is not None else "",
                "name": name_el.text if name_el is not None else "",
            })

        if response_format == "json":
            return json.dumps({"sets": sets}, ensure_ascii=False, indent=2)

        lines = ["# Nationalbibliothek — Verfügbare Sammlungen (OAI-PMH Sets)\n"]
        lines.append(f"Insgesamt {len(sets)} Sets\n")
        for s in sets:
            lines.append(f"- **{s['name']}** — `{s['spec']}`")
        lines.append(
            "\n*Verwende den `set_spec`-Wert als Parameter `set_spec` in `heritage_search_helveticat`.*"
        )
        return "\n".join(lines)

    except Exception as e:
        return _handle_error(e)


class PublicationDetailInput(BaseModel):
    """Input für NB OAI-PMH GetRecord."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    identifier: str = Field(
        ..., min_length=5,
        description="OAI-Identifier aus heritage_search_helveticat (z. B. 'oai:helveticat.ch:...')"
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


@mcp.tool(
    name="heritage_get_publication",
    annotations={
        "title": "Publikationsdetails abrufen (NB OAI-PMH GetRecord)",
        "readOnlyHint":    True,
        "destructiveHint": False,
        "idempotentHint":  True,
        "openWorldHint":   True,
    },
)
async def heritage_get_publication(params: PublicationDetailInput) -> str:
    """Ruft vollständige Dublin-Core-Metadaten einer Publikation der NB ab.

    Args:
        params (PublicationDetailInput):
            - identifier (str): OAI-ID aus heritage_search_helveticat
            - response_format: 'markdown' oder 'json'

    Returns:
        str: Vollständige DC-Metadaten (Titel, Autor, Verlag, Sprache, Rechte, etc.).

        DC-Felder: title, creator, contributor, publisher, date, type, format,
                   language, subject, description, source, relation, coverage, rights
    """
    try:
        resp = await _http_get(
            NB_OAI_PMH,
            params={"verb": "GetRecord", "identifier": params.identifier, "metadataPrefix": "oai_dc"},
        )
        resp.raise_for_status()

        records = _parse_oai_records(resp.text)
        if not records:
            return f"Keine Publikation gefunden mit OAI-ID `{params.identifier}`."

        rec = records[0]

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(rec, ensure_ascii=False, indent=2)

        title = rec.get("title") or "Ohne Titel"
        if isinstance(title, list):
            title = title[0]

        lines = [f"# {title}\n"]

        dc_fields = [
            ("creator",     "Autor·in / Urheber·in"),
            ("contributor", "Mitwirkende"),
            ("publisher",   "Verlag / Herausgeber"),
            ("date",        "Erscheinungsjahr"),
            ("type",        "Typ"),
            ("format",      "Format"),
            ("language",    "Sprache"),
            ("subject",     "Schlagwörter"),
            ("description", "Beschreibung"),
            ("source",      "Quelle"),
            ("relation",    "Verwandte Ressourcen"),
            ("coverage",    "Abdeckung (Zeit/Raum)"),
            ("rights",      "Rechte / Lizenz"),
            ("oai_identifier", "OAI-Identifier"),
            ("identifier",  "Identifier (DC)"),
        ]
        for key, label in dc_fields:
            val = rec.get(key)
            if val:
                if isinstance(val, list):
                    val = " | ".join(v for v in val if v)
                lines.append(f"**{label}:** {val}")

        return "\n".join(lines)

    except Exception as e:
        return _handle_error(e)


# ══════════════════════════════════════════════════════════════════════════════
#  MODUL 4 — QUELLENÜBERGREIFENDE SUCHE
# ══════════════════════════════════════════════════════════════════════════════

class CrossSearchInput(BaseModel):
    """Input für quellenübergreifende Suche."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    query: str = Field(
        ..., min_length=2, max_length=200,
        description=(
            "Suchbegriff (z. B. 'Ferdinand Hodler', 'Volksschule Zürich', 'Mittelalter', "
            "'Industrialisierung Schweiz')"
        )
    )
    sources: List[str] = Field(
        default=["sik_isea", "snm", "nb"],
        description="Quellen: 'sik_isea', 'snm', 'nb' (Standard: alle drei)",
    )
    limit_per_source: int = Field(
        default=5, ge=1, le=20,
        description="Max. Ergebnisse pro Quelle (Standard: 5)"
    )

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, v: List[str]) -> List[str]:
        valid   = {"sik_isea", "snm", "nb"}
        invalid = set(v) - valid
        if invalid:
            raise ValueError(f"Ungültige Quellen: {invalid}. Gültig: {valid}")
        return list(dict.fromkeys(v))  # Deduplizieren, Reihenfolge erhalten


@mcp.tool(
    name="heritage_cross_search",
    annotations={
        "title": "Quellenübergreifende Kulturerbe-Suche (SIK-ISEA + SNM + NB)",
        "readOnlyHint":    True,
        "destructiveHint": False,
        "idempotentHint":  False,
        "openWorldHint":   True,
    },
)
async def heritage_cross_search(params: CrossSearchInput) -> str:
    """Durchsucht SIK-ISEA, SNM und NB gleichzeitig nach einem Begriff.

    Aggregiert Ergebnisse aus drei Schweizer Kulturerbe-Quellen in einer
    einzigen Abfrage — ideal für interdisziplinäre Recherchen.

    Beispiele:
        - 'Ferdinand Hodler' → Biografie (SIK-ISEA) + SNM-Objekte + Bücher (NB)
        - 'Mittelalter Zürich' → Kunstwerke + Museumsobjekte + Forschungsliteratur
        - 'Volksschule' → Bildungsgeschichte + Historisches + Kunstpädagogik
        - 'Gottfried Keller' → Autor (NB) + historische Objekte (SNM)

    Args:
        params (CrossSearchInput):
            - query (str): Suchbegriff
            - sources (List[str]): ['sik_isea', 'snm', 'nb'] (Standard: alle)
            - limit_per_source (int): Max. Ergebnisse je Quelle (Standard: 5)

    Returns:
        str: Aggregierte Markdown-Ergebnisse aus allen gewählten Quellen.
    """
    n    = params.limit_per_source
    q    = params.query

    async def _sik_isea() -> dict:
        try:
            resp = await _http_get(f"{SIK_ISEA_API}/personendaten", params={"q": q, "format": "json"})
            resp.raise_for_status()
            text = resp.text.strip()
            if text.startswith("{") or text.startswith("["):
                data    = resp.json()
                artists = (data if isinstance(data, list) else data.get("results", []))[:n]
            else:
                reader  = csv.DictReader(io.StringIO(text))
                artists = list(reader)[:n]
            return {"source": "SIK-ISEA", "label": "Künstler·innen", "items": artists}
        except Exception as e:
            return {"source": "SIK-ISEA", "error": str(e)}

    async def _snm() -> dict:
        try:
            resp = await _http_get(
                f"{CKAN_API}/package_search",
                params={"q": f"{q} organization:{SNM_ORG}", "rows": n},
            )
            resp.raise_for_status()
            pkgs = resp.json().get("result", {}).get("results", [])
            return {"source": "SNM", "label": "Museumsdatensätze", "items": pkgs}
        except Exception as e:
            return {"source": "SNM", "error": str(e)}

    async def _nb() -> dict:
        try:
            resp = await _http_get(NB_OAI_PMH, params={"verb": "ListRecords", "metadataPrefix": "oai_dc"})
            resp.raise_for_status()
            records  = _parse_oai_records(resp.text)
            q_lower  = q.lower()
            filtered = [r for r in records if q_lower in json.dumps(r, ensure_ascii=False).lower()][:n]
            return {"source": "NB", "label": "Publikationen", "items": filtered}
        except Exception as e:
            return {"source": "NB", "error": str(e)}

    task_map = {"sik_isea": _sik_isea, "snm": _snm, "nb": _nb}
    results  = await asyncio.gather(*(task_map[s]() for s in params.sources if s in task_map))

    lines = [f"# Kulturerbe-Suche: *{q}*\n"]
    lines.append(f"Quellen: {', '.join(params.sources)}  ·  Max. {n} Ergebnisse/Quelle\n")
    lines.append("---\n")

    for res in results:
        src   = res.get("source", "?")
        label = res.get("label", "Einträge")

        if "error" in res:
            lines.append(f"## {src}\n⚠️ Fehler: {res['error']}\n")
            continue

        items = res.get("items", [])
        lines.append(f"## {src} — {label} ({len(items)})\n")

        if not items:
            lines.append("*Keine Treffer*\n")
            continue

        for item in items:
            if src == "SIK-ISEA":
                name    = item.get("Name") or item.get("name", "")
                vorname = item.get("Vorname") or item.get("vorname", "")
                full    = f"{vorname} {name}".strip() or "—"
                birth   = item.get("Geburtsjahr", "")
                death   = item.get("Todesjahr", "")
                canton  = item.get("Kanton", "")
                dating  = f" ({birth}–{death})" if birth or death else ""
                ctxt    = f" · {canton}" if canton else ""
                lines.append(f"- **{full}**{dating}{ctxt}")

            elif src == "SNM":
                title = _normalize_ckan_title(item.get("title"))
                lines.append(f"- {title}")

            elif src == "NB":
                title = item.get("title") or "Ohne Titel"
                if isinstance(title, list):
                    title = title[0]
                creator = item.get("creator", "")
                if isinstance(creator, list):
                    creator = creator[0]
                date = item.get("date", "")
                auth = f" — {creator}" if creator else ""
                yr   = f" ({date})" if date else ""
                lines.append(f"- **{title}**{auth}{yr}")

        lines.append("")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
#  RESOURCES
# ══════════════════════════════════════════════════════════════════════════════

@mcp.resource("heritage://sik-isea/overview")
async def sik_isea_overview() -> str:
    """Übersicht SIK-ISEA: Datenquelle, Umfang und verfügbare Tools."""
    return """# SIK-ISEA — Schweizerisches Institut für Kunstwissenschaft

## Was ist SIK-ISEA?
Das Schweizerische Institut für Kunstwissenschaft (SIK-ISEA) ist die zentrale
Forschungs- und Informationsstelle für Kunst in der Schweiz. Die Künstler-Datenbank
umfasst über 50'000 Einträge zu Schweizer Künstler·innen aller Epochen und Medien.

## Verfügbare Daten
- Biografische Angaben (Geburt, Tod, Herkunft, Kanton)
- Technik und Medium (Ölmalerei, Skulptur, Grafik, Fotografie, …)
- Berufsbezeichnung und Epoche
- Verlinkung zu weiterführenden Ressourcen

## API-Zugang
- Endpoint:     https://api.sik-isea.ch/personendaten
- Format:       JSON / CSV
- Authentifizierung: Keine (Open Data)
- Lizenz:       CC0 / Freie Nutzung

## Verfügbare MCP-Tools
| Tool                      | Funktion                                 |
|---------------------------|------------------------------------------|
| `heritage_search_artists` | Künstler·innen suchen (Name, Kanton, ...) |
| `heritage_get_artist`     | Detaildaten zu einer Künstler·in          |
| `heritage_cross_search`   | Suche über alle drei Quellen              |

## Demo-Abfragen
- «Welche Künstlerinnen aus dem Kanton Zürich gibt es?»
- «Zeige mir alle Einträge zu Ferdinand Hodler»
- «Schweizer Bildhauer·innen des 19. Jahrhunderts»
"""


@mcp.resource("heritage://nb/collections")
async def nb_collections_overview() -> str:
    """Statische Übersicht der Nationalbibliothek-Sammlungen und OAI-PMH-Endpunkte."""
    return """# Schweizerische Nationalbibliothek (NB) — Sammlungsübersicht

## OAI-PMH Endpunkt
- URL:           https://www.nb.admin.ch/oai/oai-provider
- Protokoll:     OAI-PMH 2.0
- Metadaten:     Dublin Core (oai_dc)
- Authentifizierung: Keine

## Hauptsammlungen (OAI-Sets)
| Set            | Inhalt                                        |
|----------------|-----------------------------------------------|
| helveticat     | Schweizerische Nationalbibliografie            |
| e-periodica    | Digitalisierte Schweizer Zeitschriften          |
| webarchiv      | Archivierte Schweizer Websites                 |
| sla            | Schweizerisches Literaturarchiv                |
| phonothek      | Schweizerische Nationalphonothek               |

## Verfügbare MCP-Tools
| Tool                          | Funktion                                  |
|-------------------------------|-------------------------------------------|
| `heritage_search_helveticat`  | Suche in der Nationalbibliografie         |
| `heritage_list_nb_collections`| Alle verfügbaren OAI-Sets auflisten       |
| `heritage_get_publication`    | Vollständige Metadaten einer Publikation  |

## Wichtiger Hinweis zu OAI-PMH
OAI-PMH unterstützt keine Volltextsuche. Die effektivsten Filter sind
Datum (`from_date`/`until_date`) und Sammlung (`set_spec`).
Für komplexe Suchen: https://www.helveticat.ch

## Nutzungsrechte
- Metadaten: Frei verwendbar (kommerziell und nicht-kommerziell)
- Digitalisate: Individuelle Lizenzprüfung erforderlich
"""


# ══════════════════════════════════════════════════════════════════════════════
#  PROMPTS
# ══════════════════════════════════════════════════════════════════════════════

@mcp.prompt()
def heritage_research_artist(
    artist_name: str,
    context: str = "allgemein",
) -> str:
    """Strukturierter Recherche-Prompt zu einer Schweizer Künstler·in.

    Args:
        artist_name: Name der zu recherchierenden Künstler·in
        context: Forschungskontext (z. B. 'Unterricht Sek I', 'Ausstellung', 'Monografie')
    """
    return f"""Führe eine strukturierte Recherche zu **{artist_name}** durch.
Kontext: {context}

## Schritt 1 — Basisrecherche SIK-ISEA
Rufe `heritage_search_artists` auf (query="{artist_name}").
Falls mehrere Treffer: `heritage_get_artist` für den relevantesten Eintrag.

## Schritt 2 — Quellenübergreifende Suche
Rufe `heritage_cross_search` auf (query="{artist_name}", sources=["sik_isea","snm","nb"]).
Notiere alle Treffer aus SNM und NB.

## Schritt 3 — Vertiefung
- Für interessante NB-Einträge: `heritage_get_publication` aufrufen
- Falls SNM-Treffer: `heritage_search_museum_datasets` für Sammlungsdetails

## Gewünschte Ausgabe
1. **Biografie**: Lebensdaten, Herkunft, Ausbildung, Kanton
2. **Künstlerisches Werk**: Technik, Epoche, wichtige Werke
3. **Museale Präsenz**: SNM-Sammlungen
4. **Bibliografie**: Relevante Publikationen aus Helveticat
5. **Relevanz für Kontext**: {context}

Antworte auf Deutsch, präzise und quellenbasiert. Zitiere SIK-IDs und OAI-Identifier."""


@mcp.prompt()
def heritage_find_educational_resources(
    topic: str,
    school_level: str = "Sekundarstufe I",
) -> str:
    """Prompt zur Suche nach Bildungsressourcen aus Schweizer Kulturerbe-Quellen.

    Args:
        topic: Thema für den Unterricht (z. B. 'Mittelalter', 'Schweizer Kunst', 'Migration')
        school_level: Schulstufe (z. B. 'Primarstufe', 'Sekundarstufe I', 'Gymnasium')
    """
    return f"""Suche Bildungsressourcen zum Thema **{topic}** für die **{school_level}**.

## Suchstrategie

1. **Überblick** — `heritage_cross_search` (query="{topic}", limit_per_source=5)
   → Verschaffe dir einen Überblick über alle drei Quellen

2. **Fachliteratur** — `heritage_search_helveticat` (query="{topic}", from_date="2000-01-01")
   → Neuere Publikationen bevorzugen

3. **Anschauungsmaterial** — `heritage_search_museum_datasets` (query="{topic}")
   → Museumsobjekte als didaktische Primärquellen

4. **Kunstbezug** — Falls relevant: `heritage_search_artists` (technique oder period passend zu "{topic}")

## Auswahlkriterien
- Altersgerecht für **{school_level}**
- Bezug zum Schweizer Lehrplan 21 / Bildungsplan Gymnasien
- Open Access oder über Schulbibliotheken zugänglich
- Schweizer Perspektive / lokaler Bezug bevorzugt

## Ausgabeformat
Strukturiere die Antwort nach:
1. 📚 Empfohlene Publikationen (mit NB-OAI-Identifikatoren)
2. 🏛️ Museumsobjekte als Unterrichtsmaterial (mit SNM-Ressourcen-Links)
3. 🎨 Künstlerische Beispiele (falls themenrelevant)
4. 🔗 Weiterführende Online-Ressourcen (Open Access)

Antworte auf Deutsch."""


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if "--http" in sys.argv:
        port_idx = sys.argv.index("--port") + 1 if "--port" in sys.argv else None
        port     = int(sys.argv[port_idx]) if port_idx else 8000
        mcp.run(transport="streamable-http", port=port)
    else:
        mcp.run()
