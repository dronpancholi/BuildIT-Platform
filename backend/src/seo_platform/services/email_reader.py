"""
SEO Platform — Email Reader
============================
IMAP email reader for verification workflows.
Searches inbox for verification emails and extracts confirmation links.
"""

from __future__ import annotations

import email
import imaplib
import re
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.header import decode_header
from email.message import Message
from typing import Any, Optional

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

# Common verification link patterns
VERIFICATION_PATTERNS = [
    r"https?://[^\s<>\"']+/verify/[a-zA-Z0-9_\-]+",
    r"https?://[^\s<>\"']+/confirm/[a-zA-Z0-9_\-]+",
    r"https?://[^\s<>\"']+/activate/[a-zA-Z0-9_\-]+",
    r"https?://[^\s<>\"']+/register/confirm/[a-zA-Z0-9_\-]+",
    r"https?://[^\s<>\"']+/email/verify/[a-zA-Z0-9_\-]+",
    r"https?://[^\s<>\"']+/email/confirm/[a-zA-Z0-9_\-]+",
    r"https?://[^\s<>\"']+/verify_email/[a-zA-Z0-9_\-]+",
    r"https?://[^\s<>\"']+/account/verify/[a-zA-Z0-9_\-]+",
    r"https?://[^\s<>\"']+/account/confirm/[a-zA-Z0-9_\-]+",
    r"https?://[^\s<>\"']+/users/verify_email\?[^\s<>\"']+",
    r"https?://[^\s<>\"']+/confirmemail\.php\?[^\s<>\"']+",
    r"https?://[^\s<>\"']+/signup/confirm/[a-zA-Z0-9_\-]+",
]

# IMAP provider configurations
IMAP_PROVIDERS = {
    "gmail": {
        "host": "imap.gmail.com",
        "port": 993,
        "use_ssl": True,
    },
    "outlook": {
        "host": "outlook.office365.com",
        "port": 993,
        "use_ssl": True,
    },
    "yahoo": {
        "host": "imap.mail.yahoo.com",
        "port": 993,
        "use_ssl": True,
    },
    "custom": {
        "host": "",
        "port": 993,
        "use_ssl": True,
    },
}


@dataclass
class EmailMessage:
    """Parsed email message."""
    uid: str
    from_address: str
    from_name: str
    subject: str
    date: datetime
    body_text: str
    body_html: str
    verification_links: list[str] = field(default_factory=list)
    raw_headers: dict[str, str] = field(default_factory=dict)


@dataclass
class VerificationEmail:
    """Email that contains verification links."""
    email: EmailMessage
    links: list[str]
    matched_pattern: str


def _decode_header_value(value: str | None) -> str:
    """Decode email header value (handles encoded words)."""
    if not value:
        return ""
    decoded_parts = decode_header(value)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def _extract_text_body(msg: Message) -> tuple[str, str]:
    """Extract plain text and HTML body from email message."""
    text_body = ""
    html_body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))

            if "attachment" in disposition:
                continue

            payload = part.get_payload(decode=True)
            if payload is None:
                continue

            charset = part.get_content_charset() or "utf-8"

            if content_type == "text/plain":
                text_body = payload.decode(charset, errors="replace")
            elif content_type == "text/html":
                html_body = payload.decode(charset, errors="replace")
    else:
        content_type = msg.get_content_type()
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            decoded = payload.decode(charset, errors="replace")
            if content_type == "text/plain":
                text_body = decoded
            elif content_type == "text/html":
                html_body = decoded

    return text_body, html_body


def _extract_links_from_html(html: str) -> list[str]:
    """Extract all URLs from HTML content."""
    url_pattern = r'href=["\']([^"\']+)["\']'
    urls = re.findall(url_pattern, html, re.IGNORECASE)
    return urls


def _extract_links_from_text(text: str) -> list[str]:
    """Extract all URLs from plain text content."""
    url_pattern = r'https?://[^\s<>\"\'\)]+'
    return re.findall(url_pattern, text)


def _is_verification_link(url: str, patterns: list[str] | None = None) -> bool:
    """Check if a URL matches verification link patterns."""
    check_patterns = patterns or VERIFICATION_PATTERNS
    for pattern in check_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False


class EmailReader:
    """
    Reads emails from IMAP inbox for verification workflows.

    Supports:
    - Multiple IMAP providers (Gmail, Outlook, custom)
    - Subject/body search
    - HTML and plain text parsing
    - Verification link extraction
    """

    def __init__(
        self,
        imap_host: str,
        email_address: str,
        password: str,
        port: int = 993,
        use_ssl: bool = True,
    ):
        self.host = imap_host
        self.email = email_address
        self.password = password
        self.port = port
        self.use_ssl = use_ssl
        self._connection: imaplib.IMAP4_SSL | imaplib.IMAP4 | None = None

    @classmethod
    def from_provider(
        cls,
        provider: str,
        email_address: str,
        password: str,
    ) -> EmailReader:
        """Create reader from known provider name."""
        config = IMAP_PROVIDERS.get(provider, IMAP_PROVIDERS["custom"])
        return cls(
            imap_host=config["host"],
            email_address=email_address,
            password=password,
            port=config["port"],
            use_ssl=config["use_ssl"],
        )

    def connect(self) -> bool:
        """Connect to IMAP server."""
        try:
            if self.use_ssl:
                self._connection = imaplib.IMAP4_SSL(self.host, self.port)
            else:
                self._connection = imaplib.IMAP4(self.host, self.port)

            self._connection.login(self.email, self.password)
            logger.info("imap_connected", host=self.host, email=self.email)
            return True

        except imaplib.IMAP4.error as e:
            logger.error("imap_auth_failed", error=str(e), host=self.host)
            return False
        except Exception as e:
            logger.error("imap_connect_failed", error=str(e), host=self.host)
            return False

    def disconnect(self) -> None:
        """Disconnect from IMAP server."""
        if self._connection:
            try:
                self._connection.logout()
            except Exception:
                pass
            self._connection = None

    def _ensure_connected(self) -> bool:
        """Ensure we have an active connection."""
        if self._connection is None:
            return self.connect()
        try:
            self._connection.noop()
            return True
        except Exception:
            return self.connect()

    def search_emails(
        self,
        folder: str = "INBOX",
        sender_filter: str | None = None,
        subject_filter: str | None = None,
        since: datetime | None = None,
        before: datetime | None = None,
        unseen_only: bool = False,
        limit: int = 10,
    ) -> list[EmailMessage]:
        """Search for emails matching criteria."""
        if not self._ensure_connected():
            return []

        try:
            self._connection.select(folder, readonly=True)

            # Build search criteria
            criteria = []
            if sender_filter:
                criteria.append(f'FROM "{sender_filter}"')
            if subject_filter:
                criteria.append(f'SUBJECT "{subject_filter}"')
            if since:
                criteria.append(f'SINCE {since.strftime("%d-%b-%Y")}')
            if before:
                criteria.append(f'BEFORE {before.strftime("%d-%b-%Y")}')
            if unseen_only:
                criteria.append("UNSEEN")

            search_str = " ".join(criteria) if criteria else "ALL"
            status, data = self._connection.search(None, search_str)

            if status != "OK":
                return []

            # Get message IDs (limit to most recent)
            msg_ids = data[0].split()
            if limit:
                msg_ids = msg_ids[-limit:]

            emails = []
            for msg_id in reversed(msg_ids):  # Most recent first
                email_msg = self._fetch_email(msg_id)
                if email_msg:
                    emails.append(email_msg)

            return emails

        except Exception as e:
            logger.error("email_search_failed", error=str(e))
            return []

    def _fetch_email(self, msg_id: bytes) -> EmailMessage | None:
        """Fetch a single email by ID."""
        try:
            status, data = self._connection.fetch(msg_id, "(RFC822)")
            if status != "OK":
                return None

            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Parse body
            text_body, html_body = _extract_text_body(msg)

            # Extract verification links
            all_links = []
            all_links.extend(_extract_links_from_html(html_body))
            all_links.extend(_extract_links_from_text(text_body))
            verification_links = [link for link in all_links if _is_verification_link(link)]

            # Parse date
            date_str = msg.get("Date", "")
            try:
                date_tuple = email.utils.parsedate_to_datetime(date_str)
            except Exception:
                date_tuple = datetime.now()

            return EmailMessage(
                uid=msg_id.decode(),
                from_address=msg.get("From", ""),
                from_name=_decode_header_value(msg.get("From", "")),
                subject=_decode_header_value(msg.get("Subject", "")),
                date=date_tuple,
                body_text=text_body,
                body_html=html_body,
                verification_links=verification_links,
                raw_headers={
                    "message-id": msg.get("Message-ID", ""),
                    "in-reply-to": msg.get("In-Reply-To", ""),
                },
            )

        except Exception as e:
            logger.error("email_fetch_failed", msg_id=msg_id, error=str(e))
            return None

    def search_verification_emails(
        self,
        sender_domains: list[str],
        subject_patterns: list[str],
        after_timestamp: datetime | None = None,
        folder: str = "INBOX",
    ) -> list[VerificationEmail]:
        """
        Search for verification emails from specific senders.

        Args:
            sender_domains: List of sender domains to match (e.g., ["truelocal.com.au"])
            subject_patterns: Subject line patterns (e.g., ["verify", "confirm"])
            after_timestamp: Only look for emails after this time
            folder: IMAP folder to search

        Returns:
            List of VerificationEmail objects with extracted links
        """
        results = []

        for domain in sender_domains:
            # Search by sender domain
            emails = self.search_emails(
                folder=folder,
                sender_filter=f"@{domain}",
                since=after_timestamp,
                limit=5,
            )

            for email_msg in emails:
                # Check subject patterns
                subject_lower = email_msg.subject.lower()
                matches_pattern = any(
                    pat.lower() in subject_lower for pat in subject_patterns
                )

                if matches_pattern and email_msg.verification_links:
                    results.append(VerificationEmail(
                        email=email_msg,
                        links=email_msg.verification_links,
                        matched_pattern=next(
                            (p for p in subject_patterns if p.lower() in subject_lower),
                            subject_patterns[0],
                        ),
                    ))

        # Sort by date (most recent first)
        results.sort(key=lambda x: x.email.date, reverse=True)
        return results

    def get_latest_verification_link(
        self,
        sender_domains: list[str],
        subject_patterns: list[str],
        after_timestamp: datetime | None = None,
    ) -> str | None:
        """Get the most recent verification link."""
        results = self.search_verification_emails(
            sender_domains=sender_domains,
            subject_patterns=subject_patterns,
            after_timestamp=after_timestamp,
        )

        if results and results[0].links:
            return results[0].links[0]

        return None

    def check_inbox_preview(
        self,
        folder: str = "INBOX",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get a preview of recent emails (for UI display)."""
        emails = self.search_emails(folder=folder, limit=limit)
        return [
            {
                "uid": e.uid,
                "from": e.from_address,
                "subject": e.subject,
                "date": e.date.isoformat(),
                "has_verification_links": bool(e.verification_links),
                "link_count": len(e.verification_links),
            }
            for e in emails
        ]
