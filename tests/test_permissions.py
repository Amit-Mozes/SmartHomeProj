import unittest

from smart_home_project.server.permission_manager import PermissionManager


class PermissionTests(unittest.TestCase):
    def setUp(self):
        self.permissions = PermissionManager(PermissionManager.default_permissions())

    def test_admin_can_control_fridge(self):
        self.assertTrue(self.permissions.can_execute("admin", "SET_TEMPERATURE", "mini_fridge_1", "mini_fridge"))

    def test_guest_can_only_view(self):
        self.assertTrue(self.permissions.can_execute("guest", "GET_STATUS", "led_strip_1", "led_strip"))
        self.assertFalse(self.permissions.can_execute("guest", "TURN_ON", "led_strip_1", "led_strip"))

    def test_child_cannot_control_fridge_temperature(self):
        self.assertFalse(self.permissions.can_execute("child", "SET_TEMPERATURE", "mini_fridge_1", "mini_fridge"))


if __name__ == "__main__":
    unittest.main()
