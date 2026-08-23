"""Tests for project-level error handlers (C2).

Django only invokes ``handler404`` / ``handler500`` when ``DEBUG=False``, so
these tests override that setting. They verify:

  * ``/api/*`` paths return JSON with no leaked traceback or template vars.
  * Other paths (``/admin/``) still get Django's default HTML pages so the
    admin keeps working unchanged.
"""

import json

from django.http import Http404
from django.test import RequestFactory, TestCase, override_settings
from django.urls import path

from testimonies import urls as project_urls
from testimonies.urls import api_not_found, api_server_error


@override_settings(DEBUG=False, ALLOWED_HOSTS=['*'])
class JsonErrorHandlerTest(TestCase):
    """End-to-end: a request that doesn't match any URL pattern triggers
    ``handler404``; we assert the response shape by content type."""

    def test_api_404_returns_json(self):
        response = self.client.get('/api/this-route-does-not-exist/')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response['Content-Type'], 'application/json')
        body = json.loads(response.content)
        self.assertEqual(body, {'detail': 'Not found', 'path': '/api/this-route-does-not-exist/'})

    def test_non_api_404_falls_back_to_html(self):
        # A path that doesn't match any URL pattern and isn't /api/* should
        # still get Django's default HTML page (so admin / allauth keep
        # working). We avoid /admin/ because unauth requests redirect to
        # /admin/login/ instead of 404ing.
        response = self.client.get('/this-route-does-not-exist/')
        self.assertEqual(response.status_code, 404)
        self.assertNotEqual(response['Content-Type'], 'application/json')


class HandlerUnitTest(TestCase):
    """Unit-level: exercise the handler callables directly so they don't
    depend on Django's DEBUG gate."""

    def test_api_not_found_returns_json_for_api_path(self):
        rf = RequestFactory()
        request = rf.get('/api/foo/bar')
        response = api_not_found(request, exception=Http404('boom'))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response['Content-Type'], 'application/json')
        body = json.loads(response.content)
        self.assertEqual(body['detail'], 'Not found')
        self.assertEqual(body['path'], '/api/foo/bar')

    def test_api_not_found_falls_back_to_html_for_admin_path(self):
        rf = RequestFactory()
        request = rf.get('/admin/foo/')
        response = api_not_found(request, exception=Http404('boom'))
        # Django's default page_not_found returns HTML.
        self.assertNotEqual(response['Content-Type'], 'application/json')

    def test_api_server_error_returns_json_for_api_path_no_traceback(self):
        rf = RequestFactory()
        request = rf.get('/api/foo')
        response = api_server_error(request)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response['Content-Type'], 'application/json')
        body = json.loads(response.content)
        self.assertEqual(body, {'detail': 'Internal server error'})
        # No traceback markers leak into the body.
        self.assertNotIn('Traceback', response.content.decode())
        self.assertNotIn('raise ', response.content.decode())

    def test_api_server_error_falls_back_to_html_for_admin_path(self):
        rf = RequestFactory()
        request = rf.get('/admin/foo/')
        response = api_server_error(request)
        self.assertNotEqual(response['Content-Type'], 'application/json')

    def test_handler_strings_point_at_the_module_callables(self):
        """Sanity check on the module-level Django handler bindings."""
        self.assertEqual(project_urls.handler404, 'testimonies.urls.api_not_found')
        self.assertEqual(project_urls.handler500, 'testimonies.urls.api_server_error')
