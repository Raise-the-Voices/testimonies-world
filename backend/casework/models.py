from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserPreference(models.Model):
    """
    Per-user notification preferences. Lives in the `casework` app because
    that's the only consumer today — kept narrow so we don't grow an
    "accounts" app for two booleans.

    Default for a new user: email ON, in-app ON. Volunteers (who can't
    see casework anyway) have in-app effectively suppressed because no
    notifications are ever addressed to them; this preference is a manual
    opt-out, not the role gate.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preference',
    )
    notify_email = models.BooleanField(
        default=True,
        help_text='Receive an email when casework events affect you.',
    )
    notify_inapp = models.BooleanField(
        default=True,
        help_text='Show in-app notifications in the bell.',
    )

    def __str__(self):
        return f'Prefs for {self.user}'


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_user_preference(sender, instance, created, **kwargs):
    """Make sure every User has a UserPreference row, defaulting to both
    channels ON. Idempotent — a no-op if it already exists."""
    UserPreference.objects.get_or_create(user=instance)


class CaseworkRecord(models.Model):
    class ActionType(models.TextChoices):
        OUTREACH = 'outreach', 'Outreach'
        LEGAL_FILING = 'legal_filing', 'Legal filing'
        MEDIA = 'media', 'Media engagement'
        ADVOCACY = 'advocacy', 'Advocacy'
        INVESTIGATION = 'investigation', 'Investigation'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        IN_PROGRESS = 'in_progress', 'In progress'
        DONE = 'done', 'Done'

    persons = models.ManyToManyField(
        'cases.Person', blank=True, related_name='casework_records'
    )
    action_type = models.CharField(
        max_length=20, choices=ActionType.choices, default=ActionType.OTHER
    )
    description = models.TextField()
    date = models.DateField()
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='casework_performed'
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    next_steps = models.TextField(blank=True, default='')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.get_action_type_display()} — {self.date}'


class Notification(models.Model):
    """
    One row per recipient per event. Same row carries both the in-app
    "have you seen this?" signal and the idempotency marker (`emailed_at`)
    for the outbound email. Keeping them on one row is what makes the
    audit story honest — there's only one notification, just delivered
    through two channels.

    `digest_key` is reserved for a future per-case daily-digest job; left
    blank in v1 because we emit one email per event.
    """

    class Kind(models.TextChoices):
        RECORD_CREATED = 'record_created', 'New casework record'
        RECORD_UPDATED = 'record_updated', 'Casework record updated'
        STATUS_DONE = 'status_done', 'Casework marked done'
        RECORD_SEEN = 'record_seen', 'A peer opened this record'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    kind = models.CharField(max_length=24, choices=Kind.choices)
    casework = models.ForeignKey(
        CaseworkRecord,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications_acted',
        help_text='The user whose action caused this notification (often ≠ recipient).',
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    emailed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the email for this row was sent. NULL = not yet emailed.',
    )
    digest_key = models.CharField(max_length=64, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
            models.Index(fields=['recipient', 'emailed_at']),
            models.Index(fields=['casework', '-created_at']),
        ]

    def __str__(self):
        return f'{self.recipient} ← {self.get_kind_display()} (#{self.casework_id})'