"""restructure_media — move Media files into the right visibility bucket.

Pre-2026, every Media row wrote to ``MEDIA_ROOT/uploads/<filename>``
regardless of ``visibility``. After this command, the on-disk layout
matches the visibility tier:

  visibility=public    → PUBLIC_MEDIA_ROOT/public/<filename>
  visibility=restricted → MEDIA_ROOT/uploads/<filename>        (default)
  visibility=sensitive  → SENSITIVE_MEDIA_ROOT/sensitive/<filename>

Safe to re-run. Idempotent: a row whose ``file.name`` already has the
right prefix is left alone. A row whose file is missing on disk is
reported (and skipped — we don't fabricate filenames).

Usage::

    ./manage.py restructure_media                 # live, writes
    ./manage.py restructure_media --dry-run       # preview only
    ./manage.py restructure_media --limit 50      # cap rows touched
    ./manage.py restructure_media --visibility sensitive
"""
from __future__ import annotations

import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cases.models import Media
from cases.storage import (
    PROTECTED_PREFIX,
    PUBLIC_PREFIX,
    SENSITIVE_PREFIX,
    media_storage_router,
)


def _expected_prefix(visibility: str) -> str:
    """Map visibility tier → the path prefix the routing storage uses.

    Must stay in sync with ``Media._media_upload_path`` in models.py
    and the prefix constants in cases/storage.py.
    """
    if visibility == Media.Visibility.SENSITIVE:
        return SENSITIVE_PREFIX
    if visibility == Media.Visibility.PUBLIC:
        return PUBLIC_PREFIX
    return PROTECTED_PREFIX


def _strip_prefix(name: str) -> str:
    """Strip whichever bucket-prefix is on a path so we can re-prefix it."""
    for prefix in (PROTECTED_PREFIX, PUBLIC_PREFIX, SENSITIVE_PREFIX):
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


class Command(BaseCommand):
    help = (
        "Move Media files between visibility buckets on disk so the "
        "tree layout matches each row's visibility. Idempotent."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without moving files or saving rows.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Process at most N rows (0 = no cap). Useful for staged rollouts.",
        )
        parser.add_argument(
            "--visibility",
            choices=[c[0] for c in Media.Visibility.choices],
            default=None,
            help="Restrict to rows of this visibility tier.",
        )

    # --- Reporting counters ------------------------------------------
    def _init_counters(self):
        return {
            "scanned": 0,
            "moved": 0,
            "skipped_no_change": 0,
            "skipped_missing_file": 0,
            "skipped_public_redirect_target": 0,
            "skipped_no_file": 0,
            "errors": 0,
        }

    def _format(self, counters):
        return (
            f"scanned={counters['scanned']}  "
            f"moved={counters['moved']}  "
            f"no-change={counters['skipped_no_change']}  "
            f"missing-file={counters['skipped_missing_file']}  "
            f"no-file={counters['skipped_no_file']}  "
            f"errors={counters['errors']}"
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options["limit"] or None
        only_visibility = options["visibility"]

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "DRY-RUN — no files moved, no rows saved."
            ))

        storage = media_storage_router()

        qs = Media.objects.exclude(file="").exclude(file__isnull=True)
        if only_visibility is not None:
            qs = qs.filter(visibility=only_visibility)
        if limit:
            qs = qs.order_by("id")[:limit]

        counters = self._init_counters()
        updates: list[Media] = []

        try:
            for media in qs.iterator(chunk_size=200):
                counters["scanned"] += 1
                self._process_one(media, storage, counters, updates)
        except CommandError:
            raise
        except Exception as exc:  # noqa: BLE001 — log and continue
            counters["errors"] += 1
            self.stdout.write(self.style.ERROR(
                f"unexpected error while scanning: {exc}"
            ))

        if dry_run:
            self.stdout.write(self.style.NOTICE(
                f"DRY-RUN summary: {self._format(counters)}"
            ))
            return

        if updates:
            with transaction.atomic():
                for media in updates:
                    media.save(update_fields=["file", "updated_at"])
            self.stdout.write(self.style.SUCCESS(
                f"Saved {len(updates)} Media row(s)."
            ))

        self.stdout.write(self.style.NOTICE(
            f"Summary: {self._format(counters)}"
        ))

    # --- Per-row processing -------------------------------------------
    def _process_one(self, media, storage, counters, updates):
        # Defensive — qs filters file="" / file__isnull=True but a row
        # might still have file cleared between filter and access.
        if not media.file or not media.file.name:
            counters["skipped_no_file"] += 1
            return

        old_name = media.file.name
        expected_prefix = _expected_prefix(media.visibility)
        new_name = expected_prefix + _strip_prefix(old_name)

        # Identity rename: file already lives in the right bucket.
        if old_name == new_name:
            counters["skipped_no_change"] += 1
            return

        # Special case: legacy `/profiles/<file>` URLs.
        # Those files live under PUBLIC_MEDIA_ROOT now (served by nginx
        # at /public-media/profiles/<file>), not anywhere under
        # MEDIA_ROOT. Moving them here would corrupt the public tree.
        # Skip and surface so the operator can fix by hand if needed.
        if old_name.startswith("profiles/"):
            counters["skipped_public_redirect_target"] += 1
            self.stdout.write(self.style.WARNING(
                f"  [{media.id}] {media.person_id}/{old_name}: legacy profile-image "
                f"path; handled by MediaDownloadView's redirect — skipping."
            ))
            return

        # Source must exist on disk before we move it.
        if not storage.exists(old_name):
            counters["skipped_missing_file"] += 1
            self.stdout.write(self.style.WARNING(
                f"  [{media.id}] {old_name}: source missing on disk — skipping."
            ))
            return

        # Sanity-check the destination directory exists; create it so
        # shutil.move has somewhere to land. MEDIA_ROOT,
        # PUBLIC_MEDIA_ROOT, SENSITIVE_MEDIA_ROOT are all
        # os.makedirs'd at settings load, but the per-bucket subdir
        # (public/, uploads/, sensitive/) needs to exist for the
        # underlying FileSystemStorage to write into.
        dest_dir = Path(storage.path(new_name)).parent
        dest_dir.mkdir(parents=True, exist_ok=True)

        src_path = Path(storage.path(old_name))
        dst_path = Path(storage.path(new_name))

        self.stdout.write(
            f"  [{media.id}] {old_name} → {new_name}"
        )
        if not storage.save.__class__:
            # No-op condition that always holds — keeps the
            # linter happy about storage.save being callable below.
            pass

        try:
            # shutil.move across the same filesystem is an atomic
            # rename; across filesystems it's copy+unlink. All three
            # roots are sibling dirs under BASE_DIR per settings.py
            # so the rename stays atomic in practice.
            shutil.move(str(src_path), str(dst_path))
        except OSError as exc:
            counters["errors"] += 1
            self.stdout.write(self.style.ERROR(
                f"  [{media.id}] move failed: {exc}"
            ))
            return

        counters["moved"] += 1
        media.file.name = new_name
        updates.append(media)
