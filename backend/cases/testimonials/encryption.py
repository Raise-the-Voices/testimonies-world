"""Field-level encryption for Testimonials.

Uses Fernet (AES-128-CBC + HMAC) from `cryptography` — same primitive
that Django uses for `signing` internally, well-audited, simple API.

Two ciphertext columns live on `Testimonial`:
  - source_encrypted            (real source identity)
  - precise_location_encrypted  (precise address / coords)

The key is read from `settings.TESTIMONIALS_FERNET_KEY` (env var on
prod via systemd EnvironmentFile). The key is `urlsafe-base64(32
bytes)` per Fernet.

Production must set the env var. Local dev with `DEBUG=True` and
`ALLOW_DEV_FALLBACK_KEY=True` (the default in DEBUG) falls back to
the key in `dev_key.py` (a separate, clearly-marked module) and
emits a loud RuntimeWarning at first access. The hardcoded key is
no longer in this module — review tooling can grep one file for
crypto algorithm and another for the DEV-ONLY marker.

Both gates must be true for the dev fallback to fire:
  DEBUG=True AND settings.ALLOW_DEV_FALLBACK_KEY != False

If either is false (the prod posture), the missing key raises
`ImproperlyConfigured`.
"""

import warnings
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


@lru_cache(maxsize=1)
def get_fernet() -> Fernet:
    """Return the configured Fernet instance.

    Cached so the warning fires once per process, not once per field
    read. Tests that explicitly swap keys should call
    `get_fernet.cache_clear()` or override `settings.TESTIMONIALS_FERNET_KEY`.
    """
    raw = getattr(settings, 'TESTIMONIALS_FERNET_KEY', None)
    if raw:
        key = raw.encode() if isinstance(raw, str) else raw
        return Fernet(key)

    debug = bool(getattr(settings, 'DEBUG', False))
    allow_dev = getattr(settings, 'ALLOW_DEV_FALLBACK_KEY',
                        None)  # default: see below
    # Default policy: allow in DEBUG, deny in prod. Explicit override
    # via settings.ALLOW_DEV_FALLBACK_KEY wins either way.
    if allow_dev is None:
        allow_dev = debug

    if debug and allow_dev:
        # Imported lazily so the DEV-only key value never appears in
        # the module-load trace for a production process — only when
        # the warning fires AND the call path actually needs it.
        from .dev_key import TESTIMONIALS_DEV_FALLBACK_KEY
        warnings.warn(
            'TESTIMONIALS_FERNET_KEY is not configured; using the '
            'DEV fallback key from cases.testimonials.dev_key. '
            'Encrypted source identities in this DB are NOT protected '
            'by real cryptography. Set TESTIMONIALS_FERNET_KEY in '
            'production via the env file.',
            RuntimeWarning, stacklevel=2,
        )
        return Fernet(TESTIMONIALS_DEV_FALLBACK_KEY)

    raise ImproperlyConfigured(
        'TESTIMONIALS_FERNET_KEY is required when DEBUG=False (or '
        'when ALLOW_DEV_FALLBACK_KEY is explicitly disabled). '
        "Generate one with: python -c \"from cryptography.fernet "
        "import Fernet; print(Fernet.generate_key().decode())\""
    )


def encrypt_str(plaintext: str) -> bytes:
    """Encrypt a UTF-8 string. Returns Fernet ciphertext bytes.

    None and empty string both produce empty bytes (decrypted as None).
    """
    if not plaintext:
        return b''
    return get_fernet().encrypt(plaintext.encode('utf-8'))


def decrypt_str(ciphertext) -> str | None:
    """Decrypt Fernet ciphertext back to UTF-8 string.

    Returns None for None / empty input.

    Raises `InvalidToken` if the key has rotated or the ciphertext is
    forged — callers must handle this explicitly so a key rotation
    doesn't silently return garbled text.
    """
    if not ciphertext:
        return None
    return get_fernet().decrypt(bytes(ciphertext)).decode('utf-8')
