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


# ---------------------------------------------------------------------------
# C3 — Production security defaults
# ---------------------------------------------------------------------------
# The base settings module is loaded once and cached for the lifetime of
# the test process, so to verify the validation in different env-var
# configurations we run small Python scripts in subprocesses with
# PYTHONPATH pointed at backend/ and cwd outside it (so decouple doesn't
# pick up our local backend/.env).

import os
import subprocess
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[1]


def _import_settings_subprocess(env_overrides, settings_module='testimonies.settings',
                               inspect_attrs=()):
    """Spawn a fresh Python that imports django.conf.settings with the
    given env overrides; returns the completed subprocess.

    When ``inspect_attrs`` is non-empty, the subprocess prints those
    attribute names (one per line) so tests can assert on the actual
    loaded values without poking the cached parent-process settings.
    """
    env = os.environ.copy()
    # Strip whatever the parent shell / .env provided so the subprocess
    # only sees what we explicitly set.
    for key in ('SECRET_KEY', 'DEBUG', 'ALLOWED_HOSTS'):
        env.pop(key, None)
    env.update(env_overrides)
    env['DJANGO_SETTINGS_MODULE'] = settings_module
    env['PYTHONPATH'] = str(_BACKEND_DIR)
    # Run from /tmp so decouple does not pick up backend/.env.
    if inspect_attrs:
        # Build a literal list — `[*inspect_attrs]` would also work, but
        # doing it this way makes the script self-contained.
        attrs_literal = '[' + ', '.join(repr(a) for a in inspect_attrs) + ']'
        script = (
            'import django, json; django.setup()\n'
            'from django.conf import settings\n'
            'attrs = ' + attrs_literal + '\n'
            'print(json.dumps({a: getattr(settings, a) for a in attrs}))\n'
        )
    else:
        script = 'import django; django.setup()'
    return subprocess.run(
        [sys.executable, '-c', script],
        env=env,
        cwd='/tmp',
        capture_output=True,
        text=True,
        timeout=30,
    )


class ProdSettingsValidationTest(TestCase):
    """settings.py enforces the bare minimum when DEBUG=False.

    SECRET_KEY was relaxed to a self-heal fallback (per-process random
    key with a stderr WARNING) so a missing env var doesn't 502 the
    whole site. ALLOWED_HOSTS='*' is still a hard error — wildcard
    in prod is never acceptable.
    """

    def test_no_secret_key_falls_back_to_random(self):
        result = _import_settings_subprocess({
            'DEBUG': 'False',
            'SECRET_KEY': '',
            'ALLOWED_HOSTS': 'cases.raisethevoices.org',
        }, inspect_attrs=('SECRET_KEY',))
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        observed = json.loads(result.stdout.strip())
        self.assertGreaterEqual(len(observed['SECRET_KEY']), 30)
        self.assertIn('SECRET_KEY not set', result.stderr)

    def test_wildcard_allowed_hosts_raises(self):
        result = _import_settings_subprocess({
            'DEBUG': 'False',
            'SECRET_KEY': 'a-real-key-just-for-testing',
            'ALLOWED_HOSTS': '*',
        })
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('ALLOWED_HOSTS must not contain', result.stderr)


class SettingsProdTest(TestCase):
    """settings_prod.py layers strict prod invariants on top of base.

    The strict-mode behavior was relaxed to self-heal fallbacks so the
    site can come up even when the systemd unit forgets to export
    SECRET_KEY / ALLOWED_HOSTS. The remaining hard requirement is that
    ALLOWED_HOSTS must not contain '*'.
    """

    def test_empty_allowed_hosts_falls_back_to_safe_defaults(self):
        result = _import_settings_subprocess(
            {
                'SECRET_KEY': 'a-real-key-just-for-testing',
                'ALLOWED_HOSTS': '',
            },
            settings_module='testimonies.settings_prod',
            inspect_attrs=(
                'ALLOWED_HOSTS', 'DEBUG', 'SECRET_KEY',
            ),
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        observed = json.loads(result.stdout.strip())
        self.assertIn('cases.raisethevoices.org', observed['ALLOWED_HOSTS'])
        self.assertIn('localhost', observed['ALLOWED_HOSTS'])
        # Warning is logged to stderr at import time.
        self.assertIn('ALLOWED_HOSTS not set', result.stderr)

    def test_wildcard_allowed_hosts_raises(self):
        result = _import_settings_subprocess(
            {
                'SECRET_KEY': 'a-real-key-just-for-testing',
                'ALLOWED_HOSTS': '*',
            },
            settings_module='testimonies.settings_prod',
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('ALLOWED_HOSTS must not contain', result.stderr)

    def test_empty_secret_key_falls_back_to_random(self):
        result = _import_settings_subprocess(
            {
                'SECRET_KEY': '',
                'ALLOWED_HOSTS': 'cases.raisethevoices.org',
            },
            settings_module='testimonies.settings_prod',
            inspect_attrs=('SECRET_KEY',),  # trailing comma — must stay a tuple
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        observed = json.loads(result.stdout.strip())
        # Fallback key is generated per-process; just verify it's
        # non-empty and has reasonable entropy.
        self.assertGreaterEqual(len(observed['SECRET_KEY']), 30)
        self.assertIn('SECRET_KEY not set', result.stderr)

    def test_valid_prod_env_loads_and_sets_secure_flags(self):
        result = _import_settings_subprocess(
            {
                'SECRET_KEY': 'a-real-key-just-for-testing',
                'ALLOWED_HOSTS': 'cases.raisethevoices.org',
            },
            settings_module='testimonies.settings_prod',
            inspect_attrs=(
                'DEBUG',
                'SESSION_COOKIE_SECURE',
                'CSRF_COOKIE_SECURE',
                'SECURE_SSL_REDIRECT',
                'SECURE_HSTS_SECONDS',
                'SECURE_HSTS_INCLUDE_SUBDOMAINS',
                'SECURE_HSTS_PRELOAD',
                'SECURE_REFERRER_POLICY',
                'SECURE_PROXY_SSL_HEADER',
                'ALLOWED_HOSTS',
            ),
        )
        self.assertEqual(
            result.returncode, 0,
            msg=f'settings_prod refused a valid prod env:\n{result.stderr}',
        )
        observed = json.loads(result.stdout.strip())
        self.assertEqual(observed['DEBUG'], False)
        self.assertEqual(observed['SESSION_COOKIE_SECURE'], True)
        self.assertEqual(observed['CSRF_COOKIE_SECURE'], True)
        self.assertEqual(observed['SECURE_SSL_REDIRECT'], True)
        self.assertEqual(observed['SECURE_HSTS_SECONDS'], 31536000)
        self.assertEqual(observed['SECURE_HSTS_INCLUDE_SUBDOMAINS'], True)
        self.assertEqual(observed['SECURE_HSTS_PRELOAD'], True)
        self.assertEqual(observed['ALLOWED_HOSTS'], ['cases.raisethevoices.org'])


class UnsafeDefaultsRemovedTest(TestCase):
    """Source-level checks that the known-insecure defaults are gone."""

    def test_settings_source_no_insecure_secret_key_default(self):
        # The unsafe default string should not appear as an actual default
        # value anywhere in settings.py. We allow it to appear in the
        # module docstring (which describes what was removed) but not in
        # any executable line.
        import re
        source = (_BACKEND_DIR / 'testimonies' / 'settings.py').read_text()
        # Strip the docstring(s) so we only inspect executable code.
        stripped = re.sub(r'"""[\s\S]*?"""', '', source)
        self.assertNotIn("'dev-insecure-change-in-production'", stripped)
        self.assertNotIn('"dev-insecure-change-in-production"', stripped)
        # After C5 the SECRET_KEY config call may pass default='' (an empty
        # string), which enables the per-process random fallback in the
        # `if not SECRET_KEY:` block below. What we don't want is any
        # actual weak *string* being passed as default.
        self.assertNotRegex(stripped, r"config\(\s*'SECRET_KEY'\s*,\s*default\s*=\s*['\"][^'\"]+['\"]")

    def test_settings_source_debug_default_is_false(self):
        source = (_BACKEND_DIR / 'testimonies' / 'settings.py').read_text()
        # DEBUG default must be False, not True.
        import re
        match = re.search(r"DEBUG\s*=\s*config\(\s*'DEBUG'\s*,\s*default\s*=\s*(\w+)", source)
        self.assertIsNotNone(match, 'DEBUG config() call not found in settings.py')
        self.assertEqual(match.group(1), 'False')

    def test_settings_source_allowed_hosts_default_is_not_wildcard(self):
        source = (_BACKEND_DIR / 'testimonies' / 'settings.py').read_text()
        # The literal string "default='*'" must not appear anywhere in settings.py.
        self.assertNotIn("default='*'", source)

    def test_settings_prod_file_exists(self):
        self.assertTrue((_BACKEND_DIR / 'testimonies' / 'settings_prod.py').exists())
