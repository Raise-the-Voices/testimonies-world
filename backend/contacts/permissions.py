"""
Permission classes for the contacts app.

`IsAdvocate` gates the contacts API on the Advocate group (or staff). The
page itself enforces the same check in the frontend; the backend must
match, otherwise a non-advocate who knows the URL gets read/write access
to a list of always-private contacts (name, email, phone, signal handle).

We follow the project's role table in CLAUDE.md:
  - Public: no contact access
  - Volunteer: no contact access
  - Advocate: contacts (read + write)
  - Admin (is_staff): contacts (read + write)
"""

from rest_framework import permissions


class IsAdvocate(permissions.BasePermission):
    """Allow access only to users in the Advocate group or staff."""

    message = 'You must be an Advocate to manage contacts.'

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff:
            return True
        return user.groups.filter(name='Advocate').exists()