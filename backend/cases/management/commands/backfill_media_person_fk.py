"""backfill_media_person_fk — populate Media.person_id where it's NULL.

Audit-driven cleanup for a bug where the Submit flow created Media rows
with only ``report=<id>`` set and ``person`` left NULL. The case detail
page filters /api/media by ``person=<id>`` and therefore hid those
rows. The submit flow now sends both FKs; this command backfills the
existing orphan rows by copying ``report.person_id`` onto ``Media.person_id``.

Safe to re-run — already-populated rows are skipped. Wrapped in a single
transaction so partial failures roll back.

Usage::

    ./manage.py backfill_media_person_fk            # live, writes
    ./manage.py backfill_media_person_fk --dry-run  # preview only
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from cases.models import Media


class Command(BaseCommand):
    help = (
        "Populate Media.person_id from report.person_id where it's NULL. "
        "Repairs submit-flow rows that lost the person FK before the fix."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change; don't write.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        qs = Media.objects.filter(person__isnull=True, report__isnull=False)
        # select_related so we don't N+1 the report lookup inside the loop.
        qs = qs.select_related("report", "report__person")
        rows = list(qs)
        if not rows:
            self.stdout.write(self.style.SUCCESS("No orphan Media rows — nothing to do."))
            return

        self.stdout.write(f"Found {len(rows)} Media rows with person_id NULL.")
        fixed = 0
        skipped = 0
        with transaction.atomic():
            for m in rows:
                if not m.report_id or not m.report or not m.report.person_id:
                    skipped += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  skip Media#{m.id}: report missing or has no person"
                        )
                    )
                    continue
                if dry_run:
                    self.stdout.write(
                        f"  would set Media#{m.id} -> person={m.report.person_id}"
                    )
                else:
                    m.person_id = m.report.person_id
                    m.save(update_fields=["person"])
                fixed += 1

        verb = "Would fix" if dry_run else "Fixed"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} {fixed} rows; {skipped} skipped "
                f"(of {len(rows)} total). {'DRY-RUN' if dry_run else ''}"
            ).rstrip()
        )