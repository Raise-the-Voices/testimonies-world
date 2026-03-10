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

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.get_role_display()})'
