# Raspberry Pi Setup

Copy the project to the Raspberry Pi. The Pi needs the server and common packages, but copying the whole project is easiest.

## Install

```bash
cd SmartHomeProject
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install gpiozero
```

## Configure

Edit:

```bash
nano smart_home_project/server/server_settings.json
```

For remote control from another computer or phone app, use:

```json
{
  "host": "0.0.0.0",
  "port": 8820,
  "device_mode": "mock"
}
```

Use `"device_mode": "gpio"` only after wiring and testing hardware safely.

For ESP32/ESP8266 wireless modules, use:

```json
"device_mode": "esp"
```

and point `device_config` to an ESP config file. See `ESP_SETUP.md`.

## Run Server

```bash
source .venv/bin/activate
python -m smart_home_project.server.main
```

Find the Pi IP:

```bash
hostname -I
```

On the computer client, use that IP in the Host field.

## Run On Boot With systemd

Copy `deployment/smart-home-server.service` to:

```bash
sudo cp deployment/smart-home-server.service /etc/systemd/system/
```

Edit paths/user in the service file if needed, then run:

```bash
sudo systemctl daemon-reload
sudo systemctl enable smart-home-server
sudo systemctl start smart-home-server
sudo systemctl status smart-home-server
```

Logs are written to:

```text
logs/server.log
```
