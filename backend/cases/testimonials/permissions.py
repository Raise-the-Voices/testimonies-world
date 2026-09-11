"""Permission classes for the testimonials workflow.

Mapping (mirrors the project role matrix in CLAUDE.md):

  - CanSubmitTestimonial:   any authenticated role (volunteer +
                            advocate + admin) can create a draft
                            and submit it for review.
                            Volunteers cannot publish directly.

  - CanReviewTestimonial:   Advocate or is_staff. Required to move a
                            testimonial from `under_review` to
                            `approved` or `rejected`.

  - CanPublishTestimonial:  Advocate or is_staff. Required to move
                            a testimonial from `approved` to
                            `published`, or from `published` to
                            `archived`.

  - CanViewEncryptedSource: Advocate or is_staff. Required to read
                            the decrypted source identity or
                            precise location via the dedicated
                            endpoints. Frontend mirrors this gate
                            with `canDecrypt(user)`.

These match the existing `cases.IsVolunteer` / `cases.IsAdvocate` /
`is_staff` pattern — extending roles here would be a stop-and-ask
change per SYSTEM_RULES §12.
"""

from rest_framework import permissions


def _is_staff_or_advocate(user) -> bool:
    """Helper: True for admin or Advocate group members.

    Volunteers fall through to False — they can read public
    testimonials but never decrypt source identities or precise
    locations, because decryption exposes the same identity that
    source_visibility='hidden' is meant to protect.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    return user.groups.filter(name='Advocate').exists()


class CanSubmitTestimonial(permissions.BasePermission):
    """Allow create + draft edit + submit-to-review.

    Volunteers can write drafts and submit them to the review queue.
    They CANNOT publish directly. Read methods are open via the
    parent `IsAuthenticatedOrReadOnly` chain.
    """

    message = 'You must be authenticated to submit testimonials.'

    def has_permission(self, request, view) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        # Any state-changing write — drafts, edits, submits.
        user = request.user
        return bool(user and user.is_authenticated)


class CanReviewTestimonial(permissions.BasePermission):
    """Approve / reject testimonials — Advocate or Admin only."""

    message = 'Only Advocates or Admins can review testimonials.'

    def has_permission(self, request, view) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        # Object-level check is on the viewset's transition actions;
        # the gate here is for the action route itself.
        return _is_staff_or_advocate(request.user)


class CanPublishTestimonial(permissions.BasePermission):
    """Publish / archive testimonials — Advocate or Admin only."""

    message = 'Only Advocates or Admins can publish testimonials.'

    def has_permission(self, request, view) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        return _is_staff_or_advocate(request.user)


class CanViewEncryptedSource(permissions.BasePermission):
    """Decrypt source identity / precise location.

    This is the only path that can read `source_encrypted` or
    `precise_location_encrypted` plaintext. Gated to Advocate+ on
    the dedicated endpoints; never satisfied for Volunteers even
    when source_visibility != 'hidden' on the row (a volunteer
    reading the public surface should never see who the real
    source was — that's how retaliation risk is contained).
    """

    message = 'Only Advocates or Admins can decrypt source identities.'

    def has_permission(self, request, view) -> bool:
        return _is_staff_or_advocate(request.user)
