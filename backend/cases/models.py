from django.conf import settings
from django.db import models

from .storage import VisibilityRouterStorage


def _media_upload_to(instance, filename):
    """Route uploads into ``MEDIA_ROOT/{visibility}/`` for permission enforcement.

    The leading directory segment matches ``Media.Visibility`` so that
    ``MediaDownloadView`` can resolve a request path back to a ``Media`` row
    and decide whether the caller may fetch it.
    """
    vis = getattr(instance, 'visibility', Media.Visibility.PUBLIC) or Media.Visibility.PUBLIC
    return f'{vis}/{filename}'


class CaseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        verbose_name_plural = 'case categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Person(models.Model):
    class Status(models.TextChoices):
        DETAINED = 'detained', 'Detained'
        DISAPPEARED = 'disappeared', 'Disappeared'
        RESTRICTED_MOVEMENT = 'restricted_movement', 'Restricted Movement'
        RELEASED = 'released', 'Released'
        DECEASED = 'deceased', 'Deceased'
        UNKNOWN = 'unknown', 'Unknown'
        STATELESS = 'stateless', 'Stateless'
        RIGHTS_RESTRICTED = 'rights_restricted', 'Rights Restricted'

    class MedicalStatus(models.TextChoices):
        UNKNOWN = 'unknown', 'Unknown'
        HEALTHY = 'healthy', 'Healthy'
        HEALTH_CONCERNS = 'health_concerns', 'Health Concerns'
        CRITICAL = 'critical', 'Critical'
        DECEASED = 'deceased', 'Deceased'

    class Gender(models.TextChoices):
        MALE = 'M', 'Male'
        FEMALE = 'F', 'Female'
        OTHER = 'O', 'Other'
        UNKNOWN = 'U', 'Unknown'

    class QualityTier(models.IntegerChoices):
        STRONG = 1, 'Tier 1 — Strong evidence'
        AVERAGE = 2, 'Tier 2 — Average evidence'
        WEAK = 3, 'Tier 3 — Weak evidence'

    # Identity
    name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True, default='')
    aliases = models.CharField(max_length=500, blank=True, default='')
    country = models.CharField(max_length=100)
    ethnicity = models.CharField(max_length=100, blank=True, default='')
    gender = models.CharField(
        max_length=1, choices=Gender.choices, blank=True, default=''
    )
    date_of_birth = models.DateField(null=True, blank=True)

    # Status
    current_status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.UNKNOWN
    )
    medical_status = models.CharField(
        max_length=20, choices=MedicalStatus.choices, default=MedicalStatus.UNKNOWN
    )
    medical_notes = models.TextField(blank=True, default='')  # PRIVATE

    # Location
    rough_location = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Country/region level — shown publicly'
    )
    precise_location = models.CharField(
        max_length=500, blank=True, default='',
        help_text='City/address level — private by default'
    )
    last_known_date = models.DateField(null=True, blank=True)

    # Narrative
    summary_narrative = models.TextField(blank=True, default='')
    profile_image = models.ImageField(
        upload_to='profiles/', null=True, blank=True
    )

    # Source attribution — for cases imported from external databases
    authoritative_source = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Name of source database — e.g. "AAPP", "HRW", "shahit.biz"'
    )
    authoritative_url = models.URLField(
        max_length=1000, blank=True, default='',
        help_text='Link to this case in the original database'
    )

    # Classification
    categories = models.ManyToManyField(CaseCategory, blank=True)
    quality_tier = models.IntegerField(
        choices=QualityTier.choices, null=True, blank=True
    )
    is_published = models.BooleanField(default=True)

    # Meta
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='persons_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'persons'
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.name} ({self.country})'

    @property
    def days_since_last_report(self):
        last_report = self.reports.order_by('-date_start').first()
        if last_report and last_report.date_start:
            from django.utils import timezone
            return (timezone.now().date() - last_report.date_start).days
        return None


class Report(models.Model):
    class SourceType(models.TextChoices):
        FIRSTHAND = 'firsthand', 'Firsthand'
        SECONDHAND = 'secondhand', 'Secondhand'
        NEWS = 'news', 'News report'
        DOCUMENT = 'document', 'Document'

    person = models.ForeignKey(
        Person, on_delete=models.CASCADE, related_name='reports'
    )
    source_type = models.CharField(
        max_length=20, choices=SourceType.choices, default=SourceType.FIRSTHAND
    )
    source_attribution = models.CharField(
        max_length=500, blank=True, default='',
        help_text='Public attribution — e.g. "family member", "BBC report"'
    )
    reporter_name = models.CharField(
        max_length=255, blank=True, default=''
    )  # PRIVATE
    reporter_contact = models.TextField(blank=True, default='')  # PRIVATE

    # Dates — can be a range or single date
    date_start = models.DateField(null=True, blank=True)
    date_end = models.DateField(
        null=True, blank=True,
        help_text='Leave blank for single-date events'
    )

    # Location
    rough_location = models.CharField(max_length=255, blank=True, default='')
    precise_location = models.CharField(
        max_length=500, blank=True, default=''
    )  # PRIVATE

    # Content
    narrative = models.TextField()
    suspected_reason = models.TextField(
        blank=True, default='',
        help_text='What family/source believes is the reason'
    )
    official_reason = models.TextField(
        blank=True, default='',
        help_text='What the state officially charged'
    )

    is_private = models.BooleanField(
        default=False,
        help_text='If true, entire report hidden from public view'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reports_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_start', '-created_at']

    def __str__(self):
        return f'Report on {self.person.name} ({self.get_source_type_display()})'


class Media(models.Model):
    class MediaType(models.TextChoices):
        PHOTO = 'photo', 'Photo'
        DOCUMENT = 'document', 'Document'
        VIDEO = 'video', 'Video'
        LINK = 'link', 'External link'

    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Public'
        RESTRICTED = 'restricted', 'Restricted — authenticated users only'
        SENSITIVE = 'sensitive', 'Sensitive — advocates/admin only'

    person = models.ForeignKey(
        Person, on_delete=models.CASCADE,
        null=True, blank=True, related_name='media_files'
    )
    report = models.ForeignKey(
        Report, on_delete=models.CASCADE,
        null=True, blank=True, related_name='media_files'
    )
    file = models.FileField(
        upload_to=_media_upload_to,
        storage=VisibilityRouterStorage(),
        null=True,
        blank=True,
    )
    url = models.URLField(max_length=1000, blank=True, default='')
    media_type = models.CharField(
        max_length=20, choices=MediaType.choices, default=MediaType.PHOTO
    )
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.PUBLIC
    )
    description = models.CharField(max_length=500, blank=True, default='')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'media'
        ordering = ['-created_at']

    def __str__(self):
        target = self.person or self.report
        return f'{self.get_media_type_display()} — {target}'


class FamilyRelationship(models.Model):
    class RelationType(models.TextChoices):
        PARENT = 'parent', 'Parent'
        CHILD = 'child', 'Child'
        SIBLING = 'sibling', 'Sibling'
        SPOUSE = 'spouse', 'Spouse'
        OTHER = 'other', 'Other relative'

    person_a = models.ForeignKey(
        Person, on_delete=models.CASCADE, related_name='relationships_as_a'
    )
    person_b = models.ForeignKey(
        Person, on_delete=models.CASCADE, related_name='relationships_as_b'
    )
    relationship_type = models.CharField(
        max_length=20, choices=RelationType.choices
    )
    notes = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        unique_together = ['person_a', 'person_b']

    def __str__(self):
        return f'{self.person_a.name} — {self.get_relationship_type_display()} — {self.person_b.name}'


class AuditLog(models.Model):
    class Action(models.TextChoices):
        VIEWED = 'viewed', 'Viewed'
        DOWNLOADED = 'downloaded', 'Downloaded'
        EDITED = 'edited', 'Edited'
        DELETED = 'deleted', 'Deleted'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='audit_logs'
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    target_type = models.CharField(max_length=50)
    target_id = models.IntegerField()
    details = models.TextField(blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.user} {self.action} {self.target_type}#{self.target_id}'
