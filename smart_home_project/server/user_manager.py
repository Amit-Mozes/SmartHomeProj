"""JSON-backed users and password hashing."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional


class UserManager:
    def __init__(self, config_path: Path):
        self.config_path = Path(config_path)
        self._lock = threading.RLock()
        self.users: Dict[str, Dict[str, str]] = {}
        self.load()

    def load(self) -> None:
        with self._lock:
            if not self.config_path.exists():
                self._create_default_config()
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            self.users = {user["username"]: user for user in data.get("users", [])}

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, str]]:
        with self._lock:
            user = self.users.get(username)
            if not user:
                return None
            if self.verify_password(password, user["password_hash"]):
                return {"username": username, "role": user["role"]}
            return None

    def register_user(self, username: str, password: str, role: str = "guest") -> Dict[str, str]:
        return self.create_user(username, password, role, allowed_roles={"guest", "child", "parent"})

    def create_user(
        self,
        username: str,
        password: str,
        role: str = "guest",
        allowed_roles: Optional[set[str]] = None,
    ) -> Dict[str, str]:
        username = username.strip()
        allowed_roles = allowed_roles or {"admin", "parent", "child", "guest"}
        role = role if role in allowed_roles else "guest"
        if not username:
            raise ValueError("Username is required")
        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters")
        if not username.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username can contain only letters, numbers, underscores, and hyphens")
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters")

        with self._lock:
            if username in self.users:
                raise ValueError("Username already exists")
            user = {"username": username, "password_hash": self.hash_password(password), "role": role}
            self.users[username] = user
            self._save()
            return {"username": username, "role": role}

    def list_users(self) -> List[Dict[str, str]]:
        with self._lock:
            return [
                {"username": user["username"], "role": user["role"]}
                for user in sorted(self.users.values(), key=lambda item: item["username"])
            ]

    def update_role(self, username: str, role: str) -> Dict[str, str]:
        if role not in {"admin", "parent", "child", "guest"}:
            raise ValueError("Invalid role")
        with self._lock:
            if username not in self.users:
                raise ValueError("Unknown user")
            self.users[username]["role"] = role
            self._save()
            return {"username": username, "role": role}

    def delete_user(self, username: str) -> Dict[str, str]:
        with self._lock:
            if username not in self.users:
                raise ValueError("Unknown user")
            if len(self.users) == 1:
                raise ValueError("Cannot delete the last user")
            user = self.users.pop(username)
            self._save()
            return {"username": user["username"], "role": user["role"]}

    def _save(self) -> None:
        data = {"users": list(self.users.values())}
        self.config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _create_default_config(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        users = [
            {"username": "admin", "password_hash": self.hash_password("admin123"), "role": "admin"},
            {"username": "parent", "password_hash": self.hash_password("parent123"), "role": "parent"},
            {"username": "child", "password_hash": self.hash_password("child123"), "role": "child"},
            {"username": "guest", "password_hash": self.hash_password("guest123"), "role": "guest"},
        ]
        self.config_path.write_text(json.dumps({"users": users}, indent=2), encoding="utf-8")

    @staticmethod
    def hash_password(password: str, salt: Optional[bytes] = None) -> str:
        salt = salt or os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
        return "pbkdf2_sha256$120000${}${}".format(
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(digest).decode("ascii"),
        )

    @staticmethod
    def verify_password(password: str, stored_hash: str) -> bool:
        try:
            algorithm, iterations, salt_b64, digest_b64 = stored_hash.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            salt = base64.b64decode(salt_b64.encode("ascii"))
            expected = base64.b64decode(digest_b64.encode("ascii"))
            actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(actual, expected)
