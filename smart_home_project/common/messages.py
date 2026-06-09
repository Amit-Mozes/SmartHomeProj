"""JSON message utilities used by client and server."""

from __future__ import annotations

import json
from typing import Any, Dict


def encode_message(message: Dict[str, Any]) -> bytes:
    return json.dumps(message, separators=(",", ":"), sort_keys=True).encode("utf-8")


def decode_message(payload: bytes) -> Dict[str, Any]:
    try:
        message = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid JSON message") from exc
    if not isinstance(message, dict):
        raise ValueError("JSON message must be an object")
    return message


def ok(message: str, data: Any = None) -> Dict[str, Any]:
    return {"status": "ok", "message": message, "data": data}


def error(message: str, code: str = "ERROR", data: Any = None) -> Dict[str, Any]:
    return {"status": "error", "code": code, "message": message, "data": data}
