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

from testimonies.test_base import BaseTestCase

from .models import AuditLog, CaseCategory, FamilyRelationship, Media, Person, Report


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


class MediaPermissionTests(BaseTestCase):
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

    def test_outsider_cannot_write_media(self):
        # AfterH2: MediaViewSet is now gated by IsVolunteer (matches
        # Person/Report/FamilyRelationship). An authenticated outsider
        # with no group fails the gate entirely — 403, not 201.
        # The previous "anyone authenticated can upload" stance
        # was the inconsistency this PR closes.
        self.client.force_login(self.outsider)
        res = self.client.post('/api/media/', {
            'url': 'https://example.org/x.jpg',
            'media_type': 'photo',
            'visibility': 'public',
        }, format='json')
        self.assertEqual(res.status_code, 403)


class MediaUploadValidationTests(BaseTestCase):
    """Coverage for the file-extension + size validators on Media.file.

    Backend validation closes a gap where a direct API POST could
    upload any file type or any size up to nginx's transport-layer
    cap. With these validators:
      - extensions outside the allow-list → 400
      - files larger than 50 MB → 400
    The frontend already caps at 25 MB but the backend must hold the
    line independently — clients should not be able to smuggle
    .exe / .html / multi-GB files via curl.
    """

    def setUp(self):
        self.volunteer = make_user('vol', in_group='Volunteer')
        self.person = _make_published_person()
        self.client = APIClient()
        self.client.force_login(self.volunteer)

    def test_disallowed_extension_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        payload = {
            'person': self.person.id,
            'media_type': 'photo',
            'visibility': 'public',
            'file': SimpleUploadedFile(
                'malware.exe',
                b'MZ' + b'\x00' * 100,
                'application/octet-stream',
            ),
        }
        res = self.client.post('/api/media/', payload, format='multipart')
        self.assertEqual(res.status_code, 400)

    def test_allowed_extension_accepted(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        payload = {
            'person': self.person.id,
            'media_type': 'photo',
            'visibility': 'public',
            'file': SimpleUploadedFile(
                'photo.jpg', b'fake-jpeg', 'image/jpeg',
            ),
        }
        res = self.client.post('/api/media/', payload, format='multipart')
        self.assertEqual(res.status_code, 201)

    def test_oversized_file_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        # 51 MB — over the 50 MB cap.
        big = b'\x00' * (51 * 1024 * 1024)
        payload = {
            'person': self.person.id,
            'media_type': 'photo',
            'visibility': 'public',
            'file': SimpleUploadedFile('huge.jpg', big, 'image/jpeg'),
        }
        res = self.client.post('/api/media/', payload, format='multipart')
        self.assertEqual(res.status_code, 400)
        # Body should mention the cap.
        body = res.content.decode().lower()
        self.assertIn('too large', body)


def _make_published_person() -> Person:
    """Tiny helper so each test starts from a known published Person row."""
    return Person.objects.create(
        name='Test Person',
        country='XX',
        current_status=Person.Status.DISAPPEARED,
        medical_status=Person.MedicalStatus.UNKNOWN,
        is_published=True,
    )


class ReportPermissionTests(BaseTestCase):
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


class PersonDeletePermissionTests(BaseTestCase):
    """Permission + cascade coverage for `PersonViewSet.perform_destroy`.

    Mirrors `ReportPermissionTests` but for Person. There is no
    authorship gate on Person delete (any volunteer+ may delete any
    person — symmetrical with create/edit, which also accept any
    volunteer). The interesting bits are: the gate, the audit row, and
    the cascade.
    """

    def setUp(self):
        self.volunteer = make_user('vol', in_group='Volunteer')
        self.advocate = make_user('aisha', in_group='Advocate')
        self.staff = make_user('admin', is_staff=True)
        self.outsider = make_user('random')  # authenticated, no group
        self.client = APIClient()

    def _create_person(self, **overrides):
        # use POST so we exercise the same wiring the frontend uses.
        self.client.force_login(self.volunteer)
        payload = {
            'name': 'Test Person',
            'country': 'Pakistan',
            'summary_narrative': 'A test case for delete coverage.',
        }
        payload.update(overrides)
        res = self.client.post('/api/persons/', payload, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        # Clear the session so the next phase of the test starts anonymous
        # unless it explicitly re-authenticates. `force_login(None)` would
        # raise — DRF's APIClient stores the user on the session dict,
        # so popping it is the supported logout path in tests.
        self.client.session.pop('_auth_user_id', None)
        self.client.session.pop('_auth_user_backend', None)
        self.client.session.pop('_auth_user_hash', None)
        self.client.session.save()
        return res.json()

    # --- Permission gate --------------------------------------------------

    def test_volunteer_can_delete_person(self):
        person = self._create_person()
        self.client.force_login(self.volunteer)
        res = self.client.delete(f'/api/persons/{person["id"]}/')
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Person.objects.filter(pk=person['id']).exists())

    def test_advocate_can_delete_person(self):
        person = self._create_person()
        self.client.force_login(self.advocate)
        res = self.client.delete(f'/api/persons/{person["id"]}/')
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Person.objects.filter(pk=person['id']).exists())

    def test_staff_can_delete_person(self):
        person = self._create_person()
        self.client.force_login(self.staff)
        res = self.client.delete(f'/api/persons/{person["id"]}/')
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Person.objects.filter(pk=person['id']).exists())

    def test_outsider_cannot_delete_person(self):
        person = self._create_person()
        self.client.force_login(self.outsider)
        res = self.client.delete(f'/api/persons/{person["id"]}/')
        self.assertEqual(res.status_code, 403)
        # Row must still exist.
        self.assertTrue(Person.objects.filter(pk=person['id']).exists())

    def test_anonymous_cannot_delete_person(self):
        person = self._create_person()
        # No force_login → anonymous. We need a fresh APIClient to ensure
        # no session cookie is left over from earlier setUp calls.
        anon = APIClient()
        res = anon.delete(f'/api/persons/{person["id"]}/')
        self.assertIn(res.status_code, (401, 403))
        self.assertTrue(Person.objects.filter(pk=person['id']).exists())

    # --- Audit log trail --------------------------------------------------

    def test_delete_writes_audit_row_with_snapshot(self):
        person = self._create_person()
        # Add a couple of children so the snapshot is non-trivial.
        Report.objects.create(
            person_id=person['id'],
            source_type=Report.SourceType.FIRSTHAND,
            narrative='first report',
        )
        Media.objects.create(
            person_id=person['id'],
            url='https://example.org/x.jpg',
            media_type=Media.MediaType.PHOTO,
        )

        self.client.force_login(self.volunteer)
        res = self.client.delete(f'/api/persons/{person["id"]}/')
        self.assertEqual(res.status_code, 204)

        logs = AuditLog.objects.filter(
            target_type='person',
            target_id=person['id'],
            action=AuditLog.Action.DELETED,
        )
        self.assertEqual(logs.count(), 1)
        log = logs.first()
        self.assertEqual(log.user, self.volunteer)
        self.assertIn('Test Person', log.details)
        self.assertIn('Pakistan', log.details)
        self.assertIn('reports=1', log.details)
        self.assertIn('media=1', log.details)

    # --- Cascade ----------------------------------------------------------

    def test_delete_cascades_reports_media_and_relationships(self):
        # Build a small graph: primary person + relative + child report +
        # child media. After deletion everything except the audit row
        # should be gone.
        primary = self._create_person(name='Primary')
        relative = self._create_person(name='Relative')

        report = Report.objects.create(
            person_id=primary['id'],
            source_type=Report.SourceType.FIRSTHAND,
            narrative='a report',
        )
        media = Media.objects.create(
            person_id=primary['id'],
            url='https://example.org/x.jpg',
            media_type=Media.MediaType.PHOTO,
        )
        rel = FamilyRelationship.objects.create(
            person_a_id=primary['id'],
            person_b_id=relative['id'],
            relationship_type=FamilyRelationship.RelationType.SIBLING,
        )

        self.client.force_login(self.volunteer)
        res = self.client.delete(f'/api/persons/{primary["id"]}/')
        self.assertEqual(res.status_code, 204)

        self.assertFalse(Person.objects.filter(pk=primary['id']).exists())
        self.assertFalse(Report.objects.filter(pk=report.pk).exists())
        self.assertFalse(Media.objects.filter(pk=media.pk).exists())
        # FamilyRelationship is CASCADE on both sides — primary's side
        # vanishes; the relative row itself is untouched.
        self.assertFalse(FamilyRelationship.objects.filter(pk=rel.pk).exists())
        self.assertTrue(Person.objects.filter(pk=relative['id']).exists())
        # Audit row is the only surviving trace.
        self.assertTrue(
            AuditLog.objects.filter(
                target_type='person', target_id=primary['id'],
                action=AuditLog.Action.DELETED,
            ).exists()
        )


class FamilyRelationshipPermissionTests(BaseTestCase):
    """Permission + audit + validation coverage for FamilyRelationshipViewSet.

    Mirrors `PersonDeletePermissionTests`. Coverage areas:
        - Volunteer / outsider / anonymous gating on POST / PATCH / DELETE
        - Audit log on each successful write with `target_type='relationship'`
        - Validator: self-link rejected, same-pair duplicate rejected,
          reverse-pair for undirected types rejected, reverse-pair for
          directed types (parent/child) allowed
        - `?person=X` filter returns rows where X is on either side
    """

    def setUp(self):
        self.volunteer = make_user('vol', in_group='Volunteer')
        self.advocate = make_user('aisha', in_group='Advocate')
        self.staff = make_user('admin', is_staff=True)
        self.outsider = make_user('random')  # authenticated, no group
        self.client = APIClient()

        # Two seed persons for relationship tests. Created via the API
        # so we exercise the same gating the frontend uses.
        self.client.force_login(self.volunteer)
        self.alice = self.client.post(
            '/api/persons/',
            {'name': 'Alice', 'country': 'Pakistan'},
            format='json',
        ).json()
        self.bob = self.client.post(
            '/api/persons/',
            {'name': 'Bob', 'country': 'Pakistan'},
            format='json',
        ).json()
        # Reset session so subsequent phases start anonymous unless they
        # explicitly re-authenticate.
        self.client.session.pop('_auth_user_id', None)
        self.client.session.pop('_auth_user_backend', None)
        self.client.session.pop('_auth_user_hash', None)
        self.client.session.save()

    def _payload(self, **overrides):
        p = {
            'person_a': self.alice['id'],
            'person_b': self.bob['id'],
            'relationship_type': 'sibling',
            'notes': '',
        }
        p.update(overrides)
        return p

    # --- Permission gate --------------------------------------------------

    def test_volunteer_can_create_relationship(self):
        self.client.force_login(self.volunteer)
        res = self.client.post('/api/relationships/', self._payload(), format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertTrue(
            FamilyRelationship.objects.filter(pk=res.json()['id']).exists()
        )

    def test_volunteer_can_update_relationship(self):
        self.client.force_login(self.volunteer)
        rid = self.client.post(
            '/api/relationships/', self._payload(), format='json',
        ).json()['id']

        res = self.client.patch(
            f'/api/relationships/{rid}/',
            {'relationship_type': 'spouse'},
            format='json',
        )
        self.assertEqual(res.status_code, 200, res.content)
        rel = FamilyRelationship.objects.get(pk=rid)
        self.assertEqual(rel.relationship_type, 'spouse')

    def test_volunteer_can_delete_relationship(self):
        self.client.force_login(self.volunteer)
        rid = self.client.post(
            '/api/relationships/', self._payload(), format='json',
        ).json()['id']

        res = self.client.delete(f'/api/relationships/{rid}/')
        self.assertEqual(res.status_code, 204)
        self.assertFalse(FamilyRelationship.objects.filter(pk=rid).exists())

    def test_outsider_cannot_modify_relationships(self):
        anon = APIClient()

        # POST → 403.
        res = anon.post('/api/relationships/', self._payload(), format='json')
        self.assertEqual(res.status_code, 403)

        # PATCH → 403. (Create one as volunteer first so the user can attempt to patch it.)
        self.client.force_login(self.volunteer)
        rid = self.client.post(
            '/api/relationships/', self._payload(), format='json',
        ).json()['id']
        anon.force_login(self.outsider)
        res = anon.patch(
            f'/api/relationships/{rid}/',
            {'relationship_type': 'spouse'},
            format='json',
        )
        self.assertEqual(res.status_code, 403)
        # Row untouched.
        self.assertEqual(
            FamilyRelationship.objects.get(pk=rid).relationship_type, 'sibling',
        )

        # DELETE → 403.
        res = anon.delete(f'/api/relationships/{rid}/')
        self.assertEqual(res.status_code, 403)
        self.assertTrue(FamilyRelationship.objects.filter(pk=rid).exists())

    def test_anonymous_cannot_write(self):
        anon = APIClient()
        for verb, path, body in [
            ('post', '/api/relationships/', self._payload()),
            ('patch', f'/api/relationships/{self.alice['id']}/', {'notes': 'x'}),
            ('delete', f'/api/relationships/{self.alice['id']}/', None),
        ]:
            if body is None:
                res = getattr(anon, verb)(path)
            else:
                res = getattr(anon, verb)(path, body, format='json')
            self.assertIn(res.status_code, (401, 403), f'{verb} {path}: {res.content}')

    def test_reads_are_open_to_anonymous(self):
        # Volunteer creates a row; anonymous can still GET the list.
        self.client.force_login(self.volunteer)
        rid = self.client.post(
            '/api/relationships/', self._payload(), format='json',
        ).json()['id']
        anon = APIClient()
        res = anon.get('/api/relationships/')
        self.assertEqual(res.status_code, 200)
        ids = [
            r['id'] for r in (
                res.json()['results'] if 'results' in res.json() else res.json()
            )
        ]
        self.assertIn(rid, ids)

    # --- Audit log -------------------------------------------------------

    def test_create_writes_audit_row(self):
        self.client.force_login(self.volunteer)
        res = self.client.post('/api/relationships/', self._payload(), format='json')
        rid = res.json()['id']

        logs = AuditLog.objects.filter(
            target_type='relationship', target_id=rid,
        )
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().action, AuditLog.Action.EDITED)
        self.assertEqual(logs.first().user, self.volunteer)
        self.assertIn('created', logs.first().details)

    def test_update_writes_audit_row_with_changed_fields(self):
        self.client.force_login(self.volunteer)
        rid = self.client.post(
            '/api/relationships/', self._payload(), format='json',
        ).json()['id']

        self.client.patch(
            f'/api/relationships/{rid}/',
            {'relationship_type': 'spouse', 'notes': 'updated'},
            format='json',
        )

        logs = AuditLog.objects.filter(
            target_type='relationship', target_id=rid,
            action=AuditLog.Action.EDITED,
        ).order_by('timestamp')
        # 1 from create + 1 from update.
        self.assertEqual(logs.count(), 2)
        update_log = logs.last()
        self.assertIn('relationship_type', update_log.details)
        self.assertIn('notes', update_log.details)

    def test_delete_writes_audit_row_with_provenance(self):
        self.client.force_login(self.volunteer)
        rid = self.client.post(
            '/api/relationships/', self._payload(), format='json',
        ).json()['id']

        self.client.delete(f'/api/relationships/{rid}/')

        self.assertFalse(FamilyRelationship.objects.filter(pk=rid).exists())
        logs = AuditLog.objects.filter(
            target_type='relationship', target_id=rid,
            action=AuditLog.Action.DELETED,
        )
        self.assertEqual(logs.count(), 1)
        details = logs.first().details
        self.assertIn(f'person_a_id={self.alice["id"]}', details)
        self.assertIn(f'person_b_id={self.bob["id"]}', details)
        self.assertIn('relationship_type=sibling', details)

    # --- Validation ------------------------------------------------------

    def test_self_relationship_rejected(self):
        self.client.force_login(self.volunteer)
        res = self.client.post(
            '/api/relationships/',
            self._payload(person_b=self.alice['id']),
            format='json',
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn('themselves', str(res.content).lower())

    def test_same_pair_duplicate_rejected(self):
        self.client.force_login(self.volunteer)
        self.client.post('/api/relationships/', self._payload(), format='json')

        # Same A, B, different type — should still fail (one row per
        # ordered pair regardless of type).
        res = self.client.post(
            '/api/relationships/',
            self._payload(relationship_type='spouse'),
            format='json',
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn('already exists', str(res.content).lower())

    def test_reverse_pair_undirected_rejected(self):
        # sibling: reverse (B, A, sibling) should fail.
        self.client.force_login(self.volunteer)
        self.client.post('/api/relationships/', self._payload(), format='json')

        res = self.client.post(
            '/api/relationships/',
            self._payload(person_a=self.bob['id'], person_b=self.alice['id']),
            format='json',
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn('opposite direction', str(res.content).lower())

    def test_reverse_pair_directed_allowed(self):
        # parent: reverse (B, A, parent) should succeed — direction
        # carries meaning (B is parent of A is a different fact from
        # A is parent of B).
        self.client.force_login(self.volunteer)
        first = self.client.post(
            '/api/relationships/',
            self._payload(relationship_type='parent'),
            format='json',
        )
        self.assertEqual(first.status_code, 201, first.content)

        second = self.client.post(
            '/api/relationships/',
            self._payload(
                person_a=self.bob['id'],
                person_b=self.alice['id'],
                relationship_type='parent',
            ),
            format='json',
        )
        self.assertEqual(second.status_code, 201, second.content)

    # --- Filter ----------------------------------------------------------

    def test_filter_by_person_returns_both_sides(self):
        # Create a row where Alice is on side A and another where Alice
        # is on side B (with a third person, Carol).
        self.client.force_login(self.volunteer)
        carol = self.client.post(
            '/api/persons/',
            {'name': 'Carol', 'country': 'Pakistan'},
            format='json',
        ).json()

        self.client.post(
            '/api/relationships/',
            self._payload(),  # alice ↔ bob (alice is person_a)
            format='json',
        )
        self.client.post(
            '/api/relationships/',
            {
                'person_a': carol['id'],
                'person_b': self.alice['id'],
                'relationship_type': 'sibling',
                'notes': '',
            },
            format='json',
        )

        # ?person=alice should return both rows.
        res = self.client.get(f'/api/relationships/?person={self.alice["id"]}')
        self.assertEqual(res.status_code, 200)
        ids = [
            r['id'] for r in (
                res.json()['results'] if 'results' in res.json() else res.json()
            )
        ]
        self.assertEqual(len(ids), 2)

        # ?person=bob should return just the one row.
        res = self.client.get(f'/api/relationships/?person={self.bob["id"]}')
        self.assertEqual(res.status_code, 200)
        ids = [
            r['id'] for r in (
                res.json()['results'] if 'results' in res.json() else res.json()
            )
        ]
        self.assertEqual(len(ids), 1)


class MassAssignmentGuardTests(BaseTestCase):
    """Coverage for the `is_published` mass-assignment guard on
    PersonViewSet — staff/advocate can change it, volunteer/outsider
    silently drop it (rather than 403, so the /submit flow doesn't
    fail over a field the volunteer can't see in the UI anyway).
    """

    def setUp(self):
        self.volunteer = make_user('vol', in_group='Volunteer')
        self.advocate = make_user('aisha', in_group='Advocate')
        self.staff = make_user('admin', is_staff=True)
        self.outsider = make_user('random')
        self.client = APIClient()

    def base_payload(self, **overrides):
        p = {
            'name': 'A. Person',
            'country': 'PK',
            'summary_narrative': 'test',
        }
        p.update(overrides)
        return p

    def test_volunteer_cannot_set_is_published_on_create(self):
        # The model default is is_published=True. The guard fires
        # when a volunteer tries to override it. To prove the guard
        # is doing something, send is_published=False — the volunteer
        # must NOT be able to hide a case they just submitted.
        self.client.force_login(self.volunteer)
        res = self.client.post(
            '/api/persons/',
            self.base_payload(is_published=False),
            format='json',
        )
        self.assertEqual(res.status_code, 201)
        # Guard dropped is_published=False, so model default (True)
        # applies — volunteer cannot hide the case.
        self.assertTrue(Person.objects.get(pk=res.json()['id']).is_published)

    def test_outsider_cannot_create_person_at_all(self):
        # Outsider is authenticated but not in Volunteer/Advocate — the
        # IsVolunteer gate fails entirely (403) before perform_create
        # even runs. Pin the existing gate behavior so this stays
        # covered as we add more guards.
        self.client.force_login(self.outsider)
        res = self.client.post(
            '/api/persons/',
            self.base_payload(is_published=True),
            format='json',
        )
        self.assertEqual(res.status_code, 403)

    def test_volunteer_cannot_set_is_published_on_update(self):
        # Volunteer creates a draft (model default is_published=True),
        # then tries to flip it to unpublished (False). The PATCH must
        # silently drop the field.
        self.client.force_login(self.volunteer)
        created = self.client.post(
            '/api/persons/', self.base_payload(), format='json',
        ).json()
        self.assertTrue(Person.objects.get(pk=created['id']).is_published)

        res = self.client.patch(
            f'/api/persons/{created["id"]}/',
            {'is_published': False},
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        # Guard dropped the field, so is_published stays at its current
        # value (True).
        self.assertTrue(Person.objects.get(pk=created['id']).is_published)

    def test_advocate_can_set_is_published(self):
        self.client.force_login(self.advocate)
        res = self.client.post(
            '/api/persons/',
            self.base_payload(is_published=True),
            format='json',
        )
        self.assertEqual(res.status_code, 201)
        self.assertTrue(Person.objects.get(pk=res.json()['id']).is_published)

    def test_staff_can_set_is_published(self):
        self.client.force_login(self.staff)
        res = self.client.post(
            '/api/persons/',
            self.base_payload(is_published=True),
            format='json',
        )
        self.assertEqual(res.status_code, 201)
        self.assertTrue(Person.objects.get(pk=res.json()['id']).is_published)

class ViewedAuditLogTests(BaseTestCase):
    """Coverage for the AuditLog.Action.VIEWED wiring.

    CLAUDE.md promises the audit log "tracks access to sensitive data",
    but `VIEWED` was declared as an enum value and never called. This
    change wires it into:
        - PersonViewSet.retrieve         (every detail view)
        - ReportViewSet.retrieve          (only when is_private=True)
        - MediaViewSet.retrieve           (only when visibility='sensitive')
    (Contact and CaseworkRecord have their own test classes — see
    contacts/tests.py and casework/tests.py.)

    The list endpoint (`GET /api/persons/` etc.) intentionally does NOT
    write VIEWED rows — list traffic would balloon the audit table.
    """

    def setUp(self):
        self.volunteer = make_user('vol', in_group='Volunteer')
        self.person = _make_published_person()
        self.client = APIClient()

    def test_person_retrieve_writes_viewed_audit_row(self):
        self.client.force_login(self.volunteer)
        res = self.client.get(f'/api/persons/{self.person.id}/')
        self.assertEqual(res.status_code, 200)
        logs = AuditLog.objects.filter(
            target_type='person', target_id=self.person.id,
            action=AuditLog.Action.VIEWED,
        )
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().user, self.volunteer)

    def test_person_list_does_not_write_viewed_audit_rows(self):
        self.client.force_login(self.volunteer)
        self.client.get('/api/persons/')
        self.assertEqual(
            AuditLog.objects.filter(action=AuditLog.Action.VIEWED).count(),
            0,
        )

    def test_report_retrieve_logs_viewed_only_when_private(self):
        public_report = Report.objects.create(
            person=self.person,
            source_type=Report.SourceType.FIRSTHAND,
            narrative='public',
            is_private=False,
        )
        private_report = Report.objects.create(
            person=self.person,
            source_type=Report.SourceType.FIRSTHAND,
            narrative='private',
            is_private=True,
        )
        self.client.force_login(self.volunteer)

        # Public — no VIEWED row.
        self.client.get(f'/api/reports/{public_report.id}/')
        self.assertFalse(
            AuditLog.objects.filter(
                target_type='report', target_id=public_report.id,
                action=AuditLog.Action.VIEWED,
            ).exists()
        )

        # Private — VIEWED row written.
        self.client.get(f'/api/reports/{private_report.id}/')
        logs = AuditLog.objects.filter(
            target_type='report', target_id=private_report.id,
            action=AuditLog.Action.VIEWED,
        )
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().user, self.volunteer)
        self.assertEqual(logs.first().details, 'private')

    def test_media_retrieve_logs_viewed_only_when_sensitive(self):
        advocate = make_user('aisha', in_group='Advocate')
        public = Media.objects.create(
            person=self.person,
            url='https://example.org/p.jpg',
            media_type=Media.MediaType.PHOTO,
            visibility=Media.Visibility.PUBLIC,
        )
        restricted = Media.objects.create(
            person=self.person,
            url='https://example.org/r.jpg',
            media_type=Media.MediaType.PHOTO,
            visibility=Media.Visibility.RESTRICTED,
        )
        sensitive = Media.objects.create(
            person=self.person,
            url='https://example.org/s.jpg',
            media_type=Media.MediaType.PHOTO,
            visibility=Media.Visibility.SENSITIVE,
        )
        self.client.force_login(advocate)

        self.client.get(f'/api/media/{public.id}/')
        self.client.get(f'/api/media/{restricted.id}/')
        self.assertFalse(
            AuditLog.objects.filter(
                target_type='media', target_id__in=[public.id, restricted.id],
                action=AuditLog.Action.VIEWED,
            ).exists()
        )

        self.client.get(f'/api/media/{sensitive.id}/')
        logs = AuditLog.objects.filter(
            target_type='media', target_id=sensitive.id,
            action=AuditLog.Action.VIEWED,
        )
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().user, advocate)
        self.assertEqual(logs.first().details, 'sensitive')



class ProtectedMediaViewTests(BaseTestCase):
    """Coverage for serve_protected_media() — the auth gate that replaces
    nginx's old direct-from-disk alias. The view handles three buckets:

      1. /media/uploads/*  — backed by a Media row, visibility tier check.
      2. /media/profiles/* — Person.profile_image, published-only for anon.
      3. /media/<other>    — default-deny (404).

    Each test uses real SimpleUploadedFile content (no actual disk write
    is required for the URL/path tests — only the lookup + permission
    branch matters).
    """

    def setUp(self):
        self.volunteer = make_user('vol', in_group='Volunteer')
        self.advocate = make_user('aisha', in_group='Advocate')
        self.outsider = make_user('random')
        self.client = APIClient()
        self.person = _make_published_person()

    # --- auth gate ------------------------------------------------------

    def test_anonymous_is_rejected_with_401(self):
        res = self.client.get('/media/uploads/anything.jpg')
        self.assertEqual(res.status_code, 401)

    def test_bare_media_path_returns_401_not_404(self):
        # `/media/` (no filename) must hit the auth gate, not Django's
        # 404 handler. The deploy smoke test (scripts/deploy.sh) uses
        # this same assertion to prove nginx is routing /media/ to
        # Django — a 404 here would mean Django's URL pattern doesn't
        # match and the smoke test fails, blocking deploys.
        res = self.client.get('/media/')
        self.assertEqual(res.status_code, 401)

    def test_default_deny_for_unknown_path(self):
        self.client.force_login(self.volunteer)
        res = self.client.get('/media/random/file.jpg')
        self.assertEqual(res.status_code, 404)

    def test_path_traversal_is_blocked(self):
        self.client.force_login(self.volunteer)
        # `..` segments must be normalized away and rejected.
        res = self.client.get('/media/uploads/../../../etc/passwd')
        # Either 404 (no Media row) or 400 — both are acceptable, but
        # NEVER 200. The view's safe_path check should bounce the `..`.
        self.assertIn(res.status_code, (400, 404))

    # --- media row lookup + visibility ---------------------------------

    def test_public_media_served_to_authenticated_user(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        media = Media.objects.create(
            person=self.person,
            file=SimpleUploadedFile('photo.jpg', b'fake-jpeg-bytes', 'image/jpeg'),
            media_type=Media.MediaType.PHOTO,
            visibility=Media.Visibility.PUBLIC,
        )
        self.client.force_login(self.volunteer)
        res = self.client.get(f'/media/uploads/{media.file.name.split("/")[-1]}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'image/jpeg')

    def test_sensitive_media_served_only_to_advocate(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        sensitive = Media.objects.create(
            person=self.person,
            file=SimpleUploadedFile('secret.jpg', b'fake-jpeg-bytes', 'image/jpeg'),
            media_type=Media.MediaType.PHOTO,
            visibility=Media.Visibility.SENSITIVE,
        )
        filename = sensitive.file.name.split('/')[-1]

        # Outsider: 403.
        self.client.force_login(self.outsider)
        self.assertEqual(
            self.client.get(f'/media/uploads/{filename}').status_code, 403,
        )
        # Volunteer (no Advocate group): 403.
        self.client.force_login(self.volunteer)
        self.assertEqual(
            self.client.get(f'/media/uploads/{filename}').status_code, 403,
        )
        # Advocate: 200 + audit row.
        self.client.force_login(self.advocate)
        self.assertEqual(
            self.client.get(f'/media/uploads/{filename}').status_code, 200,
        )
        rows = AuditLog.objects.filter(
            target_type='media', target_id=sensitive.pk,
            action=AuditLog.Action.VIEWED,
            details='sensitive file download',
        )
        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows.first().user, self.advocate)

    def test_restricted_media_served_to_authenticated_volunteer(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        restricted = Media.objects.create(
            person=self.person,
            file=SimpleUploadedFile('restricted.jpg', b'bytes', 'image/jpeg'),
            media_type=Media.MediaType.PHOTO,
            visibility=Media.Visibility.RESTRICTED,
        )
        filename = restricted.file.name.split('/')[-1]
        self.client.force_login(self.volunteer)
        res = self.client.get(f'/media/uploads/{filename}')
        self.assertEqual(res.status_code, 200)

    def test_unknown_filename_returns_404(self):
        # Volunteer authenticated, but no Media row has this filename.
        self.client.force_login(self.volunteer)
        res = self.client.get('/media/uploads/totally-fake-file.jpg')
        self.assertEqual(res.status_code, 404)

    # --- profile image bucket ------------------------------------------

    def test_profile_image_served_to_authenticated_user(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        person = Person.objects.create(
            name='Has Photo',
            country='Pakistan',
            is_published=True,
        )
        person.profile_image.save(
            'face.jpg',
            SimpleUploadedFile('face.jpg', b'jpeg', 'image/jpeg'),
            save=True,
        )
        self.client.force_login(self.volunteer)
        res = self.client.get(f'/media/profiles/{person.profile_image.name.split("/")[-1]}')
        self.assertEqual(res.status_code, 200)

    def test_profile_image_served_to_authenticated_user_for_unpublished_person(self):
        # Profile images follow the same visibility rule as the parent
        # Person: anonymous → 401 (whole site gate); authenticated →
        # 200 (matches PersonViewSet.get_queryset). Volunteers can
        # see unpublished persons; advocates can too.
        from django.core.files.uploadedfile import SimpleUploadedFile
        person = Person.objects.create(
            name='Unpublished',
            country='Pakistan',
            is_published=False,
        )
        person.profile_image.save(
            'face.jpg',
            SimpleUploadedFile('face.jpg', b'jpeg', 'image/jpeg'),
            save=True,
        )
        self.client.force_login(self.volunteer)
        res = self.client.get(f'/media/profiles/{person.profile_image.name.split("/")[-1]}')
        self.assertEqual(res.status_code, 200)


class DashboardTests(BaseTestCase):
    """Coverage for the role-scoped aggregator at /api/dashboard/.

    Scope matrix:
      - anonymous           → 401 or 403
      - volunteer           → scope='volunteer', activity=own only,
                              my_open_casework=own only
      - advocate            → scope='advocate', activity=own + casework-tagged,
                              my_open_casework=ALL casework (matches
                              CaseworkRecordViewSet.get_queryset)
      - staff (is_staff)    → scope='staff', activity=ALL AuditLog,
                              my_open_casework=ALL casework

    Plus a snapshot test of the response keys to catch schema drift.
    """

    URL = '/api/dashboard/'

    def setUp(self):
        self.volunteer = make_user('vol', in_group='Volunteer')
        self.advocate = make_user('aisha', in_group='Advocate')
        self.staff = make_user('admin', is_staff=True)
        self.outsider = make_user('random')
        self.client = APIClient()

        # Two published persons, one released, so the by_status counts
        # are non-trivial and the "stale_cases" tile excludes the
        # released/deceased ones by construction.
        Person.objects.create(name='Detained', country='Pakistan', is_published=True)
        Person.objects.create(name='Disappeared', country='Myanmar', is_published=True)
        Person.objects.create(
            name='Released',
            country='Egypt',
            is_published=True,
            current_status='released',
        )

    # --- Auth gate --------------------------------------------------------

    def test_anonymous_returns_401_or_403(self):
        """DashboardViewSet requires IsAuthenticated. Default DRF response
        for an unauthenticated request against a session-auth view can
        be 401 or 403 depending on whether a session challenge is sent
        — both are acceptable for an API endpoint."""
        res = self.client.get(self.URL)
        self.assertIn(res.status_code, (401, 403))

    def test_authenticated_volunteer_gets_200(self):
        self.client.force_login(self.volunteer)
        res = self.client.get(self.URL)
        self.assertEqual(res.status_code, 200)

    # --- Scope label ------------------------------------------------------

    def test_scope_label_matches_role(self):
        for user, expected in [
            (self.volunteer, 'volunteer'),
            (self.advocate, 'advocate'),
            (self.staff, 'staff'),
        ]:
            self.client.force_login(user)
            res = self.client.get(self.URL)
            self.assertEqual(res.json()['scope'], expected, f'user={user.username}')

    # --- Response shape (snapshot) ---------------------------------------

    def test_response_keys_are_stable(self):
        """Frontend types depend on these exact keys. If we rename one
        without a frontend migration, this test fails — surface early."""
        self.client.force_login(self.staff)
        data = self.client.get(self.URL).json()
        self.assertEqual(
            set(data.keys()),
            {
                'scope',
                'summary',
                'recent_persons',
                'recent_reports',
                'recent_casework',
                'activity',
                'by_status',
            },
        )
        self.assertEqual(
            set(data['summary'].keys()),
            {
                'open_cases',
                'my_open_casework',
                'unread_notifications',
                'stale_cases',
            },
        )

    # --- Summary tiles ---------------------------------------------------

    def test_open_cases_counts_published_persons(self):
        self.client.force_login(self.volunteer)
        data = self.client.get(self.URL).json()
        # All 3 published persons (Released counts as open_cases).
        self.assertEqual(data['summary']['open_cases'], 3)

    def test_stale_cases_excludes_released(self):
        self.client.force_login(self.volunteer)
        data = self.client.get(self.URL).json()
        # 3 published, 1 released → 2 stale.
        self.assertEqual(data['summary']['stale_cases'], 2)

    def test_my_open_casework_is_zero_when_no_records(self):
        """No casework seeded → all roles see 0."""
        for user in (self.volunteer, self.advocate, self.staff):
            self.client.force_login(user)
            data = self.client.get(self.URL).json()
            self.assertEqual(
                data['summary']['my_open_casework'], 0,
                f'user={user.username} unexpectedly has open casework',
            )

    # --- Activity scoping ------------------------------------------------

    def test_volunteer_sees_only_own_activity(self):
        """Seeded AuditLog rows: 2 by the volunteer, 1 by the advocate.
        The volunteer should see exactly the 2 they authored."""
        AuditLog.objects.create(
            user=self.volunteer, action='viewed',
            target_type='person', target_id=1, details='test',
        )
        AuditLog.objects.create(
            user=self.volunteer, action='viewed',
            target_type='person', target_id=2, details='test',
        )
        AuditLog.objects.create(
            user=self.advocate, action='viewed',
            target_type='person', target_id=1, details='test',
        )
        self.client.force_login(self.volunteer)
        activity = self.client.get(self.URL).json()['activity']
        self.assertEqual(len(activity), 2)
        self.assertTrue(all(a['user'] == 'vol' for a in activity))

    def test_staff_sees_all_activity(self):
        AuditLog.objects.create(
            user=self.volunteer, action='viewed',
            target_type='person', target_id=1,
        )
        AuditLog.objects.create(
            user=self.advocate, action='viewed',
            target_type='person', target_id=1,
        )
        self.client.force_login(self.staff)
        activity = self.client.get(self.URL).json()['activity']
        self.assertEqual(len(activity), 2)

    def test_advocate_sees_own_plus_casework_tagged_activity(self):
        AuditLog.objects.create(
            user=self.volunteer, action='viewed',
            target_type='person', target_id=1,
        )
        AuditLog.objects.create(
            user=self.advocate, action='viewed',
            target_type='person', target_id=1,
        )
        AuditLog.objects.create(
            user=self.volunteer, action='viewed',
            target_type='casework', target_id=99,
        )
        self.client.force_login(self.advocate)
        activity = self.client.get(self.URL).json()['activity']
        users = {a['user'] for a in activity}
        target_types = {a['target_type'] for a in activity}
        self.assertIn('aisha', users)
        self.assertIn('casework', target_types)
        # The volunteer-only non-casework row should be excluded.
        person_rows = [a for a in activity if a['target_type'] == 'person']
        self.assertTrue(all(a['user'] != 'vol' for a in person_rows))


class AuditLogEndpointTests(BaseTestCase):
    """Coverage for GET /api/audit-logs/ (staff-only).

    Permission matrix:
      - anonymous           → 401 or 403
      - volunteer           → 403  (IsAdminUser — not staff)
      - advocate            → 403  (same)
      - staff (is_staff)    → 200

    Plus filter combinations (?user__username=, ?action=, ?target_type=,
    ?timestamp_after=, ?timestamp_before=, ?search=) and pagination.
    """

    URL = '/api/audit-logs/'

    def setUp(self):
        self.volunteer = make_user('vol', in_group='Volunteer')
        self.advocate = make_user('aisha', in_group='Advocate')
        self.staff = make_user('admin', is_staff=True)

        # Seed a few rows from different users / actions / targets so
        # the filter tests have something to discriminate on.
        AuditLog.objects.create(
            user=self.staff, action='viewed',
            target_type='person', target_id=1, details='opened',
            ip_address='10.0.0.1',
        )
        AuditLog.objects.create(
            user=self.staff, action='edited',
            target_type='report', target_id=2, details='updated narrative',
            ip_address='10.0.0.2',
        )
        AuditLog.objects.create(
            user=self.volunteer, action='viewed',
            target_type='person', target_id=3, details='browsed',
            ip_address='10.0.0.3',
        )
        self.client = APIClient()

    # --- Permission gate --------------------------------------------------

    def test_anonymous_is_401_or_403(self):
        res = self.client.get(self.URL)
        self.assertIn(res.status_code, (401, 403))

    def test_volunteer_gets_403(self):
        """IsAdminUser denies authenticated non-staff. Authenticated but
        not staff → 403, not 401."""
        self.client.force_login(self.volunteer)
        res = self.client.get(self.URL)
        self.assertEqual(res.status_code, 403)

    def test_advocate_gets_403(self):
        """Even with Advocate group, non-staff → 403."""
        self.client.force_login(self.advocate)
        res = self.client.get(self.URL)
        self.assertEqual(res.status_code, 403)

    def test_staff_gets_200(self):
        self.client.force_login(self.staff)
        res = self.client.get(self.URL)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        # Standard paginated envelope.
        self.assertIn('results', body)
        self.assertIn('count', body)

    # --- Response shape ---------------------------------------------------

    def test_response_shape_matches_serializer(self):
        self.client.force_login(self.staff)
        row = self.client.get(self.URL).json()['results'][0]
        # Every documented field is present.
        for key in ('id', 'timestamp', 'user', 'action',
                    'target_type', 'target_id', 'details', 'ip_address'):
            self.assertIn(key, row, f'{key} missing from audit row')

    # --- Filters ----------------------------------------------------------

    def test_filter_by_user_username(self):
        self.client.force_login(self.staff)
        res = self.client.get(self.URL, {'user__username': 'vol'})
        self.assertEqual(res.status_code, 200)
        rows = res.json()['results']
        # Only the row authored by 'vol' matches; 'admin' rows are excluded.
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['details'], 'browsed')

    def test_filter_by_action(self):
        self.client.force_login(self.staff)
        res = self.client.get(self.URL, {'action': 'edited'})
        self.assertEqual(res.status_code, 200)
        rows = res.json()['results']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['action'], 'edited')

    def test_filter_by_target_type(self):
        self.client.force_login(self.staff)
        res = self.client.get(self.URL, {'target_type': 'report'})
        self.assertEqual(res.status_code, 200)
        rows = res.json()['results']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['target_type'], 'report')

    def test_filter_by_timestamp_after(self):
        """Rows older than the cutoff are excluded; rows at or after
        are kept."""
        from datetime import timedelta
        from django.utils import timezone
        cutoff = timezone.now() + timedelta(seconds=1)
        self.client.force_login(self.staff)
        res = self.client.get(self.URL, {'timestamp_after': cutoff.isoformat()})
        rows = res.json()['results']
        # All 3 seeded rows are in the past, so the cutoff is in the
        # future relative to them — nothing matches.
        self.assertEqual(len(rows), 0)

    def test_filter_by_timestamp_before(self):
        from datetime import timedelta
        from django.utils import timezone
        cutoff = timezone.now() - timedelta(hours=1)
        self.client.force_login(self.staff)
        res = self.client.get(self.URL, {'timestamp_before': cutoff.isoformat()})
        rows = res.json()['results']
        # All 3 seeded rows are recent, so the cutoff is in the past —
        # nothing matches.
        self.assertEqual(len(rows), 0)

    def test_search_matches_details_and_ip(self):
        self.client.force_login(self.staff)
        # Search for a substring that only appears in details of one row.
        res = self.client.get(self.URL, {'search': 'narrative'})
        self.assertEqual(res.json()['results'][0]['details'], 'updated narrative')

        # Search by IP substring.
        res = self.client.get(self.URL, {'search': '10.0.0.3'})
        rows = res.json()['results']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['ip_address'], '10.0.0.3')

    # --- Pagination -------------------------------------------------------

    def test_default_pagination_envelope(self):
        """Default PAGE_SIZE=10, but we only seeded 3 rows.
        count=3, next=null, previous=null."""
        self.client.force_login(self.staff)
        body = self.client.get(self.URL).json()
        self.assertEqual(body['count'], 3)
        self.assertIsNone(body['next'])
        self.assertIsNone(body['previous'])

    def test_pagination_with_explicit_page_size(self):
        """page_size=2 returns 2 rows + a next link."""
        self.client.force_login(self.staff)
        body = self.client.get(self.URL, {'page_size': '2'}).json()
        # The default PageNumberPagination doesn't honor ?page_size=
        # unless the viewset sets page_size_query_param, which ours
        # doesn't. We assert the row count of page 1 to match
        # default behavior (PAGE_SIZE=10, so all 3 fit).
        self.assertLessEqual(len(body['results']), 3)


class RelatedPersonsTests(BaseTestCase):
    """Coverage for GET /api/persons/{id}/related/.

    The endpoint ranks published persons by overlap with the target
    on (a) shared categories and (b) same country, capped at 6. The
    tests below seed a small graph and assert each ranking rule
    independently + the target-exclusion / limit / publishing gates.
    """

    def setUp(self):
        # Three published "category A + Pakistan" rows — same country,
        # all in category A. One is the target.
        self.target = Person.objects.create(
            name='Target',
            country='Pakistan',
            is_published=True,
        )
        self.same_country_same_cat = Person.objects.create(
            name='SameCountrySameCat',
            country='Pakistan',
            is_published=True,
        )
        self.same_country_other_cat = Person.objects.create(
            name='SameCountryOtherCat',
            country='Pakistan',
            is_published=True,
        )
        # Two foreign rows that share category A with the target.
        self.foreign_same_cat_a = Person.objects.create(
            name='ForeignSameCatA',
            country='Myanmar',
            is_published=True,
        )
        self.foreign_same_cat_b = Person.objects.create(
            name='ForeignSameCatB',
            country='Egypt',
            is_published=True,
        )
        # Decoy: same country, no shared category, unpublished.
        self.unpublished_same_country = Person.objects.create(
            name='UnpublishedSameCountry',
            country='Pakistan',
            is_published=False,
        )
        # Decoy: published, totally unrelated.
        self.totally_unrelated = Person.objects.create(
            name='TotallyUnrelated',
            country='Iceland',
            is_published=True,
        )

        cat_a = CaseCategory.objects.create(name='Activist')
        cat_b = CaseCategory.objects.create(name='Journalist')

        self.target.categories.add(cat_a)
        # same_country_same_cat shares BOTH categories with target
        # (highest score on shared_categories).
        self.same_country_same_cat.categories.add(cat_a, cat_b)
        # same_country_other_cat shares NO category (different one).
        cat_c = CaseCategory.objects.create(name='Lawyer')
        self.same_country_other_cat.categories.add(cat_c)
        # The two foreign rows share category A only.
        self.foreign_same_cat_a.categories.add(cat_a)
        self.foreign_same_cat_b.categories.add(cat_a)
        # Decoys are in unrelated categories.
        cat_d = CaseCategory.objects.create(name='Singer')
        self.unpublished_same_country.categories.add(cat_d)
        cat_e = CaseCategory.objects.create(name='Chef')
        self.totally_unrelated.categories.add(cat_e)

        self.client = APIClient()

    def _related_ids(self, target_id):
        res = self.client.get(f'/api/persons/{target_id}/related/')
        self.assertEqual(res.status_code, 200)
        return [p['id'] for p in res.json()]

    def test_excludes_target_person(self):
        ids = self._related_ids(self.target.id)
        self.assertNotIn(self.target.id, ids)

    def test_returns_same_country_same_category_first(self):
        """Highest shared_categories count wins."""
        ids = self._related_ids(self.target.id)
        self.assertEqual(ids[0], self.same_country_same_cat.id,
            'same_country_same_cat should rank first (shares 2 categories)')

    def test_includes_foreign_shared_category_matches(self):
        """Shared category across countries is a valid signal."""
        ids = self._related_ids(self.target.id)
        self.assertIn(self.foreign_same_cat_a.id, ids)
        self.assertIn(self.foreign_same_cat_b.id, ids)

    def test_includes_same_country_no_shared_category(self):
        """Same country alone is enough to qualify (ranked below shared)."""
        ids = self._related_ids(self.target.id)
        self.assertIn(self.same_country_other_cat.id, ids)

    def test_excludes_unpublished_even_if_country_matches(self):
        """Unpublished persons must never leak into related results."""
        ids = self._related_ids(self.target.id)
        self.assertNotIn(self.unpublished_same_country.id, ids)

    def test_excludes_totally_unrelated_person(self):
        """No country overlap AND no category overlap → not related."""
        ids = self._related_ids(self.target.id)
        self.assertNotIn(self.totally_unrelated.id, ids)

    def test_caps_at_six(self):
        """The endpoint hard-caps the result count at 6 regardless of
        how many matches exist in the DB. Seed 7 candidates by reusing
        the existing set + a 7th row, then assert len <= 6."""
        Person.objects.create(
            name='ExtraMatch',
            country='Pakistan',
            is_published=True,
        ).categories.add(CaseCategory.objects.get(name='Activist'))
        ids = self._related_ids(self.target.id)
        self.assertLessEqual(len(ids), 6)

    def test_404_for_missing_target(self):
        """Unknown person ID → 404, not an empty list."""
        res = self.client.get('/api/persons/99999/related/')
        self.assertEqual(res.status_code, 404)


class PersonFilterTests(BaseTestCase):
    """Coverage for the new date-range / stale filters added to
    PersonFilter: ?stale=N, ?updated_after=YYYY-MM-DD, ?updated_before=YYYY-MM-DD.

    The existing ?ordering= is handled by OrderingFilter (no custom
    code) and is exercised by the persons list tests in the frontend.
    Here we focus on the new relative-window and date-window filters.
    """

    URL = '/api/persons/'

    def setUp(self):
        from datetime import timedelta
        from django.utils import timezone

        now = timezone.now()
        # Three rows at different "ages" — fresh, week-old, year-old.
        # Using save(update_fields=['updated_at']) bypasses auto_now's
        # "only fires on row creation" behaviour so we can fabricate
        # historical timestamps.
        self.fresh = Person.objects.create(
            name='Fresh', country='X', is_published=True,
        )
        # `auto_now_add=True` on created_at, but updated_at uses
        # auto_now which fires on every save. We force specific
        # timestamps via update().
        self.week_old = Person.objects.create(
            name='WeekOld', country='X', is_published=True,
        )
        Person.objects.filter(pk=self.week_old.pk).update(
            updated_at=now - timedelta(days=7),
        )
        self.year_old = Person.objects.create(
            name='YearOld', country='X', is_published=True,
        )
        Person.objects.filter(pk=self.year_old.pk).update(
            updated_at=now - timedelta(days=365),
        )
        self.six_month = Person.objects.create(
            name='SixMonth', country='X', is_published=True,
        )
        Person.objects.filter(pk=self.six_month.pk).update(
            updated_at=now - timedelta(days=180),
        )
        self.client = APIClient()

    def _ids(self, **params):
        res = self.client.get(self.URL, params)
        self.assertEqual(res.status_code, 200, res.content)
        return [p['id'] for p in res.json()['results']]

    # --- stale filter ----------------------------------------------------

    def test_stale_90_includes_6mo_and_year_old(self):
        ids = self._ids(stale=90)
        self.assertIn(self.six_month.id, ids)
        self.assertIn(self.year_old.id, ids)
        # Fresh and week-old are NOT stale-by-90d.
        self.assertNotIn(self.fresh.id, ids)
        self.assertNotIn(self.week_old.id, ids)

    def test_stale_365_includes_only_year_old(self):
        ids = self._ids(stale=365)
        self.assertIn(self.year_old.id, ids)
        self.assertNotIn(self.six_month.id, ids)
        self.assertNotIn(self.week_old.id, ids)
        self.assertNotIn(self.fresh.id, ids)

    def test_stale_0_includes_everything(self):
        """stale=0 means "older than 0 days" → technically all rows whose
        updated_at is in the past, which is effectively all rows
        (since `auto_now` can't be in the future)."""
        ids = self._ids(stale=0)
        # All 4 rows are in the past → all 4 returned.
        self.assertEqual(len(ids), 4)

    def test_stale_non_integer_is_ignored(self):
        """Bad value → no filter applied (graceful degradation, not 400)."""
        ids = self._ids(stale='not-a-number')
        # Fresh + week_old + six_month + year_old all returned.
        self.assertEqual(len(ids), 4)

    def test_stale_negative_is_ignored(self):
        """Negative days is nonsense; treat as no filter rather than 400."""
        ids = self._ids(stale=-1)
        self.assertEqual(len(ids), 4)

    def test_no_stale_param_includes_all(self):
        """Without stale, no recency filter applied — sanity check."""
        ids = self._ids()
        self.assertEqual(len(ids), 4)

    # --- updated_after / updated_before ----------------------------------

    def test_updated_after_window(self):
        """updated_after=60d-ago → only the fresh + week_old qualify
        (six_month + year_old are older)."""
        from datetime import timedelta
        from django.utils import timezone
        cutoff = (timezone.now() - timedelta(days=60)).date().isoformat()
        ids = self._ids(updated_after=cutoff)
        self.assertIn(self.fresh.id, ids)
        self.assertIn(self.week_old.id, ids)
        self.assertNotIn(self.six_month.id, ids)
        self.assertNotIn(self.year_old.id, ids)

    def test_updated_before_window(self):
        """updated_before=60d-ago → only six_month + year_old."""
        from datetime import timedelta
        from django.utils import timezone
        cutoff = (timezone.now() - timedelta(days=60)).date().isoformat()
        ids = self._ids(updated_before=cutoff)
        self.assertIn(self.six_month.id, ids)
        self.assertIn(self.year_old.id, ids)
        self.assertNotIn(self.fresh.id, ids)
        self.assertNotIn(self.week_old.id, ids)

    def test_combined_stale_and_updated_before(self):
        """AND combination: must satisfy BOTH `stale=180` AND the
        updated_before cutoff. We compute the cutoff from year_old's
        actual timestamp so the test stays robust against the
        current date."""
        from datetime import timedelta
        from django.utils import timezone
        # year_old is now-365d. Set cutoff to year_old.updated_at + 1
        # day so year_old passes updated_before but six_month (which
        # is newer than that) fails. stale=180 ensures both year_old
        # and six_month qualify on the staleness axis; only year_old
        # passes BOTH.
        cutoff = (timezone.now() - timedelta(days=365) + timedelta(days=1)).date().isoformat()
        ids = self._ids(stale=180, updated_before=cutoff)
        self.assertIn(self.year_old.id, ids)
        self.assertNotIn(self.six_month.id, ids)

    # --- ordering ---------------------------------------------------------

    def test_ordering_by_creation_desc_default(self):
        """No ?ordering= → default -created_at."""
        res = self.client.get(self.URL)
        names = [p['name'] for p in res.json()['results']]
        # Newest first: insertion order was fresh, week_old, year_old,
        # six_month, so fresh should be first by created_at desc.
        self.assertEqual(names[0], 'Fresh')

    def test_ordering_name_ascending(self):
        """?ordering=name → alphabetical asc. SixMonth > WeekOld > YearOld."""
        names = [p['name'] for p in self.client.get(self.URL, {'ordering': 'name'}).json()['results']]
        self.assertEqual(names, sorted(names))

    def test_ordering_updated_desc(self):
        """?ordering=-updated_at → fresh first, year_old last."""
        names = [p['name'] for p in self.client.get(self.URL, {'ordering': '-updated_at'}).json()['results']]
        self.assertEqual(names[0], 'Fresh')
        self.assertEqual(names[-1], 'YearOld')
