"""
bootstrap_e2e_fixtures — one-shot seed for the Playwright E2E suite.

Idempotent. Re-runnable. Creates (if missing):

  - The `Advocate` group (matches backend/CLAUDE.md).
  - The `e2e-advocate` user with no usable password (the E2E
    bootstrap never sends a password; it uses the
    /__test__/login/ token-gated endpoint — see
    cases/test_auth.py for the security model).
  - One fresh testimonial in UNDER_REVIEW status owned by an
    `admin` user (NOT by `e2e-advocate` — the spec is testing
    a rejection *of someone else's* draft, which is the realistic
    case).

Usage:

    backend/.venv/bin/python backend/scripts/bootstrap_e2e_fixtures.py

Reads no env, takes no args. Safe to run any time.

The script writes its work to stdout (one line per action) so a
caller can grep for FAIL or SKIP. Exit 0 on success, non-zero
if Django itself can't bootstrap.
"""

import os
import sys

import django

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testimonies.settings")
django.setup()

from django.contrib.auth.models import Group, User  # noqa: E402

from cases.models import Testimonial  # noqa: E402


def _ensure_group(name: str) -> Group:
    group, created = Group.objects.get_or_create(name=name)
    print(("CREATED " if created else "EXISTS  ") + f"group {name!r}")
    return group


def _ensure_advocate_user(group: Group) -> User:
    user, created = User.objects.get_or_create(
        username="e2e-advocate",
        defaults={"email": "e2e-advocate@example.org", "is_active": True},
    )
    if created:
        # The E2E bootstrap never uses passwords — set unusable so
        # an accidental password login attempt can't be brute-forced.
        user.set_unusable_password()
        user.save()
        print("CREATED  user 'e2e-advocate' (unusable password)")
    else:
        print("EXISTS   user 'e2e-advocate'")

    if not user.groups.filter(pk=group.pk).exists():
        user.groups.add(group)
        print("ADDED    'e2e-advocate' -> Advocate group")
    else:
        print("EXISTS   'e2e-advocate' in Advocate group")
    return user


def _ensure_under_review_fixture() -> None:
    # Clear any prior fixtures so the spec always has exactly one
    # card to click. The test transitions the row to REJECTED, so
    # re-running without re-seeding would land on an empty queue
    # and the spec would fail at the "click first card" step.
    deleted, _ = Testimonial.objects.filter(slug__startswith="pw-e2e-").delete()
    if deleted:
        print(f"REMOVED  {deleted} prior pw-e2e-* fixture(s)")

    # Author is intentionally NOT e2e-advocate — the spec verifies
    # an advocate acting on someone else's draft. `admin` is the
    # canonical superuser seeded by Django; if absent we surface
    # the error instead of silently switching authors.
    author = User.objects.get(username="admin")
    t = Testimonial.objects.create(
        title="Playwright E2E fixture",
        slug="pw-e2e-fixture-reject",
        country="US",
        region="CA",
        language="en",
        summary="Synthetic testimonial for the Playwright E2E reject workflow.",
        narrative=(
            "A synthetic testimonial created by bootstrap_e2e_fixtures.py so "
            "the Review queue always has at least one under_review row for "
            "the advocate spec. Safe to delete at any time."
        ),
        outcome="Outcome not yet determined.",
        source_visibility="hidden",
        location_visibility="public_region",
        status="under_review",
        submitted_by=author,
        reviewed_by=None,
        reviewed_at=None,
        review_notes="",
        family_protected=True,
        contact_protected=True,
    )
    print(f"CREATED  fixture id={t.id} status={t.status}")


def main() -> int:
    group = _ensure_group("Advocate")
    _ensure_advocate_user(group)
    _ensure_under_review_fixture()

    print()
    print("=== Summary ===")
    print(
        "  under_review rows:",
        Testimonial.objects.filter(status="under_review").count(),
    )
    print(
        "  e2e-advocate in Advocate group:",
        User.objects.get(username="e2e-advocate")
        .groups.filter(name="Advocate")
        .exists(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())