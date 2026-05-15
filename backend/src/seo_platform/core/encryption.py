"""
SEO Platform — Field-Level Encryption & Security
===================================================
Enforces AES-256-GCM encryption for sensitive fields at rest (e.g., provider API keys).
In a production AWS environment, this integrates with AWS KMS for key management
and envelope encryption.
"""

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

class EncryptionService:
    """
    Handles cryptographic operations for sensitive tenant data.
    Ensures that OAuth tokens, API keys, and PII are never stored in plaintext
    in the PostgreSQL database.
    """

    def __init__(self):
        # In production, this would be fetched from AWS Secrets Manager or KMS Data Key
        key_b64 = os.getenv("ENCRYPTION_MASTER_KEY", "bW9ja19tYXN0ZXJfa2V5XzMyX2J5dGVzX2xvbmdfc3RyaW5n")
        try:
            self._key = base64.b64decode(key_b64)
            if len(self._key) not in (16, 24, 32):
                # Fallback for dev
                self._key = os.urandom(32)
        except Exception:
            self._key = os.urandom(32)

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
