"""UDP request/response discovery for ESP device announcements."""

from __future__ import annotations

import json
import logging
import socket
import threading
from typing import Optional

from smart_home_project.server.device_manager import DeviceManager


class ESPDiscoveryService:
    """Sends discovery requests and listens for ESP replies."""

    def __init__(self, device_manager: DeviceManager, port: int = 8891):
        self.device_manager = device_manager
        self.port = int(port)
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.sock: Optional[socket.socket] = None
        self.logger = logging.getLogger("smart_home.server.esp_discovery")

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
            sock.bind(("", self.port))
            sock.settimeout(1.0)
            self.logger.info("ESP discovery listening on UDP port %s", self.port)

            while self.running:
                try:
                    payload, address = sock.recvfrom(2048)
                except socket.timeout:
                    continue
                except OSError:
                    break

                try:
                    announcement = json.loads(payload.decode("utf-8"))
                    self._handle_announcement(announcement, address[0])
                except Exception as exc:
                    self.logger.warning("Invalid ESP discovery packet from %s: %s", address, exc)

    def discover_now(self) -> None:
        """Ask ESP modules to announce themselves once."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                request = json.dumps({"type": "smart_home_discovery_request"}).encode("utf-8")
                sock.sendto(request, ("255.255.255.255", self.port))
            self.logger.info("ESP discovery request broadcast on UDP port %s", self.port)
        except OSError as exc:
            self.logger.warning("Unable to broadcast ESP discovery request: %s", exc)

    def _handle_announcement(self, announcement: dict, source_ip: str) -> None:
        if announcement.get("type") != "smart_home_esp":
            return
        esp_port = int(announcement.get("port", 8890))
        remote_ids = []
        if isinstance(announcement.get("devices"), list):
            remote_ids.extend(str(item.get("remote_device_id") or item.get("device_id")) for item in announcement["devices"])
        else:
            remote_ids.append(str(announcement.get("remote_device_id") or announcement.get("device_id") or ""))

        for remote_device_id in [remote_id for remote_id in remote_ids if remote_id]:
            updated = self.device_manager.update_esp_location(remote_device_id, source_ip, esp_port)
            if updated:
                self.logger.info("ESP %s discovered at %s:%s", remote_device_id, source_ip, esp_port)
