# Hardware Safety Notes

Use the Raspberry Pi GPIO pins as control signals, not as power supplies.

## Small Single LEDs

For a basic LED:

- Use a current-limiting resistor, usually 220-330 ohms.
- Connect GPIO pin -> resistor -> LED anode.
- Connect LED cathode -> Raspberry Pi GND.

## LED Strips, Motors, Fridges, and Larger Loads

Do not power these directly from GPIO pins.

Use:

- External power supply sized for the device.
- MOSFET driver for DC LED strips or motors.
- Relay module when switching isolated loads.
- Shared ground between the Pi and external DC power supply when using MOSFETs.
- Flyback diode for inductive loads if your module does not already include protection.

## Recommended First Hardware Test

Start with one small LED on one GPIO pin. After that works, move to MOSFET-driven LED strips.

## GPIO Mode

The project defaults to mock mode. On the Pi, edit:

```text
smart_home_project/server/server_settings.json
```

Set:

```json
"device_mode": "gpio"
```

Then define GPIO-capable devices in:

```text
smart_home_project/server/devices_config.json
```

Example:

```json
{
  "device_id": "real_led_1",
  "name": "Real LED",
  "type": "gpio_led",
  "pin": 17
}
```
