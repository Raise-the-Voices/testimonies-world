"""allauth adapters — tighten Google OAuth signup behind an allow-list.

Background
----------
Before M2, ``SOCIALACCOUNT_AUTO_SIGNUP = True`` meant anyone with a
Google account could create a User row and authenticate against the
platform, regardless of whether they had been vetted as a volunteer,
advocate, or partner. Even though write actions are gated by
``cases.permissions.IsVolunteer``, read actions on FamilyRelationship
(and several other PII-adjacent endpoints) require *authentication*
— so an unauthorized user could still enumerate case data simply by
signing up.

This module implements M2's gate: ``SOCIALACCOUNT_AUTO_SIGNUP`` is
flipped to ``False`` in ``testimonies/settings.py``, and
``CustomSocialAccountAdapter.is_auto_signup_allowed`` returns True
only for one of:

  * an existing User with an existing SocialAccount (normal login
    flow — already authorized by virtue of having a linked identity)
  * ``is_staff`` (operator / admin)
  * membership in the ``Volunteer`` or ``Advocate`` group
  * email is on ``cases.models.PreApprovedEmail`` (case-insensitive)

Anything else raises a friendly error rather than silently creating
an account. See ``test_adapters.py`` for the coverage matrix.
"""

from __future__ import annotations

import logging

from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.shortcuts import redirect

from .models import PreApprovedEmail

log = logging.getLogger(__name__)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """OAuth adapter that gates signup behind an explicit allow-list."""

    # The friendly message surfaced to rejected users. Defined on the
    # class so tests can assert against it without scraping HTML.
    REJECTED_MESSAGE = (
        "Your Google account is not on the approved list for this "
        "platform. To get access, ask your project coordinator to add "
        "your email to the pre-approved list, then try again."
    )

    # Groups whose members are considered authorized. Mirrors the
    # role list in cases/permissions.py::IsVolunteer.
    AUTHORIZED_GROUPS = ('Volunteer', 'Advocate')

    def is_auto_signup_allowed(self, request, sociallogin):
        """Return True only for pre-approved OAuth attempts.

        ``sociallogin.is_existing`` is True when allauth has already
        matched the incoming identity to an existing User with a
        SocialAccount row — that's the normal "I have logged in
        before" path and must keep working without any extra gating.

        For first-time logins, we accept the request only if the
        user matches one of the authorization criteria below.
        """
        # Existing User + existing SocialAccount → already linked.
        if sociallogin.is_existing:
            return True

        user = sociallogin.user
        # is_staff → operator / admin.
        if user.is_staff:
            return True
        # Member of an authorized group. ``groups.filter`` requires a
        # saved pk — for an unsaved User (first-time signup) the
        # M2M descriptor raises ValueError, so we skip the check.
        if user.pk is not None and user.groups.filter(
            name__in=self.AUTHORIZED_GROUPS
        ).exists():
            return True

        # Email is on the pre-approval allow-list. Case-insensitive
        # because Gmail addresses are case-insensitive in practice.
        email = self._extract_email(sociallogin)
        if email and PreApprovedEmail.objects.filter(email__iexact=email).exists():
            return True

        return False

    def pre_social_login(self, request, sociallogin):
        """Run before allauth decides whether to link or signup.

        If the request would be refused by ``is_auto_signup_allowed``,
        we surface a friendly message via the messages framework and
        redirect back to the login page so the user sees something
        actionable instead of allauth's generic "sign-up is closed"
        wording.
        """
        if not self.is_auto_signup_allowed(request, sociallogin):
            log.info(
                "OAuth signup rejected: email=%s provider=%s",
                self._extract_email(sociallogin),
                sociallogin.account.provider,
            )
            messages.error(request, self.REJECTED_MESSAGE)
            raise ImmediateHttpResponse(redirect("account_login"))

        # Authorized — fall through to the default behaviour, which
        # links the SocialAccount to an existing User when one is
        # matched by email. This is the defence-in-depth path that
        # fixes the orphan-EmailAddress class of bug: a User whose
        # auth_user.email matches the OAuth email but who has no
        # SocialAccount row yet gets linked here rather than
        # triggering a duplicate-username collision on signup.
        return super().pre_social_login(request, sociallogin)

    # -- helpers ---------------------------------------------------------

    @staticmethod
    def _extract_email(sociallogin) -> str:
        """Pull a normalised email out of the social account payload.

        ``sociallogin.account.extra_data['email']`` is the canonical
        source for Google OAuth. We tolerate ``user.email`` as a
        fallback in case allauth has already populated the user
        object from the social payload before this method runs.
        """
        email = (
            sociallogin.account.extra_data.get("email")
            or getattr(sociallogin.user, "email", "")
            or ""
        )
        return email.strip().lower()
