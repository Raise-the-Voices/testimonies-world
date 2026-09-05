from django.db import models


class Contact(models.Model):
    class Role(models.TextChoices):
        FAMILY = 'family', 'Family member'
        ADVOCATE = 'advocate', 'Advocate'
        LAWYER = 'lawyer', 'Lawyer'
        OFFICIAL = 'official', 'Government official'
        JOURNALIST = 'journalist', 'Journalist'
        REPORTER = 'reporter', 'Reporter/witness'
        OTHER = 'other', 'Other'

    name = models.CharField(max_length=255)
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.OTHER
    )
    persons = models.ManyToManyField(
        'cases.Person', blank=True, related_name='contacts'
    )
    phone = models.CharField(max_length=50, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    signal = models.CharField(max_length=50, blank=True, default='')
    whatsapp = models.CharField(max_length=50, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    # Soft-delete tombstone. Contacts appear in historical casework
    # narratives, so hard-deleting breaks provenance — we mark the row
    # as removed and the viewset's get_queryset filters it out of the
    # default response. Future PR can wire a separate "show deleted"
    # admin view if needed.
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ['name']
        indexes = [
            # `?role=lawyer` is the only filter on the contacts list;
            # a single-column index is enough for the equality lookup.
            models.Index(fields=['role'], name='contact_role_idx'),
        ]

    def __str__(self):
        return f'{self.name} ({self.get_role_display()})'
