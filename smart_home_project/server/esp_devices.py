"""ESP32/ESP8266 network-backed smart-home devices.

The Raspberry Pi remains the main encrypted server for PC/phone clients. ESP
boards are treated as local Wi-Fi device modules. The Pi talks to each ESP
using a small length-prefixed JSON TCP protocol, reusing the shared Protocol
class framing:

    0000000042{"command":"TURN_ON","device_id":"led_1"}

The ESP side can be implemented in MicroPython, Arduino, or CircuitPython as
long as it follows the same 10-byte length prefix and JSON fields.
"""

from __future__ import annotations

import socket
from typing import Any, Dict, Iterable, Optional

from smart_home_project.common.messages import decode_message, encode_message
from smart_home_project.common.protocol import Protocol, ProtocolError, SocketDisconnected
from smart_home_project.server.devices import BaseDevice, DeviceError


class ESPCommunicationError(DeviceError):
    """Raised when an ESP board cannot be reached or returns invalid data."""


class ESPDevice(BaseDevice):
    """Base class for a device controlled by an ESP board over TCP."""

    def __init__(
        self,
        device_id: str,
        name: str,
        esp_host: str,
        esp_port: int,
        remote_device_id: Optional[str] = None,
        timeout: float = 3.0,
        device_type: str = "esp_device",
        actions: Iterable[str] = ("TURN_ON", "TURN_OFF", "GET_STATUS"),
        room: str = "General",
    ):
        super().__init__(device_id, name, device_type, actions, room)
        self.esp_host = esp_host
        self.esp_port = int(esp_port)
        self.remote_device_id = remote_device_id or device_id
        self.timeout = float(timeout)
        self.last_seen = None

    def update_location(self, esp_host: str, esp_port: int) -> None:
        self.esp_host = esp_host
        self.esp_port = int(esp_port)
        import time

        self.last_seen = int(time.time())

    def perform_action(self, action: str, value: Any = None) -> Dict[str, Any]:
        if action not in self.allowed_actions:
            raise DeviceError(f"Action {action} is not supported by {self.device_id}")

        response = self._send_esp_command(action, value)
        if response.get("status") != "ok":
            raise ESPCommunicationError(response.get("message", "ESP command failed"))

        data = response.get("data") or {}
        if isinstance(data, dict):
            self._apply_remote_state(data)
        elif action == "TURN_ON":
            self.state = "on"
        elif action == "TURN_OFF":
            self.state = "off"
        return self.to_dict()

    def _send_esp_command(self, action: str, value: Any = None) -> Dict[str, Any]:
        request = {"command": action, "device_id": self.remote_device_id}
        if value is not None:
            request["value"] = value

        try:
            with socket.create_connection((self.esp_host, self.esp_port), timeout=self.timeout) as sock:
                sock.settimeout(self.timeout)
                protocol = Protocol(sock)
                protocol.send_msg(encode_message(request))
                payload = protocol.get_msg()
        except (OSError, ProtocolError, SocketDisconnected) as exc:
            raise ESPCommunicationError(f"ESP device {self.device_id} is unreachable: {exc}") from exc

        if payload is None:
            raise ESPCommunicationError(f"ESP device {self.device_id} disconnected")
        try:
            return decode_message(payload)
        except ValueError as exc:
            raise ESPCommunicationError(f"ESP device {self.device_id} returned invalid JSON") from exc

    def _apply_remote_state(self, data: Dict[str, Any]) -> None:
        if "state" in data:
            self.state = str(data["state"])

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update(
            {
                "esp_host": self.esp_host,
                "esp_port": self.esp_port,
                "remote_device_id": self.remote_device_id,
                "online": self.last_seen is not None,
                "last_seen": self.last_seen,
            }
        )
        return data


class ESPLEDDevice(ESPDevice):
    """ESP-controlled LED or LED strip with optional brightness support."""

    def __init__(
        self,
        device_id: str,
        name: str,
        esp_host: str,
        esp_port: int,
        remote_device_id: Optional[str] = None,
        timeout: float = 3.0,
        room: str = "General",
    ):
        super().__init__(
            device_id,
            name,
            esp_host,
            esp_port,
            remote_device_id,
            timeout,
            "esp_led",
            ("TURN_ON", "TURN_OFF", "SET_BRIGHTNESS", "GET_STATUS"),
            room,
        )
        self.brightness = 0

    def _apply_remote_state(self, data: Dict[str, Any]) -> None:
        super()._apply_remote_state(data)
        if "brightness" in data:
            self.brightness = int(data["brightness"])
            self.state = "on" if self.brightness > 0 else "off"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["brightness"] = self.brightness
        return data


class ESPRelayDevice(ESPDevice):
    """ESP-controlled relay output."""

    def __init__(
        self,
        device_id: str,
        name: str,
        esp_host: str,
        esp_port: int,
        remote_device_id: Optional[str] = None,
        timeout: float = 3.0,
        room: str = "General",
    ):
        super().__init__(
            device_id,
            name,
            esp_host,
            esp_port,
            remote_device_id,
            timeout,
            "esp_relay",
            ("TURN_ON", "TURN_OFF", "GET_STATUS"),
            room,
        )


class ESPFanDevice(ESPDevice):
    """ESP-controlled fan output through a transistor/MOSFET/relay driver."""

    def __init__(
        self,
        device_id: str,
        name: str,
        esp_host: str,
        esp_port: int,
        remote_device_id: Optional[str] = None,
        timeout: float = 3.0,
        room: str = "General",
    ):
        super().__init__(
            device_id,
            name,
            esp_host,
            esp_port,
            remote_device_id,
            timeout,
            "esp_fan",
            ("TURN_ON", "TURN_OFF", "GET_STATUS"),
            room,
        )


class ESPServoDevice(ESPDevice):
    """ESP-controlled micro-servo."""

    def __init__(
        self,
        device_id: str,
        name: str,
        esp_host: str,
        esp_port: int,
        remote_device_id: Optional[str] = None,
        timeout: float = 3.0,
        room: str = "General",
    ):
        super().__init__(
            device_id,
            name,
            esp_host,
            esp_port,
            remote_device_id,
            timeout,
            "esp_servo",
            ("SET_POSITION", "GET_STATUS"),
            room,
        )
        self.position = 0

    def _apply_remote_state(self, data: Dict[str, Any]) -> None:
        super()._apply_remote_state(data)
        if "position" in data:
            self.position = int(data["position"])
            self.state = f"{self.position} degrees"

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["position"] = self.position
        return data
