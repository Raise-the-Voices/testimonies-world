"""
Tests for the contacts API.

The viewset enforces:
- IsAdvocate permission (advocate group OR is_staff)
- Soft-delete (DELETE sets deleted_at, doesn't remove the row)
- AuditLog writes on create / update / delete

We test at the request layer (APIClient) so we exercise the full
permission + viewset + serializer + audit-log path. SQLite test DB
already configured in settings.py — no PG needed.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from cases.models import AuditLog
from .models import Contact


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


class PermissionTests(TestCase):
    def setUp(self):
        self.advocate = make_user('aisha', in_group='Advocate')
        self.staff = make_user('admin', is_staff=True)
        self.volunteer = make_user('vol', in_group='Volunteer')
        self.outsider = make_user('random')
        self.client = APIClient()

    def test_outsider_cannot_list(self):
        self.client.force_login(self.outsider)
        res = self.client.get('/api/contacts/')
        self.assertEqual(res.status_code, 403)

    def test_volunteer_cannot_list(self):
        self.client.force_login(self.volunteer)
        res = self.client.get('/api/contacts/')
        self.assertEqual(res.status_code, 403)

    def test_volunteer_cannot_create(self):
        self.client.force_login(self.volunteer)
        res = self.client.post('/api/contacts/', {'name': 'X', 'role': 'other'})
        self.assertEqual(res.status_code, 403)

    def test_outsider_cannot_create(self):
        self.client.force_login(self.outsider)
        res = self.client.post('/api/contacts/', {'name': 'X', 'role': 'other'})
        self.assertEqual(res.status_code, 403)

    def test_advocate_can_list_and_create(self):
        self.client.force_login(self.advocate)
        self.assertEqual(self.client.get('/api/contacts/').status_code, 200)
        res = self.client.post('/api/contacts/', {
            'name': 'Layla H.', 'role': 'lawyer', 'email': 'layla@example.org',
        })
        self.assertEqual(res.status_code, 201)
        self.assertTrue(Contact.objects.filter(name='Layla H.').exists())

    def test_staff_can_list_and_create(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get('/api/contacts/').status_code, 200)
        res = self.client.post('/api/contacts/', {'name': 'Sami K.', 'role': 'family'})
        self.assertEqual(res.status_code, 201)


class SoftDeleteTests(TestCase):
    def setUp(self):
        self.advocate = make_user('aisha', in_group='Advocate')
        self.client = APIClient()
        self.client.force_login(self.advocate)
        self.contact = Contact.objects.create(name='Layla H.', role='lawyer')

    def test_delete_sets_tombstone_not_row_removal(self):
        pk = self.contact.pk
        res = self.client.delete(f'/api/contacts/{pk}/')
        self.assertEqual(res.status_code, 204)
        # Row still exists; deleted_at is set.
        self.contact.refresh_from_db()
        self.assertIsNotNone(self.contact.deleted_at)
        self.assertTrue(Contact.objects.filter(pk=pk).exists())

    def test_deleted_row_excluded_from_default_list(self):
        self.client.delete(f'/api/contacts/{self.contact.pk}/')
        res = self.client.get('/api/contacts/')
        self.assertEqual(res.status_code, 200)
        # DRF pagination wraps the list in {results, count}; read results.
        ids = [c['id'] for c in res.json()['results']]
        self.assertNotIn(self.contact.pk, ids)

    def test_deleted_row_visible_with_explicit_filter(self):
        self.client.delete(f'/api/contacts/{self.contact.pk}/')
        res = self.client.get('/api/contacts/?deleted=true')
        self.assertEqual(res.status_code, 200)
        ids = [c['id'] for c in res.json()['results']]
        self.assertIn(self.contact.pk, ids)

    def test_double_delete_rejected(self):
        self.client.delete(f'/api/contacts/{self.contact.pk}/')
        # Second DELETE: the viewset rejects with 403 (PermissionDenied)
        # because the row is already tombstoned.
        res = self.client.delete(f'/api/contacts/{self.contact.pk}/')
        self.assertEqual(res.status_code, 403)


class AuditLogTests(TestCase):
    def setUp(self):
        self.advocate = make_user('aisha', in_group='Advocate')
        self.client = APIClient()
        self.client.force_login(self.advocate)

    def test_create_writes_audit_log(self):
        res = self.client.post('/api/contacts/', {
            'name': 'Layla H.', 'role': 'lawyer', 'email': 'layla@example.org',
        })
        self.assertEqual(res.status_code, 201)
        contact_id = res.json()['id']
        rows = AuditLog.objects.filter(
            target_type='contact', target_id=contact_id, action='edited',
        )
        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows.first().user, self.advocate)
        self.assertEqual(rows.first().details, 'created')

    def test_update_writes_audit_log_with_changed_fields(self):
        c = Contact.objects.create(name='Layla H.', role='lawyer')
        self.client.patch(f'/api/contacts/{c.pk}/', {'email': 'layla@example.org'})
        rows = AuditLog.objects.filter(
            target_type='contact', target_id=c.pk, action='edited',
        )
        # One row: the update. Direct ORM create bypasses the viewset
        # so no 'created' row from setUp.
        self.assertEqual(rows.count(), 1)
        self.assertIn('email', rows.first().details)

    def test_delete_writes_audit_log(self):
        c = Contact.objects.create(name='Layla H.', role='lawyer')
        self.client.delete(f'/api/contacts/{c.pk}/')
        rows = AuditLog.objects.filter(
            target_type='contact', target_id=c.pk, action='deleted',
        )
        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows.first().user, self.advocate)
        self.assertEqual(rows.first().details, 'soft-deleted')

    def test_audit_records_client_ip_from_xff(self):
        # APIClient doesn't populate X-Forwarded-For automatically;
        # sending one explicitly proves the helper extracts it.
        res = self.client.post(
            '/api/contacts/',
            {'name': 'Layla H.', 'role': 'lawyer'},
            HTTP_X_FORWARDED_FOR='203.0.113.42, 10.0.0.1',
        )
        self.assertEqual(res.status_code, 201)
        row = AuditLog.objects.filter(
            target_type='contact', target_id=res.json()['id'],
        ).first()
        self.assertEqual(row.ip_address, '203.0.113.42')