"""Server settings loaded from JSON for local and Raspberry Pi deployments."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from smart_home_project.common.protocol import Protocol


@dataclass
class ServerSettings:
    host: str = "0.0.0.0"
    port: int = Protocol.PORT
    device_mode: str = "mock"
    user_db: str = "server_config.json"
    device_config: str = "devices_config.json"
    log_file: str = "../../logs/server.log"
    server_discovery_enabled: bool = True
    server_discovery_port: int = 8821
    server_discovery_name: str = "Smart Home Server"
    esp_discovery_enabled: bool = True
    esp_discovery_port: int = 8891

    @classmethod
    def load(cls, path: Path) -> "ServerSettings":
        if not path.exists():
            path.write_text(json.dumps(cls().__dict__, indent=2), encoding="utf-8")
        data: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        defaults = cls().__dict__
        defaults.update(data)
        return cls(**defaults)

    def resolve(self, base_dir: Path, value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else (base_dir / path).resolve()
