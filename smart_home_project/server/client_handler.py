"""Per-client server thread."""

from __future__ import annotations

import logging
import socket
import threading
from typing import Any, Dict, Optional

from smart_home_project.common.encryption import EncryptionManager
from smart_home_project.common.messages import decode_message, encode_message, error, ok
from smart_home_project.common.protocol import Protocol, ProtocolError, SocketDisconnected
from smart_home_project.server.devices import DeviceError


class ClientHandler(threading.Thread):
    def __init__(self, client_socket: socket.socket, address, server: "SmartHomeServer"):
        super().__init__(daemon=True)
        self.client_socket = client_socket
        self.address = address
        self.server = server
        self.protocol = Protocol(client_socket)
        self.encryption = EncryptionManager(private_key=server.encryption.private_key)
        self.user: Optional[Dict[str, str]] = None
        self.running = True
        self.logger = logging.getLogger("smart_home.server.client")

    def run(self) -> None:
        self.logger.info("Client connected: %s", self.address)
        try:
            self._handshake()
            while self.running:
                request = self._receive_encrypted_json()
                if request is None:
                    break
                response = self._handle_request(request)
                self._send_encrypted_json(response)
                if request.get("command") == "EXIT":
                    break
        except (ProtocolError, SocketDisconnected, ValueError) as exc:
            self.logger.warning("Client %s disconnected/error: %s", self.address, exc)
        except Exception:
            self.logger.exception("Unexpected client handler error for %s", self.address)
        finally:
            self.running = False
            try:
                self.client_socket.close()
            finally:
                self.logger.info("Client closed: %s", self.address)

    def _handshake(self) -> None:
        self.protocol.send_msg(encode_message({"type": "SERVER_PUBLIC_KEY", "public_key": self.server.encryption.public_key_pem()}))
        payload = self.protocol.get_msg()
        if payload is None:
            raise SocketDisconnected("Client disconnected during handshake")
        message = decode_message(payload)
        if message.get("type") != "SESSION_KEY":
            raise ProtocolError("Expected SESSION_KEY during handshake")
        self.encryption.accept_encrypted_session_key(message["encrypted_key"])
        self.protocol.send_msg(encode_message({"type": "HANDSHAKE_OK"}))

    def _receive_encrypted_json(self) -> Optional[Dict[str, Any]]:
        payload = self.protocol.get_msg()
        if payload is None:
            return None
        decrypted = self.encryption.decrypt(payload)
        return decode_message(decrypted)

    def _send_encrypted_json(self, response: Dict[str, Any]) -> None:
        self.protocol.send_msg(self.encryption.encrypt(encode_message(response)))

    def _handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        command = str(request.get("command", "")).upper()
        self.logger.info("Command from %s user=%s command=%s", self.address, self.user, command)

        if command == "LOGIN":
            username = str(request.get("username", ""))
            password = str(request.get("password", ""))
            user = self.server.user_manager.authenticate(username, password)
            if not user:
                self.logger.warning("Failed login from %s for user=%s", self.address, username)
                return error("Invalid username or password", "AUTH_FAILED")
            self.user = user
            if self.server.esp_discovery:
                self.server.esp_discovery.discover_now()
            return ok("Login successful", {"username": user["username"], "role": user["role"]})

        if command in {"SIGN_UP", "SIGNUP"}:
            username = str(request.get("username", ""))
            password = str(request.get("password", ""))
            role = str(request.get("role", "guest"))
            try:
                user = self.server.user_manager.register_user(username, password, role)
            except ValueError as exc:
                return error(str(exc), "SIGN_UP_FAILED")
            self.logger.info("New user registered from %s username=%s role=%s", self.address, user["username"], user["role"])
            return ok("Account created", user)

        if command == "EXIT":
            self.running = False
            return ok("Goodbye")

        if command == "PING":
            return ok("Smart-home server is reachable", {"supports_signup": True})

        if self.user is None:
            return error("Please login first", "NOT_AUTHENTICATED")

        if command == "LIST_DEVICES":
            if not self._is_allowed(command):
                return self._permission_denied(command)
            return ok("Devices listed", self.server.device_manager.list_devices())

        if command == "DEMO_RESET":
            if not self._is_allowed(command):
                return self._permission_denied(command)
            return ok("Demo reset complete", self.server.device_manager.reset_demo())

        if command == "GET_UPDATES":
            if not self._is_allowed(command):
                return self._permission_denied(command)
            since_revision = int(request.get("since_revision", 0))
            timeout = float(request.get("timeout", 25.0))
            timeout = max(1.0, min(timeout, 60.0))
            return ok("Device updates", self.server.device_manager.wait_for_updates(since_revision, timeout))

        if command == "LIST_USERS":
            if not self._is_allowed(command):
                return self._permission_denied(command)
            return ok("Users listed", self.server.user_manager.list_users())

        if command == "UPDATE_ROLE":
            if not self._is_allowed(command):
                return self._permission_denied(command)
            if not self._confirm_admin_password(str(request.get("admin_password", ""))):
                return error("Admin password confirmation failed", "ADMIN_CONFIRM_FAILED")
            try:
                user = self.server.user_manager.update_role(
                    str(request.get("username", "")),
                    str(request.get("role", "")),
                )
            except ValueError as exc:
                return error(str(exc), "USER_ERROR")
            return ok("Role updated", user)

        if command == "CREATE_USER":
            if not self._is_allowed(command):
                return self._permission_denied(command)
            if not self._confirm_admin_password(str(request.get("admin_password", ""))):
                return error("Admin password confirmation failed", "ADMIN_CONFIRM_FAILED")
            try:
                user = self.server.user_manager.create_user(
                    str(request.get("username", "")),
                    str(request.get("password", "")),
                    str(request.get("role", "guest")),
                )
            except ValueError as exc:
                return error(str(exc), "USER_ERROR")
            return ok("User created", user)

        if command == "DELETE_USER":
            if not self._is_allowed(command):
                return self._permission_denied(command)
            if not self._confirm_admin_password(str(request.get("admin_password", ""))):
                return error("Admin password confirmation failed", "ADMIN_CONFIRM_FAILED")
            username = str(request.get("username", ""))
            if self.user and username == self.user["username"]:
                return error("Admins cannot delete their own active account", "USER_ERROR")
            try:
                user = self.server.user_manager.delete_user(username)
            except ValueError as exc:
                return error(str(exc), "USER_ERROR")
            return ok("User deleted", user)

        if command == "GET_STATUS":
            device_id = str(request.get("device_id", ""))
            if not self._is_allowed(command, device_id):
                return self._permission_denied(command, device_id)
            try:
                return ok("Device status", self.server.device_manager.get_status(device_id))
            except DeviceError as exc:
                return error(str(exc), "DEVICE_ERROR")

        if command in {"TURN_ON", "TURN_OFF", "SET_BRIGHTNESS", "SET_TEMPERATURE", "SET_POSITION"}:
            device_id = str(request.get("device_id", ""))
            value = request.get("value")
            if not self._is_allowed(command, device_id):
                return self._permission_denied(command, device_id)
            try:
                state = self.server.device_manager.execute(device_id, command, value)
                return ok("Command executed", state)
            except (DeviceError, ValueError) as exc:
                return error(str(exc), "DEVICE_ERROR")

        return error(f"Unknown command: {command}", "UNKNOWN_COMMAND")

    def _is_allowed(self, command: str, device_id: Optional[str] = None) -> bool:
        role = self.user["role"] if self.user else ""
        device_type = None
        if device_id:
            try:
                device_type = self.server.device_manager.get_status(device_id)["type"]
            except Exception:
                device_type = None
        return self.server.permission_manager.can_execute(role, command, device_id, device_type)

    def _confirm_admin_password(self, password: str) -> bool:
        if not self.user or self.user.get("role") != "admin":
            return False
        return self.server.user_manager.authenticate(self.user["username"], password) is not None

    def _permission_denied(self, command: str, device_id: Optional[str] = None) -> Dict[str, Any]:
        self.logger.warning("Permission denied user=%s command=%s device=%s", self.user, command, device_id)
        return error("Permission denied", "PERMISSION_DENIED")
