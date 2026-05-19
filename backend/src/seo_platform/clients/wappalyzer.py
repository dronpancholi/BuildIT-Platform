"""
SEO Platform — Wappalyzer Technology Profiler
=================================================
Regex-based technology detection for publisher domains.
"""

from __future__ import annotations

import re

TECH_PATTERNS: dict[str, list[str]] = {
    "WordPress": [
        r"wp-content",
        r"wp-includes",
        r'meta name="generator" content="WordPress',
    ],
    "Shopify": [
        r"cdn\.shopify\.com",
        r"shopify-payment-button",
        r"/cdn/shop/",
    ],
    "Webflow": [
        r"data-wf-page",
        r"uploads-ssl\.webflow\.com",
    ],
    "Ghost": [
        r"ghost/core",
        r"data-ghost-*",
        r"<meta name=\"generator\" content=\"Ghost",
    ],
    "Wix": [
        r"/_api/",
        r"wix\.com",
        r"static\.parastorage\.com",
    ],
    "Drupal": [
        r"/sites/default/files/",
        r"Drupal\.settings",
    ],
    "Next.js": [
        r"__NEXT_DATA__",
        r"/_next/static/",
    ],
    "Nuxt.js": [
        r"__NUXT__",
        r"/_nuxt/",
    ],
    "Google Analytics": [
        r"googletagmanager\.com/gtag/js",
        r"ga\('create'",
        r"gtag\('config'",
    ],
    "Cloudflare": [
        r"__cfruid",
        r"cloudflare-static",
        r"cf-ray",
    ],
    "Disqus": [
        r"disqus\.com/embed\.js",
        r"disqus_thread",
    ],
    "HubSpot": [
        r"js\.hs-scripts\.com",
        r"hs-analytics",
        r"hubspot",
    ],
    "Hotjar": [
        r"hotjar\.com",
        r"hj-",
    ],
    "Mailchimp": [
        r"mailchimp\.com",
        r"list-manage\.com",
    ],
    "Stripe": [
        r"stripe\.com/billing",
        r"js\.stripe\.com",
    ],
}


class WappalyzerProfiler:
    """
    Scans HTML source code to identify technology stacks and platforms.
    """

    @staticmethod
    def detect_technologies(html: str) -> list[str]:
        detected: list[str] = []
        for tech, patterns in TECH_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, html, re.IGNORECASE):
                    detected.append(tech)
                    break
        return detected
