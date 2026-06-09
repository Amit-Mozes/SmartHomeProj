"""Socket client for the smart-home server."""

from __future__ import annotations

import socket
import threading
from typing import Any, Dict, List, Optional

from smart_home_project.common.encryption import EncryptionManager
from smart_home_project.common.messages import decode_message, encode_message
from smart_home_project.common.protocol import Protocol


class SmartHomeClient:
    def __init__(self, host: str = "127.0.0.1", port: int = Protocol.PORT, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None
        self.protocol: Optional[Protocol] = None
        self.encryption = EncryptionManager.for_client()
        self._command_lock = threading.RLock()

    def connect(self) -> None:
        self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self.protocol = Protocol(self.sock)
        self._handshake()

    def close(self) -> None:
        with self._command_lock:
            try:
                if self.protocol and self.encryption.session:
                    self.send_command("EXIT")
            except Exception:
                pass
            if self.sock:
                self.sock.close()

    def abort(self) -> None:
        """Close the socket immediately without waiting for a pending command.

        This is used for the live-update connection, which may be blocked in a
        long-poll GET_UPDATES request. A graceful EXIT could wait for that
        request to return and freeze the GUI.
        """
        sock = self.sock
        self.protocol = None
        self.sock = None
        if not sock:
            return
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            sock.close()
        except OSError:
            pass

    def login(self, username: str, password: str) -> Dict[str, Any]:
        return self.send_command("LOGIN", username=username, password=password)

    def sign_up(self, username: str, password: str, role: str = "guest") -> Dict[str, Any]:
        return self.send_command("SIGN_UP", username=username, password=password, role=role)

    def ping(self) -> Dict[str, Any]:
        return self.send_command("PING")

    def list_devices(self) -> List[Dict[str, Any]]:
        response = self.send_command("LIST_DEVICES")
        if response.get("status") != "ok":
            raise RuntimeError(response.get("message", "Unable to list devices"))
        return response.get("data", [])

    def get_status(self, device_id: str) -> Dict[str, Any]:
        return self.send_command("GET_STATUS", device_id=device_id)

    def control_device(self, command: str, device_id: str, value: Any = None) -> Dict[str, Any]:
        return self.send_command(command, device_id=device_id, value=value)

    def demo_reset(self) -> Dict[str, Any]:
        return self.send_command("DEMO_RESET")

    def get_updates(self, since_revision: int, timeout: float = 25.0) -> Dict[str, Any]:
        if not self.sock:
            raise RuntimeError("Client is not connected")
        old_timeout = self.sock.gettimeout()
        self.sock.settimeout(timeout + 5.0)
        try:
            return self.send_command("GET_UPDATES", since_revision=since_revision, timeout=timeout)
        finally:
            self.sock.settimeout(old_timeout)

    def list_users(self) -> List[Dict[str, str]]:
        response = self.send_command("LIST_USERS")
        if response.get("status") != "ok":
            raise RuntimeError(response.get("message", "Unable to list users"))
        return response.get("data", [])

    def update_role(self, username: str, role: str, admin_password: str) -> Dict[str, Any]:
        return self.send_command("UPDATE_ROLE", username=username, role=role, admin_password=admin_password)

    def create_user(self, username: str, password: str, role: str, admin_password: str) -> Dict[str, Any]:
        return self.send_command(
            "CREATE_USER",
            username=username,
            password=password,
            role=role,
            admin_password=admin_password,
        )

    def delete_user(self, username: str, admin_password: str) -> Dict[str, Any]:
        return self.send_command("DELETE_USER", username=username, admin_password=admin_password)

    def send_command(self, command: str, **kwargs: Any) -> Dict[str, Any]:
        with self._command_lock:
            if not self.protocol:
                raise RuntimeError("Client is not connected")
            request = {"command": command}
            request.update(kwargs)
            self.protocol.send_msg(self.encryption.encrypt(encode_message(request)))
            response_payload = self.protocol.get_msg()
            if response_payload is None:
                raise RuntimeError("Server disconnected")
            return decode_message(self.encryption.decrypt(response_payload))

    def _handshake(self) -> None:
        if not self.protocol:
            raise RuntimeError("Client is not connected")
        server_key_payload = self.protocol.get_msg()
        if server_key_payload is None:
            raise RuntimeError("Server disconnected during handshake")
        server_key_message = decode_message(server_key_payload)
        if server_key_message.get("type") != "SERVER_PUBLIC_KEY":
            raise RuntimeError("Invalid server handshake")

        session_key = self.encryption.create_session_key()
        encrypted_key = self.encryption.encrypt_session_key_for_server(
            server_key_message["public_key"],
            session_key,
        )
        self.protocol.send_msg(encode_message({"type": "SESSION_KEY", "encrypted_key": encrypted_key}))

        ack_payload = self.protocol.get_msg()
        if ack_payload is None:
            raise RuntimeError("Server disconnected before handshake acknowledgement")
        ack = decode_message(ack_payload)
        if ack.get("type") != "HANDSHAKE_OK":
            raise RuntimeError("Encrypted handshake failed")
