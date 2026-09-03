"""
Permission classes for the cases app.

`IsVolunteer` gates write actions on the ReportViewSet. The frontend
already uses the same gate (`isVolunteer(currentUser)` in $lib/session)
to show / hide the "Add report" / "Edit" / "Delete" buttons — the
backend must match, otherwise a non-volunteer who knows the URL could
mutate case data they should only be able to read.

We follow the role table in CLAUDE.md:
  - Public:    no report access
  - Volunteer: read all reports on published persons; create + edit +
               delete their own reports (or any report, if staff/advocate)
  - Advocate:  full read; full write on all reports
  - Admin (is_staff): full read; full write on all reports

The authorship check (`user == instance.created_by`) is enforced
inside `perform_update` / `perform_destroy` on the viewset, not here,
because `has_object_permission` would require a separate object lookup
and the role gate alone is enough at the view level.
"""

from rest_framework import permissions


class IsVolunteer(permissions.BasePermission):
    """Allow mutating actions only to users in the Volunteer / Advocate
    groups, or staff. Read access remains open via the viewset's
    `IsAuthenticatedOrReadOnly` parent."""

    message = 'You must be a Volunteer (or higher) to modify reports.'

    def has_permission(self, request, view) -> bool:
        # Safe methods (GET / HEAD / OPTIONS) are handled by the parent
        # permission_classes chain — we only gate state-changing verbs.
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff:
            return True
        # Volunteer is a superset of Advocate — anyone in Advocate is
        # already a Volunteer at the role-table level. We accept either.
        return user.groups.filter(name__in=['Volunteer', 'Advocate']).exists()
