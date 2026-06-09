"""Thread-safe registry and dispatcher for smart-home devices."""

from __future__ import annotations

import threading
import json
from pathlib import Path
from typing import Any, Dict, List

from .devices import BaseDevice, DeviceError, LEDStripDevice, MiniFridgeDevice, MockDevice


class DeviceManager:
    def __init__(self, config_path: Path | None = None, device_mode: str = "mock"):
        self._lock = threading.RLock()
        self._changed = threading.Condition(self._lock)
        self._devices: Dict[str, BaseDevice] = {}
        self._revision = 0
        self.device_mode = device_mode
        if config_path:
            self._load_from_config(config_path)
        else:
            self._load_default_mock_devices()

    def _load_from_config(self, config_path: Path) -> None:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        for item in data.get("devices", []):
            self.add_device(self._create_device(item))

    def _create_device(self, item: Dict[str, Any]) -> BaseDevice:
        device_type = item.get("type", "mock")
        device_id = item["device_id"]
        name = item["name"]

        if self.device_mode in {"esp", "mixed"} and device_type in {"esp_led", "esp_relay", "esp_fan", "esp_servo", "esp_device"}:
            return self._create_esp_device(item)
        if self.device_mode in {"gpio", "mixed"} and device_type in {"gpio_led", "led_strip"} and "pin" in item:
            from smart_home_project.server.gpio_devices import GPIOLedDevice

            return GPIOLedDevice(device_id, name, int(item["pin"]), item.get("room", "General"))
        if device_type == "led_strip":
            return LEDStripDevice(device_id, name, item.get("room", "General"))
        if device_type == "mini_fridge":
            return MiniFridgeDevice(device_id, name, item.get("room", "General"))
        return MockDevice(device_id, name, device_type, item.get("room", "General"))

    def _create_esp_device(self, item: Dict[str, Any]) -> BaseDevice:
        from smart_home_project.server.esp_devices import ESPDevice, ESPFanDevice, ESPLEDDevice, ESPRelayDevice, ESPServoDevice

        device_type = item.get("type", "esp_device")
        kwargs = {
            "device_id": item["device_id"],
            "name": item["name"],
            "esp_host": item["esp_host"],
            "esp_port": int(item.get("esp_port", 8890)),
            "remote_device_id": item.get("remote_device_id"),
            "timeout": float(item.get("timeout", 3.0)),
            "room": item.get("room", "General"),
        }
        if device_type == "esp_led":
            return ESPLEDDevice(**kwargs)
        if device_type == "esp_relay":
            return ESPRelayDevice(**kwargs)
        if device_type == "esp_fan":
            return ESPFanDevice(**kwargs)
        if device_type == "esp_servo":
            return ESPServoDevice(**kwargs)
        return ESPDevice(device_type="esp_device", actions=item.get("actions", ["TURN_ON", "TURN_OFF", "GET_STATUS"]), **kwargs)

    def _load_default_mock_devices(self) -> None:
        self.add_device(LEDStripDevice("led_strip_1", "Living Room LED Strip"))
        self.add_device(LEDStripDevice("led_strip_2", "Bedroom LED Strip"))
        self.add_device(MiniFridgeDevice("mini_fridge_1", "Kitchen Mini Fridge"))
        self.add_device(MockDevice("fan_1", "Ventilation Fan", "fan"))
        self.add_device(MockDevice("sensor_1", "Door Sensor", "sensor"))

    def add_device(self, device: BaseDevice) -> None:
        with self._lock:
            self._devices[device.device_id] = device
            self._mark_changed()

    def list_devices(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [device.to_dict() for device in self._devices.values()]

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {"revision": self._revision, "devices": self.list_devices()}

    def wait_for_updates(self, since_revision: int, timeout: float = 25.0) -> Dict[str, Any]:
        with self._changed:
            if self._revision <= since_revision:
                self._changed.wait_for(lambda: self._revision > since_revision, timeout=timeout)
            changed = self._revision > since_revision
            return {
                "changed": changed,
                "revision": self._revision,
                "devices": self.list_devices() if changed else [],
            }

    def get_status(self, device_id: str) -> Dict[str, Any]:
        with self._lock:
            return self._get_device(device_id).to_dict()

    def update_esp_location(self, remote_device_id: str, esp_host: str, esp_port: int) -> bool:
        with self._lock:
            for device in self._devices.values():
                if getattr(device, "remote_device_id", None) == remote_device_id:
                    old_host = getattr(device, "esp_host", None)
                    old_port = getattr(device, "esp_port", None)
                    if hasattr(device, "update_location"):
                        device.update_location(esp_host, esp_port)
                    else:
                        setattr(device, "esp_host", esp_host)
                        setattr(device, "esp_port", int(esp_port))
                    if old_host != esp_host or old_port != int(esp_port):
                        self._mark_changed()
                    return True
            return False

    def reset_demo(self) -> Dict[str, Any]:
        results = []
        with self._lock:
            for device in self._devices.values():
                try:
                    if "TURN_OFF" in device.allowed_actions:
                        results.append(device.perform_action("TURN_OFF"))
                    elif "SET_POSITION" in device.allowed_actions:
                        results.append(device.perform_action("SET_POSITION", 0))
                except Exception as exc:
                    results.append({"device_id": device.device_id, "status": "error", "message": str(exc)})
            self._mark_changed()
            return {"devices": results}

    def execute(self, device_id: str, action: str, value: Any = None) -> Dict[str, Any]:
        with self._lock:
            device = self._get_device(device_id)
            before = device.to_dict()
            result = device.perform_action(action, value)
            if result != before and action != "GET_STATUS":
                self._mark_changed()
            return result

    def _get_device(self, device_id: str) -> BaseDevice:
        try:
            return self._devices[device_id]
        except KeyError as exc:
            raise DeviceError(f"Unknown device: {device_id}") from exc

    def _mark_changed(self) -> None:
        self._revision += 1
        self._changed.notify_all()
