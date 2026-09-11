"""Delete gibberish Testimonials that landed in the DB before the
client-side validation gate landed on `feat/testimonials-frontend`
(commit 9b11b51). One-shot cleanup command. Re-runnable; idempotent
on a clean DB (no rows match the heuristic).

Heuristic (matches the frontend's `validate()` on
`/testimonials/new`):

  - Title is empty / single-letter / <5 characters
  - Title, summary, or narrative is pure-punctuation / whitespace
    or a single-character-spam pattern like 'aaaaa' / '-----'
  - Country/region strings <2 chars
  - Narrative is empty or <50 chars

Matches across all statuses (draft / under_review / approved /
published / archived) — historically the user submitted gibberish
that hasn't transitioned. Edit the status filter below to scope
the cleanup to a specific state.

Audit: every deletion writes an AuditLog row (per SYSTEM_RULES §5:
audit-log every CRUD op on a sensitive viewset — Testimonials are
sensitive by design). The AuditLog row is the only surviving trace
after DELETE, so future "why was X removed?" questions have an
answer.

Usage:

  # Preview the matches without deleting:
  python manage.py cleanup_gibberish_testimonials --dry-run

  # Actually delete (after `--dry-run` output is reviewed):
  python manage.py cleanup_gibberish_testimonials

  # Limit to a specific status:
  python manage.py cleanup_gibberish_testimonials --status draft

Exit code 0 in all paths; in non-dry-run mode, prints the number of
rows deleted at the end.
"""

import re

from django.core.management.base import BaseCommand

from cases.models import AuditLog, Testimonial


# Same pattern the frontend's `validate()` uses — keeps the
# cleanup rule in sync with what the form would have rejected.
SPAM_PATTERN = re.compile(r"^[\W_]+$|^(.)\1{4,}$")


class Command(BaseCommand):
    help = (
        "Delete Testimonial rows whose content looks like gibberish "
        "from before the client-side validation gate was added."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print which rows match and exit without deleting.",
        )
        parser.add_argument(
            "--status",
            default=None,
            help=(
                "Optional status filter. Pass e.g. 'draft' to limit the "
                "cleanup to one bucket. Default: every status."
            ),
        )

    # ------------------------------------------------------------------
    # Heuristic — kept identical to the frontend's `validate()` so
    # the cleanup deletes the rows the form WOULD have rejected.
    # ------------------------------------------------------------------
    @staticmethod
    def _is_gibberish(t: Testimonial) -> tuple[bool, str]:
        """Return (match, reason). `reason` is human-readable for the
        dry-run report."""
        title = (t.title or "").strip()
        summary = (t.summary or "").strip()
        narrative = (t.narrative or "").strip()
        country = (t.country or "").strip()
        region = (t.region or "").strip()

        if not title:
            return True, "title is empty"
        if len(title) < 5:
            return True, f"title is too short ({len(title)} chars): {title!r}"
        if SPAM_PATTERN.match(title):
            return True, f"title is spam pattern: {title!r}"
        if len(country) < 2:
            return True, f"country is too short ({len(country)} chars): {country!r}"
        if SPAM_PATTERN.match(country):
            return True, f"country is spam pattern: {country!r}"
        if len(region) < 2:
            return True, f"region is too short ({len(region)} chars): {region!r}"
        if SPAM_PATTERN.match(region):
            return True, f"region is spam pattern: {region!r}"
        if not summary:
            return True, "summary is empty"
        if len(summary) < 20:
            return True, f"summary too short ({len(summary)} chars): {summary!r}"
        if SPAM_PATTERN.match(summary):
            return True, f"summary is spam pattern: {summary!r}"
        if not narrative:
            return True, "narrative is empty"
        if len(narrative) < 50:
            return True, f"narrative too short ({len(narrative)} chars): {narrative!r}"
        if SPAM_PATTERN.match(narrative):
            return True, f"narrative is spam pattern"
        return False, ""

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        status_filter = options["status"]

        qs = Testimonial.objects.all()
        if status_filter:
            qs = qs.filter(status=status_filter)

        matches = []
        for t in qs:
            is_gib, reason = self._is_gibberish(t)
            if is_gib:
                matches.append((t, reason))

        if not matches:
            self.stdout.write("No gibberish testimonials matched.")
            return

        self.stdout.write(self.style.WARNING(
            f"Found {len(matches)} gibberish testimonial(s):"
        ))
        # Tabulate for readability. Truncate long reasons at 60 chars.
        for t, reason in matches:
            short = (reason[:60] + "…") if len(reason) > 60 else reason
            self.stdout.write(
                f"  #{t.id:>4}  [{t.status:14}]  {short}"
            )

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "\nDRY RUN — no rows deleted. "
                "Re-run without --dry-run to actually delete."
            ))
            return

        # Each deletion gets an AuditLog row. SYSTEM_RULES §5 requires
        # this for every CRUD op on a sensitive viewset; Testimonials
        # are sensitive by design (encrypted source/precise-location).
        deleted = 0
        for t, reason in matches:
            details = (
                f"cleanup_gibberish_testimonials: removed row "
                f"(reason={reason!r}; title={t.title!r}; "
                f"summary={t.summary!r})"
            )
            AuditLog.objects.create(
                # No requesting user — this is a system-level cleanup
                # command, not a user CRUD op.
                user=None,
                action=AuditLog.Action.DELETED,
                target_type="testimonial",
                target_id=t.pk,
                details=details,
                ip_address=None,
            )
            t.delete()
            deleted += 1

        self.stdout.write(self.style.SUCCESS(
            f"Deleted {deleted} testimonial(s). AuditLog rows written."
        ))
