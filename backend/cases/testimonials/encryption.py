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

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _key_to_fernet(raw) -> Fernet:
    """Coerce a single key (str or bytes) to a Fernet instance."""
    if isinstance(raw, str):
        raw = raw.encode()
    return Fernet(raw)


@lru_cache(maxsize=1)
def get_fernet() -> Fernet | MultiFernet:
    """Return the configured Fernet (or MultiFernet for rotation).

    Resolution order:
      1. `settings.TESTIMONIALS_FERNET_KEYS` — a list of keys. The
         first key is used for ENCRYPTION; all keys are tried for
         DECRYPTION in order. This is the rotation path: ship the
         new key at index 0, keep the old key at index 1 until all
         rows have been re-encrypted, then drop the old key. Use
         `MultiFernet` under the hood — same encrypt/decrypt API.
      2. `settings.TESTIMONIALS_FERNET_KEY` — single key (legacy).
         Equivalent to a one-element KEYS list.
      3. Dev fallback (DEBUG=True + ALLOW_DEV_FALLBACK_KEY) — a
         single key from cases.testimonials.dev_key, with a loud
         RuntimeWarning.
      4. Otherwise: ImproperlyConfigured.

    Cached so the warning fires once per process, not once per field
    read. Tests that swap keys should call `get_fernet.cache_clear()`
    or override settings.
    """
    keys_raw = getattr(settings, 'TESTIMONIALS_FERNET_KEYS', None)
    if keys_raw:
        fernets = [_key_to_fernet(k) for k in keys_raw]
        if len(fernets) == 1:
            return fernets[0]
        return MultiFernet(fernets)

    raw = getattr(settings, 'TESTIMONIALS_FERNET_KEY', None)
    if raw:
        return _key_to_fernet(raw)

    debug = bool(getattr(settings, 'DEBUG', False))
    allow_dev = getattr(settings, 'ALLOW_DEV_FALLBACK_KEY', None)
    if allow_dev is None:
        allow_dev = debug

    if debug and allow_dev:
        from .dev_key import TESTIMONIALS_DEV_FALLBACK_KEY
        warnings.warn(
            'TESTIMONIALS_FERNET_KEY is not configured; using the '
            'DEV fallback key from cases.testimonials.dev_key. '
            'Encrypted source identities in this DB are NOT protected '
            'by real cryptography. Set TESTIMONIALS_FERNET_KEY (or '
            'TESTIMONIALS_FERNET_KEYS for rotation) in production via '
            'the env file.',
            RuntimeWarning, stacklevel=2,
        )
        # Audit H-6: emit a separate DeprecationWarning alongside the
        # RuntimeWarning so dev sees a clear "this is going away"
        # signal. Kept the original RuntimeWarning unchanged so the
        # existing pin in tests.py keeps passing. The DeprecationWarning
        # will surface in any dev tooling that filters for it; the
        # grace period is ~4 weeks from this commit, after which the
        # fallback path itself goes away (separate commit).
        warnings.warn(
            'cases.testimonials.dev_key fallback is DEPRECATED and '
            'will be removed (audit H-6). Generate a real key with '
            '`./scripts/gen-dev-key.sh` and set TESTIMONIALS_FERNET_KEY '
            'in your .env.',
            DeprecationWarning, stacklevel=2,
        )
        return _key_to_fernet(TESTIMONIALS_DEV_FALLBACK_KEY)

    raise ImproperlyConfigured(
        'TESTIMONIALS_FERNET_KEY (or TESTIMONIALS_FERNET_KEYS) is '
        'required when DEBUG=False (or when ALLOW_DEV_FALLBACK_KEY '
        'is explicitly disabled). '
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
