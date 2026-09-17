"""
backfill_email_addresses — one-shot reconciliation for the orphan-EmailAddress
class of bug on cases.raisethevoices.org.

Background
----------
django-allauth (we're on 0.63.2) only inserts `account_emailaddress` rows
when ACCOUNT_EMAIL_VERIFICATION is something other than 'none'. With
'none' (the prior value), local signups wrote `auth_user.email` but no
matching EmailAddress row, and so allauth's email-keyed OAuth lookup had
nothing to bind to. The symptom is the Nazir case: a User exists with
their real Gmail address but no SocialAccount, so the Google OAuth
callback falls through to auto-signup, which then errors on the
username/email uniqueness check and renders
/accounts/3rdparty/signup/ with the "account already exists" error.

This command does NOT touch auth_user.email or socialaccount rows. It
ONLY inserts missing EmailAddress rows for users whose auth_user.email is
already populated.

Defaults to verified=False (the safe choice — we don't have cryptographic
proof of email ownership for any user this command touches). A future
custom SocialAccountAdapter (cases.adapters.CustomSocialAccountAdapter)
will upgrade to verified=True during OAuth based on Google's
`email_verified=true` claim.

Idempotency
-----------
The command is keyed on (user, email) pairs and uses
`EmailAddress.objects.get_or_create(...)`. Re-running after the first
apply is a no-op.

Audit
-----
Each inserted row writes an AuditLog entry (action='CREATED',
target_type='email_address', details include the username + whether
the row was set verified). Operator can grep journalctl / log streams
for 'backfill_email_addresses' to see when the command ran.

Usage
-----
    # Dry-run, show what would be inserted (no writes):
    manage.py backfill_email_addresses --dry-run

    # Apply:
    manage.py backfill_email_addresses

    # If you KNOW the user controls the email (e.g., you verified out-
    # of-band) and want the adapter's auto-link path to fire
    # immediately, opt in per-user with --verified-usernames:
    manage.py backfill_email_addresses --verified-usernames root,admin

Never pass --verified-usernames for ordinary user accounts — only for
operator-controlled ones where you've independently confirmed
ownership. Setting verified=True on a row whose email is NOT actually
owned by that User is an account-takeover primitive.
"""

import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from allauth.account.models import EmailAddress

from cases.models import AuditLog

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Backfill missing allauth EmailAddress rows for existing users. "
        "Idempotent and audit-logged. Safe default: verified=False."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be inserted; don't write to the DB.",
        )
        parser.add_argument(
            "--verified-usernames",
            default="",
            help=(
                "Comma-separated list of usernames to mark verified=True. "
                "ONLY for operator accounts you've independently confirmed. "
                "Never use for ordinary users."
            ),
        )

    def handle(self, *args, dry_run=False, verified_usernames="", **opts):
        U = get_user_model()
        verified_set = {
            s.strip() for s in verified_usernames.split(",") if s.strip()
        }

        # Find users whose auth_user.email is set but who have no
        # EmailAddress row. EmailAddress.email__iexact covers the
        # mixed-case race (e.g. Nazir@gmail.com vs nazirafghan9251@gmail.com).
        orphans = (
            U.objects.exclude(email="")
            .exclude(email__isnull=True)
            .filter(emailaddress__isnull=True)
            .order_by("pk")
        )

        summary = {"created": 0, "skipped": 0, "verified_marked": 0}
        rows = []
        with transaction.atomic():
            for u in orphans:
                already = EmailAddress.objects.filter(
                    user=u, email__iexact=u.email
                ).exists()
                if already:
                    summary["skipped"] += 1
                    continue

                mark_verified = u.username in verified_set
                row = {
                    "pk": u.pk,
                    "username": u.username,
                    "email": u.email,
                    "verified": mark_verified,
                }
                rows.append(row)

                if not dry_run:
                    EmailAddress.objects.create(
                        user=u,
                        email=u.email,
                        primary=True,
                        verified=mark_verified,
                    )
                    AuditLog.objects.create(
                        user=None,
                        action="CREATED",
                        target_type="email_address",
                        target_id=u.pk,
                        details=(
                            "backfill_email_addresses: "
                            f"username={u.username} verified={mark_verified}"
                        ),
                        ip_address="127.0.0.1",
                    )
                    if mark_verified:
                        summary["verified_marked"] += 1
                    summary["created"] += 1

        verb = "WOULD insert" if dry_run else "Inserted"
        self.stdout.write(self.style.NOTICE(f"\n{verb} {len(rows)} row(s):"))
        for r in rows:
            mark = "  [verified=True]" if r["verified"] else ""
            self.stdout.write(
                f"  pk={r['pk']:>3}  {r['username']:<24}  {r['email']}{mark}"
            )
        self.stdout.write("")
        self.stdout.write(
            f"Summary: created={summary['created']}  "
            f"skipped={summary['skipped']}  "
            f"verified_marked={summary['verified_marked']}  "
            f"dry_run={dry_run}"
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\nDRY RUN — no DB writes. Re-run without --dry-run to apply."
                )
            )