"""Move existing profile images from the protected media root to the
public one.

Person.profile_image moved from MEDIA_ROOT to PUBLIC_MEDIA_ROOT when the
two roots were split. The stored column value is unchanged
('profiles/<file>' either way) — only the directory the file sits in
moves, so this is a filesystem migration with no SQL counterpart, which
is why it is a management command rather than a data migration.

Idempotent: files already at the destination are left alone, and a
second run reports 'already public' rather than failing.

    python manage.py publish_profile_images --dry-run
    python manage.py publish_profile_images
"""

import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from cases.models import Person


class Command(BaseCommand):
    help = 'Move Person.profile_image files from MEDIA_ROOT to PUBLIC_MEDIA_ROOT'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report what would move without touching the filesystem',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        source_dir = Path(settings.MEDIA_ROOT) / 'profiles'
        dest_dir = Path(settings.PUBLIC_MEDIA_ROOT) / 'profiles'

        self.stdout.write(f'source: {source_dir}')
        self.stdout.write(f'dest:   {dest_dir}')

        if not dry_run:
            dest_dir.mkdir(parents=True, exist_ok=True)

        stats = {'moved': 0, 'already_public': 0, 'missing': 0, 'orphan': 0}

        # --- Files referenced by a Person row --------------------------
        # Walk the DB rather than the directory so a row whose file never
        # made it across is reported loudly instead of silently 404ing on
        # the public site later.
        referenced = set()
        rows = Person.objects.exclude(profile_image='').exclude(profile_image=None)
        for person in rows.only('id', 'profile_image').iterator():
            name = person.profile_image.name  # e.g. 'profiles/foo.jpg'
            referenced.add(name)
            source = Path(settings.MEDIA_ROOT) / name
            dest = Path(settings.PUBLIC_MEDIA_ROOT) / name

            if dest.exists():
                stats['already_public'] += 1
                continue
            if not source.exists():
                stats['missing'] += 1
                self.stderr.write(
                    self.style.WARNING(f'  MISSING person {person.pk}: {name}')
                )
                continue

            self.stdout.write(f'  move person {person.pk}: {name}')
            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(dest))
            stats['moved'] += 1

        # --- Files on disk with no Person row ---------------------------
        # Carried across too. They are profile photos by virtue of living
        # in profiles/, and leaving them behind would mean a re-linked row
        # silently loses its image.
        if source_dir.is_dir():
            for source in sorted(source_dir.iterdir()):
                if not source.is_file():
                    continue
                name = f'profiles/{source.name}'
                if name in referenced:
                    continue
                dest = Path(settings.PUBLIC_MEDIA_ROOT) / name
                if dest.exists():
                    continue
                self.stdout.write(f'  move orphan: {name}')
                if not dry_run:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(source), str(dest))
                stats['orphan'] += 1

        verb = 'DRY RUN — would move' if dry_run else 'moved'
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} {stats['moved']} referenced + {stats['orphan']} "
                f"orphan file(s); {stats['already_public']} already public; "
                f"{stats['missing']} missing on disk"
            )
        )
