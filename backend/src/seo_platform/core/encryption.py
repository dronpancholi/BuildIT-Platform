"""
SEO Platform — Field-Level Encryption & Security
===================================================
Enforces AES-256-GCM encryption for sensitive fields at rest (e.g., provider API keys).
In a production AWS environment, this integrates with AWS KMS for key management
and envelope encryption.
"""

import base64
import math
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

# Well-known weak keys that MUST NEVER be used in production.
_FORBIDDEN_KEYS = frozenset({
    "bW9ja19tYXN0ZXJfa2V5XzMyX2J5dGVzX2xvbmdfc3RyaW5n",  # mock_master_key_32_bytes_long_string
    "",
    "dev",
    "development",
    "test",
    "changeme",
})


def _shannon_entropy(data: bytes) -> float:
    """Compute Shannon entropy in bits/byte. Strong keys have >= 4.5 bits/byte."""
    if not data:
        return 0.0
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in counts if c > 0)


def validate_encryption_key(key_b64: str | None = None) -> tuple[bool, str]:
    """
    Validate a base64-encoded 256-bit encryption key. Alias of
    validate_encryption_key_entropy that accepts an explicit key for testability.

    Returns (is_valid, message).
    """
    if key_b64 is None:
        return validate_encryption_key_entropy()
    if not key_b64:
        return False, "ENCRYPTION_MASTER_KEY environment variable is not set"
    if key_b64 in _FORBIDDEN_KEYS:
        return False, f"ENCRYPTION_MASTER_KEY is a well-known weak key (forbidden: {key_b64[:20]}...)"
    try:
        raw = base64.b64decode(key_b64)
    except Exception as e:
        return False, f"ENCRYPTION_MASTER_KEY is not valid base64: {e}"
    if len(raw) != 32:
        return False, f"ENCRYPTION_MASTER_KEY must decode to 32 bytes (got {len(raw)})"
    entropy = _shannon_entropy(raw)
    if entropy < 4.5:
        return False, f"ENCRYPTION_MASTER_KEY has insufficient entropy ({entropy:.2f} bits/byte, need >= 4.5)"
    return True, "ok"


def validate_encryption_key_entropy() -> tuple[bool, str]:
    """
    Validate the ENCRYPTION_MASTER_KEY environment variable.

    Returns (is_valid, message). A key is valid if it is:
    - present in env
    - not a well-known weak key
    - base64-decodes to 32 bytes (256 bits)
    - has Shannon entropy >= 4.5 bits/byte (i.e. not repetitive)
    """
    key_b64 = os.getenv("ENCRYPTION_MASTER_KEY", "")
    if not key_b64:
        return False, "ENCRYPTION_MASTER_KEY environment variable is not set"
    if key_b64 in _FORBIDDEN_KEYS:
        return False, f"ENCRYPTION_MASTER_KEY is a well-known weak key (forbidden: {key_b64[:20]}...)"
    try:
        raw = base64.b64decode(key_b64)
    except Exception as e:
        return False, f"ENCRYPTION_MASTER_KEY is not valid base64: {e}"
    if len(raw) != 32:
        return False, f"ENCRYPTION_MASTER_KEY must decode to 32 bytes (got {len(raw)})"
    entropy = _shannon_entropy(raw)
    if entropy < 4.5:
        return False, f"ENCRYPTION_MASTER_KEY has insufficient entropy ({entropy:.2f} bits/byte, need >= 4.5)"
    return True, "ok"


class EncryptionService:
    """
    Handles cryptographic operations for sensitive tenant data.
    Ensures that OAuth tokens, API keys, and PII are never stored in plaintext
    in the PostgreSQL database.
    """

    def __init__(self):
        is_valid, msg = validate_encryption_key_entropy()
        if not is_valid:
            # In production, fail fast. In dev, fall back to a random per-process key
            # so unencrypted local development still works without leaking plaintext.
            from seo_platform.config import get_settings
            settings = get_settings()
            if settings.is_production:
                raise RuntimeError(f"Encryption key validation failed: {msg}")
            logger.warning("encryption_key_weak_in_dev", message=msg)
            self._key = os.urandom(32)
        else:
            key_b64 = os.environ["ENCRYPTION_MASTER_KEY"]
            self._key = base64.b64decode(key_b64)

        self._aesgcm = AESGCM(self._key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypts a string using AES-256-GCM and returns base64 string."""
        if not plaintext:
            return plaintext

        nonce = os.urandom(12)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        # Prepend nonce to ciphertext and b64 encode
        return base64.b64encode(nonce + ciphertext).decode("utf-8")

    def decrypt(self, encrypted_b64: str) -> str:
        """Decrypts a base64 string using AES-256-GCM."""
        if not encrypted_b64:
            return encrypted_b64

        try:
            data = base64.b64decode(encrypted_b64)
            nonce = data[:12]
            ciphertext = data[12:]
            plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode("utf-8")
        except Exception as e:
            logger.error("decryption_failed", error=str(e))
            raise ValueError("Failed to decrypt sensitive field")

encryption_service = EncryptionService()
