"""
Performance regression tests.

Don't measure wall-clock time (flaky in CI). Assert an upper
bound on the number of queries each hot endpoint issues, so a
refactor that re-introduces an N+1 fails this test even if the
endpoint still returns 200.

Upper bounds are calibrated against the prefetch wiring in this
PR — they give ~50% headroom for legitimate additions (e.g. a
new prefetched relation) but fail loudly if a query count
roughly doubles.
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from casework.models import CaseworkRecord
from testimonies.test_base import BaseTestCase

from .models import CaseCategory, Person, Report
from .tests import make_user


User = get_user_model()


class PersonListQueryCountTests(BaseTestCase):
    """Per-page query count for /api/persons/ list.

    Authenticated volunteer, 10 published persons, each with one
    category and one report. /api/persons/ list returns
    PersonListSerializer which walks created_by / categories /
    media_files / reports; the viewset select_relateds and
    prefetches all of them. Measured in CI: ~10 queries (auth
    + paginated COUNT + Person SELECT + 4 prefetches + 2
    framework queries). 15 leaves headroom for future additions.
    """

    def setUp(self):
        self.volunteer = make_user('vol', in_group='Volunteer')
        self.client = APIClient()
        self.client.force_login(self.volunteer)
        self.cat = CaseCategory.objects.create(name='Journalist')
        for i in range(10):
            p = Person.objects.create(
                name=f'P{i}', country='Y', is_published=True,
            )
            p.categories.add(self.cat)
            Report.objects.create(
                person=p, narrative=f'narrative {i}',
                source_type=Report.SourceType.FIRSTHAND,
            )

    def test_list_under_15_queries(self):
        with CaptureQueriesContext(connection) as ctx:
            res = self.client.get('/api/persons/')
        self.assertEqual(res.status_code, 200)
        n = len(ctx.captured_queries)
        self.assertLess(
            n, 15,
            f'/api/persons/ issued {n} queries — N+1? '
            f'Captured:\n' + '\n'.join(str(q['sql']) for q in ctx.captured_queries),
        )

    def test_watchdog_under_8_queries(self):
        """Watchdog gates the heavy prefetches off (only categories +
        media_files + reports for the Max annotation). Measured in
        CI: 6 queries for 10 published persons."""
        with CaptureQueriesContext(connection) as ctx:
            res = self.client.get('/api/persons/watchdog/')
        self.assertEqual(res.status_code, 200)
        n = len(ctx.captured_queries)
        self.assertLess(
            n, 8,
            f'/api/persons/watchdog/ issued {n} queries',
        )

    def test_related_under_15_queries(self):
        """Related-persons action returns PersonListSerializer for up
        to 6 rows. Measured in CI: 11 queries (auth + get_object +
        target.categories + main query + 3 prefetches)."""
        target = Person.objects.create(name='Target', country='Y', is_published=True)
        with CaptureQueriesContext(connection) as ctx:
            res = self.client.get(f'/api/persons/{target.pk}/related/')
        self.assertEqual(res.status_code, 200)
        n = len(ctx.captured_queries)
        self.assertLess(
            n, 15,
            f'/api/persons/{{id}}/related/ issued {n} queries',
        )


class ReportListQueryCountTests(BaseTestCase):
    """Per-page query count for /api/reports/ list.

    Authenticated volunteer, 10 reports on 10 published persons.
    ReportSerializer walks person / created_by / media_files; the
    viewset select_relateds person+created_by and prefetches
    media_files. Budget: ~8 queries.
    """

    def setUp(self):
        self.volunteer = make_user('vol', in_group='Volunteer')
        self.client = APIClient()
        self.client.force_login(self.volunteer)
        for i in range(10):
            p = Person.objects.create(name=f'P{i}', country='Y', is_published=True)
            Report.objects.create(
                person=p, narrative=f'narrative {i}',
                source_type=Report.SourceType.FIRSTHAND,
            )

    def test_list_under_10_queries(self):
        with CaptureQueriesContext(connection) as ctx:
            res = self.client.get('/api/reports/')
        self.assertEqual(res.status_code, 200)
        n = len(ctx.captured_queries)
        self.assertLess(
            n, 10,
            f'/api/reports/ issued {n} queries',
        )


class CaseworkQueryCountTests(BaseTestCase):
    """Per-page query count for /api/casework/ list.

    Authenticated advocate, 5 casework records. Serializer walks
    performed_by / persons / seen-by notifications. The viewset
    select_relateds performed_by and prefetches persons + a
    filtered notifications Prefetch. Budget: ~12 queries.
    """

    def setUp(self):
        self.adv = make_user('aisha', in_group='Advocate')
        self.client = APIClient()
        self.client.force_login(self.adv)
        for i in range(5):
            CaseworkRecord.objects.create(
                action_type=CaseworkRecord.ActionType.OTHER,
                description=f'd {i}',
                date=date(2026, 1, 1),
                performed_by=self.adv,
            )

    def test_list_under_15_queries(self):
        with CaptureQueriesContext(connection) as ctx:
            res = self.client.get('/api/casework/')
        self.assertEqual(res.status_code, 200)
        n = len(ctx.captured_queries)
        self.assertLess(
            n, 15,
            f'/api/casework/ issued {n} queries',
        )


class AuditLogQueryCountTests(BaseTestCase):
    """Per-page query count for /api/audit-logs/ list.

    Staff user; 10 audit rows. ViewSet select_relateds user.
    Default ordering is -timestamp. Budget: ~5 queries.
    """

    def setUp(self):
        self.staff = make_user('admin', is_staff=True)
        self.client = APIClient()
        self.client.force_login(self.staff)
        from cases.models import AuditLog
        for i in range(10):
            AuditLog.objects.create(
                user=self.staff,
                action=AuditLog.Action.EDITED,
                target_type='person',
                target_id=i + 1,
            )

    def test_list_under_8_queries(self):
        with CaptureQueriesContext(connection) as ctx:
            res = self.client.get('/api/audit-logs/')
        self.assertEqual(res.status_code, 200)
        n = len(ctx.captured_queries)
        self.assertLess(
            n, 8,
            f'/api/audit-logs/ issued {n} queries',
        )
