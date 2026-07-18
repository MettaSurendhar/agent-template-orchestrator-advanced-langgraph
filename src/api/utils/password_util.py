"""Simple password hashing using PBKDF2-HMAC (stdlib only, no extra dependency)."""

import hashlib
import os

_ITERATIONS = 260_000


def hash_password(password: str) -> tuple[str, str]:
    """Return (password_hash, salt), both hex-encoded."""
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _ITERATIONS)
    return digest.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Check a plaintext password against a stored hash + salt."""
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _ITERATIONS)
    return digest.hex() == password_hash
