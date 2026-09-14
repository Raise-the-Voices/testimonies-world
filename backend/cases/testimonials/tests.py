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
    decrypt_str, encrypt_str,
)
# Generate a fresh key per test process — never load the hardcoded
# dev key from cases.testimonials.dev_key. The hardcoded key's
# existence is acceptable (it's a clearly-marked DEV-ONLY constant)
# but tests should not be load-bearing on its value.
from cryptography.fernet import Fernet as _Fernet
_TEST_FERNET_KEY = _Fernet.generate_key()

FERNET_KEY_SETTING = override_settings(TESTIMONIALS_FERNET_KEY=_TEST_FERNET_KEY)
from cases.testimonials.export import EXPORT_SCHEMA, TestimonialExportSerializer
from cases.tests import make_user
from testimonies.test_base import BaseTestCase


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


# Rotation + production gate — closes the audit gaps.
class EncryptionRotationAndGateTests(BaseTestCase):
    """MultiFernet rotation + ImproperlyConfigured + RuntimeWarning.

    No `FERNET_KEY_SETTING` decorator: these tests assert the
    unconfigured path.
    """

    def setUp(self):
        super().setUp()
        from cases.testimonials import encryption
        encryption.get_fernet.cache_clear()

    def tearDown(self):
        from cases.testimonials import encryption
        encryption.get_fernet.cache_clear()
        super().tearDown()

    def test_multifernet_decrypts_old_key_after_rotation(self):
        """Old ciphertext, encrypted under key A, decrypts successfully
        when the runtime is configured with [B, A] — the rotation
        path. Without this, every prod rotation 500s every existing
        row.
        """
        import warnings
        from cryptography.fernet import Fernet
        from django.test import override_settings
        key_a = Fernet.generate_key()
        key_b = Fernet.generate_key()
        with override_settings(TESTIMONIALS_FERNET_KEYS=[key_b, key_a]):
            from cases.testimonials import encryption
            encryption.get_fernet.cache_clear()
            # Encrypt under key_a (we construct the Fernet directly
            # to simulate data written by a previous version).
            ct = Fernet(key_a).encrypt(b'legacy plaintext')
            # Decrypt via the running config — should succeed.
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', RuntimeWarning)
                self.assertEqual(
                    encryption.decrypt_str(ct),
                    'legacy plaintext',
                )

    def test_multifernet_uses_first_key_for_encrypt(self):
        """Encrypt under a [B, A] config yields ciphertext that B can
        decrypt — A cannot. First-key-wins for writes; all-keys-tried
        for reads.
        """
        from cryptography.fernet import Fernet, InvalidToken
        from django.test import override_settings
        key_a = Fernet.generate_key()
        key_b = Fernet.generate_key()
        with override_settings(TESTIMONIALS_FERNET_KEYS=[key_b, key_a]):
            from cases.testimonials import encryption
            encryption.get_fernet.cache_clear()
            ct = encryption.encrypt_str('hello')
            self.assertEqual(
                Fernet(key_b).decrypt(bytes(ct)),
                b'hello',
            )
            with self.assertRaises(InvalidToken):
                Fernet(key_a).decrypt(bytes(ct))

    def test_single_key_setting_still_works(self):
        """Backward-compat: TESTIMONIALS_FERNET_KEY (single) still
        encrypts + decrypts as before. Pin the legacy config.
        """
        from cryptography.fernet import Fernet
        from django.test import override_settings
        key = Fernet.generate_key()
        with override_settings(TESTIMONIALS_FERNET_KEY=key):
            from cases.testimonials import encryption
            encryption.get_fernet.cache_clear()
            ct = encryption.encrypt_str('legacy single-key mode')
            self.assertEqual(
                encryption.decrypt_str(ct),
                'legacy single-key mode',
            )

    def test_improperly_configured_when_debug_false_and_no_key(self):
        """DEBUG=False + no TESTIMONIALS_FERNET_KEY[S] + ALLOW_DEV_FALLBACK_KEY
        default (False in prod) → ImproperlyConfigured on first call.

        The audit's gap: this fired only at first decrypt, but a
        startup that never touches encryption would silently boot
        and 500 on the first /source/ hit. The first-call behavior is
        what we pin here — pinning it at startup is a follow-up.
        """
        from django.core.exceptions import ImproperlyConfigured
        from django.test import override_settings
        with override_settings(
            DEBUG=False,
            TESTIMONIALS_FERNET_KEY=None,
            TESTIMONIALS_FERNET_KEYS=None,
            ALLOW_DEV_FALLBACK_KEY=False,
        ):
            from cases.testimonials import encryption
            encryption.get_fernet.cache_clear()
            with self.assertRaises(ImproperlyConfigured):
                encryption.get_fernet()

    def test_runtime_warning_when_debug_true_and_no_key(self):
        """DEBUG=True + no key + ALLOW_DEV_FALLBACK_KEY default (True)
        → RuntimeWarning fires once per process (lru_cache). The
        warning is the cue that production data isn't protected.
        """
        import warnings
        from django.test import override_settings
        with override_settings(
            DEBUG=True,
            TESTIMONIALS_FERNET_KEY=None,
            TESTIMONIALS_FERNET_KEYS=None,
        ):
            from cases.testimonials import encryption
            encryption.get_fernet.cache_clear()
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always')
                encryption.get_fernet()
                runtime_warnings = [
                    w for w in caught
                    if issubclass(w.category, RuntimeWarning)
                ]
                self.assertTrue(
                    runtime_warnings,
                    'expected RuntimeWarning when no key is configured '
                    'and DEBUG=True',
                )
                msg = str(runtime_warnings[0].message)
                self.assertIn('DEV fallback key', msg)


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

        # Advocate approves — single-step, lands the row at
        # 'published' directly. The 2-step (approve → publish) flow
        # is gone; legacy approved rows can still be migrated via
        # /publish/ but new rows never sit at 'approved'.
        res = self._post_action(self.advocate, pk, 'approve',
                                {'review_notes': 'verified'})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()['status'], 'published')
        # Both stamps land in the same transition.
        self.assertIsNotNone(res.json().get('reviewed_at'))
        self.assertIsNotNone(res.json().get('published_at'))

        # AuditLog rows exist for create + every transition.
        audit_actions = list(
            AuditLog.objects
            .filter(target_type='testimonial', target_id=pk)
            .order_by('timestamp')
            .values_list('action', flat=True)
        )
        # 1 create + 2 transitions (submit, approve) = 3
        # EDITED rows total. No VIEWED rows in this test — those
        # belong to the encrypted-source endpoint tests.
        self.assertEqual(len(audit_actions), 3)
        details = list(
            AuditLog.objects
            .filter(target_type='testimonial', target_id=pk,
                    action=AuditLog.Action.EDITED)
            .values_list('details', flat=True)
        )
        # Each EDITED row carries a transition note.
        self.assertTrue(any('draft' in d and 'under_review' in d for d in details))
        self.assertTrue(any('under_review' in d and 'published' in d for d in details))

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
        # Cannot archive a draft directly (archive requires PUBLISHED).
        res = self._post_action(self.advocate, pk, 'archive')
        self.assertEqual(res.status_code, 400)
        body = res.content.decode()
        # DRF JSON-escapes inner quotes in error bodies; assert on
        # the structural tokens rather than the exact rendered
        # message to keep the test stable across quote-escaping
        # behaviour.
        self.assertIn('Cannot archive from', body)
        self.assertIn('draft', body)
        self.assertIn('published', body)


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


# Status filtering: pin the contract that drafts NEVER leak to
# anonymous users, and that the create path always lands at
# status='draft' regardless of what the client tries to send.
#
# These tests are the safety net for the public-vs-private boundary.
# Existing list tests (PublicPayloadMaskingTests) cover the
# anonymous list; this class closes the gap on:
#   - create defaults to DRAFT (and silently drops client-supplied
#     status, since TestimonialWriteSerializer excludes it)
#   - retrieve honors the same role/status scoping as list
#   - the explicit ?status=published query param works for any
#     authenticated viewer (anonymous is already filtered above)
@FERNET_KEY_SETTING
class TestimonialStatusFilterTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.author = make_user('author', in_group='Volunteer')
        self.other_volunteer = make_user('other-vol', in_group='Volunteer')
        self.advocate = make_user('adv', in_group='Advocate')
        self.client = APIClient()

    def _make_row(self, *, status_value, created_by=None, slug=None):
        """Insert a Testimonial directly (bypasses create flow) so we
        can stage arbitrary statuses for the read-path tests below."""
        slug = slug or f's-{Testimonial.objects.count() + 1}-{uuid.uuid4().hex[:6]}'
        return Testimonial.objects.create(
            title='row', slug=slug, language='en',
            country='Iraq', region='Erbil',
            summary='s', narrative='n', outcome='o',
            source_visibility='hidden',
            public_source_label='Family member',
            location_visibility='public_region',
            public_location_display='Erbil',
            status=status_value,
            created_by=created_by,
        )

    # ---- Create defaults to DRAFT, ignores client status payload ----

    def test_create_defaults_to_draft_status(self):
        """POST without `status` → server lands at draft.

        The model has default=Status.DRAFT and the write serializer
        excludes `status`, so this combination lands every create at
        'draft' regardless of client input. Pin it: a regression that
        defaulted to PUBLISHED here would publish every draft by
        accident — the original 'drafts leaking' incident in spirit.
        """
        self.client.force_login(self.author)
        res = self.client.post('/api/testimonials/', {
            'title': 'Detention in Erbil',
            'language': 'en',
            'country': 'Iraq',
            'region': 'Erbil',
            'summary': 'summary',
            'narrative': 'narrative',
            'outcome': 'outcome',
            'source_visibility': 'hidden',
            'public_source_label': 'Family member',
            'location_visibility': 'public_region',
            'public_location_display': 'Erbil',
        }, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        # The create response uses the write serializer (which
        # excludes `status`); re-fetch the row from DB to read the
        # post-save status — that's the source of truth.
        row = Testimonial.objects.get(pk=res.json()['id'])
        self.assertEqual(row.status, Testimonial.Status.DRAFT)

    def test_create_ignores_client_supplied_status(self):
        """A malicious or confused client cannot self-publish via POST.

        `status` is in `TestimonialWriteSerializer.Meta.exclude`, so
        any payload value is silently dropped. The model default
        (DRAFT) wins. This is the mass-assignment guard from
        SYSTEM_RULES §5 applied to the most dangerous field on the
        model.
        """
        self.client.force_login(self.author)
        for attempted in ('published', 'approved', 'under_review'):
            res = self.client.post('/api/testimonials/', {
                'title': f'attempt-{attempted}',
                'language': 'en',
                'country': 'Iraq',
                'region': 'Erbil',
                'summary': 'summary',
                'narrative': 'narrative',
                'outcome': 'outcome',
                'source_visibility': 'hidden',
                'public_source_label': 'Family member',
                'location_visibility': 'public_region',
                'public_location_display': 'Erbil',
                'status': attempted,
            }, format='json')
            self.assertEqual(res.status_code, 201, res.content)
            # Re-fetch from DB — the create response uses the write
            # serializer which omits `status`, so it can't tell us
            # what landed.
            row = Testimonial.objects.get(pk=res.json()['id'])
            self.assertEqual(
                row.status, Testimonial.Status.DRAFT,
                msg=(
                    f'Client supplied status={attempted!r} but row '
                    f'landed at status={row.status!r} — silent drop '
                    f'failed for {attempted}.'
                ),
            )

    def test_patch_ignores_client_supplied_status(self):
        """Same mass-assignment guard on PATCH — a draft owner cannot
        self-publish by sneaking `status` into a partial_update.
        """
        self.client.force_login(self.author)
        create = self.client.post('/api/testimonials/', {
            'title': 't', 'language': 'en',
            'country': 'Iraq', 'region': 'Erbil',
            'summary': 'summary', 'narrative': 'narrative',
            'outcome': 'outcome',
            'source_visibility': 'hidden',
            'public_source_label': 'Family member',
            'location_visibility': 'public_region',
            'public_location_display': 'Erbil',
        }, format='json')
        self.assertEqual(create.status_code, 201, create.content)
        pk = create.json()['id']

        # Try to PATCH to published — must be ignored.
        patch = self.client.patch(
            f'/api/testimonials/{pk}/',
            {'status': 'published'},
            format='json',
        )
        self.assertEqual(patch.status_code, 200, patch.content)
        row = Testimonial.objects.get(pk=pk)
        self.assertEqual(row.status, Testimonial.Status.DRAFT)

    # ---- Retrieve honors the same scoping as list ----

    def test_anonymous_cannot_retrieve_draft(self):
        """Direct GET on a draft id returns 404 to an anonymous client.

        Without the get_queryset filter, ModelViewSet.retrieve would
        hand back the draft — the same privacy leak as a list leak,
        just through a different URL.
        """
        draft = self._make_row(status_value=Testimonial.Status.DRAFT)
        res = self.client.get(f'/api/testimonials/{draft.id}/')
        self.assertEqual(res.status_code, 404)

    def test_author_can_retrieve_own_draft(self):
        """The draft owner is the only volunteer who can retrieve a
        draft via GET — the role/status scoping for retrieve must
        match the list endpoint.
        """
        draft = self._make_row(
            status_value=Testimonial.Status.DRAFT,
            created_by=self.author,
        )
        self.client.force_login(self.author)
        res = self.client.get(f'/api/testimonials/{draft.id}/')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()['status'], 'draft')

    def test_other_volunteer_cannot_retrieve_someone_elses_draft(self):
        """A second volunteer's GET on someone else's draft is 404.

        Without the role-based scoping, this is exactly the cross-user
        leak `test_volunteer_does_not_see_other_users_drafts` guards
        against in list — same fix, different endpoint.
        """
        draft = self._make_row(
            status_value=Testimonial.Status.DRAFT,
            created_by=self.author,
        )
        self.client.force_login(self.other_volunteer)
        res = self.client.get(f'/api/testimonials/{draft.id}/')
        self.assertEqual(res.status_code, 404)

    def test_anyone_can_retrieve_published(self):
        """A published row is public — anonymous, the author, another
        volunteer, and an advocate all get a 200. Pins the read path
        for the success side of the contract.
        """
        published = self._make_row(
            status_value=Testimonial.Status.PUBLISHED,
            created_by=self.author,
        )
        for who in ('anon', 'author', 'other_volunteer', 'advocate'):
            if who == 'anon':
                self.client.logout()
            elif who == 'author':
                self.client.force_login(self.author)
            elif who == 'other_volunteer':
                self.client.force_login(self.other_volunteer)
            else:
                self.client.force_login(self.advocate)
            res = self.client.get(f'/api/testimonials/{published.id}/')
            self.assertEqual(
                res.status_code, 200,
                msg=(
                    f'{who!r} should see the published row but got '
                    f'status {res.status_code} (body: {res.content!r})'
                ),
            )
            self.assertEqual(res.json()['status'], 'published')

    # ---- Explicit ?status=published query filter ----

    def test_status_published_query_param_filters_to_published(self):
        """`?status=published` returns only published rows regardless
        of role — for an advocate (who normally sees everything) this
        proves the explicit filter narrows the result rather than
        widening it.
        """
        # Stage a published + a draft + an under_review row.
        self._make_row(status_value=Testimonial.Status.PUBLISHED)
        self._make_row(status_value=Testimonial.Status.DRAFT)
        self._make_row(status_value=Testimonial.Status.UNDER_REVIEW)

        self.client.force_login(self.advocate)
        res = self.client.get('/api/testimonials/?status=published')
        self.assertEqual(res.status_code, 200)
        statuses = [r['status'] for r in res.json()['results']]
        self.assertTrue(
            statuses, '?status=published returned an empty list — '
                     'the filter probably shadowed the data.'
        )
        for s in statuses:
            self.assertEqual(s, 'published')

    def test_volunteer_status_draft_returns_only_own_drafts(self):
        """`?status=draft` for a Volunteer must narrow to that
        volunteer's own drafts. Without the explicit filter, the
        queryset would fall through to the role-based union
        (`created_by=user | status=PUBLISHED`) and the volunteer
        would see every published row mixed in — which is exactly
        the "My drafts" tab loading the wrong rows bug the front
        end was reporting.
        """
        # Stage: own draft, other-volunteer draft, own under_review,
        # published-by-someone-else. Only the first should appear.
        own_draft = self._make_row(
            status_value=Testimonial.Status.DRAFT,
            created_by=self.author,
        )
        self._make_row(
            status_value=Testimonial.Status.DRAFT,
            created_by=self.other_volunteer,
        )
        self._make_row(
            status_value=Testimonial.Status.UNDER_REVIEW,
            created_by=self.author,
        )
        self._make_row(
            status_value=Testimonial.Status.PUBLISHED,
            created_by=self.other_volunteer,
        )

        self.client.force_login(self.author)
        res = self.client.get('/api/testimonials/?status=draft')
        self.assertEqual(res.status_code, 200)
        ids = [r['id'] for r in res.json()['results']]
        self.assertEqual(ids, [own_draft.id])
        for r in res.json()['results']:
            self.assertEqual(r['status'], 'draft')

    def test_advocate_status_draft_returns_only_own_drafts(self):
        """`?status=draft` for an Advocate must ALSO narrow to the
        Advocate's own drafts. The semantic of "My drafts" is
        "MY drafts" — Advocate+ don't get a privileged view of
        every other user's in-flight drafts through this endpoint;
        they use `?status=under_review` (Review queue) for that.

        Without this narrowing, the front-end "My drafts" tab would
        either show every staff member's drafts mixed in (cluttered)
        or be force-cleared client-side for staff (always empty,
        contradicting the principle that "My X" means "my X").

        Regression test for the bug where `?status=draft` widened to
        `qs.filter(status='draft')` for Advocate+, leaving staff
        unable to track their own drafts through the dedicated tab.
        """
        # Stage: advocate's own draft, another volunteer's draft,
        # a published row, an under_review row. Only the first
        # should appear for the Advocate on `?status=draft`.
        own_draft = self._make_row(
            status_value=Testimonial.Status.DRAFT,
            created_by=self.advocate,
        )
        self._make_row(
            status_value=Testimonial.Status.DRAFT,
            created_by=self.other_volunteer,
        )
        self._make_row(
            status_value=Testimonial.Status.PUBLISHED,
            created_by=self.author,
        )
        self._make_row(
            status_value=Testimonial.Status.UNDER_REVIEW,
            created_by=self.author,
        )

        self.client.force_login(self.advocate)
        res = self.client.get('/api/testimonials/?status=draft')
        self.assertEqual(res.status_code, 200)
        ids = [r['id'] for r in res.json()['results']]
        self.assertEqual(ids, [own_draft.id])
        for r in res.json()['results']:
            self.assertEqual(r['status'], 'draft')

    def test_advocate_status_under_review_narrows_to_under_review(self):
        """`?status=under_review` for an Advocate narrows to that
        status. Without the explicit filter, an Advocate (who
        normally sees everything) would get the full queryset and
        the front-end "Review queue" tab would have to bucket-filter
        client-side — slow and error-prone.
        """
        pending = self._make_row(status_value=Testimonial.Status.UNDER_REVIEW)
        self._make_row(status_value=Testimonial.Status.DRAFT)
        self._make_row(status_value=Testimonial.Status.REJECTED)
        self._make_row(status_value=Testimonial.Status.PUBLISHED)

        self.client.force_login(self.advocate)
        res = self.client.get('/api/testimonials/?status=under_review')
        self.assertEqual(res.status_code, 200)
        ids = [r['id'] for r in res.json()['results']]
        self.assertEqual(ids, [pending.id])
        for r in res.json()['results']:
            self.assertEqual(r['status'], 'under_review')

    def test_anonymous_status_draft_does_not_leak(self):
        """`?status=draft` for an anonymous client must NOT return
        drafts — that's private information. The backend should
        silently fall back to the PUBLISHED-only branch rather
        than 500 or leak rows.
        """
        self._make_row(status_value=Testimonial.Status.DRAFT)
        self._make_row(status_value=Testimonial.Status.PUBLISHED)

        # Anonymous client — no force_login.
        res = self.client.get('/api/testimonials/?status=draft')
        self.assertEqual(res.status_code, 200)
        statuses = [r['status'] for r in res.json()['results']]
        for s in statuses:
            self.assertEqual(s, 'published')

    def test_unknown_status_param_falls_through_safely(self):
        """Garbage status values (?status=banana) must not 500 or
        return every row. They fall through to the role-based
        default scoping (anonymous → PUBLISHED only).
        """
        self._make_row(status_value=Testimonial.Status.DRAFT)
        self._make_row(status_value=Testimonial.Status.PUBLISHED)

        res = self.client.get('/api/testimonials/?status=banana')
        self.assertEqual(res.status_code, 200)
        statuses = [r['status'] for r in res.json()['results']]
        for s in statuses:
            self.assertEqual(s, 'published')


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


# Per-action permission gating — closes the destroy + cross-user PATCH
# holes the audit found (class-level permission_classes was too coarse).
@FERNET_KEY_SETTING
class PermissionBoundaryTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.author = make_user('author', in_group='Volunteer')
        self.other_volunteer = make_user('other-vol', in_group='Volunteer')
        self.advocate = make_user('adv', in_group='Advocate')
        self.client = APIClient()

    def _make(self, *, status_value, created_by=None):
        return Testimonial.objects.create(
            title='t', slug=f's-perm-{Testimonial.objects.count()+1}',
            language='en', country='Iraq', region='Erbil',
            summary='s', narrative='n', outcome='o',
            source_visibility='hidden',
            public_source_label='Family member',
            location_visibility='public_region',
            public_location_display='Erbil',
            status=status_value, created_by=created_by,
        )

    def test_volunteer_cannot_destroy_any_testimonial(self):
        for st in (Testimonial.Status.DRAFT, Testimonial.Status.PUBLISHED):
            row = self._make(status_value=st, created_by=self.author)
            self.client.force_login(self.other_volunteer)
            res = self.client.delete(f'/api/testimonials/{row.id}/')
            self.assertEqual(
                res.status_code, 403,
                msg=f'delete of {st} by other-volunteer should 403',
            )
            self.assertTrue(
                Testimonial.objects.filter(pk=row.id).exists(),
                f'delete of {st} row actually removed — RBAC hole!',
            )

    def test_anonymous_cannot_destroy(self):
        row = self._make(status_value=Testimonial.Status.PUBLISHED)
        res = self.client.delete(f'/api/testimonials/{row.id}/')
        self.assertEqual(res.status_code, 403)
        self.assertTrue(Testimonial.objects.filter(pk=row.id).exists())

    def test_advocate_can_destroy_published(self):
        row = self._make(status_value=Testimonial.Status.PUBLISHED)
        self.client.force_login(self.advocate)
        res = self.client.delete(f'/api/testimonials/{row.id}/')
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Testimonial.objects.filter(pk=row.id).exists())

    def test_volunteer_cannot_patch_other_volunteers_draft(self):
        draft = self._make(
            status_value=Testimonial.Status.DRAFT,
            created_by=self.author,
        )
        self.client.force_login(self.other_volunteer)
        res = self.client.patch(
            f'/api/testimonials/{draft.id}/',
            {'title': 'hijacked'}, format='json',
        )
        # 403 if the queryset exposes the row but the object
        # permission denies; 404 if the queryset scopes the row out
        # entirely (which is what get_queryset does for non-owner
        # volunteers). Either response is acceptable as long as
        # the row is not modified.
        self.assertIn(res.status_code, (403, 404),
                      f'unexpected status {res.status_code}')
        draft.refresh_from_db()
        self.assertEqual(draft.title, 't')

    def test_owner_can_patch_own_draft(self):
        draft = self._make(
            status_value=Testimonial.Status.DRAFT,
            created_by=self.author,
        )
        self.client.force_login(self.author)
        res = self.client.patch(
            f'/api/testimonials/{draft.id}/',
            {'title': 'updated by owner'}, format='json',
        )
        self.assertEqual(res.status_code, 200, res.content)
        draft.refresh_from_db()
        self.assertEqual(draft.title, 'updated by owner')

    def test_owner_cannot_patch_own_published_row(self):
        row = self._make(
            status_value=Testimonial.Status.PUBLISHED,
            created_by=self.author,
        )
        self.client.force_login(self.author)
        res = self.client.patch(
            f'/api/testimonials/{row.id}/',
            {'title': 'tampered'}, format='json',
        )
        self.assertEqual(res.status_code, 403)
        row.refresh_from_db()
        self.assertEqual(row.title, 't')

    def test_advocate_can_patch_any_draft(self):
        draft = self._make(
            status_value=Testimonial.Status.DRAFT,
            created_by=self.author,
        )
        self.client.force_login(self.advocate)
        res = self.client.patch(
            f'/api/testimonials/{draft.id}/',
            {'title': 'advocate edit'}, format='json',
        )
        self.assertEqual(res.status_code, 200, res.content)


# Endpoints the audit found untested: /precise_location/ audit row,
# archive transition, IDOR on under_review/rejected, audit-actor
# server-side pinning, internal serializer ciphertext exclusion.
@FERNET_KEY_SETTING
class PreciseLocationEndpointTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.volunteer = make_user('vol', in_group='Volunteer')
        self.advocate = make_user('adv', in_group='Advocate')
        self.client = APIClient()

    def _make(self, *, precise_loc=''):
        t = Testimonial.objects.create(
            title='x', slug=f's-ploc-{Testimonial.objects.count()+1}',
            language='en', country='x', region='y',
            source_visibility='hidden',
            public_source_label='Family member',
            location_visibility='hidden',
            public_location_display='Erbil',
            summary='s', narrative='n', outcome='o',
        )
        if precise_loc:
            t.set_precise_location(precise_loc)
        t.save()
        return t

    def test_volunteer_decrypt_precise_location_is_403(self):
        t = self._make(precise_loc='Erbil, 36.19, 44.01')
        self.client.force_login(self.volunteer)
        res = self.client.get(
            f'/api/testimonials/{t.id}/precise_location/',
        )
        self.assertEqual(res.status_code, 403)
        self.assertNotIn(b'36.19', res.content)

    def test_advocate_decrypt_precise_location_works_and_audits(self):
        t = self._make(precise_loc='Erbil, 36.19, 44.01')
        self.client.force_login(self.advocate)
        res = self.client.get(
            f'/api/testimonials/{t.id}/precise_location/',
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.json()['precise_location'], 'Erbil, 36.19, 44.01',
        )
        log = AuditLog.objects.filter(
            target_type='testimonial', target_id=t.id,
            action=AuditLog.Action.VIEWED,
        ).first()
        self.assertIsNotNone(log)
        self.assertIn('decrypted precise location', log.details)

    def test_anonymous_cannot_decrypt_precise_location(self):
        t = self._make(precise_loc='secret')
        res = self.client.get(
            f'/api/testimonials/{t.id}/precise_location/',
        )
        self.assertEqual(res.status_code, 403)


@FERNET_KEY_SETTING
class ArchiveTransitionTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.author = make_user('author', in_group='Volunteer')
        self.advocate = make_user('adv', in_group='Advocate')
        self.client = APIClient()

    def _create_via_api(self, user):
        self.client.force_login(user)
        res = self.client.post('/api/testimonials/', {
            'title': 't', 'language': 'en',
            'country': 'Iraq', 'region': 'Erbil',
            'summary': 's', 'narrative': 'n', 'outcome': 'o',
            'source_visibility': 'hidden',
            'public_source_label': 'Family member',
            'location_visibility': 'public_region',
            'public_location_display': 'Erbil',
        }, format='json')
        return res.json()['id']

    def _submit_and_approve(self, pk):
        self.client.force_login(self.author)
        self.client.post(f'/api/testimonials/{pk}/submit/')
        self.client.force_login(self.advocate)
        self.client.post(f'/api/testimonials/{pk}/approve/', {})

    def test_archive_published_creates_audit_and_stamps_archived_at(self):
        pk = self._create_via_api(self.author)
        self._submit_and_approve(pk)
        row = Testimonial.objects.get(pk=pk)
        self.assertEqual(row.status, Testimonial.Status.PUBLISHED)
        # Archive.
        self.client.force_login(self.advocate)
        res = self.client.post(f'/api/testimonials/{pk}/archive/')
        self.assertEqual(res.status_code, 200, res.content)
        row.refresh_from_db()
        self.assertEqual(row.status, Testimonial.Status.ARCHIVED)
        self.assertIsNotNone(row.archived_at)
        # Audit row.
        audit = AuditLog.objects.filter(
            target_type='testimonial', target_id=pk,
            action=AuditLog.Action.EDITED,
        )
        self.assertTrue(
            any('published' in a.details and 'archived' in a.details
                for a in audit),
            'no audit row for the published → archived transition',
        )

    def test_volunteer_cannot_archive(self):
        pk = self._create_via_api(self.author)
        self._submit_and_approve(pk)
        self.client.force_login(self.author)
        res = self.client.post(f'/api/testimonials/{pk}/archive/')
        self.assertEqual(res.status_code, 403)
        row = Testimonial.objects.get(pk=pk)
        self.assertEqual(row.status, Testimonial.Status.PUBLISHED)


@FERNET_KEY_SETTING
class IDORNonDraftTests(BaseTestCase):
    """The audit found that IDOR was only pinned for DRAFT — the
    same scoping must apply to under_review, rejected, and archived
    rows for non-owner non-Advocate users.
    """

    def setUp(self):
        super().setUp()
        self.author = make_user('author', in_group='Volunteer')
        self.other = make_user('other-vol', in_group='Volunteer')
        self.advocate = make_user('adv', in_group='Advocate')
        self.client = APIClient()

    def _make(self, *, status_value, created_by=None):
        return Testimonial.objects.create(
            title='t', slug=f's-idor-{Testimonial.objects.count()+1}',
            language='en', country='Iraq', region='Erbil',
            summary='s', narrative='n', outcome='o',
            source_visibility='hidden',
            public_source_label='Family member',
            location_visibility='public_region',
            public_location_display='Erbil',
            status=status_value, created_by=created_by,
        )

    def _get(self, row):
        self.client.force_login(self.other)
        return self.client.get(f'/api/testimonials/{row.id}/')

    def test_other_volunteer_cannot_retrieve_someone_elses_under_review(self):
        row = self._make(
            status_value=Testimonial.Status.UNDER_REVIEW,
            created_by=self.author,
        )
        res = self._get(row)
        # Under the role-based scoping, another volunteer cannot see
        # someone else's in-flight row — 404 is the correct response.
        self.assertIn(res.status_code, (403, 404))

    def test_other_volunteer_cannot_retrieve_someone_elses_rejected(self):
        row = self._make(
            status_value=Testimonial.Status.REJECTED,
            created_by=self.author,
        )
        res = self._get(row)
        self.assertIn(res.status_code, (403, 404))

    def test_other_volunteer_cannot_retrieve_someone_elses_archived(self):
        row = self._make(
            status_value=Testimonial.Status.ARCHIVED,
            created_by=self.author,
        )
        res = self._get(row)
        self.assertIn(res.status_code, (403, 404))

    def test_owner_can_retrieve_own_under_review(self):
        row = self._make(
            status_value=Testimonial.Status.UNDER_REVIEW,
            created_by=self.author,
        )
        self.client.force_login(self.author)
        res = self.client.get(f'/api/testimonials/{row.id}/')
        self.assertEqual(res.status_code, 200)

    def test_advocate_can_retrieve_any_status(self):
        for st in (Testimonial.Status.UNDER_REVIEW,
                   Testimonial.Status.REJECTED,
                   Testimonial.Status.ARCHIVED):
            row = self._make(
                status_value=st, created_by=self.author,
            )
            self.client.force_login(self.advocate)
            res = self.client.get(f'/api/testimonials/{row.id}/')
            self.assertEqual(
                res.status_code, 200,
                f'advocate should retrieve {st}, got {res.status_code}',
            )


@FERNET_KEY_SETTING
class AuditActorPinningTests(BaseTestCase):
    """Server-side pinning: AuditLog.user is always request.user,
    even if a client tries to spoof by sending `user` or `actor` in
    the request body. The audit row's `user` reflects the real
    requester; the request body's value is silently dropped.
    """

    def setUp(self):
        super().setUp()
        self.author = make_user('author', in_group='Volunteer')
        self.advocate = make_user('adv', in_group='Advocate')
        self.client = APIClient()

    def test_patch_with_user_field_does_not_spoof_audit_actor(self):
        """A malicious client sends `user=42` in a PATCH body. The
        audit row must attribute the change to request.user, not 42.
        """
        self.client.force_login(self.author)
        create = self.client.post('/api/testimonials/', {
            'title': 't', 'language': 'en',
            'country': 'Iraq', 'region': 'Erbil',
            'summary': 's', 'narrative': 'n', 'outcome': 'o',
            'source_visibility': 'hidden',
            'public_source_label': 'Family member',
            'location_visibility': 'public_region',
            'public_location_display': 'Erbil',
        }, format='json')
        pk = create.json()['id']
        # Try to spoof the actor.
        patch = self.client.patch(
            f'/api/testimonials/{pk}/',
            {'title': 'spoofed', 'user': 99999, 'created_by': 99999},
            format='json',
        )
        self.assertEqual(patch.status_code, 200, patch.content)
        # Audit row was written for the UPDATE — user must be self.author.
        audit = AuditLog.objects.filter(
            target_type='testimonial', target_id=pk,
            action=AuditLog.Action.EDITED,
        )
        self.assertTrue(audit.exists())
        # The 'updated' audit row (not 'created') is the one we're
        # interested in.
        update_audits = [a for a in audit if 'updated' in a.details]
        self.assertTrue(update_audits,
                        'no UPDATE audit row found')
        for a in update_audits:
            self.assertEqual(a.user, self.author,
                             'audit row attributed to spoofed actor')


@FERNET_KEY_SETTING
class InternalSerializerCiphertextExclusionTests(BaseTestCase):
    """Even an authenticated Advocate's GET on /api/testimonials/{id}/
    must not include source_encrypted / precise_location_encrypted.
    Decrypted plaintext flows only through the dedicated endpoints.
    """

    def setUp(self):
        super().setUp()
        self.advocate = make_user('adv', in_group='Advocate')
        self.client = APIClient()

    def test_internal_serializer_excludes_ciphertext_columns(self):
        t = Testimonial.objects.create(
            title='t', slug='s-cipher-1',
            language='en', country='Iraq', region='Erbil',
            summary='s', narrative='n', outcome='o',
            source_visibility='hidden',
            public_source_label='Family member',
            location_visibility='public_region',
            public_location_display='Erbil',
            status=Testimonial.Status.PUBLISHED,
        )
        t.set_source('real-secret')
        t.set_precise_location('Erbil precise')
        t.save()
        self.client.force_login(self.advocate)
        res = self.client.get(f'/api/testimonials/{t.id}/')
        self.assertEqual(res.status_code, 200)
        body = res.content.decode()
        self.assertNotIn('source_encrypted', body)
        self.assertNotIn('precise_location_encrypted', body)
        self.assertNotIn('real-secret', body,
                         'plaintext source leaked into internal serializer')
        self.assertNotIn('Erbil precise', body,
                         'plaintext location leaked into internal serializer')
