import json
import tempfile
import unittest
from pathlib import Path

from smart_home_project.server.user_manager import UserManager


class UserManagerTests(unittest.TestCase):
    def test_register_user_hashes_and_persists_password(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "users.json"
            manager = UserManager(db_path)

            user = manager.register_user("new_user", "secret123", "guest")

            self.assertEqual(user, {"username": "new_user", "role": "guest"})
            data = json.loads(db_path.read_text(encoding="utf-8"))
            stored = next(item for item in data["users"] if item["username"] == "new_user")
            self.assertNotEqual(stored["password_hash"], "secret123")
            self.assertTrue(UserManager.verify_password("secret123", stored["password_hash"]))

            reloaded = UserManager(db_path)
            self.assertEqual(reloaded.authenticate("new_user", "secret123")["role"], "guest")

    def test_register_user_rejects_duplicate_username(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = UserManager(Path(tmp) / "users.json")
            manager.register_user("new_user", "secret123")
            with self.assertRaises(ValueError):
                manager.register_user("new_user", "another123")

    def test_update_role_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "users.json"
            manager = UserManager(db_path)
            manager.register_user("new_user", "secret123", "guest")
            manager.update_role("new_user", "child")

            reloaded = UserManager(db_path)
            self.assertEqual(reloaded.authenticate("new_user", "secret123")["role"], "child")

    def test_create_and_delete_user(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "users.json"
            manager = UserManager(db_path)
            manager.create_user("managed_user", "secret123", "parent")
            self.assertEqual(manager.authenticate("managed_user", "secret123")["role"], "parent")

            deleted = manager.delete_user("managed_user")
            self.assertEqual(deleted["username"], "managed_user")
            self.assertIsNone(manager.authenticate("managed_user", "secret123"))


if __name__ == "__main__":
    unittest.main()
