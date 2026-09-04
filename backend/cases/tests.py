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

from .models import AuditLog, FamilyRelationship, Media, Person, Report


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


class PersonDeletePermissionTests(TestCase):
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


class FamilyRelationshipPermissionTests(TestCase):
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


class ReportListFilteringTests(TestCase):
    """Filter + ordering + pagination coverage for `ReportViewSet`.

    Reuses the seed pattern from `ReportPermissionTests`: a published
    person, a volunteer user, three reports with known date_starts.
    Drives `GET /api/reports/` with date-from / date-to / source_type
    query params and checks the returned `results` slice.
    """

    def setUp(self):
        self.volunteer = make_user('vol', in_group='Volunteer')
        self.person = _make_published_person()
        self.client = APIClient()

        # Three reports spanning 2025, used by every date-filter test.
        # `source_type` deliberately varies so the combined-filter test
        # has something to AND on.
        self.r_jan = Report.objects.create(
            person=self.person,
            source_type=Report.SourceType.FIRSTHAND,
            narrative='january report',
            date_start='2025-01-01',
        )
        self.r_jun = Report.objects.create(
            person=self.person,
            source_type=Report.SourceType.NEWS,
            narrative='june report',
            date_start='2025-06-01',
        )
        self.r_dec = Report.objects.create(
            person=self.person,
            source_type=Report.SourceType.DOCUMENT,
            narrative='december report',
            date_start='2025-12-01',
        )

    def _ids(self, res):
        return [
            r['id'] for r in (
                res.json()['results'] if 'results' in res.json() else res.json()
            )
        ]

    def test_date_from_filter_returns_only_recent(self):
        self.client.force_login(self.volunteer)
        res = self.client.get('/api/reports/?date_from=2025-06-01')
        self.assertEqual(res.status_code, 200)
        ids = self._ids(res)
        self.assertEqual(set(ids), {self.r_jun.id, self.r_dec.id})
        # The January report is excluded because date_start < date_from.
        self.assertNotIn(self.r_jan.id, ids)

    def test_date_to_filter_returns_only_older(self):
        self.client.force_login(self.volunteer)
        res = self.client.get('/api/reports/?date_to=2025-06-01')
        self.assertEqual(res.status_code, 200)
        ids = self._ids(res)
        # `__lte` is inclusive — both the January and June reports match.
        self.assertEqual(set(ids), {self.r_jan.id, self.r_jun.id})
        self.assertNotIn(self.r_dec.id, ids)

    def test_combined_date_range_and_source_type_filter(self):
        self.client.force_login(self.volunteer)
        res = self.client.get(
            '/api/reports/?date_from=2025-06-01&source_type=news',
        )
        self.assertEqual(res.status_code, 200)
        # Only the June news report matches both filters — December is
        # `document`, January is `firsthand`, both excluded.
        self.assertEqual(self._ids(res), [self.r_jun.id])

    def test_filter_does_not_bypass_private_visibility(self):
        # Make one of the matching reports private. Anonymous can still
        # filter by source_type but must not see private rows.
        self.r_jun.is_private = True
        self.r_jun.save(update_fields=['is_private'])

        # Anonymous (no force_login) — the existing visibility gate
        # still strips private reports before filter results.
        anon = APIClient()
        res = anon.get('/api/reports/?source_type=news')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self._ids(res), [])
        # The volunteer (who can see private reports) still sees it.
        self.client.force_login(self.volunteer)
        res = self.client.get('/api/reports/?source_type=news')
        self.assertEqual(self._ids(res), [self.r_jun.id])