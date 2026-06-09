"""Smart-home device models and mock hardware implementations."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


class DeviceError(ValueError):
    """Raised when a device action is invalid."""


class BaseDevice:
    """Base class for all simulated and future real hardware devices."""

    def __init__(self, device_id: str, name: str, device_type: str, actions: Iterable[str], room: str = "General"):
        self.device_id = device_id
        self.name = name
        self.type = device_type
        self.state = "off"
        self.allowed_actions = list(actions)
        self.room = room

    def perform_action(self, action: str, value: Any = None) -> Dict[str, Any]:
        if action not in self.allowed_actions:
            raise DeviceError(f"Action {action} is not supported by {self.device_id}")

        if action == "TURN_ON":
            self.state = "on"
        elif action == "TURN_OFF":
            self.state = "off"
        elif action == "GET_STATUS":
            pass
        else:
            raise DeviceError(f"Action {action} is not implemented by {self.device_id}")
        return self.to_dict()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "type": self.type,
            "room": self.room,
            "state": self.state,
            "allowed_actions": self.allowed_actions,
        }


class MockDevice(BaseDevice):
    """Generic simulated on/off gadget."""

    def __init__(self, device_id: str, name: str, device_type: str = "mock", room: str = "General"):
        super().__init__(device_id, name, device_type, ["TURN_ON", "TURN_OFF", "GET_STATUS"], room)


class LEDStripDevice(BaseDevice):
    """Simulated LED strip with brightness control."""

    def __init__(self, device_id: str, name: str, room: str = "General"):
        super().__init__(
            device_id,
            name,
            "led_strip",
            ["TURN_ON", "TURN_OFF", "SET_BRIGHTNESS", "GET_STATUS"],
            room,
        )
        self.brightness = 0

    def perform_action(self, action: str, value: Any = None) -> Dict[str, Any]:
        if action == "SET_BRIGHTNESS":
            if action not in self.allowed_actions:
                raise DeviceError(f"Action {action} is not supported by {self.device_id}")
            brightness = int(value)
            if not 0 <= brightness <= 100:
                raise DeviceError("Brightness must be between 0 and 100")
            self.brightness = brightness
            self.state = "on" if brightness > 0 else "off"
            return self.to_dict()
        return super().perform_action(action, value)

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["brightness"] = self.brightness
        return data


class MiniFridgeDevice(BaseDevice):
    """Simulated mini-fridge with temperature setting."""

    def __init__(self, device_id: str, name: str, room: str = "General"):
        super().__init__(
            device_id,
            name,
            "mini_fridge",
            ["TURN_ON", "TURN_OFF", "SET_TEMPERATURE", "GET_STATUS"],
            room,
        )
        self.temperature_c = 4

    def perform_action(self, action: str, value: Any = None) -> Dict[str, Any]:
        if action == "SET_TEMPERATURE":
            if action not in self.allowed_actions:
                raise DeviceError(f"Action {action} is not supported by {self.device_id}")
            temperature = int(value)
            if not -5 <= temperature <= 15:
                raise DeviceError("Temperature must be between -5 and 15 C")
            self.temperature_c = temperature
            return self.to_dict()
        return super().perform_action(action, value)

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["temperature_c"] = self.temperature_c
        return data
