import json
import socket
import tempfile
import time
import unittest
from pathlib import Path

from smart_home_project.server.device_manager import DeviceManager
from smart_home_project.server.esp_discovery import ESPDiscoveryService


class ESPDiscoveryTests(unittest.TestCase):
    def test_discovery_updates_matching_esp_device_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "devices.json"
            config_path.write_text(
                json.dumps(
                    {
                        "devices": [
                            {
                                "device_id": "esp_lamp",
                                "name": "ESP Lamp",
                                "type": "esp_led",
                                "esp_host": "192.168.1.10",
                                "esp_port": 8890,
                                "remote_device_id": "led_1",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            manager = DeviceManager(config_path, "esp")

            updated = manager.update_esp_location("led_1", "192.168.1.219", 8890)

            self.assertTrue(updated)
            device = manager.get_status("esp_lamp")
            self.assertEqual(device["esp_host"], "192.168.1.219")

    def test_discovery_service_accepts_udp_announcement(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "devices.json"
            config_path.write_text(
                json.dumps(
                    {
                        "devices": [
                            {
                                "device_id": "esp_lamp",
                                "name": "ESP Lamp",
                                "type": "esp_led",
                                "esp_host": "192.168.1.10",
                                "esp_port": 8890,
                                "remote_device_id": "led_1",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            manager = DeviceManager(config_path, "esp")
            port_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            port_sock.bind(("127.0.0.1", 0))
            port = port_sock.getsockname()[1]
            port_sock.close()

            service = ESPDiscoveryService(manager, port)
            service.start()
            time.sleep(0.1)

            sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sender.sendto(
                json.dumps({"type": "smart_home_esp", "remote_device_id": "led_1", "port": 8890}).encode(),
                ("127.0.0.1", port),
            )
            sender.close()
            time.sleep(0.2)
            service.stop()

            self.assertEqual(manager.get_status("esp_lamp")["esp_host"], "127.0.0.1")

    def test_discovery_service_accepts_multi_device_announcement(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "devices.json"
            config_path.write_text(
                json.dumps(
                    {
                        "devices": [
                            {
                                "device_id": "room_light",
                                "name": "Room Light",
                                "type": "esp_led",
                                "esp_host": "192.168.1.10",
                                "esp_port": 8890,
                                "remote_device_id": "room_light",
                            },
                            {
                                "device_id": "room_servo",
                                "name": "Room Servo",
                                "type": "esp_servo",
                                "esp_host": "192.168.1.10",
                                "esp_port": 8890,
                                "remote_device_id": "room_servo",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            manager = DeviceManager(config_path, "esp")
            port_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            port_sock.bind(("127.0.0.1", 0))
            port = port_sock.getsockname()[1]
            port_sock.close()

            service = ESPDiscoveryService(manager, port)
            service.start()
            time.sleep(0.1)
            sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sender.sendto(
                json.dumps(
                    {
                        "type": "smart_home_esp",
                        "port": 8890,
                        "devices": [
                            {"remote_device_id": "room_light"},
                            {"remote_device_id": "room_servo"},
                        ],
                    }
                ).encode(),
                ("127.0.0.1", port),
            )
            sender.close()
            time.sleep(0.2)
            service.stop()

            self.assertEqual(manager.get_status("room_light")["esp_host"], "127.0.0.1")
            self.assertEqual(manager.get_status("room_servo")["esp_host"], "127.0.0.1")

    def test_discover_now_sends_udp_request(self):
        port_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        port_sock.bind(("127.0.0.1", 0))
        port = port_sock.getsockname()[1]
        port_sock.close()

        listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listener.bind(("", port))
        listener.settimeout(2)

        manager = DeviceManager()
        service = ESPDiscoveryService(manager, port)
        service.discover_now()

        payload, _address = listener.recvfrom(512)
        listener.close()
        self.assertEqual(json.loads(payload.decode())["type"], "smart_home_discovery_request")

if __name__ == "__main__":
    unittest.main()
