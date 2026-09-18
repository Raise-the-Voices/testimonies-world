"""Signal handlers for the cases app.

Right now: keep ``Media.file`` in sync with ``Media.visibility`` —
when a volunteer changes a record's visibility tier, the underlying
file has to move between buckets (PUBLIC_MEDIA_ROOT / MEDIA_ROOT /
SENSITIVE_MEDIA_ROOT) or the on-disk layout drifts from the DB.

This signal complements the routing storage in ``cases.storage``:
the storage dispatches NEW uploads to the right bucket at save
time (via ``_media_upload_path``); the signal handles the case
where someone changes visibility AFTER upload.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from django.db.models.signals import pre_save
from django.dispatch import receiver

from cases.models import Media
from cases.storage import (
    PROTECTED_PREFIX,
    PUBLIC_PREFIX,
    SENSITIVE_PREFIX,
    media_storage_router,
)


log = logging.getLogger(__name__)


def _expected_prefix(visibility: str) -> str:
    """Map visibility tier → the path prefix that the routing storage
    uses for files at that tier. Kept in sync with
    ``Media._media_upload_path``."""
    if visibility == Media.Visibility.SENSITIVE:
        return SENSITIVE_PREFIX
    if visibility == Media.Visibility.PUBLIC:
        return PUBLIC_PREFIX
    return PROTECTED_PREFIX


def _move_file(old_name: str, new_name: str) -> str:
    """Move a file between storage buckets on disk. Returns the new
    relative name. Errors are logged but not raised — a missing file
    is a soft failure (the row will keep its record, the next
    restructure_media run can clean up).
    """
    storage = media_storage_router()
    if not storage.exists(old_name):
        log.warning("Media: cannot move %s → %s; source missing on disk", old_name, new_name)
        return new_name

    old_path = Path(storage.path(old_name))
    new_path = Path(storage.path(new_name))
    new_path.parent.mkdir(parents=True, exist_ok=True)

    # shutil.move across filesystems falls back to copy+unlink; the
    # three roots all live on the same filesystem (MEDIA_ROOT,
    # PUBLIC_MEDIA_ROOT, SENSITIVE_MEDIA_ROOT are sibling dirs under
    # BASE_DIR per settings.py) so this is a same-filesystem rename
    # and stays atomic.
    shutil.move(str(old_path), str(new_path))
    log.info("Media: moved %s → %s", old_name, new_name)
    return new_name


@receiver(pre_save, sender=Media)
def move_media_file_on_visibility_change(sender, instance, **kwargs):
    """Move the underlying file when ``Media.visibility`` flips between
    tiers.

    No-op for new rows (instance.pk is None) — the upload-to
    callable in the model handles the bucket choice for first save.
    """
    if not instance.pk:
        return
    if not instance.file:
        return

    try:
        old = Media.objects.get(pk=instance.pk)
    except Media.DoesNotExist:
        return

    if old.visibility == instance.visibility:
        return

    old_name = old.file.name if old.file else None
    new_name = instance.file.name if instance.file else None
    if not old_name or not new_name:
        return
    if old_name == new_name:
        # The user uploaded a new file in the same path slot; no move
        # needed — the new file is already in the right bucket.
        return

    # Ensure the new path has the right visibility prefix. The form
    # might have written to uploads/... even though visibility is
    # sensitive, because the visibility field on the form was set
    # before the file picker committed. Re-prefix to match the
    # current visibility.
    expected_prefix = _expected_prefix(instance.visibility)
    if not new_name.startswith(expected_prefix):
        # Strip the existing prefix from new_name and re-apply the
        # expected one. The file already landed somewhere on disk;
        # we move it to the correct bucket.
        for p in (PROTECTED_PREFIX, PUBLIC_PREFIX, SENSITIVE_PREFIX):
            if new_name.startswith(p):
                stripped = new_name[len(p):]
                break
        else:
            stripped = new_name  # unusual; leave as-is and move
        new_prefixed = expected_prefix + stripped
        moved_name = _move_file(new_name, new_prefixed)
        instance.file.name = moved_name
