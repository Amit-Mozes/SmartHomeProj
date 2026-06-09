# ESP Device Setup

This project can use ESP32/ESP8266 boards as wireless device modules.

Recommended architecture:

```text
PC / Phone Client
        |
        | encrypted smart-home TCP protocol
        v
Raspberry Pi Server
        |
        | local Wi-Fi TCP to ESP boards
        v
ESP32 / ESP8266
        |
        v
LEDs / relays / sensors
```

Keep ESP boards on the local network. For remote access from outside home, connect to the Raspberry Pi through a VPN such as Tailscale/WireGuard rather than exposing ESP boards directly to the internet.

## Pi Configuration

On the Raspberry Pi, edit:

```text
smart_home_project/server/server_settings.json
```

For ESP devices:

```json
{
  "device_mode": "esp",
  "device_config": "esp_devices_config.example.json"
}
```

Or copy the example to your own file:

```bash
cp smart_home_project/server/esp_devices_config.example.json smart_home_project/server/my_esp_devices.json
```

Then set:

```json
"device_config": "my_esp_devices.json"
```

## ESP Protocol

The Pi sends a UDP discovery request on port `8891` when the server starts and
when a client logs in. ESP boards listen for that request and reply once with
their identity. This avoids constant broadcast traffic on the LAN.

Example announcement:

```json
{
  "type": "smart_home_esp",
  "remote_device_id": "led_1",
  "name": "ESP LED",
  "device_type": "esp_led",
  "port": 8890
}
```

The Pi sends JSON commands using the same 10-byte length prefix:

```text
0000000045{"command":"TURN_ON","device_id":"led_1"}
```

Supported ESP responses:

```json
{
  "status": "ok",
  "message": "done",
  "data": {
    "device_id": "led_1",
    "state": "on",
    "brightness": 75
  }
}
```

If something fails:

```json
{
  "status": "error",
  "message": "Unknown device",
  "data": null
}
```

## MicroPython Example

See:

```text
esp_examples/micropython_esp_room_server.py
```

Change Wi-Fi name, password, pins, and the `DEVICES` dictionary as needed.

Example one-room layout:

```python
DEVICES = {
    "living_room_light": {"type": "led", "pin": 2, "active_low": True},
    "living_room_servo": {"type": "servo", "pin": 13}
}
```
