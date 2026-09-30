"""Field-level encryption for Testimonials.

Uses Fernet (AES-128-CBC + HMAC) from `cryptography` — same primitive
that Django uses for `signing` internally, well-audited, simple API.

Two ciphertext columns live on `Testimonial`:
  - source_encrypted            (real source identity)
  - precise_location_encrypted  (precise address / coords)

The key is read from `settings.TESTIMONIALS_FERNET_KEY` (env var on
prod via systemd EnvironmentFile). The key is `urlsafe-base64(32
bytes)` per Fernet.

AUDIT H-6 (2026-09-30): there is no development fallback. The
previous `cases.testimonials.dev_key` module — which held a
hardcoded key reachable when `DEBUG=True AND ALLOW_DEV_FALLBACK_KEY`
held — has been removed. Every environment, local or production,
must set `TESTIMONIALS_FERNET_KEY` explicitly. Local dev gets a key
via `./scripts/gen-dev-key.sh`. A missing key raises
`ImproperlyConfigured` at first encrypt/decrypt, not a silent
decryption by anyone with repo read.

If you find yourself adding a fallback path here, stop — the audit
(H-6) and the upgrade plan (`UPGRADE_PLAN.md §1.5`) both explicitly
forbid it. The path was a privacy leak by construction: every
``source_encrypted`` row written under it was decryptable by any
operator with repository read.
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
      1. ``settings.TESTIMONIALS_FERNET_KEYS`` — a list of keys. The
         first key is used for ENCRYPTION; all keys are tried for
         DECRYPTION in order. This is the rotation path: ship the
         new key at index 0, keep the old key at index 1 until all
         rows have been re-encrypted, then drop the old key. Use
         ``MultiFernet`` under the hood — same encrypt/decrypt API.
      2. ``settings.TESTIMONIALS_FERNET_KEY`` — single key (legacy).
         Equivalent to a one-element KEYS list.
      3. Otherwise: ``ImproperlyConfigured``.

    Cached so the warning fires once per process, not once per field
    read. Tests that swap keys should call ``get_fernet.cache_clear()``
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

    # Audit H-6: the DEV fallback is gone. There is no dev_key.py,
    # no DEBUG=True shortcut, no committed plaintext key. A missing
    # key raises immediately on first encrypt/decrypt. Local dev
    # sets the key via `./scripts/gen-dev-key.sh` → backend/.env.
    raise ImproperlyConfigured(
        'TESTIMONIALS_FERNET_KEY (or TESTIMONIALS_FERNET_KEYS) is '
        'required. Generate one with `python -c "from cryptography'
        '.fernet import Fernet; print(Fernet.generate_key().decode'
        '())"` or run `./scripts/gen-dev-key.sh` and add the printed '
        'line to backend/.env. The DEV fallback was removed (audit '
        'H-6) — see backend/cases/testimonials/encryption.py.'
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
