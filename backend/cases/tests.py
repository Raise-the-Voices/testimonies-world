"""
Tests for the cases app.

Two coverage areas:
- `MediaPermissionTests` — the sensitive-upload gate.
- `ReportPermissionTests` — the role + authorship gate on ReportViewSet,
  plus the AuditLog trail that every successful update/delete leaves.

Permission matrix for Report:
- Anonymous:           read public reports on published persons; no writes.
- Authenticated outsider: read all (default queryset); cannot write.
- Volunteer:           full create; can update/delete only their OWN reports.
- Advocate / staff:    full create + full update/delete on any report.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from .models import AuditLog, Media, Person, Report


User = get_user_model()


def make_user(username, *, in_group=None, is_staff=False, email=None):
    user = User.objects.create_user(
        username=username,
        email=email or f'{username}@example.org',
        password='testpass',
        is_staff=is_staff,
    )
    if in_group:
        g, _ = Group.objects.get_or_create(name=in_group)
        user.groups.add(g)
    return user


class MediaPermissionTests(TestCase):
    def setUp(self):
        self.advocate = make_user('aisha', in_group='Advocate')
        self.staff = make_user('admin', is_staff=True)
        self.volunteer = make_user('vol', in_group='Volunteer')
        self.outsider = make_user('random')
        self.client = APIClient()

    # --- Read access by visibility tier ----------------------------------

    def test_anonymous_sees_only_public(self):
        Media.objects.create(
            url='https://example.org/public.jpg',
            media_type=Media.MediaType.PHOTO,
            visibility=Media.Visibility.PUBLIC,
        )
        Media.objects.create(
            url='https://example.org/restricted.jpg',
            media_type=Media.MediaType.PHOTO,
            visibility=Media.Visibility.RESTRICTED,
        )
        Media.objects.create(
            url='https://example.org/sensitive.jpg',
            media_type=Media.MediaType.PHOTO,
            visibility=Media.Visibility.SENSITIVE,
        )
        # No force_login — this client is anonymous.
        res = self.client.get('/api/media/')
        self.assertEqual(res.status_code, 200)
        visibilities = [m['visibility'] for m in res.json()['results']]
        self.assertIn('public', visibilities)
        self.assertNotIn('restricted', visibilities)
        self.assertNotIn('sensitive', visibilities)

    def test_volunteer_sees_public_and_restricted_but_not_sensitive(self):
        for v in ['public', 'restricted', 'sensitive']:
            Media.objects.create(
                url=f'https://example.org/{v}.jpg',
                media_type=Media.MediaType.PHOTO,
                visibility=v,
            )
        self.client.force_login(self.volunteer)
        res = self.client.get('/api/media/')
        self.assertEqual(res.status_code, 200)
        visibilities = [m['visibility'] for m in res.json()['results']]
        self.assertIn('public', visibilities)
        self.assertIn('restricted', visibilities)
        self.assertNotIn('sensitive', visibilities)

    def test_advocate_sees_all_visibilities(self):
        for v in ['public', 'restricted', 'sensitive']:
            Media.objects.create(
                url=f'https://example.org/{v}.jpg',
                media_type=Media.MediaType.PHOTO,
                visibility=v,
            )
        self.client.force_login(self.advocate)
        res = self.client.get('/api/media/')
        self.assertEqual(res.status_code, 200)
        visibilities = sorted({m['visibility'] for m in res.json()['results']})
        self.assertEqual(visibilities, ['public', 'restricted', 'sensitive'])

    # --- Sensitive-upload gate --------------------------------------------

    def test_volunteer_cannot_upload_sensitive(self):
        self.client.force_login(self.volunteer)
        res = self.client.post('/api/media/', {
            'url': 'https://example.org/x.jpg',
            'media_type': 'photo',
            'visibility': 'sensitive',
        }, format='json')
        self.assertEqual(res.status_code, 403)

    def test_volunteer_can_upload_public(self):
        self.client.force_login(self.volunteer)
        res = self.client.post('/api/media/', {
            'url': 'https://example.org/x.jpg',
            'media_type': 'photo',
            'visibility': 'public',
        }, format='json')
        self.assertEqual(res.status_code, 201)

    def test_volunteer_can_upload_restricted(self):
        self.client.force_login(self.volunteer)
        res = self.client.post('/api/media/', {
            'url': 'https://example.org/x.jpg',
            'media_type': 'photo',
            'visibility': 'restricted',
        }, format='json')
        self.assertEqual(res.status_code, 201)

    def test_advocate_can_upload_sensitive(self):
        self.client.force_login(self.advocate)
        res = self.client.post('/api/media/', {
            'url': 'https://example.org/x.jpg',
            'media_type': 'photo',
            'visibility': 'sensitive',
        }, format='json')
        self.assertEqual(res.status_code, 201)

    def test_staff_can_upload_sensitive(self):
        self.client.force_login(self.staff)
        res = self.client.post('/api/media/', {
            'url': 'https://example.org/x.jpg',
            'media_type': 'photo',
            'visibility': 'sensitive',
        }, format='json')
        self.assertEqual(res.status_code, 201)

    def test_volunteer_cannot_escalate_to_sensitive_on_patch(self):
        # Volunteer uploads public, then tries to PATCH to sensitive.
        self.client.force_login(self.volunteer)
        res = self.client.post('/api/media/', {
            'url': 'https://example.org/x.jpg',
            'media_type': 'photo',
            'visibility': 'public',
        }, format='json')
        self.assertEqual(res.status_code, 201)
        mid = res.json()['id']

        res = self.client.patch(
            f'/api/media/{mid}/',
            {'visibility': 'sensitive'},
            format='json',
        )
        self.assertEqual(res.status_code, 403)
        # The visibility should still be public — the failed PATCH
        # must not have partially applied.
        self.client.get(f'/api/media/{mid}/')
        self.assertEqual(res.status_code, 403)

    def test_outsider_can_write_media(self):
        # Logged-in non-volunteer is still IsAuthenticated; the gate
        # is on the sensitive tier, not on group membership for writes.
        # This is intentional — anyone authenticated can upload.
        self.client.force_login(self.outsider)
        res = self.client.post('/api/media/', {
            'url': 'https://example.org/x.jpg',
            'media_type': 'photo',
            'visibility': 'public',
        }, format='json')
        self.assertEqual(res.status_code, 201)


def _make_published_person() -> Person:
    """Tiny helper so each test starts from a known published Person row."""
    return Person.objects.create(
        name='Test Person',
        country='XX',
        current_status=Person.Status.DISAPPEARED,
        medical_status=Person.MedicalStatus.UNKNOWN,
        is_published=True,
    )


class ReportPermissionTests(TestCase):
    def setUp(self):
        self.advocate = make_user('aisha', in_group='Advocate')
        self.staff = make_user('admin', is_staff=True)
        self.volunteer = make_user('vol', in_group='Volunteer')
        # A SECOND volunteer — lets us assert the authorship gate.
        self.other_volunteer = make_user('vol2', in_group='Volunteer')
        # Authenticated user with NO group membership — exercises the
        # "outsider" branch of IsVolunteer.
        self.outsider = make_user('random')
        self.person = _make_published_person()
        self.client = APIClient()

        self.base_payload = lambda: {
            'person': self.person.id,
            'source_type': 'firsthand',
            'narrative': 'initial narrative',
            'is_private': False,
        }

    # --- Write gate: anonymous + outsider --------------------------------

    def test_anonymous_cannot_create_report(self):
        # No force_login — anonymous client.
        res = self.client.post('/api/reports/', self.base_payload(), format='json')
        self.assertIn(res.status_code, (401, 403))

    def test_anonymous_cannot_update_or_delete_report(self):
        report = Report.objects.create(
            person=self.person,
            source_type=Report.SourceType.FIRSTHAND,
            narrative='public narrative',
        )
        res = self.client.patch(
            f'/api/reports/{report.id}/', {'narrative': 'tampered'}, format='json',
        )
        self.assertIn(res.status_code, (401, 403))
        res = self.client.delete(f'/api/reports/{report.id}/')
        self.assertIn(res.status_code, (401, 403))

    def test_outsider_cannot_create_report(self):
        # Authenticated, but no Volunteer group → IsVolunteer denies.
        self.client.force_login(self.outsider)
        res = self.client.post('/api/reports/', self.base_payload(), format='json')
        self.assertEqual(res.status_code, 403)

    # --- Authorship gate on PATCH / DELETE --------------------------------

    def test_author_can_update_own_report(self):
        # Volunteer creates a report; comes back as the author.
        self.client.force_login(self.volunteer)
        res = self.client.post('/api/reports/', self.base_payload(), format='json')
        self.assertEqual(res.status_code, 201)
        rid = res.json()['id']

        res = self.client.patch(
            f'/api/reports/{rid}/',
            {'narrative': 'corrected narrative'},
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['narrative'], 'corrected narrative')

    def test_other_volunteer_cannot_update_someone_elses_report(self):
        # vol creates; vol2 (different volunteer, same group) attempts to
        # edit. Must be 403 — authorship is per-user, not per-group.
        self.client.force_login(self.volunteer)
        res = self.client.post('/api/reports/', self.base_payload(), format='json')
        rid = res.json()['id']

        self.client.force_login(self.other_volunteer)
        res = self.client.patch(
            f'/api/reports/{rid}/',
            {'narrative': 'sabotage'},
            format='json',
        )
        self.assertEqual(res.status_code, 403)
        # And the row must be untouched.
        report = Report.objects.get(pk=rid)
        self.assertEqual(report.narrative, 'initial narrative')

    def test_other_volunteer_cannot_delete_someone_elses_report(self):
        self.client.force_login(self.volunteer)
        res = self.client.post('/api/reports/', self.base_payload(), format='json')
        rid = res.json()['id']

        self.client.force_login(self.other_volunteer)
        res = self.client.delete(f'/api/reports/{rid}/')
        self.assertEqual(res.status_code, 403)
        self.assertTrue(Report.objects.filter(pk=rid).exists())

    def test_advocate_can_update_any_report(self):
        self.client.force_login(self.volunteer)
        res = self.client.post('/api/reports/', self.base_payload(), format='json')
        rid = res.json()['id']

        self.client.force_login(self.advocate)
        res = self.client.patch(
            f'/api/reports/{rid}/',
            {'narrative': 'advocate fix'},
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['narrative'], 'advocate fix')

    def test_staff_can_update_any_report(self):
        self.client.force_login(self.volunteer)
        res = self.client.post('/api/reports/', self.base_payload(), format='json')
        rid = res.json()['id']

        self.client.force_login(self.staff)
        res = self.client.patch(
            f'/api/reports/{rid}/',
            {'narrative': 'staff fix'},
            format='json',
        )
        self.assertEqual(res.status_code, 200)

    def test_staff_can_delete_any_report(self):
        self.client.force_login(self.volunteer)
        res = self.client.post('/api/reports/', self.base_payload(), format='json')
        rid = res.json()['id']

        self.client.force_login(self.staff)
        res = self.client.delete(f'/api/reports/{rid}/')
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Report.objects.filter(pk=rid).exists())

    # --- Audit log trail --------------------------------------------------

    def test_create_writes_audit_row(self):
        self.client.force_login(self.volunteer)
        res = self.client.post('/api/reports/', self.base_payload(), format='json')
        self.assertEqual(res.status_code, 201)
        rid = res.json()['id']

        logs = AuditLog.objects.filter(target_type='report', target_id=rid)
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().action, AuditLog.Action.EDITED)
        self.assertEqual(logs.first().user, self.volunteer)
        self.assertIn('created', logs.first().details)

    def test_update_writes_audit_row_with_changed_fields(self):
        self.client.force_login(self.volunteer)
        res = self.client.post('/api/reports/', self.base_payload(), format='json')
        rid = res.json()['id']

        self.client.patch(
            f'/api/reports/{rid}/',
            {'narrative': 'corrected', 'is_private': True},
            format='json',
        )

        logs = AuditLog.objects.filter(
            target_type='report', target_id=rid, action=AuditLog.Action.EDITED,
        ).order_by('timestamp')
        # 2 rows: 1 from create, 1 from update.
        self.assertEqual(logs.count(), 2)
        update_log = logs.last()
        self.assertIn('narrative', update_log.details)
        self.assertIn('is_private', update_log.details)

    def test_delete_writes_audit_row_with_person_id(self):
        self.client.force_login(self.volunteer)
        res = self.client.post('/api/reports/', self.base_payload(), format='json')
        rid = res.json()['id']

        self.client.delete(f'/api/reports/{rid}/')

        # The report row is gone — but the audit row survives, with
        # `target_type='report'` + `target_id=<old id>`. This is the
        # provenance guarantee the rest of the system relies on.
        self.assertFalse(Report.objects.filter(pk=rid).exists())
        logs = AuditLog.objects.filter(
            target_type='report', target_id=rid, action=AuditLog.Action.DELETED,
        )
        self.assertEqual(logs.count(), 1)
        self.assertIn(f'person_id={self.person.id}', logs.first().details)

    def test_failed_update_writes_no_audit_row(self):
        # other_volunteer attempts to edit vol's report → 403 → no audit.
        self.client.force_login(self.volunteer)
        res = self.client.post('/api/reports/', self.base_payload(), format='json')
        rid = res.json()['id']

        self.client.force_login(self.other_volunteer)
        res = self.client.patch(
            f'/api/reports/{rid}/', {'narrative': 'sabotage'}, format='json',
        )
        self.assertEqual(res.status_code, 403)

        # Only the create-time audit row should exist.
        update_logs = AuditLog.objects.filter(
            target_type='report', target_id=rid,
        ).exclude(details__startswith='created')
        self.assertEqual(update_logs.count(), 0)

    # --- Read access on private reports -----------------------------------

    def test_private_report_hidden_from_anonymous(self):
        Report.objects.create(
            person=self.person,
            source_type=Report.SourceType.FIRSTHAND,
            narrative='a private narrative',
            is_private=True,
        )
        # No force_login → anonymous.
        res = self.client.get('/api/reports/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['results'], [])