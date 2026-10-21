"""Per-launch bearer tokens (ADR-0011). Only a token's SHA-256 is ever stored."""

import hashlib
import secrets


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()
