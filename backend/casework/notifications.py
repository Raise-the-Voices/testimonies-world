"""
Recipient rules and email rendering for casework notifications.

Kept in a single module so the policy ("who gets notified when") is
readable in one place. If this grows, split into:
  - `recipient_rules.py` (who, when)
  - `emails.py` (what the email looks like)
  - `digest.py` (per-case aggregation)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import CaseworkRecord, Notification


User = get_user_model()


# ---------------------------------------------------------------------------
# Recipient resolution
# ---------------------------------------------------------------------------

ADVOCATE_GROUP = 'Advocate'


def is_eligible_recipient(user) -> bool:
    """A user can be a notification target only if they would be able to
    act on the casework list. Advocate group OR is_staff. Anyone else
    is excluded up front — even if their preference object says in-app
    ON, they wouldn't know what the notification is about.
    """
    if not getattr(user, 'is_authenticated', False):
        return False
    if not user.is_active:
        return False
    if user.is_staff:
        return True
    return user.groups.filter(name=ADVOCATE_GROUP).exists()


def recipient_queryset():
    """All users that *could* be recipients of a casework notification."""
    return User.objects.filter(is_active=True).filter(
        # is_staff OR in Advocate group — match is_eligible_recipient()
        # exactly so what we compute here and what we filter to later
        # cannot diverge.
        models_q_is_eligible(),
    ).distinct()


def models_q_is_eligible():
    return Q(is_staff=True) | Q(groups__name=ADVOCATE_GROUP)


def exclude_actor(qs, actor):
    """The author of a record shouldn't be notified about their own
    action — they're the actor."""
    if actor is None:
        return qs
    return qs.exclude(pk=actor.pk)


def opted_in_emails(qs):
    """Filter to users whose `notify_email` is True. Users without a
    UserPreference row get the default (email ON), so we LEFT JOIN."""
    return qs.filter(
        # has preference with notify_email=True OR has no preference row
        Q(notification_preference__isnull=True)
        | Q(notification_preference__notify_email=True)
    ).distinct()


def opted_in_inapp(qs):
    return qs.filter(
        Q(notification_preference__isnull=True)
        | Q(notification_preference__notify_inapp=True)
    ).distinct()


# ---------------------------------------------------------------------------
# Event construction
# ---------------------------------------------------------------------------

@dataclass
class NotificationEvent:
    kind: str
    record: CaseworkRecord
    actor: Optional[object]
    """Used for 'seen by' acknowledgements."""
    seen_by: Optional[object] = None


def build_create_event(record: CaseworkRecord, actor) -> NotificationEvent:
    return NotificationEvent(
        kind=Notification.Kind.RECORD_CREATED,
        record=record,
        actor=actor,
    )


def build_update_event(record: CaseworkRecord, actor, *, became_done: bool) -> NotificationEvent:
    return NotificationEvent(
        kind=Notification.Kind.STATUS_DONE if became_done else Notification.Kind.RECORD_UPDATED,
        record=record,
        actor=actor,
    )


def build_seen_event(record: CaseworkRecord, seen_by) -> NotificationEvent:
    return NotificationEvent(
        kind=Notification.Kind.RECORD_SEEN,
        record=record,
        actor=seen_by,
    )


# ---------------------------------------------------------------------------
# Persistence + email
# ---------------------------------------------------------------------------

EMAIL_SUPPRESS_WINDOW = timedelta(hours=24)


def should_email_for_record(record: CaseworkRecord, kind: str) -> bool:
    """Anti-spam: if the same record already has an unread email-window
    notification addressed to this set, don't email again. STATUS_DONE
    always bypasses this gate because closure deserves visibility."""
    if kind == Notification.Kind.STATUS_DONE:
        return True
    cutoff = timezone.now() - EMAIL_SUPPRESS_WINDOW
    return not Notification.objects.filter(
        casework=record,
        created_at__gte=cutoff,
        emailed_at__isnull=False,
    ).exists()


def notification_link(record: CaseworkRecord, base: str | None = None) -> str:
    """Build the canonical link to a casework record. Honors SCRIPT_NAME
    so it matches the in-app routing."""
    base = base or getattr(settings, 'SCRIPT_NAME', '') or ''
    return f"{base}/casework/?id={record.pk}"


def render_email(event: NotificationEvent, *, site_base: str) -> tuple[str, str, str]:
    """
    Return (subject, text_body, html_body) for an event.
    Plain text first, HTML mirror. No images, no tracking pixels —
    these emails travel across borders and may be forwarded.
    """
    record = event.record
    actor_name = _display_name(event.actor) if event.actor else 'Someone'
    person_names = list(record.persons.values_list('name', flat=True))[:3]
    person_label = ', '.join(person_names) if person_names else 'a person'
    if len(person_names) == 0:
        person_label = 'a case'

    link = f"{site_base}{notification_link(record)}"
    settings_url = f"{site_base}{settings.SCRIPT_NAME or ''}/settings"

    if event.kind == Notification.Kind.RECORD_CREATED:
        subject = (
            f'[Testimonies.world] {actor_name} logged '
            f'{record.get_action_type_display().lower()} — {person_label}'
        )
        lead = f'{actor_name} just logged a new {record.get_action_type_display().lower()} related to {person_label}.'
    elif event.kind == Notification.Kind.STATUS_DONE:
        subject = (
            f'[Testimonies.world] {actor_name} marked a record done — {person_label}'
        )
        lead = f'{actor_name} marked a casework record as done for {person_label}.'
    elif event.kind == Notification.Kind.RECORD_SEEN:
        subject = (
            f'[Testimonies.world] {actor_name} opened your casework record — {person_label}'
        )
        lead = f'{actor_name} opened a casework record you logged.'
    else:
        subject = (
            f'[Testimonies.world] {actor_name} updated casework — {person_label}'
        )
        lead = f'{actor_name} updated a casework record related to {person_label}.'

    text = (
        f"{lead}\n\n"
        f"  Action: {record.get_action_type_display()}\n"
        f"  Date:   {record.date.isoformat()}\n"
        f"  Status: {record.get_status_display()}\n"
        f"\n"
        f"View it: {link}\n"
        f"\n"
        f"You're receiving this because you're an advocate on testimonies.world.\n"
        f"Manage notifications: {settings_url}\n"
    )
    html = (
        f'<p style="font-family:Georgia,serif;font-size:15px;color:#222;line-height:1.5;">'
        f'{_escape(lead)}</p>'
        f'<table cellpadding="6" style="font-family:Georgia,serif;font-size:14px;color:#222;'
        f'border-collapse:collapse;border:1px solid #eee;">'
        f'<tr><td><strong>Action</strong></td><td>{_escape(record.get_action_type_display())}</td></tr>'
        f'<tr><td><strong>Date</strong></td><td>{record.date.isoformat()}</td></tr>'
        f'<tr><td><strong>Status</strong></td><td>{_escape(record.get_status_display())}</td></tr>'
        f'</table>'
        f'<p style="margin-top:18px;">'
        f'<a href="{_escape(link)}" style="background:#25646a;color:#fff;'
        f'padding:8px 14px;border-radius:4px;text-decoration:none;">View record</a></p>'
        f'<p style="font-family:Georgia,serif;font-size:12px;color:#888;margin-top:24px;">'
        f'You\'re receiving this because you\'re an advocate on testimonies.world. '
        f'<a href="{_escape(settings_url)}" style="color:#888;">Manage notifications</a></p>'
    )
    return subject, text, html


def _display_name(user) -> str:
    full = (user.get_full_name() or '').strip()
    if full:
        return full
    return user.get_username() if user.get_username() else 'Someone'


def _escape(s: str) -> str:
    return (
        s.replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
    )


# ---------------------------------------------------------------------------
# Entry points — called from the viewset's perform_* hooks
# ---------------------------------------------------------------------------

def site_base_url() -> str:
    """Best-effort absolute URL for emails. Honors SCRIPT_NAME for subpath
    deployments. Tests can monkey-patch this if they need a stable value."""
    # Use configured SITE_URL if set, else fall back to a sensible default.
    # We do NOT trust request.scheme here — emails are generated after the
    # request cycle ends (on_commit) and we don't have it.
    return getattr(settings, 'SITE_URL', 'https://demos.linkedtrust.us/testimonies')


def emit_event(event: NotificationEvent) -> list[Notification]:
    """Create Notification rows for every eligible Advocate + staff,
    honoring per-user opt-outs and the per-record 24h anti-spam rule.
    Returns the rows that were created.

    Email is dispatched via transaction.on_commit so the email only goes
    out if the parent CaseworkRecord save is committed. In dev the
    console email backend prints to stdout.
    """
    eligible = recipient_queryset()
    eligible = exclude_actor(eligible, event.actor)

    inapp_targets = opted_in_inapp(eligible)
    email_targets = opted_in_emails(eligible)

    email_due = should_email_for_record(event.record, event.kind)
    if not email_due:
        # In-app still records the notification, but the email channel
        # is suppressed for this row. We keep the rows distinct so the
        # UI can still show "you have a new event" without spamming mail.
        email_targets = User.objects.none()

    created = []
    inapp_ids = set(inapp_targets.values_list('pk', flat=True))
    email_ids = set(email_targets.values_list('pk', flat=True))

    seen_targets = User.objects.filter(pk__in=inapp_ids | email_ids)
    rows = []
    for user in seen_targets:
        rows.append(Notification(
            recipient=user,
            kind=event.kind,
            casework=event.record,
            actor=event.actor,
        ))
    Notification.objects.bulk_create(rows)

    if email_targets.exists():
        recipients_for_email = list(email_targets)
        transaction.on_commit(lambda: _dispatch_email(event, recipients_for_email))

    return Notification.objects.filter(
        casework=event.record, kind=event.kind, created_at__gte=timezone.now() - timedelta(seconds=2)
    )


def _dispatch_email(event: NotificationEvent, recipients: Iterable) -> None:
    """Best-effort send. Failures are logged, not raised — a mailer
    outage should not break casework saves."""
    import logging
    log = logging.getLogger(__name__)

    subject, text, html = render_email(event, site_base=site_base_url())
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@linkedtrust.us')
    recipients = list(recipients)
    recipient_pks = [u.pk for u in recipients]
    recipient_emails = [u.email for u in recipients if getattr(u, 'email', None)]

    if not recipient_emails:
        return

    try:
        send_mail(
            subject=subject,
            message=text,
            from_email=from_email,
            recipient_list=recipient_emails,
            html_message=html,
            fail_silently=True,
        )
    except Exception as exc:
        log.warning('casework notification email failed: %s', exc)
        return

    # Mark emailed rows. We mark by recipient pk + kind + casework, which
    # is unique enough for our flow — only one bulk_create lands per event.
    Notification.objects.filter(
        casework=event.record,
        kind=event.kind,
        recipient_id__in=recipient_pks,
        emailed_at__isnull=True,
    ).update(emailed_at=timezone.now())


# ---------------------------------------------------------------------------
# Mark-read + seen-by (the "verification" the user asked for)
# ---------------------------------------------------------------------------

def mark_read(notification: Notification, user) -> bool:
    """Mark a single notification read. Returns False if the user doesn't
    own the row — we never let a user mark another user's notification
    as read (would be a privacy leak).
    """
    if notification.recipient_id != user.pk:
        return False
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['is_read', 'read_at'])
    return True


def mark_all_read(user) -> int:
    return Notification.objects.filter(
        recipient=user, is_read=False
    ).update(is_read=True, read_at=timezone.now())


def record_seen_by(record: CaseworkRecord, viewer) -> Optional[Notification]:
    """The 'verification' feature: when an Advocate opens a record, the
    author gets a small, single 'seen by' notification — at most one per
    viewer per record.

    Returns the Notification row, or None if it would have been a no-op
    (e.g. viewer is the author, or not eligible).
    """
    if viewer is None:
        return None
    if not is_eligible_recipient(viewer):
        return None
    author = record.performed_by
    if author is None or author.pk == viewer.pk:
        return None

    seen_row = Notification.objects.filter(
        recipient=author,
        actor=viewer,
        casework=record,
        kind=Notification.Kind.RECORD_SEEN,
    ).first()
    if seen_row:
        return seen_row

    event = build_seen_event(record, viewer)
    [row] = (
        Notification.objects.bulk_create([Notification(
            recipient=author,
            kind=event.kind,
            casework=record,
            actor=viewer,
        )]) or [None]
    )
    return row


def unread_count(user) -> int:
    return Notification.objects.filter(recipient=user, is_read=False).count()