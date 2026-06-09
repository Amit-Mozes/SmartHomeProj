import socket
import threading
import unittest

from smart_home_project.common.messages import decode_message, encode_message, ok
from smart_home_project.common.protocol import Protocol
from smart_home_project.server.esp_devices import ESPFanDevice, ESPLEDDevice, ESPServoDevice


class FakeESPServer:
    def __init__(self):
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.host, self.port = self.sock.getsockname()
        self.request = None
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.sock.listen(1)
        self.thread.start()

    def _run(self):
        client, _address = self.sock.accept()
        with client:
            protocol = Protocol(client)
            payload = protocol.get_msg()
            self.request = decode_message(payload)
            if self.request["command"] == "SET_POSITION":
                data = {
                    "device_id": self.request["device_id"],
                    "state": f"{int(self.request.get('value', 0))} degrees",
                    "position": int(self.request.get("value", 0)),
                }
            else:
                data = {
                    "device_id": self.request["device_id"],
                    "state": "on",
                    "brightness": int(self.request.get("value", 100)),
                }
            protocol.send_msg(
                encode_message(
                    ok(
                        "done",
                        data,
                    )
                )
            )
        self.sock.close()


class ESPDeviceTests(unittest.TestCase):
    def test_esp_led_uses_length_prefixed_json_protocol(self):
        server = FakeESPServer()
        server.start()
        device = ESPLEDDevice(
            "pi_led",
            "Pi LED",
            server.host,
            server.port,
            remote_device_id="led_1",
            timeout=2,
        )

        state = device.perform_action("SET_BRIGHTNESS", 45)

        self.assertEqual(server.request["command"], "SET_BRIGHTNESS")
        self.assertEqual(server.request["device_id"], "led_1")
        self.assertEqual(server.request["value"], 45)
        self.assertEqual(state["state"], "on")
        self.assertEqual(state["brightness"], 45)

    def test_esp_servo_updates_position_from_response(self):
        server = FakeESPServer()
        server.start()
        device = ESPServoDevice(
            "pi_servo",
            "Pi Servo",
            server.host,
            server.port,
            remote_device_id="servo_1",
            timeout=2,
        )

        state = device.perform_action("SET_POSITION", 90)

        self.assertEqual(server.request["command"], "SET_POSITION")
        self.assertEqual(server.request["device_id"], "servo_1")
        self.assertEqual(server.request["value"], 90)
        self.assertEqual(state["position"], 90)

    def test_esp_fan_uses_on_off_command(self):
        server = FakeESPServer()
        server.start()
        device = ESPFanDevice(
            "pi_fan",
            "Pi Fan",
            server.host,
            server.port,
            remote_device_id="fan_1",
            timeout=2,
        )

        state = device.perform_action("TURN_ON")

        self.assertEqual(server.request["command"], "TURN_ON")
        self.assertEqual(server.request["device_id"], "fan_1")
        self.assertEqual(state["state"], "on")


if __name__ == "__main__":
    unittest.main()
