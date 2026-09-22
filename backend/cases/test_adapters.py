"""
test_adapters — coverage matrix for CustomSocialAccountAdapter (M2).

The adapter gates Google OAuth signup behind an explicit allow-list.
We assert the four paths plus the rejection message:

  | Path                                          | Expected       |
  |-----------------------------------------------|----------------|
  | existing User + existing SocialAccount        | allow          |
  | is_staff                                      | allow          |
  | in Volunteer / Advocate group                 | allow          |
  | email on PreApprovedEmail (case-insensitive)  | allow          |
  | none of the above                             | reject + msg   |

Tests run without `requests` installed — we build SocialAccount /
SocialLogin manually rather than relying on
``allauth.socialaccount.tests.create_oauth2_test_socialaccount_data``
(which imports requests at module load time).
"""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, RequestFactory, TestCase, override_settings

from allauth.socialaccount.models import SocialAccount, SocialLogin

from .adapters import CustomSocialAccountAdapter
from .models import PreApprovedEmail


User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(username='vol', *, in_group=None, is_staff=False, email=None):
    """Same shape as tests.py::make_user — local copy so this file
    doesn't pull in the cases.tests module (which would import the
    rest of the test suite as a side effect)."""
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


def _sociallogin_new(email):
    """A SocialLogin for a brand-new (unsaved) User — the typical
    first-time OAuth attempt before the adapter has decided anything."""
    user = User(email=email, username=email)
    account = SocialAccount(
        provider='google',
        uid='fake-uid-' + email,
        extra_data={'email': email},
    )
    return SocialLogin(user=user, account=account)


def _sociallogin_existing(user, email):
    """A SocialLogin for an existing User — the normal 'I have logged
    in before' path. ``account.user`` is set so ``is_existing`` is
    True."""
    account = SocialAccount(
        user=user,
        provider='google',
        uid='linked-uid-' + user.username,
        extra_data={'email': email or user.email},
    )
    return SocialLogin(user=user, account=account)


# ---------------------------------------------------------------------------
# is_auto_signup_allowed — direct unit coverage
# ---------------------------------------------------------------------------

class IsAutoSignupAllowedTests(TestCase):
    """Direct calls to the adapter's gate method."""

    def setUp(self):
        self.adapter = CustomSocialAccountAdapter()
        self.request = RequestFactory().get('/')

    # --- Reject -----------------------------------------------------------

    def test_unknown_email_no_group_rejected(self):
        sl = _sociallogin_new('random@gmail.com')
        self.assertFalse(self.adapter.is_auto_signup_allowed(self.request, sl))
        self.assertFalse(User.objects.filter(email='random@gmail.com').exists())

    def test_new_user_no_email_rejected(self):
        # OAuth provider returned no email — happens when scope=profile
        # only. We must refuse rather than auto-create a User with an
        # empty email (which would later collide on signup).
        sl = _sociallogin_new('')
        self.assertFalse(self.adapter.is_auto_signup_allowed(self.request, sl))

    # --- Allow: existing SocialAccount -----------------------------------

    def test_existing_user_with_socialaccount_allowed(self):
        user = make_user('returning', email='returning@example.org')
        # Simulate that allauth matched this User by email and there's
        # already a SocialAccount row linked.
        SocialAccount.objects.create(
            user=user, provider='google', uid='returning-uid',
            extra_data={'email': 'returning@example.org'},
        )
        sl = _sociallogin_existing(user, 'returning@example.org')
        self.assertTrue(sl.is_existing)
        self.assertTrue(self.adapter.is_auto_signup_allowed(self.request, sl))

    # --- Allow: is_staff --------------------------------------------------

    def test_staff_user_allowed(self):
        user = make_user('admin', is_staff=True, email='admin@example.org')
        sl = _sociallogin_new('admin@example.org')
        # Even though the sl is "new" (unsaved User object), the
        # account lookup matched an existing is_staff User by email,
        # so is_staff takes effect on the in-memory user.
        sl.user.is_staff = True
        self.assertTrue(self.adapter.is_auto_signup_allowed(self.request, sl))

    # --- Allow: group membership -----------------------------------------

    def test_volunteer_group_user_allowed(self):
        make_user('vol', in_group='Volunteer', email='vol@example.org')
        sl = _sociallogin_new('vol@example.org')
        # Mirror what allauth does after email-matching: populate the
        # in-memory user with the matched record.
        existing = User.objects.get(email='vol@example.org')
        sl.user = existing
        self.assertTrue(self.adapter.is_auto_signup_allowed(self.request, sl))

    def test_advocate_group_user_allowed(self):
        make_user('aisha', in_group='Advocate', email='aisha@example.org')
        sl = _sociallogin_new('aisha@example.org')
        sl.user = User.objects.get(email='aisha@example.org')
        self.assertTrue(self.adapter.is_auto_signup_allowed(self.request, sl))

    # --- Allow: PreApprovedEmail -----------------------------------------

    def test_preapproved_email_allowed(self):
        PreApprovedEmail.objects.create(
            email='partner@ngo.org',
            note='Partner NGO contact',
        )
        sl = _sociallogin_new('partner@ngo.org')
        self.assertTrue(self.adapter.is_auto_signup_allowed(self.request, sl))

    def test_preapproved_email_case_insensitive(self):
        PreApprovedEmail.objects.create(email='Partner@NGO.org')
        sl = _sociallogin_new('PARTNER@ngo.org')
        self.assertTrue(self.adapter.is_auto_signup_allowed(self.request, sl))

    def test_preapproved_email_with_surrounding_whitespace(self):
        # Some OAuth providers pad the email — defence in depth.
        PreApprovedEmail.objects.create(email='trim@ngo.org')
        sl = _sociallogin_new('  trim@ngo.org  ')
        self.assertTrue(self.adapter.is_auto_signup_allowed(self.request, sl))


# ---------------------------------------------------------------------------
# pre_social_login — end-to-end through the messages framework
# ---------------------------------------------------------------------------

@override_settings(
    SOCIALACCOUNT_AUTO_SIGNUP=False,
    SOCIALACCOUNT_ADAPTER='cases.adapters.CustomSocialAccountAdapter',
    ACCOUNT_EMAIL_VERIFICATION='optional',
)
class PreSocialLoginIntegrationTests(TestCase):
    """Drive the adapter via the actual allauth code path (request →
    messages → redirect) so we catch any contract drift in the
    surrounding framework."""

    def setUp(self):
        self.client = Client()
        self.adapter = CustomSocialAccountAdapter()

    def _run_pre_social_login(self, sociallogin):
        """Call pre_social_login with a real HttpRequest that has
        the messages framework attached, so the rejection path can
        queue the friendly error message.

        Returns ``(request, None)`` on success and raises whatever
        the adapter raises on rejection — the caller can introspect
        the queued messages by reading ``request._messages`` directly
        inside the assertRaises block.
        """
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.urls import reverse

        request = RequestFactory().get(reverse('account_login'))
        # ``RequestFactory`` doesn't run middleware; attach a messages
        # storage manually so ``messages.error(request, ...)`` works.
        request.session = {}
        request._messages = FallbackStorage(request)
        result = self.adapter.pre_social_login(request, sociallogin)
        return request, result

    def test_rejection_surfaces_friendly_message_and_redirects(self):
        from allauth.core.exceptions import ImmediateHttpResponse
        from django.contrib.messages.storage.fallback import FallbackStorage

        sl = _sociallogin_new('random@gmail.com')

        # Build the request with messages storage attached BEFORE
        # calling the adapter — even when the adapter raises, the
        # ``request`` is bound so we can introspect the queued
        # message in the assertRaises block.
        request = RequestFactory().get('/accounts/login/')
        request.session = {}
        request._messages = FallbackStorage(request)

        with self.assertRaises(ImmediateHttpResponse) as ctx:
            self.adapter.pre_social_login(request, sl)

        # The adapter raises ImmediateHttpResponse with a redirect
        # to the login page.
        response = ctx.exception.response
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

        # Messages framework: read directly from the request's
        # storage. The redirect response itself doesn't carry them
        # — Django's MessagesMiddleware normally writes them to the
        # cookie during the response cycle, but in this unit-test
        # bypass we read the storage we attached above.
        msgs = list(messages.get_messages(request))
        self.assertEqual(len(msgs), 1)
        self.assertIn('not on the approved list', str(msgs[0]))
        # And specifically the configured message, not allauth's
        # generic "sign-up closed" copy.
        self.assertIn(CustomSocialAccountAdapter.REJECTED_MESSAGE, str(msgs[0]))

    def test_rejection_does_not_create_user(self):
        from django.contrib.messages.storage.fallback import FallbackStorage

        sl = _sociallogin_new('random@gmail.com')
        request = RequestFactory().get('/accounts/login/')
        request.session = {}
        request._messages = FallbackStorage(request)
        try:
            self.adapter.pre_social_login(request, sl)
        except Exception:
            pass
        self.assertFalse(User.objects.filter(email='random@gmail.com').exists())

    def test_authorized_user_falls_through_to_default_behaviour(self):
        # Pre-approved email → adapter allows → super().pre_social_login
        # is invoked, which allauth uses to link the SocialAccount to
        # any matching User by email. We assert that no rejection /
        # redirect happened.
        PreApprovedEmail.objects.create(email='vol@example.org')
        user = make_user('vol', in_group='Volunteer', email='vol@example.org')
        sl = _sociallogin_new('vol@example.org')
        sl.user = user

        _, result = self._run_pre_social_login(sl)
        # Default behaviour returns None on success.
        self.assertIsNone(result)
