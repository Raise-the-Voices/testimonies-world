"""Seed the database with example Contact records so the /contacts page
has something to show during demos and development.

ALL DATA IS FAKE. Names, emails, and phone numbers are obvious
placeholders (Jane Smith, example.com, +1-555-0100) so nobody can
mistake these for real people. Don't reuse this for production data.

Idempotent: re-running won't duplicate records — we match on
(name, role) and skip if a Contact with that pair already exists.

Optional flags:
  --reset   Wipe ALL existing Contact records before seeding. Useful
            for a clean demo state. Off by default so a stray
            invocation can't blow away real data.

Run on prod (advocates only see contacts):
  cd /opt/rtv-cases/backend
  source .venv/bin/activate
  python manage.py seed_contacts
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from contacts.models import Contact


# Each entry: (name, role, email, phone, signal, whatsapp, notes).
# One of every role so the filter dropdown is exercised end-to-end.
# Phones use the 555 prefix reserved for fictional use (NANP §10) so
# nobody can dial them by accident.
SEED_CONTACTS = [
    (
        "Jane Smith (example)",
        Contact.Role.FAMILY,
        "jane.smith@example.com",
        "+1-555-0100",
        "",
        "",
        "Placeholder family contact — replace before any real use.",
    ),
    (
        "Carlos Mendoza (example)",
        Contact.Role.ADVOCATE,
        "c.mendoza@example.org",
        "+1-555-0101",
        "+1-555-0101",
        "",
        "Placeholder advocate contact.",
    ),
    (
        "Amira Hassan (example)",
        Contact.Role.LAWYER,
        "amira.hassan@example.com",
        "+1-555-0102",
        "",
        "+1-555-0102",
        "Placeholder legal counsel contact.",
    ),
    (
        "Office of the High Commissioner (example)",
        Contact.Role.OFFICIAL,
        "info@example.gov",
        "+1-555-0103",
        "",
        "",
        "Placeholder institutional contact.",
    ),
    (
        "Lena Park (example)",
        Contact.Role.JOURNALIST,
        "lena.park@example.net",
        "+1-555-0104",
        "+1-555-0104",
        "",
        "Placeholder press contact.",
    ),
    (
        "Anonymous Witness 01 (example)",
        Contact.Role.REPORTER,
        "",
        "",
        "+1-555-0105",
        "",
        "Placeholder first-hand source contact — no email/phone by design.",
    ),
    (
        "Dr. Pavel Novak (example)",
        Contact.Role.OTHER,
        "pavel.novak@example.com",
        "+1-555-0106",
        "",
        "",
        "Placeholder medical reviewer contact.",
    ),
]


class Command(BaseCommand):
    help = "Seed example Contact records (idempotent). All data is fake."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete every existing Contact before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            deleted, _ = Contact.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing Contact records."))

        created = 0
        skipped = 0
        for name, role, email, phone, signal, whatsapp, notes in SEED_CONTACTS:
            obj, was_created = Contact.objects.get_or_create(
                name=name,
                role=role,
                defaults={
                    "email": email,
                    "phone": phone,
                    "signal": signal,
                    "whatsapp": whatsapp,
                    "notes": notes,
                },
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"  + {obj}"))
            else:
                skipped += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"Done. {created} created, {skipped} already existed.")
        )