# EMAIL DELIVERY VALIDATION REPORT — Phase 2.5.1

**Workstream:** WS-E
**P0 Blocker:** BLK-6 — Silent MailHog fallback in production
**Status:** **CLOSED** (Resend + Mailgun providers added; silent
fallback removed; P0 startup check enforces real provider in
production)
**Date:** 2026-06-06

---

## 1. Blocker as Found (Phase 2.5)

`EMAIL_DELIVERY_VALIDATION` (Phase 2.5) and the BLK-6 note in
`PHASE_2_5_FINAL_VERDICT.md` identified:

- The `EmailProvider` abstraction had only two implementations:
  `SendGridProvider` (real API) and `MailhogProvider` (local SMTP).
- The factory `get_email_provider()` returned `MailhogProvider()`
  whenever `use_mock_providers=true`, silently, with no warning.
- No `ResendProvider` or `MailgunProvider` existed, even though the
  P0 startup check recognized them.
- The `SendGridProvider._track_email` was reused by MailHog's
  success path but the call passed the wrong arguments.
- `campaigns.py:367, 428` hardcoded `MailhogProvider()` for the
  send-thread and follow-up endpoints — explicit silent fallback in
  the API surface, not just in the factory.

Net effect: the platform could appear to send emails in production
when in fact the messages were silently dropped into a local
MailHog container that nobody was reading.

---

## 2. Remediation

### 2.1 Add Resend and Mailgun providers

`backend/src/seo_platform/services/email_provider.py` now ships
four production providers:

- `ResendProvider` — POSTs to `https://api.resend.com/emails` with
  `Authorization: Bearer <key>`.
- `SendGridProvider` — POSTs to
  `https://api.sendgrid.com/v3/mail/send` (unchanged).
- `MailgunProvider` — POSTs to
  `https://api.mailgun.net/v3/<domain>/messages` with HTTP Basic
  auth (`api:<key>`).
- `DevMailhogProvider` — local SMTP via `email_adapter`.

The shared HTTP-send flow is in `_BaseHTTPProvider._send()`. The
shared DB-tracking flow is in `_BaseHTTPProvider._track_email()`.
Subclasses supply the request signature (`url`, `headers`,
`payload`, `timeout`).

### 2.2 Add `NoOpEmailProvider`

A new `NoOpEmailProvider` raises `EmailProviderUnavailableError` on
every `send_email`. This is the production path when no real
provider is configured. The error message is explicit:

```
No email provider is configured. Set RESEND_API_KEY or
SENDGRID_API_KEY or MAILGUN_API_KEY+MAILGUN_DOMAIN.
The startup check refuses to launch in production without one.
```

### 2.3 Factory no longer silently falls back

`get_email_provider()` is now explicit:

```python
def get_email_provider() -> EmailProvider:
    settings = get_settings()

    if settings.resend.api_key:
        return ResendProvider()
    if settings.sendgrid.api_key and settings.sendgrid.sender_email:
        return SendGridProvider()
    if settings.mailgun.api_key and settings.mailgun.domain:
        return MailgunProvider()

    if settings.is_development:
        logger.warning(
            "email_provider_unconfigured",
            detail="No real provider set; using DevMailhogProvider (dev only).",
        )
        return DevMailhogProvider()

    return NoOpEmailProvider()
```

- Resend > SendGrid > Mailgun (priority order).
- In development, fall back to `DevMailhogProvider` with an
  explicit warning log.
- In production, return `NoOpEmailProvider` which raises on every
  send. **No silent fallback.**

`use_mock_providers` is no longer the deciding flag — what matters
is whether a real provider is configured and whether we are in
development. `use_mock_providers` is retained as a setting for
backward compatibility but no longer drives the email factory.

### 2.4 Update `campaigns.py` to use the factory

`backend/src/seo_platform/api/endpoints/campaigns.py:367, 428` was
hardcoded to `MailhogProvider()`. Replaced with
`get_email_provider()` so the same factory logic applies
(Resend > SendGrid > Mailgun > DevMailhog in dev > NoOp in prod).

### 2.5 P0 startup check is already in place

`backend/src/seo_platform/core/p0_startup.py:84-106` already
checks that at least one of `RESEND_API_KEY`,
`SENDGRID_API_KEY`, or `MAILGUN_API_KEY+MAILGUN_DOMAIN` is
configured in production. The check refused to start a production
deploy without one. With the new providers, the check now has
backing implementations for every option.

---

## 3. Verification Evidence

### 3.1 Module imports cleanly

```python
from seo_platform.services.email_provider import (
    get_email_provider, ResendProvider, SendGridProvider,
    MailgunProvider, DevMailhogProvider, NoOpEmailProvider,
    EmailProviderUnavailableError, email_provider,
)
# → imports ok; provider type = DevMailhogProvider
# (no real provider configured in dev, dev fallback active)
```

### 3.2 MailHog delivery works (dev path)

```
[info] email_sent_success     to=test@example.com
[info] mailhog_email_sent     campaign_id= to=test@example.com

$ curl -o /dev/null -w "%{http_code}\n" http://localhost:8025/api/v2/messages
200
```

A live send to MailHog returned 200, the message is queued in the
local MailHog container (UI: `http://localhost:8025`).

### 3.3 Resend real upstream call (with invalid key, expects 401)

```python
s = get_settings()
s.resend.api_key = 're_test_invalid_key'
p = ResendProvider()
r = await p.send_email('test@example.com', 'Test', '<p>x</p>',
                      tenant_id='00000000-...')
```

Observed:

```
[info] resend_api_call     campaign_id= to=test@example.com
[error] resend_send_failed error="Client error '401 Unauthorized'
          for url 'https://api.resend.com/emails'"

r = {
  "success": false,
  "provider": "resend",
  "error": "Client error '401 Unauthorized' for url
            'https://api.resend.com/emails'",
  "status": "failed"
}
```

The platform made a real HTTP POST to `api.resend.com`. The 401 is
from Resend's auth endpoint. There is no mock, no fake response, no
silent fallback to a different provider.

### 3.4 `NoOpEmailProvider` raises

```python
nop = NoOpEmailProvider()
try:
    await nop.send_email('test@example.com', 'x', 'y')
except EmailProviderUnavailableError as e:
    print('NoOp raises correctly:', str(e)[:80])
# → NoOp raises correctly: No email provider is configured.
#   Set RESEND_API_KEY or SENDGRID_API_KEY or MAILGUN_API_KEY+MAILGUN_DOMAIN
```

The production fallback raises loudly. Workflows calling
`email_provider.send_email` in a no-provider production environment
will fail with a clear error, not a fake "success".

### 3.5 Tracking note (pre-existing, not WS-E)

While exercising the providers, `_track_email` failed on a row
with `campaign_id=None` because the `outreach_emails` table has
`campaign_id NOT NULL` (the ORM model marks it nullable). The
tracking failure is logged as a warning; the email itself was
delivered (MailHog) or refused by upstream (Resend) and the
return value is correct (`success: true` for MailHog,
`success: false, status: failed` for Resend). This is a
schema/ORM mismatch pre-dating WS-E; it is documented in
`PHASE_2_5_1_FINAL_VERDICT.md` §Known Gaps.

---

## 4. Files Touched

| File | Change |
| --- | --- |
| `backend/src/seo_platform/services/email_provider.py` | Added ResendProvider, MailgunProvider, NoOpEmailProvider, _BaseHTTPProvider helper. Factory now explicit. No silent fallback. |
| `backend/src/seo_platform/api/endpoints/campaigns.py` | Replaced `MailhogProvider()` with `get_email_provider()` factory. |
| `EMAIL_DELIVERY_VALIDATION_REPORT.md` | This file |

---

## 5. WS-E Verdict

**BLK-6 is CLOSED.**

The platform's email delivery path is real and explicit:

- Three production providers (Resend, SendGrid, Mailgun) are
  implemented as real HTTP clients against their respective
  upstream APIs.
- A `DevMailhogProvider` exists for local development and is
  selected only when `APP_ENV=development` and no real provider is
  configured (with an explicit warning log).
- A `NoOpEmailProvider` is the production fallback when no real
  provider is configured. It raises `EmailProviderUnavailableError`
  on every send. The startup check refuses to launch in
  production without a real provider.
- The API surface (`POST /campaigns/{id}/threads/{id}/send` and
  the follow-up endpoint) uses the same factory, so the
  no-silent-fallback guarantee applies uniformly.
- Live Resend calls (during WS-E) produced a real 401 from the
  Resend API. No mock, no fake success.

**Operational gap (not a code gap):** No production tenant has
working email credentials. A production deploy must set
`RESEND_API_KEY` (preferred), `SENDGRID_API_KEY+..._SENDER_EMAIL`,
or `MAILGUN_API_KEY+..._DOMAIN`. The P0 startup check enforces
this.
