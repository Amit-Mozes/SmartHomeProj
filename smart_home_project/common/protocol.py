"""Length-prefixed socket protocol.

Each transmitted frame is:
    10 ASCII digits containing the payload byte length, followed by payload bytes.

The class deliberately does not assume that socket.recv(n) returns n bytes.
It can transport plain JSON bytes or encrypted token bytes.
"""

from __future__ import annotations

import socket
from typing import Optional, Union


class ProtocolError(Exception):
    """Raised when a received frame is malformed."""


class SocketDisconnected(Exception):
    """Raised when the peer closes the connection."""


class Protocol:
    LENGTH_FIELD_SIZE = 10
    PORT = 8820
    MAX_PAYLOAD_SIZE = 10_000_000

    def __init__(self, sock: socket.socket):
        self.sock = sock

    def create_msg(self, data: Union[str, bytes, bytearray]) -> bytes:
        """Create a length-prefixed message from text or bytes."""
        if isinstance(data, str):
            payload = data.encode("utf-8")
        elif isinstance(data, bytearray):
            payload = bytes(data)
        elif isinstance(data, bytes):
            payload = data
        else:
            raise TypeError("Protocol messages must be str or bytes")

        payload_length = len(payload)
        if payload_length > self.MAX_PAYLOAD_SIZE:
            raise ProtocolError("Payload too large")

        length_field = str(payload_length).zfill(self.LENGTH_FIELD_SIZE).encode("ascii")
        if len(length_field) != self.LENGTH_FIELD_SIZE:
            raise ProtocolError("Payload length does not fit in length field")
        return length_field + payload

    def send_msg(self, data: Union[str, bytes, bytearray]) -> None:
        """Send a complete message frame."""
        self.sock.sendall(self.create_msg(data))

    def get_msg(self) -> Optional[bytes]:
        """Receive one complete payload.

        Returns:
            Payload bytes, or None when the peer disconnects cleanly before a new
            frame starts.

        Raises:
            SocketDisconnected: if the peer disconnects mid-frame.
            ProtocolError: if the length field is invalid.
        """
        length_field = self.recv_exact(self.LENGTH_FIELD_SIZE, allow_empty=True)
        if length_field is None:
            return None

        if not length_field.isdigit():
            raise ProtocolError("Invalid length field")

        payload_length = int(length_field.decode("ascii"))
        if payload_length < 0 or payload_length > self.MAX_PAYLOAD_SIZE:
            raise ProtocolError("Invalid payload length")

        if payload_length == 0:
            return b""
        return self.recv_exact(payload_length, allow_empty=False)

    def get_text_msg(self) -> Optional[str]:
        """Receive one UTF-8 text payload."""
        payload = self.get_msg()
        if payload is None:
            return None
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ProtocolError("Payload is not valid UTF-8") from exc

    def recv_exact(self, n: int, allow_empty: bool = False) -> Optional[bytes]:
        """Receive exactly n bytes, handling partial receives."""
        chunks = bytearray()
        while len(chunks) < n:
            try:
                chunk = self.sock.recv(n - len(chunks))
            except (ConnectionResetError, ConnectionAbortedError) as exc:
                raise SocketDisconnected("Socket connection was reset") from exc

            if chunk == b"":
                if allow_empty and not chunks:
                    return None
                raise SocketDisconnected("Socket disconnected while receiving data")
            chunks.extend(chunk)
        return bytes(chunks)
