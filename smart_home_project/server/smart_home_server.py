"""Threaded TCP smart-home server."""

from __future__ import annotations

import logging
import socket
from pathlib import Path
from typing import List

from smart_home_project.common.encryption import EncryptionManager
from smart_home_project.common.protocol import Protocol
from smart_home_project.server.client_handler import ClientHandler
from smart_home_project.server.device_manager import DeviceManager
from smart_home_project.server.esp_discovery import ESPDiscoveryService
from smart_home_project.server.permission_manager import PermissionManager
from smart_home_project.server.server_discovery import ServerDiscoveryService
from smart_home_project.server.server_settings import ServerSettings
from smart_home_project.server.user_manager import UserManager


class SmartHomeServer:
    def __init__(self, host: str | None = None, port: int | None = None, settings_path: Path | None = None):
        self.base_dir = Path(__file__).resolve().parent
        self.settings = ServerSettings.load(settings_path or (self.base_dir / "server_settings.json"))
        self.host = host or self.settings.host
        self.port = port or self.settings.port
        self.encryption = EncryptionManager.for_server()
        self.user_manager = UserManager(self.settings.resolve(self.base_dir, self.settings.user_db))
        self.permission_manager = PermissionManager(PermissionManager.default_permissions())
        self.device_manager = DeviceManager(
            self.settings.resolve(self.base_dir, self.settings.device_config),
            self.settings.device_mode,
        )
        self.handlers: List[ClientHandler] = []
        self.esp_discovery: ESPDiscoveryService | None = None
        self.server_discovery: ServerDiscoveryService | None = None
        self.server_socket: socket.socket | None = None
        self.running = False
        self.logger = logging.getLogger("smart_home.server")

    def start(self) -> None:
        self.running = True
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            self.server_socket = server_socket
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.host, self.port))
            server_socket.listen()
            self.logger.info("SmartHomeServer listening on %s:%s", self.host, self.port)
            if self.settings.server_discovery_enabled:
                self.server_discovery = ServerDiscoveryService(
                    self.port,
                    self.settings.server_discovery_port,
                    self.settings.server_discovery_name,
                )
                self.server_discovery.start()
            if self.settings.esp_discovery_enabled and self.settings.device_mode in {"esp", "mixed"}:
                self.esp_discovery = ESPDiscoveryService(self.device_manager, self.settings.esp_discovery_port)
                self.esp_discovery.start()
                self.esp_discovery.discover_now()

            while self.running:
                try:
                    client_socket, address = server_socket.accept()
                except OSError:
                    break
                handler = ClientHandler(client_socket, address, self)
                self.handlers.append(handler)
                handler.start()

    def stop(self) -> None:
        self.running = False
        if self.server_discovery:
            self.server_discovery.stop()
        if self.esp_discovery:
            self.esp_discovery.stop()
        if self.server_socket:
            self.server_socket.close()
        for handler in self.handlers:
            handler.running = False
