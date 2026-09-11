"""Tests for the testimonials workflow.

Covers the contract spelled out in the design doc:

  - workflow transitions (DRAFT → UNDER_REVIEW → APPROVED → PUBLISHED
    → ARCHIVED) and the AuditLog row each writes;
  - role boundary: Volunteers submit drafts; only Advocate+ may
    approve / publish / archive;
  - source / location masking: ciphertext columns never reach the
    public serializer, regardless of source_visibility;
  - encrypted-source endpoint: only Advocate+ can decrypt; every
    read leaves an AuditLog trace.

Real DB tests, no mocks (per SYSTEM_RULES §7). Cryptography round-
trips are exercised but the Fernet key is the hardcoded DEV fallback
in encryption.py — see TESTIMONIALS_DEV_FALLBACK_KEY.
"""

import json
import uuid
from pathlib import Path

from cryptography.fernet import InvalidToken
from django.test import override_settings
from rest_framework.test import APIClient

from cases.models import AuditLog, Testimonial, TestimonialTag
from cases.testimonials.encryption import (
    TESTIMONIALS_DEV_FALLBACK_KEY,
    decrypt_str, encrypt_str,
)
from cases.testimonials.export import EXPORT_SCHEMA, TestimonialExportSerializer
from cases.tests import make_user
from testimonies.test_base import BaseTestCase


# Helper: every test that touches encryption needs a key configured.
# Django's test runner runs with DEBUG=False regardless of the dev
# env, so the dev fallback in encryption.py doesn't fire — we have
# to set the env var explicitly. Use the same hardcoded DEV key so
# tests stay hermetic.
FERNET_KEY_SETTING = override_settings(
    TESTIMONIALS_FERNET_KEY=TESTIMONIALS_DEV_FALLBACK_KEY
)


# AES-128-CBC + HMAC round-trip via Fernet.
@FERNET_KEY_SETTING
class FernetRoundTripTests(BaseTestCase):
    def test_encrypt_decrypt_unicode(self):
        ciphertext = encrypt_str('Source name: أحمد')
        self.assertIsInstance(ciphertext, bytes)
        self.assertNotIn('Source name'.encode(), ciphertext,
                         'plaintext must NOT leak into ciphertext')
        self.assertEqual(decrypt_str(ciphertext), 'Source name: أحمد')

    def test_encrypt_empty_is_noop(self):
        self.assertEqual(encrypt_str(''), b'')
        self.assertIsNone(decrypt_str(b''))
        self.assertIsNone(decrypt_str(None))

    def test_decrypt_forged_raises(self):
        # Mutate one byte — Fernet's HMAC catches forgery.
        ciphertext = encrypt_str('real')
        with self.assertRaises(InvalidToken):
            decrypt_str(ciphertext[:-1] + b'X')


# Workflow transitions + AuditLog.
@FERNET_KEY_SETTING
class TestimonialWorkflowTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.volunteer = make_user('vol', in_group='Volunteer')
        self.advocate = make_user('adv', in_group='Advocate')
        self.staff = make_user('admin', is_staff=True)
        self.client = APIClient()

    def _create(self, user, **overrides):
        self.client.force_login(user)
        body = {
            'title': 'Detention in Erbil',
            'language': 'en',
            'country': 'Iraq',
            'region': 'Erbil',
            'summary': 'short',
            'narrative': 'long',
            'public_source_label': 'Family member',
            'public_location_display': 'Erbil',
            'source_visibility': 'hidden',
            'location_visibility': 'public_region',
        }
        body.update(overrides)
        res = self.client.post('/api/testimonials/', body, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        return res.json()['id']

    def _post_action(self, user, pk, name, body=None):
        self.client.force_login(user)
        res = self.client.post(
            f'/api/testimonials/{pk}/{name}/',
            body or {}, format='json',
        )
        return res

    def test_full_workflow_path(self):
        pk = self._create(self.volunteer)

        # Volunteer submits.
        res = self._post_action(self.volunteer, pk, 'submit')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()['status'], 'under_review')

        # Volunteer cannot approve.
        res = self._post_action(self.volunteer, pk, 'approve')
        self.assertEqual(res.status_code, 403, res.content)

        # Advocate approves.
        res = self._post_action(self.advocate, pk, 'approve',
                                {'review_notes': 'verified'})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()['status'], 'approved')

        # Advocate publishes.
        res = self._post_action(self.advocate, pk, 'publish')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()['status'], 'published')

        # AuditLog rows exist for create + every transition.
        audit_actions = list(
            AuditLog.objects
            .filter(target_type='testimonial', target_id=pk)
            .order_by('timestamp')
            .values_list('action', flat=True)
        )
        # 1 create + 3 transitions (submit, approve, publish) = 4
        # EDITED rows total. No VIEWED rows in this test — those
        # belong to the encrypted-source endpoint tests.
        self.assertEqual(len(audit_actions), 4)
        details = list(
            AuditLog.objects
            .filter(target_type='testimonial', target_id=pk,
                    action=AuditLog.Action.EDITED)
            .values_list('details', flat=True)
        )
        # Each EDITED row carries a transition note.
        self.assertTrue(any('draft' in d and 'under_review' in d for d in details))
        self.assertTrue(any('under_review' in d and 'approved' in d for d in details))
        self.assertTrue(any('approved' in d and 'published' in d for d in details))

    def test_reject_requires_review_notes(self):
        pk = self._create(self.volunteer)
        self._post_action(self.volunteer, pk, 'submit')
        # Empty notes → 400.
        res = self._post_action(self.advocate, pk, 'reject', {})
        self.assertEqual(res.status_code, 400)
        # Notes set → 200 → status='rejected'.
        res = self._post_action(
            self.advocate, pk, 'reject', {'review_notes': 'source unreliable'}
        )
        self.assertEqual(res.json()['status'], 'rejected')

    def test_invalid_transition_rejected(self):
        pk = self._create(self.volunteer)
        # Cannot publish a draft directly.
        res = self._post_action(self.advocate, pk, 'publish')
        self.assertEqual(res.status_code, 400)
        body = res.content.decode()
        # DRF JSON-escapes inner quotes in error bodies; assert on
        # the structural tokens rather than the exact rendered
        # message to keep the test stable across quote-escaping
        # behaviour.
        self.assertIn('Cannot publish from', body)
        self.assertIn('draft', body)
        self.assertIn('approved', body)


# Role boundary + encryption endpoint.
@FERNET_KEY_SETTING
class EncryptedSourceEndpointTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.volunteer = make_user('vol', in_group='Volunteer')
        self.advocate = make_user('adv', in_group='Advocate')
        self.client = APIClient()

    def _make(self, *, source='', source_visibility='hidden', plain_loc=''):
        t = Testimonial.objects.create(
            title='x', slug=f's-{Testimonial.objects.count() + 1}',
            language='en', country='x', region='y',
            source_visibility=source_visibility,
            public_source_label='Family member',
            location_visibility='public_region',
            public_location_display='Erbil',
            summary='s', narrative='n', outcome='o',
        )
        if source:
            t.set_source(source)
        if plain_loc:
            t.set_precise_location(plain_loc)
        t.save()
        return t

    def test_volunteer_decrypt_source_is_403(self):
        t = self._make(source='real-secret-name', source_visibility='public_anonymous')
        # Even though the row is "public_anonymous" the volunteer
        # still cannot decrypt the real identity — the rule is by
        # role, not row visibility.
        self.client.force_login(self.volunteer)
        res = self.client.get(f'/api/testimonials/{t.id}/source/')
        self.assertEqual(res.status_code, 403)
        self.assertNotIn(b'real-secret-name', res.content)

    def test_advocate_decrypt_source_works_and_audits(self):
        t = self._make(source='real-secret-name')
        self.client.force_login(self.advocate)
        res = self.client.get(f'/api/testimonials/{t.id}/source/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['source'], 'real-secret-name')

        # Audit row records the decryption.
        log = AuditLog.objects.filter(
            target_type='testimonial', target_id=t.id,
            action=AuditLog.Action.VIEWED,
        ).first()
        self.assertIsNotNone(log)
        self.assertIn('decrypted source', log.details)

    def test_anonymous_cannot_decrypt(self):
        t = self._make(source='secret')
        # Anonymous client.
        res = self.client.get(f'/api/testimonials/{t.id}/source/')
        self.assertEqual(res.status_code, 403)


# Public surface masking.
@FERNET_KEY_SETTING
class PublicPayloadMaskingTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.volunteer = make_user('vol-pm', in_group='Volunteer')
        self.t = Testimonial.objects.create(
            title='x', slug='public-1',
            language='en', country='Iraq', region='Erbil',
            source_visibility='hidden',
            public_source_label='Family member',
            location_visibility='public_region',
            public_location_display='Erbil, Iraq',
            summary='s', narrative='n', outcome='o',
            status=Testimonial.Status.PUBLISHED,
        )

    def test_anonymous_public_payload_has_no_ciphertext(self):
        res = self.client.get('/api/testimonials/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('results', res.json())
        # Source-visible: must be False for hidden rows.
        results = res.json()['results']
        self.assertEqual(len(results), 1)
        row = results[0]
        self.assertFalse(row['source_visible'])
        self.assertNotIn('source_encrypted', row)
        self.assertNotIn('precise_location_encrypted', row)

    def test_anonymous_sees_only_published(self):
        # Add a draft; anon must NOT see it.
        Testimonial.objects.create(
            title='d', slug='draft-1', language='en',
            status=Testimonial.Status.DRAFT,
            summary='', narrative='', outcome='',
            country='', region='',
        )
        res = self.client.get('/api/testimonials/')
        self.assertEqual(res.status_code, 200)
        statuses = [r['status'] for r in res.json()['results']]
        self.assertEqual(statuses, ['published'])

    def test_volunteer_does_not_see_other_users_drafts(self):
        # A second volunteer's "My drafts" tab must not leak the
        # first volunteer's in-flight rows. The get_queryset filter
        # scopes non-staff authenticated users to their own rows plus
        # every published row.
        from django.contrib.auth import get_user_model
        User = get_user_model()
        other_volunteer, _ = User.objects.get_or_create(
            username='vol2',
            defaults={'is_active': True, 'email': 'vol2@test.local'},
        )
        from django.contrib.auth.models import Group
        try:
            volunteer_group = Group.objects.get(name='Volunteer')
            other_volunteer.groups.add(volunteer_group)
        except Group.DoesNotExist:
            pass

        # Create a draft authored by the OTHER volunteer.
        Testimonial.objects.create(
            title='other-vol-draft', slug='other-1',
            language='en', country='Iraq',
            status=Testimonial.Status.DRAFT,
            summary='', narrative='', outcome='',
            region='',
            created_by=other_volunteer,
        )
        # `self.t` (created in setUp) is published, so it must still
        # be visible — published rows are public to every viewer.

        self.client.force_login(self.volunteer)
        res = self.client.get('/api/testimonials/')
        self.assertEqual(res.status_code, 200)
        ids = [r['id'] for r in res.json()['results']]
        # The published row from setUp is visible; the other
        # volunteer's draft is not.
        self.assertIn(self.t.id, ids)
        for r in res.json()['results']:
            if r['status'] == 'draft':
                self.fail(
                    f"Volunteer can see another volunteer's draft "
                    f"(id={r['id']!r}, title={r.get('title')!r})"
                )


# Mass-assignment guard: volunteer cannot mark source as public_named.
@FERNET_KEY_SETTING
class SourceVisibilityPolicyTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.volunteer = make_user('vol', in_group='Volunteer')
        self.advocate = make_user('adv', in_group='Advocate')
        self.client = APIClient()

    def test_volunteer_cannot_publish_named_source(self):
        self.client.force_login(self.volunteer)
        res = self.client.post('/api/testimonials/', {
            'title': 't', 'language': 'en',
            'summary': 's', 'narrative': 'n', 'outcome': 'o',
            'country': 'c', 'region': 'r',
            'source_visibility': 'public_named',
            'public_source_label': 'witness',
            'location_visibility': 'public_region',
            'public_location_display': 'Erbil',
        }, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('Only Advocates', str(res.content))

    def test_advocate_can_publish_named_source(self):
        self.client.force_login(self.advocate)
        res = self.client.post('/api/testimonials/', {
            'title': 't', 'language': 'en',
            'summary': 's', 'narrative': 'n', 'outcome': 'o',
            'country': 'c', 'region': 'r',
            'source_visibility': 'public_named',
            'public_source_label': 'witness',
            'location_visibility': 'public_region',
            'public_location_display': 'Erbil',
        }, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['source_visibility'], 'public_named')


# Schema-version pinning: bumping the field list / JSON Schema \$id is
# an atomic, deliberate action — pin the v1 contract today.
class SchemaVersionPinTests(BaseTestCase):
    def test_export_serializer_required_fields(self):
        s = TestimonialExportSerializer()
        # schema_version, slug, language, published_at are all there.
        for f in ('schema_version', 'slug', 'language', 'published_at'):
            self.assertIn(f, s.fields)

    def test_json_schema_file_matches_python_dict(self):
        # Tests run from backend/, so resolve the schema file
        # relative to BASE_DIR (which is the backend/ directory).
        from django.conf import settings as dj_settings
        schema_path = Path(dj_settings.BASE_DIR) / 'cases/testimonials/export_schema.json'
        on_disk = json.loads(schema_path.read_text())
        # \$id is the versioned URL — bump together with schema_version.
        self.assertEqual(on_disk['$id'],
                         'https://testimonies.world/schemas/testimonial-export-v1.json')
        self.assertEqual(
            set(on_disk['required']),
            set(EXPORT_SCHEMA['required']),
        )
