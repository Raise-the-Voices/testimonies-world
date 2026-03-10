from django.conf import settings
from django.db import models


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
