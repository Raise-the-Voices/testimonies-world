"""Input sanitization for free-text and URL fields.

Why a separate module: any TextField that ends up rendered in HTML (a
Django template, an HTML email body, a future rich-text view) is a
potential XSS sink. Today the platform's only HTML sink is the
casework-notification email body, and the existing `notifications.py`
escapes values there — but there's no defense in depth for the day a
template, a `mark_safe`, or a `safe` rich-text renderer is added.

Sanitization policy:
  * Text fields: strip ALL HTML tags and attributes. Plain text only.
    We never accept rich text on this platform, so there's no tag
    allowlist to maintain.
  * URL fields: validate against Django's URLValidator with the
    http(s) scheme allowlist. Rejects `javascript:`, `data:`, `file:`,
    `ftp:`, etc. — all common XSS pivots and SSRF surfaces.

Both functions are no-ops on `None` / empty strings so they're safe
to call unconditionally on optional fields.
"""

import bleach
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

# Module-level URL validator — built once, reused on every call.
# The `schemes` argument is the canonical allowlist hook; http(s) only.
_url_validator = URLValidator(schemes=['http', 'https'])


def sanitize_text(value):
    """Strip every HTML tag and attribute from `value`.

    Returns the plain-text content. None / empty pass through.
    Uses bleach with `tags=[]` + `attributes={}` + `strip=True` so
    the result is guaranteed markup-free. `.strip()` collapses
    leading/trailing whitespace that the stripping can introduce.
    """
    if not value:
        return value or ''
    return bleach.clean(value, tags=[], attributes={}, strip=True).strip()


def sanitize_url(value):
    """Validate that `value` is an http(s) URL.

    Rejects `javascript:`, `data:`, `file:`, `ftp:`, and any other
    non-http(s) scheme — common XSS pivots and SSRF surfaces.
    Returns the value unchanged on success; raises
    `django.core.exceptions.ValidationError` on failure.
    """
    if not value:
        return value or ''
    try:
        _url_validator(value)
    except ValidationError:
        # Re-raise as a serializer-friendly ValidationError. The
        # message intentionally doesn't echo the bad input — echoing
        # would be a reflection XSS risk if the error were ever
        # rendered in HTML without escaping.
        raise ValidationError('Enter a valid http or https URL.')
    return value
