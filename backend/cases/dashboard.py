"""
Dashboard aggregator — single endpoint that returns a role-scoped
overview for the /dashboard page in the SvelteKit frontend.

Mounted at GET /api/dashboard/ via router.register in
backend/testimonies/urls.py. Returns a hand-rolled dict (no pagination)
because the dashboard consumes it as one cohesive payload, not a
paginated list.

Why a separate viewset and not @action on PersonViewSet?
  The dashboard aggregates Person + Report + CaseworkRecord + Notification
  + AuditLog — none of which are children of Person. Hanging the action
  off PersonViewSet would be a category error. A dedicated viewset with
  IsAuthenticated matches the repo's pattern for cross-cutting,
  role-aware payloads (cf. session_info in urls.py, which is also a
  sibling to the router, not nested under one resource).

Role scoping (matches the existing repo convention):
  staff     — sees all activity, all casework, full summary
  advocate  — sees all casework (CaseworkRecordViewSet.get_queryset
              returns all rows for authenticated users per
              casework/views.py:34), their own activity plus
              casework-tagged activity for context
  volunteer — sees only their own activity and their own casework
"""
from django.db.models import Count, Max, Q
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import permissions, serializers, viewsets
from rest_framework.response import Response

from .models import AuditLog, CaseCategory, Person
from .serializers import PersonListSerializer
from casework.models import CaseworkRecord, Notification


def _scope_for(user) -> str:
    """Coarse role label — kept as a string so the frontend can branch
    on it without re-implementing the role logic. Mirrors the helpers in
    frontend/src/lib/session.ts."""
    if user.is_staff:
        return 'staff'
    if user.groups.filter(name='Advocate').exists():
        return 'advocate'
    return 'volunteer'


def _by_status_counts(qs):
    """Counts by Person.current_status for the published set. Used both
    on the existing /api/persons/statistics/ endpoint and here so the
    dashboard's status breakdown stays consistent with the public stats
    page."""
    return dict(
        qs.values_list('current_status')
        .annotate(c=Count('id'))
        .values_list('current_status', 'c')
    )


def _activity_qs(user):
    """AuditLog rows visible to this user. Staff sees everything;
    advocates see their own activity plus anything tagged 'casework';
    volunteers see only their own activity."""
    if user.is_staff:
        return AuditLog.objects.all()
    if user.groups.filter(name='Advocate').exists():
        return AuditLog.objects.filter(
            Q(user=user) | Q(target_type='casework')
        )
    return AuditLog.objects.filter(user=user)


def _casework_qs(user):
    """CaseworkRecord rows visible to this user. The repo convention
    (casework/views.py:34) is that CaseworkRecordViewSet returns all
    rows to any authenticated user; the dashboard matches that for
    staff and advocate, but scopes to performed_by=user for
    volunteers so the "my open casework" tile is meaningful rather
    than an aggregate count of work they aren't doing."""
    if user.is_staff or user.groups.filter(name='Advocate').exists():
        return CaseworkRecord.objects.all()
    return CaseworkRecord.objects.filter(performed_by=user)


class DashboardViewSet(viewsets.GenericViewSet):
    """Read-only aggregator for the /dashboard page. Single endpoint
    (list, GET only) returning a curated payload."""

    permission_classes = [permissions.IsAuthenticated]
    # No queryset / serializer_class — `list()` builds the response
    # from scratch. GenericViewSet alone gives us the URL routing for
    # `list` without dragging in ModelViewSet's `retrieve`/`create`/
    # `update`/`destroy` machinery that would all 405.

    @extend_schema(
        responses={
            200: OpenApiResponse(
                description='Role-scoped dashboard payload.',
                response=inline_serializer(
                    name='DashboardResponse',
                    fields={
                        'scope': serializers.ChoiceField(
                            choices=['staff', 'advocate', 'volunteer']
                        ),
                        'summary': inline_serializer(
                            name='DashboardSummary',
                            fields={
                                'open_cases': serializers.IntegerField(
                                    help_text='Published persons count.'
                                ),
                                'my_open_casework': serializers.IntegerField(
                                    help_text=(
                                        'Casework records visible to this '
                                        'user with status in (open, '
                                        'in_progress).'
                                    ),
                                ),
                                'unread_notifications': serializers.IntegerField(),
                                'stale_cases': serializers.IntegerField(
                                    help_text=(
                                        'Watchdog count: persons needing '
                                        'attention, capped at 50 by the '
                                        'underlying /api/persons/watchdog/ '
                                        'action.'
                                    ),
                                ),
                            },
                        ),
                        'recent_persons': inline_serializer(
                            name='DashboardPerson',
                            fields={
                                'id': serializers.IntegerField(),
                                'name': serializers.CharField(),
                                'country': serializers.CharField(),
                                'current_status': serializers.CharField(),
                                'updated_at': serializers.DateTimeField(),
                                'profile_image_url': serializers.CharField(
                                    allow_null=True,
                                ),
                            },
                            many=True,
                        ),
                        'recent_reports': inline_serializer(
                            name='DashboardReport',
                            fields={
                                'id': serializers.IntegerField(),
                                'person': serializers.IntegerField(),
                                'person_name': serializers.CharField(),
                                'date_start': serializers.DateField(),
                                'source_type': serializers.CharField(),
                                'is_private': serializers.BooleanField(),
                            },
                            many=True,
                        ),
                        'recent_casework': inline_serializer(
                            name='DashboardCasework',
                            fields={
                                'id': serializers.IntegerField(),
                                'action_type': serializers.CharField(),
                                'status': serializers.CharField(),
                                'date': serializers.DateField(),
                                'description': serializers.CharField(),
                                'performed_by_name': serializers.CharField(
                                    allow_null=True,
                                ),
                                'person_ids': serializers.ListField(
                                    child=serializers.IntegerField(),
                                ),
                            },
                            many=True,
                        ),
                        'activity': inline_serializer(
                            name='DashboardActivityEntry',
                            fields={
                                'id': serializers.IntegerField(),
                                'timestamp': serializers.DateTimeField(),
                                'user': serializers.CharField(
                                    allow_null=True,
                                    help_text='Username, or null for anonymous.',
                                ),
                                'action': serializers.CharField(),
                                'target_type': serializers.CharField(),
                                'target_id': serializers.IntegerField(),
                                'details': serializers.CharField(),
                                'ip_address': serializers.CharField(
                                    allow_null=True,
                                ),
                            },
                            many=True,
                        ),
                        'by_status': serializers.DictField(
                            child=serializers.IntegerField(),
                            help_text=(
                                'Person count grouped by current_status '
                                '(detained, disappeared, released, '
                                'deceased, etc.). Mirrors '
                                '/api/persons/statistics/ for '
                                'consistency with the public stats page.'
                            ),
                        ),
                    },
                ),
            ),
        },
    )
    def list(self, request):
        user = request.user

        # Summary tiles ------------------------------------------------------------
        published_qs = Person.objects.filter(is_published=True)
        open_cases = published_qs.count()

        my_open_casework = _casework_qs(user).filter(
            status__in=[CaseworkRecord.Status.OPEN, CaseworkRecord.Status.IN_PROGRESS],
        ).count()

        unread_notifications = Notification.objects.filter(
            recipient=user, is_read=False,
        ).count()

        # "Stale cases" = published persons currently needing attention
        # (i.e., NOT released and NOT deceased — the same exclusion the
        # /api/persons/watchdog/ action uses, cases/views.py:230). The
        # watchdog action slices the *list* to 50; we want the *count*
        # of the full backlog so the dashboard tile reflects reality.
        stale_cases = (
            Person.objects.filter(is_published=True)
            .exclude(current_status__in=['released', 'deceased'])
            .count()
        )

        # Recent items -------------------------------------------------------------
        # `recent_persons`: last 5 published persons the user can see.
        # Anyone authenticated can read published persons, so no role
        # scoping needed. `profile_image` is an ImageField on the same
        # row, not a relation — no select_needed.
        recent_persons_qs = (
            Person.objects.filter(is_published=True)
            .order_by('-updated_at')[:5]
        )
        recent_persons_data = PersonListSerializer(
            recent_persons_qs, many=True, context={'request': request},
        ).data

        # `recent_reports`: lightweight payload (no narrative, no media
        # files). We deliberately avoid the full ReportSerializer to
        # keep the dashboard payload small — the user clicks through to
        # the person detail page to see the full report.
        from .models import Report
        recent_reports = list(
            Report.objects.select_related('person', 'created_by')
            .order_by('-created_at')[:5]
            .values(
                'id', 'person_id', 'person__name',
                'date_start', 'source_type', 'is_private',
            )
        )
        recent_reports_data = [
            {
                'id': r['id'],
                'person': r['person_id'],
                'person_name': r['person__name'],
                'date_start': r['date_start'],
                'source_type': r['source_type'],
                'is_private': r['is_private'],
            }
            for r in recent_reports
        ]

        # `recent_casework`: scoped to the user by the helper above.
        recent_casework_qs = (
            _casework_qs(user)
            .select_related('performed_by')
            .prefetch_related('persons')
            .order_by('-updated_at')[:5]
        )
        recent_casework_data = [
            {
                'id': cw.id,
                'action_type': cw.action_type,
                'status': cw.status,
                'date': cw.date,
                'description': cw.description,
                'performed_by_name': (
                    cw.performed_by.get_full_name() or cw.performed_by.username
                    if cw.performed_by else None
                ),
                'person_ids': list(cw.persons.values_list('id', flat=True)),
            }
            for cw in recent_casework_qs
        ]

        # `activity`: last 10 AuditLog rows scoped by role.
        activity_data = list(
            _activity_qs(user)
            .select_related('user')
            .order_by('-timestamp')[:10]
            .values(
                'id', 'timestamp', 'user__username',
                'action', 'target_type', 'target_id', 'details', 'ip_address',
            )
        )
        activity_data = [
            {
                'id': row['id'],
                'timestamp': row['timestamp'],
                'user': row['user__username'],
                'action': row['action'],
                'target_type': row['target_type'],
                'target_id': row['target_id'],
                'details': row['details'] or '',
                'ip_address': row['ip_address'],
            }
            for row in activity_data
        ]

        # Category counts — also from /api/persons/statistics/, for the
        # status-breakdown widget and any future category breakdown.
        # Cheap because CaseCategory has a small row count.
        # (Kept as a hook for v2; not in the response shape yet.)

        return Response({
            'scope': _scope_for(user),
            'summary': {
                'open_cases': open_cases,
                'my_open_casework': my_open_casework,
                'unread_notifications': unread_notifications,
                'stale_cases': stale_cases,
            },
            'recent_persons': recent_persons_data,
            'recent_reports': recent_reports_data,
            'recent_casework': recent_casework_data,
            'activity': activity_data,
            'by_status': _by_status_counts(published_qs),
        })
