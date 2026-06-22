"""
SEO Platform — Multilingual Email Reader (v2)
==============================================
Extended email reader with multi-language verification detection.
Searches for verification emails using language-appropriate subject patterns.
"""

from __future__ import annotations

import email
import imaplib
import json
import re
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from pathlib import Path
from typing import Any

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

# Path to email patterns file
EMAIL_PATTERNS_PATH = Path(__file__).parent.parent.parent.parent / "data" / "email_patterns.json"

# Common verification link patterns across languages
COMMON_LINK_PATTERNS = [
    r"verify", r"confirm", r"activate", r"validieren", r"bestätigen",
    r"aktivieren", r"vérifier", r"confirmer", r"valider", r"verificar",
    r"confirmar", r"verificar", r"確認", r"認証", r"인증", r"확인",
    r"verifizieren", r"verificar", r"verifica", r"verificatie",
]


class MultilingualEmailReader:
    """
    Extended email reader with multi-language verification detection.

    Supports:
    - Multi-language subject pattern matching
    - Language-aware sender domain matching
    - Automatic language detection from email content
    """

    def __init__(
        self,
        imap_host: str = "localhost",
        imap_port: int = 143,
        username: str = "",
        password: str = "",
        use_ssl: bool = False,
    ):
        self.imap_host = imap_host
        self.imap_port = imap_port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.patterns = self._load_patterns()
        self._connection: imaplib.IMAP4 | None = None

    def _load_patterns(self) -> dict[str, Any]:
        """Load email patterns from JSON file."""
        try:
            if EMAIL_PATTERNS_PATH.exists():
                with open(EMAIL_PATTERNS_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load email patterns: {e}")
        return {}

    def get_site_pattern(self, site_slug: str) -> dict[str, Any] | None:
        """Get email pattern for a specific site."""
        return self.patterns.get(site_slug)

    def connect(self) -> bool:
        """Connect to IMAP server."""
        try:
            if self.use_ssl:
                self._connection = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            else:
                self._connection = imaplib.IMAP4(self.imap_host, self.imap_port)
            self._connection.login(self.username, self.password)
            return True
        except Exception as e:
            logger.error(f"IMAP connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from IMAP server."""
        if self._connection:
            try:
                self._connection.logout()
            except Exception:
                pass
            self._connection = None

    def search_verification_email(
        self,
        sender_domains: list[str] | None = None,
        subject_patterns: dict[str, list[str]] | list[str] | None = None,
        after_timestamp: datetime | None = None,
        mailbox: str = "INBOX",
    ) -> dict[str, Any] | None:
        """
        Search for verification email.

        Args:
            sender_domains: List of sender domains to match (e.g., ["yelp.com"])
            subject_patterns: Subject patterns to match. Can be:
                - Dict of {language: [patterns]} for multi-language search
                - List of patterns for single-language search
            after_timestamp: Only search emails after this time
            mailbox: IMAP mailbox to search

        Returns:
            Dict with email info or None if not found
        """
        if not self._connection:
            if not self.connect():
                return None

        try:
            self._connection.select(mailbox)

            # Build search criteria
            criteria_parts = []

            # Sender domain filter
            if sender_domains:
                sender_queries = []
                for domain in sender_domains:
                    sender_queries.append(f'(FROM "*@{domain}")')
                    sender_queries.append(f'(FROM "*@{domain}")')
                if len(sender_queries) == 1:
                    criteria_parts.append(sender_queries[0])
                else:
                    criteria_parts.append(f'(OR {" ".join(sender_queries)})')

            # Time filter
            if after_timestamp:
                date_str = after_timestamp.strftime("%d-%b-%Y")
                criteria_parts.append(f'(SINCE "{date_str}")')

            # Combine criteria
            if criteria_parts:
                search_criteria = f'({" ".join(criteria_parts)})'
            else:
                search_criteria = "ALL"

            # Search
            status, message_ids = self._connection.search(None, search_criteria)
            if status != "OK":
                return None

            ids = message_ids[0].split()
            if not ids:
                return None

            # Search through messages (newest first)
            for msg_id in reversed(ids[-50:]):  # Check last 50 messages
                result = self._process_message(msg_id, subject_patterns)
                if result:
                    return result

            return None

        except Exception as e:
            logger.error(f"Email search failed: {e}")
            return None

    def _process_message(
        self,
        msg_id: bytes,
        subject_patterns: dict[str, list[str]] | list[str] | None,
    ) -> dict[str, Any] | None:
        """Process a single email message."""
        try:
            status, data = self._connection.fetch(msg_id, "(RFC822)")
            if status != "OK":
                return None

            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Decode subject
            subject = self._decode_header(msg.get("Subject", ""))

            # Check subject patterns
            if subject_patterns:
                matched = False
                detected_language = "en"

                if isinstance(subject_patterns, dict):
                    # Multi-language patterns: {language: [patterns]}
                    for language, patterns in subject_patterns.items():
                        if self._matches_patterns(subject, patterns):
                            matched = True
                            detected_language = language
                            break
                elif isinstance(subject_patterns, list):
                    # Single language patterns
                    matched = self._matches_patterns(subject, subject_patterns)

                if not matched:
                    return None
            else:
                detected_language = "en"

            # Extract sender
            from_header = msg.get("From", "")
            sender_email = self._extract_email(from_header)

            # Extract body and links
            body = self._get_body(msg)
            links = self._extract_links(body)

            # Find verification link
            verification_link = self._find_verification_link(links)

            return {
                "message_id": msg_id.decode(),
                "subject": subject,
                "from": from_header,
                "sender_email": sender_email,
                "date": msg.get("Date", ""),
                "body_preview": body[:500] if body else "",
                "links": links,
                "verification_link": verification_link,
                "detected_language": detected_language,
                "has_verification_link": verification_link is not None,
            }

        except Exception as e:
            logger.debug(f"Failed to process message {msg_id}: {e}")
            return None

    def _decode_header(self, header: str) -> str:
        """Decode email header with proper encoding."""
        if not header:
            return ""

        decoded_parts = decode_header(header)
        result = []
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                result.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                result.append(part)
        return " ".join(result)

    def _matches_patterns(self, text: str, patterns: list[str]) -> bool:
        """Check if text matches any of the given patterns."""
        text_lower = text.lower()
        for pattern in patterns:
            if pattern.lower() in text_lower:
                return True
        return False

    def _extract_email(self, from_header: str) -> str:
        """Extract email address from From header."""
        match = re.search(r"<([^>]+)>", from_header)
        if match:
            return match.group(1)
        match = re.search(r"[\w.-]+@[\w.-]+", from_header)
        if match:
            return match.group(0)
        return ""

    def _get_body(self, msg: email.message.Message) -> str:
        """Extract text body from email message."""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        return payload.decode(charset, errors="replace")
                elif content_type == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        html = payload.decode(charset, errors="replace")
                        # Strip HTML tags for plain text
                        return re.sub(r"<[^>]+>", " ", html)
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        return ""

    def _extract_links(self, body: str) -> list[str]:
        """Extract all URLs from email body."""
        url_pattern = r'https?://[^\s<>"\')\]]+'
        return re.findall(url_pattern, body)

    def _find_verification_link(self, links: list[str]) -> str | None:
        """Find the most likely verification link from a list of URLs."""
        for link in links:
            link_lower = link.lower()
            for pattern in COMMON_LINK_PATTERNS:
                if pattern in link_lower:
                    return link
        return None

    def search_all_languages(
        self,
        site_slug: str,
        sender_domains: list[str] | None = None,
        after_timestamp: datetime | None = None,
    ) -> dict[str, Any] | None:
        """
        Search for verification email trying all language variants.
        Uses the site pattern from email_patterns.json.
        """
        site_pattern = self.get_site_pattern(site_slug)
        if not site_pattern:
            logger.warning(f"No email pattern found for site: {site_slug}")
            return None

        # Get sender domains from pattern
        if not sender_domains:
            sender_domains = site_pattern.get("verification_sender", [])

        # Get subject patterns (may be multi-language)
        subject_patterns = site_pattern.get("subject_patterns", {})

        # Search
        return self.search_verification_email(
            sender_domains=sender_domains,
            subject_patterns=subject_patterns,
            after_timestamp=after_timestamp,
        )
