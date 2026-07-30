"""Eingehende Host/Origin-Prüfung des HTTP-Transports (SEC-005, eingehend).

Auslöser war kein fehlender Schutz, sondern ein zu strenger an der falschen
Adresse. mcp 2.x aktiviert automatisch eine Allow-List auf ``127.0.0.1:*``, wenn
das ``host``-Argument der App loopback-artig aussieht — und
``streamable_http_app()`` defaultet genau darauf. Der Container setzt laut
Settings-Kommentar ``MCP_HOST=0.0.0.0``, also bekam jede Anfrage unter einem
echten Hostnamen HTTP 421.

Vor der Migration auf mcp 2.x erreichte ``host`` den ``FastMCP``-Konstruktor, wo
dieselbe Logik den echten Bind sah und den Schutz korrekt ausliess.

Namensgebung: die Einstellung heisst ``inbound_allowed_hosts``, nicht
``allowed_hosts`` — letzteres ist in diesem Server die **Egress**-Allow-List
(SEC-021) und meint die Gegenrichtung.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from swiss_cultural_heritage_mcp.server import (
    build_http_app,
    build_transport_security,
    settings,
)

_INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1"},
    },
}
_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


@pytest.fixture(autouse=True)
def _clean_settings(monkeypatch):
    """Das Settings-Objekt ist modulglobal; Felder pro Test zurücksetzen."""
    monkeypatch.setattr(settings, "inbound_allowed_hosts", "", raising=False)
    monkeypatch.setattr(settings, "cors_origins", "", raising=False)
    yield


def test_loopback_bind_is_protected():
    sec = build_transport_security("127.0.0.1", 8000)
    assert sec is not None
    assert sec.enable_dns_rebinding_protection is True
    assert "127.0.0.1:8000" in sec.allowed_hosts


def test_wildcard_bind_without_allowlist_stays_off():
    """Der eigentliche Fix.

    Auf 0.0.0.0 ist der erreichbare Name hier unbekannt, und der
    SDK-Loopback-Default ist genau eine Vermutung — er reproduziert das 421.
    Also bleibt der Schutz aus und der Aufrufer warnt.
    """
    assert build_transport_security("0.0.0.0", 8000) is None


def test_wildcard_bind_with_allowlist_is_protected(monkeypatch):
    monkeypatch.setattr(settings, "inbound_allowed_hosts", "kultur.example.ch")
    sec = build_transport_security("0.0.0.0", 8000)
    assert sec is not None
    assert "kultur.example.ch" in sec.allowed_hosts
    # Loopback bleibt drin, sonst brechen Container-Health-Checks.
    assert "127.0.0.1:8000" in sec.allowed_hosts


def test_the_egress_allowlist_is_a_different_thing():
    """Verwechslungsschutz: ``allowed_hosts`` ist die Egress-Liste (SEC-021).

    Sie darf die eingehende Prüfung nicht speisen — ``ckan.opendata.swiss`` ist
    ein Upstream, unter dem dieser Server nie erreicht wird.
    """
    sec = build_transport_security("127.0.0.1", 8000)
    assert "ckan.opendata.swiss" not in sec.allowed_hosts
    assert "ckan.opendata.swiss" in settings.allowed_hosts


def test_cors_origins_pass_the_transport_check(monkeypatch):
    """Sonst weist der Transport genau die Browser-Clients ab, die CORS erlaubt."""
    monkeypatch.setattr(settings, "cors_origins", "https://claude.ai")
    sec = build_transport_security("127.0.0.1", 8000)
    assert "https://claude.ai" in sec.allowed_origins


def test_wildcard_cors_is_not_copied(monkeypatch):
    monkeypatch.setattr(settings, "cors_origins", "*")
    sec = build_transport_security("127.0.0.1", 8000)
    assert "*" not in sec.allowed_origins


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_all_loopback_forms_count_as_local(host):
    assert build_transport_security(host, 8000) is not None


def _post(app, host_header: str) -> int:
    with TestClient(app) as client:
        return client.post(
            "/mcp", headers={"Host": host_header, **_HEADERS}, json=_INIT
        ).status_code


def test_a_public_bind_is_reachable_again():
    """Die Regression selbst, durch den echten ASGI-Stack.

    Ohne den ``host``-Kwarg ist das ein 421 — der Zustand, den dieser Commit
    behebt.
    """
    assert _post(build_http_app([], "0.0.0.0", 8000), "kultur.example.ch") == 200


def test_configured_host_is_served(monkeypatch):
    monkeypatch.setattr(settings, "inbound_allowed_hosts", "kultur.example.ch")
    assert _post(build_http_app([], "0.0.0.0", 8000), "kultur.example.ch") == 200


def test_foreign_host_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "inbound_allowed_hosts", "kultur.example.ch")
    assert _post(build_http_app([], "0.0.0.0", 8000), "evil.example.com") == 421


def test_right_host_wrong_port_is_rejected(monkeypatch):
    """Der tragende Fall.

    ``evil.example.com`` allein beweist wenig: ein zurückfallender
    Loopback-Default würde ihn ebenfalls abweisen. Nur „richtiger Hostname,
    falscher Port" unterscheidet eine portgenaue Allow-List von einer, die alles
    durchlässt — und der Test fällt, sobald ``transport_security`` nicht mehr
    übergeben wird.
    """
    monkeypatch.setattr(settings, "inbound_allowed_hosts", "kultur.example.ch:8000")
    assert _post(build_http_app([], "0.0.0.0", 8000), "kultur.example.ch:9999") == 421
