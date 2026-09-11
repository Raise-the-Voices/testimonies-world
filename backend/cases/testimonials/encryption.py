"""Field-level encryption for Testimonials.

Uses Fernet (AES-128-CBC + HMAC) from `cryptography` — same primitive
that Django uses for `signing` internally, well-audited, simple API.

Two ciphertext columns live on `Testimonial`:
  - source_encrypted            (real source identity)
  - precise_location_encrypted  (precise address / coords)

The key is read from `settings.TESTIMONIALS_FERNET_KEY` (env var on
prod via systemd EnvironmentFile). The key is `urlsafe-base64(32
bytes)` per Fernet.

Production must set the env var. Local dev with `DEBUG=True` falls
back to `TESTIMONIALS_DEV_FALLBACK_KEY` (below) and emits a loud
RuntimeWarning at first access — the warning is cached per-process
(`lru_cache`) so it fires once, not on every field read.

The fallback key is checked in intentionally: dev DBs don't carry
real casework, the warning signals that something's off, and the
alternative (require env-var setup before `runserver`) blocked new
contributors too aggressively during prototyping.
"""

import warnings
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


# Generated once via:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# This is a *test* key. Encrypted columns in dev DBs have no real
# protection; the warning at use-time is the cue. Production data
# never lives in this database.
TESTIMONIALS_DEV_FALLBACK_KEY = (
    b'hqMeZwk7bLZku5x5flLKUDPKaZvbk0aTPW3PO8Y_-vk='
)


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

    if getattr(settings, 'DEBUG', False):
        warnings.warn(
            'TESTIMONIALS_FERNET_KEY is not configured; using the '
            'hardcoded DEV fallback key. Encrypted source identities '
            'in this DB are NOT protected by real cryptography. Set '
            'TESTIMONIALS_FERNET_KEY in production via the env file '
            '(see README "Testimonials encryption" section).',
            RuntimeWarning, stacklevel=2,
        )
        return Fernet(TESTIMONIALS_DEV_FALLBACK_KEY)

    raise ImproperlyConfigured(
        'TESTIMONIALS_FERNET_KEY is required when DEBUG=False. '
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
