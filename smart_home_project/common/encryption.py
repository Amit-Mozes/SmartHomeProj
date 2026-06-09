"""Encryption helpers for the socket protocol.

Handshake flow:
1. The server creates an RSA key pair when it starts.
2. A newly connected client asks for the server public key.
3. The client generates a Fernet symmetric key and encrypts it with RSA-OAEP.
4. The server decrypts that symmetric key with its RSA private key.
5. All later protocol payloads are Fernet-encrypted JSON bytes.

If the optional cryptography package is unavailable, EncryptionUnavailableError
is raised. The system intentionally does not fall back to fake encryption.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Optional


class EncryptionUnavailableError(RuntimeError):
    """Raised when cryptography is not installed."""


try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
except ImportError:  # pragma: no cover - depends on optional environment
    Fernet = None
    InvalidToken = Exception
    hashes = None
    serialization = None
    padding = None
    rsa = None


def _require_crypto() -> None:
    if Fernet is None:
        raise EncryptionUnavailableError(
            "The 'cryptography' package is required. Install dependencies with "
            "'pip install -r requirements.txt'."
        )


@dataclass
class EncryptedSession:
    """A symmetric encryption session used after the RSA handshake."""

    key: bytes

    def __post_init__(self) -> None:
        _require_crypto()
        self._fernet = Fernet(self.key)

    def encrypt(self, payload: bytes) -> bytes:
        return self._fernet.encrypt(payload)

    def decrypt(self, token: bytes) -> bytes:
        try:
            return self._fernet.decrypt(token)
        except InvalidToken as exc:
            raise ValueError("Invalid encrypted payload") from exc


class EncryptionManager:
    """Owns RSA key exchange and symmetric encryption helpers."""

    def __init__(self, private_key=None, session: Optional[EncryptedSession] = None):
        _require_crypto()
        self.private_key = private_key
        self.session = session

    @classmethod
    def for_server(cls) -> "EncryptionManager":
        _require_crypto()
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        return cls(private_key=private_key)

    @classmethod
    def for_client(cls) -> "EncryptionManager":
        _require_crypto()
        return cls()

    def public_key_pem(self) -> str:
        if self.private_key is None:
            raise ValueError("Only server managers have a public key")
        pem = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return pem.decode("ascii")

    def create_session_key(self) -> bytes:
        key = Fernet.generate_key()
        self.session = EncryptedSession(key)
        return key

    def encrypt_session_key_for_server(self, public_key_pem: str, session_key: bytes) -> str:
        public_key = serialization.load_pem_public_key(public_key_pem.encode("ascii"))
        encrypted = public_key.encrypt(
            session_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return base64.b64encode(encrypted).decode("ascii")

    def accept_encrypted_session_key(self, encrypted_key_b64: str) -> None:
        if self.private_key is None:
            raise ValueError("Server private key is required")
        encrypted_key = base64.b64decode(encrypted_key_b64.encode("ascii"))
        session_key = self.private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        self.session = EncryptedSession(session_key)

    def encrypt(self, payload: bytes) -> bytes:
        if self.session is None:
            raise ValueError("Encrypted session is not established")
        return self.session.encrypt(payload)

    def decrypt(self, token: bytes) -> bytes:
        if self.session is None:
            raise ValueError("Encrypted session is not established")
        return self.session.decrypt(token)
