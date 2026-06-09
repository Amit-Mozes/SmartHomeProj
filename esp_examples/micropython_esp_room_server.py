"""MicroPython ESP32 room-module server.

One ESP can expose several local devices, such as a light and a micro-servo.
Save this file to the ESP32 as main.py after editing Wi-Fi and pin settings.
"""

import json
import network
import socket
import time
from machine import Pin, PWM


WIFI_SSID = "YOUR_WIFI_NAME"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
HOST = "0.0.0.0"
PORT = 8890
DISCOVERY_PORT = 8891
LENGTH_FIELD_SIZE = 10

DEVICES = {
    "living_room_light": {
        "type": "led",
        "pin": 2,
        "active_low": True,
    },
    "living_room_servo": {
        "type": "servo",
        "pin": 13,
        "min_duty": 26,
        "max_duty": 123,
    },
    "living_room_second_light": {
        "type": "led",
        "pin": 23,
        "active_low": False,
    },
}


class LEDController:
    def __init__(self, device_id, config):
        self.device_id = device_id
        self.state = "off"
        self.brightness = 0
        self.active_low = config.get("active_low", False)
        self.pwm = PWM(Pin(config["pin"]), freq=1000)
        self._apply()

    def handle(self, command, value=None):
        if command == "TURN_ON":
            self.state = "on"
            if self.brightness == 0:
                self.brightness = 100
        elif command == "TURN_OFF":
            self.state = "off"
            self.brightness = 0
        elif command == "SET_BRIGHTNESS":
            brightness = int(value)
            if brightness < 0 or brightness > 100:
                raise ValueError("Brightness must be 0-100")
            self.brightness = brightness
            self.state = "on" if brightness > 0 else "off"
        elif command == "GET_STATUS":
            pass
        else:
            raise ValueError("Unsupported LED command")
        self._apply()
        return self.to_dict()

    def to_dict(self):
        return {"device_id": self.device_id, "state": self.state, "brightness": self.brightness}

    def _apply(self):
        duty = int((self.brightness / 100) * 1023)
        if self.active_low:
            duty = 1023 - duty
        self.pwm.duty(duty)


class ServoController:
    def __init__(self, device_id, config):
        self.device_id = device_id
        self.position = 0
        self.min_duty = int(config.get("min_duty", 26))
        self.max_duty = int(config.get("max_duty", 123))
        self.pwm = PWM(Pin(config["pin"]), freq=50)
        self._apply()

    def handle(self, command, value=None):
        if command == "SET_POSITION":
            position = int(value)
            if position < 0 or position > 180:
                raise ValueError("Servo position must be 0-180")
            self.position = position
        elif command == "GET_STATUS":
            pass
        else:
            raise ValueError("Unsupported servo command")
        self._apply()
        return self.to_dict()

    def to_dict(self):
        return {"device_id": self.device_id, "state": str(self.position) + " degrees", "position": self.position}

    def _apply(self):
        duty = self.min_duty + int((self.position / 180) * (self.max_duty - self.min_duty))
        self.pwm.duty(duty)


class FanController:
    def __init__(self, device_id, config):
        self.device_id = device_id
        self.state = "off"
        self.active_low = config.get("active_low", False)
        self.pin = Pin(config["pin"], Pin.OUT)
        self._apply()

    def handle(self, command, value=None):
        if command == "TURN_ON":
            self.state = "on"
        elif command == "TURN_OFF":
            self.state = "off"
        elif command == "GET_STATUS":
            pass
        else:
            raise ValueError("Unsupported fan command")
        self._apply()
        return self.to_dict()

    def to_dict(self):
        return {"device_id": self.device_id, "state": self.state}

    def _apply(self):
        value = 1 if self.state == "on" else 0
        if self.active_low:
            value = 0 if value else 1
        self.pin.value(value)


def build_controllers():
    controllers = {}
    for device_id, config in DEVICES.items():
        if config["type"] == "led":
            controllers[device_id] = LEDController(device_id, config)
        elif config["type"] == "servo":
            controllers[device_id] = ServoController(device_id, config)
        elif config["type"] == "fan":
            controllers[device_id] = FanController(device_id, config)
    return controllers


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    time.sleep(1)
    if wlan.isconnected():
        print("Wi-Fi already connected:", wlan.ifconfig())
        return
    wlan.disconnect()
    time.sleep(0.5)
    print("Connecting to Wi-Fi...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    started = time.time()
    while not wlan.isconnected():
        if time.time() - started > 30:
            raise RuntimeError("Wi-Fi connection timed out")
        time.sleep(0.5)
    print("Wi-Fi connected:", wlan.ifconfig())


def discovery_payload():
    devices = []
    for device_id, config in DEVICES.items():
        device_type_map = {"led": "esp_led", "servo": "esp_servo", "fan": "esp_fan"}
        device_type = device_type_map.get(config["type"], "esp_device")
        devices.append({"remote_device_id": device_id, "device_type": device_type})
    return json.dumps({"type": "smart_home_esp", "devices": devices, "port": PORT}).encode()


def handle_discovery_request(udp_sock):
    try:
        payload, address = udp_sock.recvfrom(512)
    except OSError:
        return
    try:
        request = json.loads(payload.decode())
    except Exception:
        return
    if request.get("type") == "smart_home_discovery_request":
        udp_sock.sendto(discovery_payload(), (address[0], DISCOVERY_PORT))


def recv_exact(sock, n):
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise OSError("client disconnected")
        data += chunk
    return data


def recv_msg(sock):
    length_field = recv_exact(sock, LENGTH_FIELD_SIZE)
    if not length_field.isdigit():
        raise ValueError("invalid length field")
    return recv_exact(sock, int(length_field))


def send_msg(sock, data):
    payload = data.encode() if isinstance(data, str) else data
    sock.sendall(("%010d" % len(payload)).encode() + payload)


def response(status, message, data=None):
    return json.dumps({"status": status, "message": message, "data": data})


def handle_request(controllers, request):
    device_id = request.get("device_id")
    controller = controllers.get(device_id)
    if not controller:
        return response("error", "Unknown device")
    try:
        data = controller.handle(request.get("command"), request.get("value"))
        return response("ok", "done", data)
    except Exception as exc:
        return response("error", str(exc))


def main():
    # A short delay makes startup more reliable when the ESP is powered from
    # an external supply instead of being started manually from Thonny.
    time.sleep(2)
    connect_wifi()
    controllers = build_controllers()
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp.bind(("0.0.0.0", DISCOVERY_PORT))
    udp.settimeout(0)

    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(3)
    server.settimeout(1)
    print("ESP room server listening on", PORT)
    print("ESP discovery waiting on UDP", DISCOVERY_PORT)

    while True:
        handle_discovery_request(udp)
        try:
            client, _address = server.accept()
        except OSError:
            continue
        try:
            payload = recv_msg(client)
            request = json.loads(payload.decode())
            send_msg(client, handle_request(controllers, request))
        except Exception as exc:
            try:
                send_msg(client, response("error", str(exc)))
            except Exception:
                pass
        finally:
            client.close()


main()

