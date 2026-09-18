"""Storage backends for the three media trees.

The platform keeps three separate trees on disk so that sensitive
content cannot leak via a misconfigured URL or an off-disk alias:

  * ``PUBLIC_MEDIA_ROOT``    — files that are public by definition
    (Person.profile_image today, plus any future opt-in public type).
    Reached via ``/public-media/``, which nginx serves straight off
    disk with no upstream hop and no auth gate.
  * ``MEDIA_ROOT``            — restricted evidence + case documents.
    Reached only via ``/media/``, which nginx proxies to
    ``MediaDownloadView`` so every byte goes through an auth +
    ``Media.visibility`` check.
  * ``SENSITIVE_MEDIA_ROOT``  — sensitive evidence (advocate-only).
    Reached via the same ``/media/`` proxy, but the auth gate is
    stricter: only Advocate / staff users, and every download writes
    an ``AuditLog`` row.

Keeping them apart means the protected tree is the default: anything
written without a deliberate choice of storage lands behind the gate.
Publishing is the explicit act, not protecting.

The ``MediaStorageRouter`` is a thin proxy over the three real
backends. It dispatches reads / writes / deletes based on the
visibility prefix that ``Media._media_upload_path`` writes into the
relative path, so each ``Media`` row's file lands in the right tree
on disk even if its ``visibility`` flips later (the
``pre_save`` signal in ``cases.signals`` handles the move at that
point).
"""

from __future__ import annotations

from django.conf import settings
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.functional import SimpleLazyObject


# --- Path prefixes ------------------------------------------------------
# The Media._media_upload_path callable prefixes the relative file
# name with one of these. The router dispatches on the prefix.
PUBLIC_PREFIX = "public/"
SENSITIVE_PREFIX = "sensitive/"
PROTECTED_PREFIX = "uploads/"


# --- Storage factories (callable, per existing convention) -------------
def public_media_storage():
    """Storage for world-readable files, served by nginx off disk."""
    return FileSystemStorage(
        location=settings.PUBLIC_MEDIA_ROOT,
        base_url=settings.PUBLIC_MEDIA_URL,
    )


def protected_media_storage():
    """Storage for restricted-visibility files. Lives behind the auth
    gate at ``/media/`` (see ``MediaDownloadView``)."""
    return FileSystemStorage(
        location=settings.MEDIA_ROOT,
        base_url=settings.MEDIA_URL,
    )


def sensitive_media_storage():
    """Storage for sensitive files. Lives behind the SAME auth gate at
    ``/media/`` but with a stricter visibility check + audit log.

    ``base_url=None`` so ``.url`` raises if anyone tries to render an
    HTML link to a sensitive file — sensitive downloads always go
    through the gated view, never via a direct URL.
    """
    return FileSystemStorage(
        location=settings.SENSITIVE_MEDIA_ROOT,
        base_url=None,
    )


# --- Routing storage ---------------------------------------------------
class MediaStorageRouter(Storage):
    """Dispatches reads/writes/deletes to one of the three backends
    based on the relative path's visibility prefix.

    Designed to be set as ``Media.file.storage``. Each call constructs
    its three delegate backends lazily so the resolved filesystem
    location comes from the live ``settings`` at request time — that
    matches the rest of the codebase's "callable factory" pattern
    (see ``public_media_storage``) and avoids baking an absolute
    filesystem path into a migration.
    """

    def __init__(self):
        # ``SimpleLazyObject`` lets us defer backend construction
        # until first use. Each delegate is itself callable so we
        # follow the existing "factories are callables" convention.
        self._public = SimpleLazyObject(public_media_storage)
        self._protected = SimpleLazyObject(protected_media_storage)
        self._sensitive = SimpleLazyObject(sensitive_media_storage)

    # --- Path dispatch ------------------------------------------------
    def _select(self, name):
        """Return ``(backend, subpath)`` for a relative file name."""
        if not name:
            return self._protected, name
        if name.startswith(PUBLIC_PREFIX):
            return self._public, name[len(PUBLIC_PREFIX):]
        if name.startswith(SENSITIVE_PREFIX):
            return self._sensitive, name[len(SENSITIVE_PREFIX):]
        return self._protected, name

    # --- FileSystemStorage API surface -------------------------------
    def _open(self, name, mode="rb"):
        backend, subpath = self._select(name)
        return backend._open(subpath, mode)

    def _save(self, name, content):
        # Delegate so the file lands in the right tree on disk. The
        # relative ``name`` already carries the prefix that
        # ``Media._media_upload_path`` wrote, so we just strip and
        # forward. The relative path inside the bucket is what the
        # delegate saves under; we re-prefix on the way out so the
        # DB row keeps the canonical full path.
        #
        # ``FileField._save`` is called from two paths: (a) the model
        # ``save()`` flow passes the FieldFile's ``.name`` (a string),
        # and (b) the FieldFile's own ``save()`` (e.g. when Django's
        # FileField updates an existing row) passes the FieldFile
        # itself as ``name``. Coerce defensively so both work.
        name = str(getattr(name, "name", name))
        backend, subpath = self._select(name)
        backend._save(subpath, content)
        return name

    def delete(self, name):
        backend, subpath = self._select(name)
        backend.delete(subpath)

    def exists(self, name):
        backend, subpath = self._select(name)
        return backend.exists(subpath)

    def url(self, name):
        backend, subpath = self._select(name)
        return backend.url(subpath)

    def path(self, name):
        backend, subpath = self._select(name)
        return backend.path(subpath)

    def size(self, name):
        backend, subpath = self._select(name)
        return backend.size(subpath)

    def open(self, name, mode="rb"):
        # Django's Storage base class dispatches through ``_open``.
        return self._open(name, mode)

    def save(self, name, content, max_length=None):
        # Used by ``ImageField`` to persist a generated thumbnail
        # alongside the original (FileField passes ``max_length``;
        # ``ImageField`` also passes a ``max_length`` for the saved
        # file name length). Strip prefix before delegating so the
        # delegate writes under its own root, then re-prefix the
        # returned name so Django stores the FULL path (including the
        # visibility bucket) on the FieldFile. Without the re-prefix,
        # ``Media.file.name`` would be the bare basename and the
        # router couldn't dispatch reads back to the right tree.
        #
        # Same defensive coercion as ``_save`` — the ``name`` arg can
        # be a FieldFile / UploadedFile object instead of a string.
        # Django's Storage.save contract is ``(name, content, max_length)``,
        # so we keep that order here.
        name = str(getattr(name, "name", name))
        backend, subpath = self._select(name)
        stored_subpath = backend.save(subpath, content, max_length=max_length)
        # Re-prefix the stored name with the bucket prefix. If the
        # delegate kept the name unchanged, this is a no-op beyond
        # adding the prefix; if it disambiguated a collision, the
        # prefix still belongs to the same bucket.
        return name.split(subpath, 1)[0] + stored_subpath

    def get_valid_name(self, name):
        # Pass through unchanged; each backend will sanitize its own
        # relative name independently.
        return name

    def get_available_name(self, name, max_length=None):
        backend, subpath = self._select(name)
        new_subpath = backend.get_available_name(subpath, max_length=max_length)
        # If the delegate altered the name (collision), re-prefix.
        if new_subpath == subpath:
            return name
        prefix = self._prefix_for(name)
        return prefix + new_subpath if prefix else new_subpath

    # --- Internal helpers ---------------------------------------------
    def _prefix_for(self, name):
        if name.startswith(PUBLIC_PREFIX):
            return PUBLIC_PREFIX
        if name.startswith(SENSITIVE_PREFIX):
            return SENSITIVE_PREFIX
        if name.startswith(PROTECTED_PREFIX):
            return PROTECTED_PREFIX
        return ""

    def __repr__(self):
        return f"<{self.__class__.__name__} public={self._public!r} protected={self._protected!r} sensitive={self._sensitive!r}>"


def media_storage_router():
    """Storage instance for ``Media.file``. Wraps the three visibility
    buckets under a single object so the field declaration stays a
    single token.
    """
    return MediaStorageRouter()
