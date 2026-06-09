"""UDP discovery helpers for finding the smart-home TCP server on a LAN."""

from __future__ import annotations

import json
import socket
import time
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from smart_home_project.common.protocol import Protocol


DISCOVERY_PORT = 8821
REQUEST_TYPE = "smart_home_server_discovery_request"
RESPONSE_TYPE = "smart_home_server"


@dataclass(frozen=True)
class DiscoveredServer:
    """A smart-home server found by UDP discovery."""

    host: str
    port: int
    name: str = "Smart Home Server"


def create_discovery_request() -> bytes:
    """Create a UDP payload asking smart-home servers to identify themselves."""
    return json.dumps({"type": REQUEST_TYPE}).encode("utf-8")


def create_discovery_response(port: int = Protocol.PORT, name: str = "Smart Home Server") -> bytes:
    """Create a UDP payload returned by the server discovery listener."""
    return json.dumps({"type": RESPONSE_TYPE, "port": int(port), "name": name}).encode("utf-8")


def parse_discovery_request(payload: bytes) -> bool:
    """Return True when a UDP packet is a valid smart-home discovery request."""
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    return data.get("type") == REQUEST_TYPE


def parse_discovery_response(payload: bytes, source_ip: str) -> DiscoveredServer | None:
    """Parse a server discovery response, returning None for unrelated packets."""
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return None
    if data.get("type") != RESPONSE_TYPE:
        return None
    try:
        port = int(data.get("port", Protocol.PORT))
    except (TypeError, ValueError):
        port = Protocol.PORT
    return DiscoveredServer(host=source_ip, port=port, name=str(data.get("name") or "Smart Home Server"))


def discover_servers(
    discovery_port: int = DISCOVERY_PORT,
    timeout: float = 2.0,
    broadcast_hosts: Iterable[str] = ("255.255.255.255",),
) -> List[DiscoveredServer]:
    """Broadcast a discovery request and collect smart-home server replies."""
    found: List[DiscoveredServer] = []
    seen: set[Tuple[str, int]] = set()
    deadline = time.monotonic() + timeout

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.25)
        request = create_discovery_request()
        for host in broadcast_hosts:
            try:
                sock.sendto(request, (host, int(discovery_port)))
            except OSError:
                continue

        while time.monotonic() < deadline:
            try:
                payload, address = sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                break
            server = parse_discovery_response(payload, address[0])
            if not server:
                continue
            key = (server.host, server.port)
            if key not in seen:
                seen.add(key)
                found.append(server)

    return found
