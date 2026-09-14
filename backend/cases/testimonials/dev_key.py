"""DEV-ONLY Fernet key for local development.

This module exists as a single-purpose, clearly-marked container for
the hardcoded Fernet key that local `runserver` falls back to when
`TESTIMONIALS_FERNET_KEY` is not set. It is isolated from
`encryption.py` so:

  1. A code search for encryption can stay focused on the algorithm.
  2. The "DEV ONLY" marker is impossible to miss when reviewing.
  3. Removing this fallback (when all environments ship explicit
     keys) is a single file delete.

NEVER use this key for any environment that holds real casework.
If `TESTIMONIALS_FERNET_KEY` is unset AND `ALLOW_DEV_FALLBACK_KEY`
is False (the prod posture), `encryption.get_fernet()` raises
`ImproperlyConfigured` at first use.

The key is generated once via:
    python -c "from cryptography.fernet import Fernet; \
        print(Fernet.generate_key().decode())"
"""

# A hardcoded Fernet key for local development ONLY. Real
# casework environments MUST set TESTIMONIALS_FERNET_KEY via the
# environment (systemd EnvironmentFile=) and have ALLOW_DEV_FALLBACK_KEY
# default to False.
TESTIMONIALS_DEV_FALLBACK_KEY = (
    b'hqMeZwk7bLZku5x5flLKUDPKaZvbk0aTPW3PO8Y_-vk='
)