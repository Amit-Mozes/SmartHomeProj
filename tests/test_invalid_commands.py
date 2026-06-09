import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock

from smart_home_project.server.client_handler import ClientHandler
from smart_home_project.server.device_manager import DeviceManager
from smart_home_project.server.permission_manager import PermissionManager
from smart_home_project.server.user_manager import UserManager


class FakeServer:
    def __init__(self):
        self.device_manager = DeviceManager()
        self.permission_manager = PermissionManager(PermissionManager.default_permissions())
        self.db_dir = Path(tempfile.mkdtemp())
        self.user_manager = UserManager(self.db_dir / "users.json")


class InvalidCommandTests(unittest.TestCase):
    def setUp(self):
        self.handler = ClientHandler.__new__(ClientHandler)
        self.handler.server = FakeServer()
        self.handler.user = {"username": "admin", "role": "admin"}
        self.handler.address = ("127.0.0.1", 12345)
        self.handler.logger = Mock()

    def test_unknown_command_returns_error(self):
        response = self.handler._handle_request({"command": "DO_MAGIC"})
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["code"], "UNKNOWN_COMMAND")

    def test_unknown_device_returns_error(self):
        response = self.handler._handle_request({"command": "TURN_ON", "device_id": "missing"})
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["code"], "DEVICE_ERROR")

    def test_invalid_value_returns_error(self):
        response = self.handler._handle_request(
            {"command": "SET_BRIGHTNESS", "device_id": "led_strip_1", "value": 150}
        )
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["code"], "DEVICE_ERROR")

    def test_sign_up_is_allowed_before_login(self):
        self.handler.user = None
        response = self.handler._handle_request(
            {"command": "SIGN_UP", "username": "new_child", "password": "secret123", "role": "child"}
        )
        self.assertEqual(response["status"], "ok")
        self.assertEqual(response["data"]["role"], "child")

    def test_ping_is_allowed_before_login(self):
        self.handler.user = None
        response = self.handler._handle_request({"command": "PING"})
        self.assertEqual(response["status"], "ok")
        self.assertTrue(response["data"]["supports_signup"])

    def test_admin_action_rejects_wrong_password(self):
        response = self.handler._handle_request(
            {
                "command": "UPDATE_ROLE",
                "username": "guest",
                "role": "child",
                "admin_password": "wrong",
            }
        )
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["code"], "ADMIN_CONFIRM_FAILED")

    def test_admin_can_create_update_and_delete_user_with_password(self):
        created = self.handler._handle_request(
            {
                "command": "CREATE_USER",
                "username": "managed_user",
                "password": "secret123",
                "role": "guest",
                "admin_password": "admin123",
            }
        )
        self.assertEqual(created["status"], "ok")

        updated = self.handler._handle_request(
            {
                "command": "UPDATE_ROLE",
                "username": "managed_user",
                "role": "child",
                "admin_password": "admin123",
            }
        )
        self.assertEqual(updated["status"], "ok")
        self.assertEqual(updated["data"]["role"], "child")

        deleted = self.handler._handle_request(
            {
                "command": "DELETE_USER",
                "username": "managed_user",
                "admin_password": "admin123",
            }
        )
        self.assertEqual(deleted["status"], "ok")


if __name__ == "__main__":
    unittest.main()
