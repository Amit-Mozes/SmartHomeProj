"""UDP responder that lets GUI clients find the Pi server automatically."""

from __future__ import annotations

import logging
import socket
import threading
from typing import Optional

from smart_home_project.common.server_discovery import (
    DISCOVERY_PORT,
    create_discovery_response,
    parse_discovery_request,
)


class ServerDiscoveryService:
    """Listens for LAN discovery requests and replies with the TCP server port."""

    def __init__(self, tcp_port: int, discovery_port: int = DISCOVERY_PORT, name: str = "Smart Home Server"):
        self.tcp_port = int(tcp_port)
        self.discovery_port = int(discovery_port)
        self.name = name
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.sock: Optional[socket.socket] = None
        self.logger = logging.getLogger("smart_home.server.discovery")

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        if self.sock:
            self.sock.close()

    def _run(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            self.sock = sock
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", self.discovery_port))
            sock.settimeout(1.0)
            response = create_discovery_response(self.tcp_port, self.name)
            self.logger.info("Server discovery listening on UDP port %s", self.discovery_port)

            while self.running:
                try:
                    payload, address = sock.recvfrom(2048)
                except socket.timeout:
                    continue
                except OSError:
                    break

                if not parse_discovery_request(payload):
                    continue
                try:
                    sock.sendto(response, address)
                    self.logger.info("Answered server discovery request from %s:%s", address[0], address[1])
                except OSError as exc:
                    self.logger.warning("Unable to answer discovery request from %s: %s", address, exc)
