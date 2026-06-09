import json
import tempfile
import unittest
from pathlib import Path

from smart_home_project.server.device_manager import DeviceManager
from smart_home_project.server.server_settings import ServerSettings


class ServerConfigTests(unittest.TestCase):
    def test_settings_file_is_created_with_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            settings = ServerSettings.load(path)

            self.assertTrue(path.exists())
            self.assertEqual(settings.port, 8820)
            self.assertEqual(settings.device_mode, "mock")

    def test_device_manager_loads_json_devices(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "devices.json"
            path.write_text(
                json.dumps(
                    {
                        "devices": [
                            {"device_id": "led_a", "name": "LED A", "type": "led_strip"},
                            {"device_id": "fan_a", "name": "Fan A", "type": "fan"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            manager = DeviceManager(path, "mock")

            devices = manager.list_devices()
            self.assertEqual(len(devices), 2)
            self.assertEqual(manager.get_status("led_a")["type"], "led_strip")


if __name__ == "__main__":
    unittest.main()
