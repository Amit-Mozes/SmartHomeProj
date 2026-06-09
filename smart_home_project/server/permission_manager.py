"""Role-based permission checks for commands and devices."""

from __future__ import annotations

from typing import Dict, Iterable, Optional


class PermissionManager:
    def __init__(self, role_permissions: Dict[str, Dict]):
        self.role_permissions = role_permissions

    def can_execute(
        self,
        role: str,
        command: str,
        device_id: Optional[str] = None,
        device_type: Optional[str] = None,
    ) -> bool:
        permissions = self.role_permissions.get(role)
        if not permissions:
            return False

        if command in permissions.get("commands", []):
            return True

        device_rules = permissions.get("devices", {})
        if device_id and command in device_rules.get(device_id, []):
            return True
        if device_type and command in device_rules.get(device_type, []):
            return True
        if command in device_rules.get("*", []):
            return True
        return False

    @staticmethod
    def default_permissions() -> Dict[str, Dict[str, Iterable[str]]]:
        return {
            "admin": {
                "commands": [
                    "LIST_DEVICES",
                    "GET_UPDATES",
                    "GET_STATUS",
                    "TURN_ON",
                    "TURN_OFF",
                    "SET_BRIGHTNESS",
                    "SET_TEMPERATURE",
                    "SET_POSITION",
                    "DEMO_RESET",
                    "LIST_USERS",
                    "UPDATE_ROLE",
                    "CREATE_USER",
                    "DELETE_USER",
                ],
                "devices": {"*": ["GET_STATUS", "TURN_ON", "TURN_OFF", "SET_BRIGHTNESS", "SET_TEMPERATURE", "SET_POSITION"]},
            },
            "parent": {
                "commands": ["LIST_DEVICES", "GET_UPDATES", "GET_STATUS"],
                "devices": {
                    "led_strip": ["GET_STATUS", "TURN_ON", "TURN_OFF", "SET_BRIGHTNESS"],
                    "esp_led": ["GET_STATUS", "TURN_ON", "TURN_OFF", "SET_BRIGHTNESS"],
                    "esp_fan": ["GET_STATUS", "TURN_ON", "TURN_OFF"],
                    "esp_servo": ["GET_STATUS", "SET_POSITION"],
                    "mini_fridge": ["GET_STATUS", "SET_TEMPERATURE"],
                    "fan": ["GET_STATUS", "TURN_ON", "TURN_OFF"],
                    "sensor": ["GET_STATUS"],
                },
            },
            "child": {
                "commands": ["LIST_DEVICES", "GET_UPDATES", "GET_STATUS"],
                "devices": {
                    "led_strip": ["GET_STATUS", "TURN_ON", "TURN_OFF", "SET_BRIGHTNESS"],
                    "esp_led": ["GET_STATUS", "TURN_ON", "TURN_OFF", "SET_BRIGHTNESS"],
                    "esp_fan": ["GET_STATUS", "TURN_ON", "TURN_OFF"],
                    "esp_servo": ["GET_STATUS", "SET_POSITION"],
                    "fan": ["GET_STATUS", "TURN_ON", "TURN_OFF"],
                    "sensor": ["GET_STATUS"],
                },
            },
            "guest": {
                "commands": ["LIST_DEVICES", "GET_UPDATES", "GET_STATUS"],
                "devices": {"*": ["GET_STATUS"]},
            },
        }
