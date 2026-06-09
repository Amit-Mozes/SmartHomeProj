import unittest

from smart_home_project.server.devices import DeviceError, LEDStripDevice, MiniFridgeDevice, MockDevice
from smart_home_project.server.device_manager import DeviceManager


class DeviceTests(unittest.TestCase):
    def test_mock_device_turns_on_and_off(self):
        device = MockDevice("mock_1", "Mock")
        self.assertEqual(device.perform_action("TURN_ON")["state"], "on")
        self.assertEqual(device.perform_action("TURN_OFF")["state"], "off")

    def test_led_brightness_validation(self):
        device = LEDStripDevice("led_1", "LED")
        self.assertEqual(device.perform_action("SET_BRIGHTNESS", 75)["brightness"], 75)
        with self.assertRaises(DeviceError):
            device.perform_action("SET_BRIGHTNESS", 101)

    def test_fridge_temperature_validation(self):
        device = MiniFridgeDevice("fridge_1", "Fridge")
        self.assertEqual(device.perform_action("SET_TEMPERATURE", 2)["temperature_c"], 2)
        with self.assertRaises(DeviceError):
            device.perform_action("SET_TEMPERATURE", 30)

    def test_invalid_device_command(self):
        manager = DeviceManager()
        with self.assertRaises(DeviceError):
            manager.execute("missing", "TURN_ON")

    def test_device_updates_report_only_after_change(self):
        manager = DeviceManager()
        initial_revision = manager.snapshot()["revision"]

        no_change = manager.wait_for_updates(initial_revision, timeout=0.01)
        self.assertFalse(no_change["changed"])

        manager.execute("led_strip_1", "TURN_ON")
        changed = manager.wait_for_updates(initial_revision, timeout=0.01)
        self.assertTrue(changed["changed"])
        self.assertGreater(changed["revision"], initial_revision)
        self.assertTrue(any(device["device_id"] == "led_strip_1" for device in changed["devices"]))


if __name__ == "__main__":
    unittest.main()
