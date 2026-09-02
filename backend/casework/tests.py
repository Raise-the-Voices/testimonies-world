"""
Tests for the casework notification system.

These are not unit tests of the model alone — they exercise the
end-to-end behavior through the views + notifications module, because
that's the surface that matters and that's where the rules live.
"""

from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import CaseworkRecord, Notification, UserPreference
from . import notifications


User = get_user_model()


def make_user(username, *, in_group=None, email=None, is_staff=False):
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


class RecipientRulesTests(TestCase):
    def setUp(self):
        self.adv1 = make_user('aisha', in_group='Advocate', email='aisha@example.org')
        self.adv2 = make_user('maya', in_group='Advocate', email='maya@example.org')
        self.staff = make_user('admin', is_staff=True, email='admin@example.org')
        self.volunteer = make_user('vol', in_group='Volunteer', email='vol@example.org')

    def test_actor_is_excluded_from_recipients(self):
        record = CaseworkRecord.objects.create(
            action_type=CaseworkRecord.ActionType.OUTREACH,
            description='test',
            date=date(2026, 9, 2),
            performed_by=self.adv1,
        )
        event = notifications.build_create_event(record, self.adv1)
        notifications.emit_event(event)
        recipients = Notification.objects.filter(casework=record).values_list('recipient__username', flat=True)
        self.assertIn('maya', recipients)
        self.assertIn('admin', recipients)
        self.assertNotIn('aisha', recipients)
        self.assertNotIn('vol', recipients)

    def test_volunteers_are_not_recipients(self):
        record = CaseworkRecord.objects.create(
            action_type=CaseworkRecord.ActionType.OUTREACH,
            description='test',
            date=date(2026, 9, 2),
            performed_by=self.adv1,
        )
        notifications.emit_event(notifications.build_create_event(record, self.adv1))
        usernames = Notification.objects.filter(casework=record).values_list('recipient__username', flat=True)
        self.assertNotIn('vol', usernames)

    def test_email_opt_out_blocks_email_but_still_records_inapp(self):
        pref, _ = UserPreference.objects.get_or_create(user=self.adv2)
        pref.notify_email = False
        pref.save()

        record = CaseworkRecord.objects.create(
            action_type=CaseworkRecord.ActionType.OUTREACH,
            description='test',
            date=date(2026, 9, 2),
            performed_by=self.adv1,
        )
        notifications.emit_event(notifications.build_create_event(record, self.adv1))

        row = Notification.objects.get(casework=record, recipient=self.adv2)
        self.assertFalse(row.emailed_at)
        self.assertFalse(row.is_read)

    def test_24h_suppression_blocks_repeat_email(self):
        record = CaseworkRecord.objects.create(
            action_type=CaseworkRecord.ActionType.OUTREACH,
            description='test',
            date=date(2026, 9, 2),
            performed_by=self.adv1,
        )
        # First event — email goes out (mocked so no real SMTP). TestCase
        # wraps the test in a transaction that never commits, so capture
        # on_commit callbacks explicitly with the helper.
        with patch('casework.notifications.send_mail') as send:
            with self.captureOnCommitCallbacks(execute=True):
                notifications.emit_event(notifications.build_create_event(record, self.adv1))
            self.assertEqual(send.call_count, 1)
            for row in Notification.objects.filter(casework=record, recipient=self.adv2):
                Notification.objects.filter(pk=row.pk).update(emailed_at=timezone.now())
        # Second event within 24h — email suppressed.
        record.description = 'updated'
        record.save()
        with patch('casework.notifications.send_mail') as send:
            with self.captureOnCommitCallbacks(execute=True):
                notifications.emit_event(
                    notifications.build_update_event(record, self.adv2, became_done=False)
                )
            self.assertEqual(send.call_count, 0)

    def test_status_done_bypasses_24h_suppression(self):
        record = CaseworkRecord.objects.create(
            action_type=CaseworkRecord.ActionType.OUTREACH,
            description='test',
            date=date(2026, 9, 2),
            performed_by=self.adv1,
        )
        with patch('casework.notifications.send_mail') as send:
            with self.captureOnCommitCallbacks(execute=True):
                notifications.emit_event(notifications.build_create_event(record, self.adv1))
            self.assertEqual(send.call_count, 1)
            Notification.objects.filter(casework=record).update(emailed_at=timezone.now())
        record.status = CaseworkRecord.Status.DONE
        record.save()
        with patch('casework.notifications.send_mail') as send:
            with self.captureOnCommitCallbacks(execute=True):
                notifications.emit_event(
                    notifications.build_update_event(record, self.adv2, became_done=True)
                )
            self.assertEqual(send.call_count, 1)


class SeenByTests(TestCase):
    def setUp(self):
        self.author = make_user('aisha', in_group='Advocate')
        self.viewer = make_user('maya', in_group='Advocate')
        self.outsider = make_user('vol', in_group='Volunteer')

    def test_seen_by_records_to_author_only(self):
        record = CaseworkRecord.objects.create(
            action_type=CaseworkRecord.ActionType.OUTREACH,
            description='test',
            date=date(2026, 9, 2),
            performed_by=self.author,
        )
        notifications.record_seen_by(record, self.viewer)
        rows = Notification.objects.filter(casework=record, kind=Notification.Kind.RECORD_SEEN)
        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows.first().recipient, self.author)

    def test_seen_by_idempotent_for_same_viewer(self):
        record = CaseworkRecord.objects.create(
            action_type=CaseworkRecord.ActionType.OUTREACH,
            description='test',
            date=date(2026, 9, 2),
            performed_by=self.author,
        )
        notifications.record_seen_by(record, self.viewer)
        notifications.record_seen_by(record, self.viewer)
        self.assertEqual(
            Notification.objects.filter(casework=record, kind=Notification.Kind.RECORD_SEEN).count(),
            1,
        )

    def test_seen_by_skipped_for_non_eligible_viewer(self):
        record = CaseworkRecord.objects.create(
            action_type=CaseworkRecord.ActionType.OUTREACH,
            description='test',
            date=date(2026, 9, 2),
            performed_by=self.author,
        )
        notifications.record_seen_by(record, self.outsider)
        self.assertEqual(
            Notification.objects.filter(casework=record, kind=Notification.Kind.RECORD_SEEN).count(),
            0,
        )


class MarkReadOwnershipTests(TestCase):
    def setUp(self):
        self.alice = make_user('alice', in_group='Advocate')
        self.bob = make_user('bob', in_group='Advocate')

    def test_user_cannot_mark_anothers_notification(self):
        record = CaseworkRecord.objects.create(
            action_type=CaseworkRecord.ActionType.OUTREACH,
            description='test',
            date=date(2026, 9, 2),
        )
        notif = Notification.objects.create(
            recipient=self.alice,
            kind=Notification.Kind.RECORD_CREATED,
            casework=record,
            actor=self.bob,
        )
        self.assertFalse(notifications.mark_read(notif, self.bob))
        notif.refresh_from_db()
        self.assertFalse(notif.is_read)

    def test_owner_can_mark_read(self):
        record = CaseworkRecord.objects.create(
            action_type=CaseworkRecord.ActionType.OUTREACH,
            description='test',
            date=date(2026, 9, 2),
        )
        notif = Notification.objects.create(
            recipient=self.alice,
            kind=Notification.Kind.RECORD_CREATED,
            casework=record,
            actor=self.bob,
        )
        self.assertTrue(notifications.mark_read(notif, self.alice))
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)


class APIEndpointTests(TestCase):
    def setUp(self):
        self.alice = make_user('alice', in_group='Advocate')
        self.bob = make_user('bob', in_group='Advocate')
        self.client = APIClient()
        self.client.force_login(self.alice)

    def test_unread_count_endpoint(self):
        record = CaseworkRecord.objects.create(
            action_type=CaseworkRecord.ActionType.OUTREACH,
            description='x',
            date=date(2026, 9, 2),
            performed_by=self.bob,
        )
        Notification.objects.create(
            recipient=self.alice,
            kind=Notification.Kind.RECORD_CREATED,
            casework=record,
            actor=self.bob,
        )
        res = self.client.get('/api/notifications/unread-count/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['count'], 1)

    def test_mark_one_read_endpoint(self):
        record = CaseworkRecord.objects.create(
            action_type=CaseworkRecord.ActionType.OUTREACH,
            description='x',
            date=date(2026, 9, 2),
            performed_by=self.bob,
        )
        notif = Notification.objects.create(
            recipient=self.alice,
            kind=Notification.Kind.RECORD_CREATED,
            casework=record,
            actor=self.bob,
        )
        res = self.client.post(f'/api/notifications/{notif.pk}/read/')
        self.assertEqual(res.status_code, 200)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_mark_all_read_endpoint(self):
        record = CaseworkRecord.objects.create(
            action_type=CaseworkRecord.ActionType.OUTREACH,
            description='x',
            date=date(2026, 9, 2),
            performed_by=self.bob,
        )
        for _ in range(3):
            Notification.objects.create(
                recipient=self.alice,
                kind=Notification.Kind.RECORD_CREATED,
                casework=record,
                actor=self.bob,
            )
        res = self.client.post('/api/notifications/read-all/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Notification.objects.filter(recipient=self.alice, is_read=False).count(), 0)

    def test_preferences_endpoint_roundtrip(self):
        res = self.client.get('/api/preferences/')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()['notify_email'])

        res = self.client.post('/api/preferences/', {'notify_email': False}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()['notify_email'])

    def test_cannot_read_anothers_notification(self):
        record = CaseworkRecord.objects.create(
            action_type=CaseworkRecord.ActionType.OUTREACH,
            description='x',
            date=date(2026, 9, 2),
            performed_by=self.alice,
        )
        notif = Notification.objects.create(
            recipient=self.bob,
            kind=Notification.Kind.RECORD_CREATED,
            casework=record,
            actor=self.alice,
        )
        # Alice tries to mark Bob's notification — get_object_or_404 should 404.
        res = self.client.post(f'/api/notifications/{notif.pk}/read/')
        self.assertEqual(res.status_code, 404)
        notif.refresh_from_db()
        self.assertFalse(notif.is_read)