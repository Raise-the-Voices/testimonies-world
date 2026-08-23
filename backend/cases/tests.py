"""Tests for the cases app.

Focus: permission enforcement on media downloads (C1 — visibility must
be checked at fetch time, not at list-query time).
"""

import tempfile

from django.contrib.auth.models import AnonymousUser, Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .models import AuditLog, Media
from .views import _can_view_visibility


# A throwaway MEDIA_ROOT so FileField storage writes don't pollute the repo.
_TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix='cases-test-media-')


@override_settings(MEDIA_ROOT=_TEST_MEDIA_ROOT)
class MediaVisibilityTest(TestCase):
    """Visibility on Media.file must be enforced at download time."""

    @classmethod
    def setUpTestData(cls):
        cls.public = Media.objects.create(
            media_type='photo',
            visibility=Media.Visibility.PUBLIC,
            file='public/public-test.jpg',
        )
        cls.restricted = Media.objects.create(
            media_type='photo',
            visibility=Media.Visibility.RESTRICTED,
            file='restricted/restricted-test.jpg',
        )
        cls.sensitive = Media.objects.create(
            media_type='photo',
            visibility=Media.Visibility.SENSITIVE,
            file='sensitive/sensitive-test.jpg',
        )

        # Real file bytes on disk so FileResponse can stream them.
        for media in (cls.public, cls.restricted, cls.sensitive):
            media.file.save(
                media.file.name,
                SimpleUploadedFile('x.bin', b'fake-bytes-for-test'),
                save=True,
            )

        cls.advocate_group, _ = Group.objects.get_or_create(name='Advocate')
        cls.advocate = User.objects.create_user(
            username='advocate', password='x'
        )
        cls.advocate.groups.add(cls.advocate_group)

        cls.staff = User.objects.create_user(
            username='staff', password='x', is_staff=True,
        )

        cls.volunteer = User.objects.create_user(
            username='volunteer', password='x',
        )

    # ----- pure-function permission helper -----------------------------

    def test_anonymous_can_view_only_public(self):
        anon = AnonymousUser()
        self.assertTrue(_can_view_visibility(anon, Media.Visibility.PUBLIC))
        self.assertFalse(_can_view_visibility(anon, Media.Visibility.RESTRICTED))
        self.assertFalse(_can_view_visibility(anon, Media.Visibility.SENSITIVE))

    def test_volunteer_can_view_public_and_restricted_not_sensitive(self):
        self.assertTrue(_can_view_visibility(self.volunteer, Media.Visibility.PUBLIC))
        self.assertTrue(_can_view_visibility(self.volunteer, Media.Visibility.RESTRICTED))
        self.assertFalse(_can_view_visibility(self.volunteer, Media.Visibility.SENSITIVE))

    def test_advocate_and_staff_can_view_sensitive(self):
        self.assertTrue(_can_view_visibility(self.advocate, Media.Visibility.SENSITIVE))
        self.assertTrue(_can_view_visibility(self.staff, Media.Visibility.SENSITIVE))

    # ----- end-to-end download view ------------------------------------

    def _download(self, media):
        return self.client.get(f'/media/{media.file.name}')

    def test_anonymous_can_download_public(self):
        self.assertEqual(self._download(self.public).status_code, 200)

    def test_anonymous_blocked_from_restricted(self):
        self.assertEqual(self._download(self.restricted).status_code, 403)

    def test_anonymous_blocked_from_sensitive(self):
        self.assertEqual(self._download(self.sensitive).status_code, 403)

    def test_volunteer_can_download_restricted_but_not_sensitive(self):
        self.client.force_login(self.volunteer)
        self.assertEqual(self._download(self.restricted).status_code, 200)
        self.assertEqual(self._download(self.sensitive).status_code, 403)

    def test_advocate_can_download_sensitive_and_creates_audit_log(self):
        self.client.force_login(self.advocate)
        before = AuditLog.objects.filter(
            target_type='media', target_id=self.sensitive.id,
            action=AuditLog.Action.DOWNLOADED,
        ).count()

        response = self._download(self.sensitive)
        self.assertEqual(response.status_code, 200)

        after = AuditLog.objects.filter(
            target_type='media', target_id=self.sensitive.id,
            action=AuditLog.Action.DOWNLOADED,
        ).count()
        self.assertEqual(after, before + 1)

        log = AuditLog.objects.filter(
            target_type='media', target_id=self.sensitive.id,
            action=AuditLog.Action.DOWNLOADED,
        ).latest('timestamp')
        self.assertEqual(log.user, self.advocate)

    def test_staff_can_download_sensitive(self):
        self.client.force_login(self.staff)
        self.assertEqual(self._download(self.sensitive).status_code, 200)

    def test_unknown_path_returns_404(self):
        self.assertEqual(
            self.client.get('/media/does/not/exist.bin').status_code,
            404,
        )


# ---------------------------------------------------------------------------
# C4 — nginx auth_request sub-request endpoint (media_auth_check)
# ---------------------------------------------------------------------------
# media_auth_check is the lightweight view that nginx calls via
# `auth_request /__media_auth` before serving /media/<path>. It only
# needs to return 200 (allowed) or 403 (denied) — never a body.

from django.test import RequestFactory
from django.urls import reverse  # noqa: E402

from .views import media_auth_check  # noqa: E402


@override_settings(MEDIA_ROOT=_TEST_MEDIA_ROOT)
class MediaAuthCheckTest(TestCase):
    """Covers the nginx auth_request sub-request endpoint used by
    deploy/nginx/rtv-cases.conf to gate /media/<path> without proxying
    the file body through Django."""

    @classmethod
    def setUpTestData(cls):
        cls.public = Media.objects.create(
            media_type='photo',
            visibility=Media.Visibility.PUBLIC,
            file='public/public-test.jpg',
        )
        cls.restricted = Media.objects.create(
            media_type='photo',
            visibility=Media.Visibility.RESTRICTED,
            file='restricted/restricted-test.jpg',
        )
        cls.sensitive = Media.objects.create(
            media_type='photo',
            visibility=Media.Visibility.SENSITIVE,
            file='sensitive/sensitive-test.jpg',
        )

        cls.advocate_group, _ = Group.objects.get_or_create(name='Advocate')
        cls.advocate = User.objects.create_user(
            username='authcheck_advocate', password='x',
        )
        cls.advocate.groups.add(cls.advocate_group)

        cls.volunteer = User.objects.create_user(
            username='authcheck_volunteer', password='x',
        )

    def _call_auth_check(self, request_uri, user=None):
        """Simulate the nginx auth_request sub-request through the test
        client so Django's exception middleware converts PermissionDenied
        into a 403 response (same as a real request)."""
        if user is not None:
            self.client.force_login(user)
        else:
            self.client.logout()
        # nginx sets X-Original-URI; the test client passes HTTP_*
        # headers via the extra={'HTTP_X_ORIGINAL_URI': ...} kwarg.
        return self.client.get(
            f'/media/_auth_check?path={request_uri}',
            HTTP_X_ORIGINAL_URI=request_uri,
        )

    def test_anonymous_can_pass_public(self):
        response = self._call_auth_check('/media/public/public-test.jpg')
        self.assertEqual(response.status_code, 200)

    def test_anonymous_blocked_from_restricted(self):
        response = self._call_auth_check('/media/restricted/restricted-test.jpg')
        self.assertEqual(response.status_code, 403)

    def test_anonymous_blocked_from_sensitive(self):
        response = self._call_auth_check('/media/sensitive/sensitive-test.jpg')
        self.assertEqual(response.status_code, 403)

    def test_volunteer_passes_restricted(self):
        response = self._call_auth_check(
            '/media/restricted/restricted-test.jpg', user=self.volunteer,
        )
        self.assertEqual(response.status_code, 200)

    def test_volunteer_blocked_from_sensitive(self):
        response = self._call_auth_check(
            '/media/sensitive/sensitive-test.jpg', user=self.volunteer,
        )
        self.assertEqual(response.status_code, 403)

    def test_advocate_passes_sensitive(self):
        response = self._call_auth_check(
            '/media/sensitive/sensitive-test.jpg', user=self.advocate,
        )
        self.assertEqual(response.status_code, 200)

    def test_unknown_path_returns_403(self):
        response = self._call_auth_check('/media/this/does/not/exist.jpg')
        self.assertEqual(response.status_code, 403)

    def test_sensitive_access_creates_audit_log(self):
        before = AuditLog.objects.filter(
            target_type='media', target_id=self.sensitive.id,
            action=AuditLog.Action.DOWNLOADED,
        ).count()
        response = self._call_auth_check(
            '/media/sensitive/sensitive-test.jpg', user=self.advocate,
        )
        self.assertEqual(response.status_code, 200)
        after = AuditLog.objects.filter(
            target_type='media', target_id=self.sensitive.id,
            action=AuditLog.Action.DOWNLOADED,
        ).count()
        self.assertEqual(after, before + 1)

    def test_url_routing_uses_auth_check_for_exact_path(self):
        """Ensure /media/_auth_check resolves to media_auth_check and
        NOT to MediaDownloadView (which would treat _auth_check as a
        file path and 404)."""
        from django.urls import resolve
        match = resolve('/media/_auth_check')
        self.assertEqual(match.func, media_auth_check)

    def test_url_routing_uses_download_view_for_other_paths(self):
        from django.urls import resolve
        match = resolve('/media/some/file.jpg')
        self.assertEqual(match.url_name, 'media_download')
