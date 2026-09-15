"""Storage backends for the two media roots.

The platform keeps two separate trees on disk:

  * ``MEDIA_ROOT``        — evidence and case documents. Reached only via
    ``/media/``, which nginx proxies to ``serve_protected_media()`` so
    every byte goes through an auth + ``Media.visibility`` check.
  * ``PUBLIC_MEDIA_ROOT`` — files that are public by definition. Reached
    via ``/public-media/``, which nginx serves straight off disk with no
    upstream hop and no auth gate.

Keeping them apart means the protected tree is the default: anything
written without a deliberate choice of storage lands behind the gate.
Publishing is the explicit act, not protecting.
"""

from django.conf import settings
from django.core.files.storage import FileSystemStorage


def public_media_storage():
    """Storage for world-readable files, served by nginx off disk.

    Declared as a callable (not a module-level instance) so migrations
    deconstruct it to this import path rather than freezing the resolved
    filesystem location into a migration file — the location differs per
    host, and a baked-in ``/opt/rtv-cases/...`` would break local dev and
    the Docker image.
    """
    return FileSystemStorage(
        location=settings.PUBLIC_MEDIA_ROOT,
        base_url=settings.PUBLIC_MEDIA_URL,
    )
