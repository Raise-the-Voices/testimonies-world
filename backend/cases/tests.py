"""
Tests for the cases app.

Currently focused on MediaViewSet permissions — the sensitive-upload gate
was added in this PR and we want to lock it down.

Permission matrix for Media:
- Anonymous: read public only; no writes (DRF default on IsAuthenticated).
- Authenticated volunteer: read public + restricted; upload public + restricted;
  cannot mark sensitive.
- Advocate / staff: full read; can upload any visibility including sensitive.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Media


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