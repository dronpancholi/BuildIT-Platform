"""
Input sanitization utilities.
Prevents XSS by stripping HTML tags from user input.
"""

import re

HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
SCRIPT_PATTERN = re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL)
SCRIPT_PATTERN_SINGLE = re.compile(r'<script[^>]*/>', re.IGNORECASE)
DANGEROUS_ATTRS = re.compile(r'\bon\w+\s*=', re.IGNORECASE)
JAVASCRIPT_PROTOCOL = re.compile(r'javascript:', re.IGNORECASE)


def sanitize_string(value: str) -> str:
    """Strip HTML tags and dangerous content from a string."""
    if not isinstance(value, str):
        return value

    value = SCRIPT_PATTERN.sub('', value)
    value = SCRIPT_PATTERN_SINGLE.sub('', value)
    value = HTML_TAG_PATTERN.sub('', value)
    value = DANGEROUS_ATTRS.sub('', value)
    value = JAVASCRIPT_PROTOCOL.sub('', value)

    import html
    value = html.unescape(value)

    return value.strip()


def sanitize_dict(data: dict) -> dict:
    """Sanitize all string values in a dictionary."""
    return {k: sanitize_string(v) if isinstance(v, str) else v for k, v in data.items()}
