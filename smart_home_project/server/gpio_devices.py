"""Raspberry Pi GPIO-backed device classes.

These classes import gpiozero only when they are constructed, so the project
can still run and test on a regular computer in mock mode.
"""

from __future__ import annotations

from typing import Any, Dict

from smart_home_project.server.devices import BaseDevice, DeviceError


class GPIOUnavailableError(RuntimeError):
    """Raised when Raspberry Pi GPIO libraries are unavailable."""


class GPIOLedDevice(BaseDevice):
    """Real GPIO LED or low-power control output."""

    def __init__(self, device_id: str, name: str, pin: int, room: str = "General"):
        super().__init__(device_id, name, "gpio_led", ["TURN_ON", "TURN_OFF", "GET_STATUS"], room)
        self.pin = pin
        try:
            from gpiozero import LED
        except ImportError as exc:
            raise GPIOUnavailableError("Install gpiozero on the Raspberry Pi to use GPIO devices") from exc
        self.led = LED(pin)

    def perform_action(self, action: str, value: Any = None) -> Dict[str, Any]:
        if action == "TURN_ON":
            self.led.on()
            self.state = "on"
        elif action == "TURN_OFF":
            self.led.off()
            self.state = "off"
        elif action == "GET_STATUS":
            pass
        else:
            raise DeviceError(f"Action {action} is not supported by {self.device_id}")
        return self.to_dict()

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["pin"] = self.pin
        return data
