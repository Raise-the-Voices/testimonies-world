import uuid

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models


# Centralized allow-list for uploaded evidence files. Photos, PDFs, and
# short videos — what the platform actually accepts. Rejecting
# arbitrary extensions at the model layer (rather than only at the
# frontend) means a direct API POST can't smuggle a .exe or .html
# into the bucket. nginx also caps request size at 25m but that's a
# transport-layer limit; this is the application-layer contract.
ALLOWED_UPLOAD_EXTENSIONS = [
    # Images
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'tiff', 'bmp',
    # Documents
    'pdf',
    # Video (small clips; large uploads use signed URLs in a future PR)
    'mp4', 'mov', 'webm',
]
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB — slightly above the 25 MB
                                       # nginx cap to leave room for
                                       # multipart overhead without
                                       # letting the bucket fill with
                                       # 1GB junk.

# Single validator instance reused per save — Django looks up
# `validators` on the field and runs each on every full_clean().
upload_extension_validator = FileExtensionValidator(
    allowed_extensions=ALLOWED_UPLOAD_EXTENSIONS,
)


def _upload_size_validator(file_obj):
    """Reject oversized uploads at the model layer.

    FileField doesn't accept `max_length` for size; we use a custom
    validator that inspects `.size`. Runs on every `full_clean()` —
    DRF's ModelSerializer calls `full_clean()` via `is_valid()` for
    write operations, so an oversized direct API POST gets a clean
    400 with the validator's message instead of silently filling
    the bucket.
    """
    if file_obj.size > MAX_UPLOAD_BYTES:
        from django.core.exceptions import ValidationError
        raise ValidationError(
            f'File too large: {file_obj.size} bytes '
            f'(max {MAX_UPLOAD_BYTES} = {MAX_UPLOAD_BYTES // 1024 // 1024} MB).',
            code='file_too_large',
        )


# --------------------------------------------------------------------------
# Documentation form enum choices (Case Documentation Form Sections A-Q).
#
# These back the new structured fields added in migrations 0006-0012. They
# are intentionally module-level (not nested inside the model classes) so
# serializers, management commands, and tests can import them directly
# without going through a model instance. The case-file values that
# already existed on Person (Status / MedicalStatus / Gender /
# QualityTier) stay nested in their model for historical reasons — they
# predate the structured-form rollout and renaming them would touch
# existing rows that the legacy UI still displays.
# --------------------------------------------------------------------------


class DuplicateCheck(models.TextChoices):
    NO_DUPLICATE = 'no_duplicate', 'No duplicate identified'
    POSSIBLE_DUPLICATE = 'possible_duplicate', 'Possible duplicate'
    EXISTING_CASE = 'existing_case', 'Existing case'


class DatePrecision(models.TextChoices):
    EXACT = 'exact', 'Exact'
    APPROXIMATE = 'approximate', 'Approximate'
    UNKNOWN = 'unknown', 'Unknown'


class YesNoUnknown(models.TextChoices):
    YES = 'yes', 'Yes'
    NO = 'no', 'No'
    UNKNOWN = 'unknown', 'Unknown'


class VerificationLevel(models.TextChoices):
    """Section L — case-level verification ladder (4 stars on the form)."""
    REPORTED = 'level_1_reported', 'Level 1 — Reported'
    PARTIALLY = 'level_2_partially_verified', 'Level 2 — Partially verified'
    CORROBORATED = 'level_3_corroborated', 'Level 3 — Corroborated'
    DOCUMENTED = 'level_4_documented', 'Level 4 — Documented'


class VerificationStatus(models.TextChoices):
    """Section H / J — per-evidence and per-response verification status.
    Distinct from `VerificationLevel` (case-level ladder)."""
    REPORTED = 'reported', 'Reported'
    PARTIALLY = 'partially_verified', 'Partially verified'
    CORROBORATED = 'corroborated', 'Corroborated'
    DOCUMENTED = 'documented', 'Documented'


class VerificationStatusUpdate(models.TextChoices):
    """Section Q — verification status on a future update. Includes
    Unverified / Pending states that the case-level ladder
    (`VerificationLevel`) does not."""
    UNVERIFIED = 'unverified', 'Unverified'
    PENDING = 'pending', 'Pending'
    PARTIALLY = 'partially_verified', 'Partially verified'
    CORROBORATED = 'corroborated', 'Corroborated'
    VERIFIED = 'verified', 'Verified'


class PublicIdentityLevel(models.TextChoices):
    FULL = 'full', 'Full name'
    PARTIAL = 'partial', 'Partial name'
    ANONYMOUS = 'anonymous', 'Anonymous'


class PublicLocationLevel(models.TextChoices):
    PROVINCE = 'province', 'Province'
    DISTRICT = 'district', 'District'
    CITY = 'city', 'City / general area'
    DO_NOT_DISCLOSE = 'do_not_disclose', 'Do not disclose'


class ConsentStatus(models.TextChoices):
    YES = 'yes', 'Yes'
    NO = 'no', 'No'
    PENDING = 'pending', 'Pending'


class EvidenceStatus(models.TextChoices):
    VERIFIED = 'verified', 'Verified'
    PARTIALLY = 'partially_verified', 'Partially verified'
    UNVERIFIED = 'unverified', 'Unverified'
    PENDING = 'pending', 'Pending'


class EvidenceKind(models.TextChoices):
    FIR = 'fir', 'FIR'
    COURT_PETITION = 'court_petition_order', 'Court petition/order'
    GOVERNMENT_DOCUMENT = 'government_document', 'Government document'
    IDENTITY_DOCUMENT = 'identity_document', 'Identity document'
    PHOTOGRAPH = 'photograph', 'Photograph'
    MEDICAL_DOCUMENT = 'medical_document', 'Medical document'
    INTERVIEW_TRANSCRIPT = 'interview_transcript', 'Interview/transcript'
    MEDIA_REPORT = 'media_report', 'Media report'
    NGO_REPORT = 'ngo_report', 'NGO report'
    OTHER = 'other', 'Other'


class PrimarySourceType(models.TextChoices):
    VICTIM_SURVIVOR = 'victim_survivor', 'Victim/survivor'
    FAMILY = 'family', 'Family'
    WITNESS = 'witness', 'Witness'
    OFFICIAL_DOCUMENT = 'official_document', 'Official document'


class AdditionalSourceType(models.TextChoices):
    LAWYER = 'lawyer', 'Lawyer'
    NGO = 'ngo', 'NGO'
    MEDIA = 'media', 'Media'
    COURT = 'court', 'Court'
    GOVERNMENT = 'government', 'Government'
    OTHER = 'other', 'Other'


class SourceConsistency(models.TextChoices):
    CONSISTENT = 'consistent', 'Consistent'
    SOME_DIFFERENCES = 'some_differences', 'Some differences'
    MAJOR_CONFLICT = 'major_conflict', 'Major conflict'
    REQUIRES_FURTHER = 'requires_further_verification', 'Requires further verification'


class ResponseType(models.TextChoices):
    CONFIRMATION = 'confirmation', 'Confirmation'
    DENIAL = 'denial', 'Denial'
    INVESTIGATION = 'investigation', 'Investigation'
    DETENTION_ACKNOWLEDGED = 'detention_acknowledged', 'Detention acknowledged'
    RELEASE_CONFIRMED = 'release_confirmed', 'Release confirmed'
    OTHER = 'other', 'Other'


class RiskLevel(models.TextChoices):
    LOW = 'low', 'Low'
    MODERATE = 'moderate', 'Moderate'
    HIGH = 'high', 'High'
    CRITICAL = 'critical', 'Critical'
    NOT_ASSESSED = 'not_assessed', 'Not assessed'


class RiskConcern(models.TextChoices):
    VICTIM = 'victim', 'Victim'
    FAMILY = 'family', 'Family'
    SOURCE = 'source', 'Source'
    INTERVIEWER = 'interviewer', 'Interviewer'
    SENSITIVE_LOCATION = 'sensitive_location', 'Sensitive location'
    RETALIATION = 'retaliation', 'Retaliation'
    SURVEILLANCE = 'surveillance', 'Surveillance'
    OTHER = 'other', 'Other'


class ReviewDecision(models.TextChoices):
    APPROVED = 'approved', 'Approved'
    CORRECTIONS_REQUIRED = 'corrections_required', 'Corrections required'
    MORE_VERIFICATION = 'more_verification_required', 'More verification required'
    INTERNAL_ONLY = 'internal_only', 'Internal only'
    DO_NOT_PUBLISH = 'do_not_publish', 'Do not publish'


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
        # Additions for Documentation Form Section D — appended (not
        # reordered) so existing rows are not remapped by accident.
        ONGOING_ENFORCED_DISAPPEARANCE = (
            'ongoing_enforced_disappearance', 'Ongoing alleged enforced disappearance',
        )
        FOUND_ALIVE = 'found_alive', 'Found alive'
        FOUND_DEAD = 'found_dead', 'Found dead'
        CASE_CLOSED = 'case_closed', 'Case closed'
        OTHER = 'other', 'Other'

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

    # =====================================================================
    # Documentation form fields — Sections A, B, D, K, N, P.
    #
    # All defaults are null / blank / empty-string so legacy rows
    # migrate without data loss and without forcing the legacy UI to
    # render the new structured fields. The structure-rollout cutoff
    # is enforced at the serializer layer (see settings.STRUCTURED_FORM_CUTOFF).
    # =====================================================================

    # ----- Section A: CASE IDENTIFICATION -----
    case_id = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False,
        help_text='External / website case ID (Section A).',
    )
    case_received_date = models.DateField(
        null=True, blank=True,
        help_text='Date the case file was received by the documentation officer (Section A).',
    )
    case_received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='cases_received',
        help_text='Documentation officer who received the case (Section A).',
    )
    case_source_types = models.JSONField(
        default=list, blank=True,
        help_text='Source-of-case checklist — list from {research_interview, '
                 'family, victim_survivor, lawyer, ngo_cso, media, '
                 'government_document, other} (Section A).',
    )
    case_source_other = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Free-text when "other" is selected above (Section A).',
    )
    duplicate_check = models.CharField(
        max_length=20, blank=True, default='',
        choices=DuplicateCheck.choices,
        help_text='Duplicate-check outcome (Section A).',
    )
    duplicate_of = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='duplicates',
        help_text='Set when duplicate_check = existing_case (Section A).',
    )

    # ----- Section B: PERSON -----
    age_at_incident = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Age at the time of the incident (Section B). Distinct from date_of_birth.',
    )
    occupation = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Occupation at time of incident (Section B).',
    )
    district = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Person-level administrative district (Section B). Distinct from Report.incident_district.',
    )
    province = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Person-level administrative province (Section B). Distinct from Report.incident_province.',
    )
    identity_verified_methods = models.JSONField(
        default=list, blank=True,
        help_text='Identity-verification checklist — list from {interview, family, '
                 'identity_document, court_document, other} (Section B).',
    )
    identity_verified_other = models.CharField(
        max_length=255, blank=True, default='',
    )

    # ----- Section D: CURRENT STATUS (metadata of the current status) -----
    current_status_date = models.DateField(
        null=True, blank=True,
        help_text='Date the current status was confirmed (Section D).',
    )
    current_status_source = models.CharField(
        max_length=500, blank=True, default='',
        help_text='Source of the current-status claim (Section D).',
    )
    current_status_verification = models.CharField(
        max_length=50, blank=True, default='',
        choices=VerificationLevel.choices,
        help_text='Verification level of the current status (Section D).',
    )

    # ----- Section K: CONSENT / PUBLICATION (person-level) -----
    consent_documentation = models.CharField(
        max_length=20, blank=True, default='',
        choices=ConsentStatus.choices,
        help_text='Consent for documentation — Yes / No / Pending (Section K).',
    )
    consent_public_publication = models.CharField(
        max_length=20, blank=True, default='',
        choices=ConsentStatus.choices,
        help_text='Consent for public publication (Section K).',
    )
    public_identity_level = models.CharField(
        max_length=20, blank=True, default='',
        choices=PublicIdentityLevel.choices,
        help_text='Full / Partial / Anonymous (Section K).',
    )
    photograph_public = models.CharField(
        max_length=20, blank=True, default='',
        choices=ConsentStatus.choices,
        help_text='Yes / No / Pending (Section K).',
    )
    public_location_level = models.CharField(
        max_length=20, blank=True, default='',
        choices=PublicLocationLevel.choices,
        help_text='Province / District / City / Do not disclose (Section K).',
    )
    information_restricted_from_publication = models.TextField(
        blank=True, default='',
        help_text='Free-text list of items withheld from publication (Section K).',
    )

    # ----- Section N: PUBLIC CASE SUMMARY -----
    public_summary = models.TextField(
        blank=True, default='',
        help_text='Approved-for-publication summary (Section N).',
    )
    public_status_text = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Public-facing status text (Section N).',
    )
    public_verification_level = models.CharField(
        max_length=50, blank=True, default='',
        choices=VerificationLevel.choices,
        help_text='Mirror of Section L for the public-facing display (Section N).',
    )

    # ----- Section P: WEBSITE ENTRY -----
    entered_in_world = models.CharField(
        max_length=20, blank=True, default='',
        choices=ConsentStatus.choices,
        help_text='Has the case been entered into Testimonies.World — Yes / No / Pending (Section P).',
    )
    entry_date = models.DateField(null=True, blank=True)
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='persons_entered',
    )
    second_person_check_completed = models.BooleanField(default=False)
    checked_against_original_documentation = models.BooleanField(default=False)
    final_reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='persons_final_reviewed',
    )
    final_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name_plural = 'persons'
        ordering = ['-updated_at']
        indexes = [
            # Single-column indexes accelerate common equality / ordering
            # paths used by the filter UI and statistics endpoint.
            models.Index(fields=['country'], name='person_country_idx'),
            models.Index(fields=['current_status'], name='person_current_status_idx'),
            models.Index(fields=['is_published'], name='person_is_published_idx'),
            models.Index(fields=['-updated_at'], name='person_updated_desc_idx'),
            # Composite covers the most common access path:
            # "published persons grouped by status" (statistics endpoint)
            # and the default list filter for unauthenticated viewers.
            models.Index(
                fields=['is_published', 'current_status'],
                name='person_pub_status_idx',
            ),
            # Standalone -created_at for the documented ?ordering=-created_at
            # sort on /api/persons/ and the "newest cases" landing page.
            models.Index(fields=['-created_at'], name='person_created_at_desc_idx'),
        ]

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

    # =====================================================================
    # Documentation form fields — Sections C, D-metadata, F, G, I, J, L, M, O.
    # Same rule as Person: null / blank / empty-string defaults so legacy
    # reports remain valid; cutoff enforcement lives in serializers.
    # =====================================================================

    # ----- Section C: INCIDENT -----
    case_types = models.JSONField(
        default=list, blank=True,
        help_text='Section C case-type checklist — list from '
                 '{enforced_disappearance, arbitrary_detention, detention, '
                 'release_following, death_following, other}.',
    )
    case_type_other = models.CharField(
        max_length=255, blank=True, default='',
    )
    incident_date = models.DateField(
        null=True, blank=True,
        help_text='Date of incident / disappearance (Section C, 4-star field).',
    )
    incident_date_precision = models.CharField(
        max_length=20, blank=True, default='',
        choices=DatePrecision.choices,
        help_text='Exact / Approximate / Unknown (Section C).',
    )
    last_known_location = models.CharField(
        max_length=500, blank=True, default='',
        help_text='Last known location of the person (Section C, 4-star field).',
    )
    incident_district = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Administrative district of the incident (Section C).',
    )
    incident_province = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Administrative province of the incident (Section C).',
    )
    # NOTE: existing `narrative` TextField is repurposed as Section C's
    # "General circumstances" — it has always been the free-text
    # incident narrative. We do not rename it for backwards
    # compatibility with legacy records and the existing UI.
    incident_information_source = models.CharField(
        max_length=500, blank=True, default='',
        help_text='Source of this specific incident information (Section C).',
    )
    incident_verification = models.CharField(
        max_length=50, blank=True, default='',
        choices=VerificationLevel.choices,
        help_text='Verification status of the incident (Section C).',
    )

    # ----- Section F: DETENTION -----
    detention_alleged = models.CharField(
        max_length=20, blank=True, default='',
        choices=YesNoUnknown.choices,
        help_text='Section F (4-star): Was detention alleged?',
    )
    alleged_detention_location = models.CharField(
        max_length=500, blank=True, default='',
        help_text='Alleged detention location (Section F).',
    )
    detention_acknowledged = models.CharField(
        max_length=20, blank=True, default='',
        choices=YesNoUnknown.choices,
        help_text='Was the detention officially acknowledged? (Section F)',
    )
    detention_information = models.TextField(
        blank=True, default='',
        help_text='Information / evidence about the detention (Section F).',
    )
    detention_verification = models.CharField(
        max_length=20, blank=True, default='',
        choices=VerificationStatus.choices,
        help_text='Per-detention verification status (Section F).',
    )

    # ----- Section G: SOURCES -----
    primary_source_type = models.CharField(
        max_length=30, blank=True, default='',
        choices=PrimarySourceType.choices,
        help_text='Primary source type (Section G).',
    )
    primary_source_description = models.CharField(
        max_length=500, blank=True, default='',
    )
    additional_source_type = models.CharField(
        max_length=30, blank=True, default='',
        choices=AdditionalSourceType.choices,
        help_text='Additional source type (Section G).',
    )
    additional_source_description = models.CharField(
        max_length=500, blank=True, default='',
    )
    source_consistency = models.CharField(
        max_length=30, blank=True, default='',
        choices=SourceConsistency.choices,
        help_text='Consistency between primary and additional sources (Section G).',
    )
    source_verification_notes = models.TextField(
        blank=True, default='',
        help_text='Free-text verification notes (Section G).',
    )

    # ----- Section I: LEGAL ACTION -----
    legal_fir_filed = models.CharField(
        max_length=20, blank=True, default='',
        choices=YesNoUnknown.choices,
        help_text='Was an FIR filed? (Section I, starred on the form)',
    )
    fir_number = models.CharField(max_length=200, blank=True, default='')
    police_station = models.CharField(max_length=255, blank=True, default='')
    legal_court_case = models.CharField(
        max_length=20, blank=True, default='',
        choices=YesNoUnknown.choices,
        help_text='Was a court case / petition filed? (Section I, starred)',
    )
    court_name = models.CharField(max_length=255, blank=True, default='')
    case_number = models.CharField(max_length=200, blank=True, default='')
    legal_commission_complaint = models.CharField(
        max_length=20, blank=True, default='',
        choices=YesNoUnknown.choices,
    )
    legal_lawyer_involved = models.CharField(
        max_length=20, blank=True, default='',
        choices=YesNoUnknown.choices,
    )
    current_legal_status = models.TextField(
        blank=True, default='',
        help_text='Current status of the legal process (Section I).',
    )

    # ----- Section J: GOVERNMENT / AUTHORITY RESPONSE -----
    official_response = models.CharField(
        max_length=20, blank=True, default='',
        choices=YesNoUnknown.choices,
    )
    responding_authority = models.CharField(
        max_length=255, blank=True, default='',
    )
    response_date = models.DateField(null=True, blank=True)
    response_type = models.CharField(
        max_length=30, blank=True, default='',
        choices=ResponseType.choices,
    )
    response_source_document = models.CharField(
        max_length=500, blank=True, default='',
    )
    response_verification = models.CharField(
        max_length=20, blank=True, default='',
        choices=VerificationStatus.choices,
        help_text='Per-response verification status (Section J).',
    )

    # ----- Section L: VERIFICATION LEVEL -----
    verification_level = models.CharField(
        max_length=50, blank=True, default='',
        choices=VerificationLevel.choices,
        help_text='Case-level verification ladder (Section L).',
    )
    verification_reason = models.TextField(
        blank=True, default='',
        help_text='Why this level was assigned (Section L).',
    )
    unverified_information_remaining = models.TextField(
        blank=True, default='',
        help_text='Information that remains unverified (Section L).',
    )

    # ----- Section M: INTERNAL RISK / SECURITY (NEVER exposed publicly) -----
    # Gated by serializer — see `to_representation` in serializers.py.
    # The model fields exist on every Report; the serializer strips them
    # for everyone below Advocate role, and `internal_notes` for everyone
    # below Admin.
    risk_level = models.CharField(
        max_length=20, blank=True, default='',
        choices=RiskLevel.choices,
        help_text='INTERNAL — Section M. Never exposed via public API.',
    )
    risk_concerns = models.JSONField(
        default=list, blank=True,
        help_text='INTERNAL — Section M checklist.',
    )
    risk_concerns_other = models.CharField(
        max_length=255, blank=True, default='',
        help_text='INTERNAL — free-text when "other" is selected.',
    )
    internal_notes = models.TextField(
        blank=True, default='',
        help_text='INTERNAL — Section M. Stripped from public API always.',
    )

    # ----- Section O: QUALITY CONTROL -----
    qc_name_checked = models.BooleanField(default=False)
    qc_duplicate_check_completed = models.BooleanField(default=False)
    qc_date_checked = models.BooleanField(default=False)
    qc_location_checked = models.BooleanField(default=False)
    qc_status_checked = models.BooleanField(default=False)
    qc_sources_recorded = models.BooleanField(default=False)
    qc_evidence_checked = models.BooleanField(default=False)
    qc_legal_information_checked = models.BooleanField(default=False)
    qc_government_response_checked = models.BooleanField(default=False)
    qc_allegations_identified = models.BooleanField(default=False)
    qc_consent_checked = models.BooleanField(default=False)
    qc_sensitive_information_removed = models.BooleanField(default=False)
    qc_verification_level_assigned = models.BooleanField(default=False)
    qc_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reports_qc_reviewed',
    )
    qc_review_date = models.DateField(null=True, blank=True)
    qc_review_decision = models.CharField(
        max_length=30, blank=True, default='',
        choices=ReviewDecision.choices,
    )

    class Meta:
        ordering = ['-date_start', '-created_at']
        indexes = [
            # The default anonymous-viewer path filters by
            # `person__is_published=True AND is_private=False`. This
            # composite covers the per-person private-filter scan inside
            # ReportViewSet.get_queryset.
            models.Index(
                fields=['person', 'is_private'],
                name='report_person_private_idx',
            ),
            # Standalone indexes for the default Meta.ordering path
            # ('-date_start', '-created_at') and the
            # ?date_from/?date_to filter lookups. The composite above
            # doesn't cover the global sort.
            models.Index(fields=['-date_start'], name='report_date_start_desc_idx'),
            models.Index(fields=['-created_at'], name='report_created_at_desc_idx'),
        ]

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
        upload_to='uploads/',
        null=True, blank=True,
        validators=[upload_extension_validator, _upload_size_validator],
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

    # =====================================================================
    # Documentation form fields — Section H (Evidence classification).
    # Adds role labels on top of the existing file/visibility pipeline.
    # =====================================================================
    evidence_kind = models.CharField(
        max_length=40, blank=True, default='',
        choices=EvidenceKind.choices,
        help_text='Section H: FIR / Court petition / Photograph / etc.',
    )
    evidence_kind_other = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Free-text when evidence_kind = other.',
    )
    evidence_reference_number = models.CharField(
        max_length=200, blank=True, default='',
    )
    evidence_status = models.CharField(
        max_length=20, blank=True, default='',
        choices=EvidenceStatus.choices,
        help_text='Section H: Verified / Partially / Unverified / Pending.',
    )

    class Meta:
        verbose_name_plural = 'media'
        ordering = ['-created_at']
        indexes = [
            # Person/media-by-visibility is the most common media lookup
            # (person-detail page rendering photos first, then filtered
            # to visibility for the requester).
            models.Index(
                fields=['person', 'visibility'],
                name='media_person_visibility_idx',
            ),
            models.Index(
                fields=['report', 'visibility'],
                name='media_report_visibility_idx',
            ),
            # For the "show me photos for this person" / "show me docs
            # for this report" gallery views.
            models.Index(
                fields=['person', 'media_type'],
                name='media_person_type_idx',
            ),
        ]

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
        indexes = [
            # relationship_type is low-cardinality but cheap to index;
            # speeds up `?relationship_type=sibling` style filters.
            models.Index(
                fields=['relationship_type'],
                name='familyrel_type_idx',
            ),
        ]

    def __str__(self):
        return f'{self.person_a.name} — {self.get_relationship_type_display()} — {self.person_b.name}'


class CaseEvent(models.Model):
    """Documentation-form Section E — case timeline event.

    One row per dated event in the case file (detention, transfer,
    court hearing, release, status change, etc.). The form's "Event"
    column is captured in both `event_kind` (machine-readable) and
    `description` (free text), so the timeline can be displayed as
    chips on the structured side and a paragraph on the legacy side.

    Always child of `Person` (one timeline per case file). Optionally
    soft-linked back to the `Report` that introduced the event — that
    link is nullable and `SET_NULL` on delete so removing a Report
    doesn't also remove history.
    """

    class EventKind(models.TextChoices):
        INCIDENT = 'incident', 'Incident'
        DETENTION = 'detention', 'Detention'
        TRANSFER = 'transfer', 'Transfer'
        COURT_HEARING = 'court_hearing', 'Court hearing'
        RELEASE = 'release', 'Release'
        STATUS_CHANGE = 'status_change', 'Status change'
        OTHER = 'other', 'Other'

    person = models.ForeignKey(
        'Person', on_delete=models.CASCADE,
        related_name='timeline_events',
    )
    report = models.ForeignKey(
        'Report', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='events',
        help_text='Optional soft link back to the originating Report.',
    )
    event_date = models.DateField(null=True, blank=True)
    event_kind = models.CharField(
        max_length=30, blank=True, default='',
        choices=EventKind.choices,
    )
    description = models.TextField(blank=True, default='')
    source = models.CharField(max_length=500, blank=True, default='')
    verification = models.CharField(
        max_length=50, blank=True, default='',
        choices=VerificationLevel.choices,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['event_date', '-created_at']
        indexes = [
            # Default per-person timeline read path: "show me this
            # person's events newest-first-by-event-date, fallback to
            # created_at". The composite covers the per-person list
            # query without a per-row sort.
            models.Index(
                fields=['person', '-event_date'],
                name='caseevent_person_date_idx',
            ),
        ]

    def __str__(self):
        kind = self.get_event_kind_display() if self.event_kind else 'Event'
        return f'{kind} — {self.person.name} ({self.event_date})'


class CaseUpdate(models.Model):
    """Documentation-form Section Q — Future Update on a case.

    One row per follow-up update after the case was first entered
    into Testimonies.World. Distinct from `CaseEvent`, which records
    anything that happened to the person; this records anything that
    happened to *the case file* (new evidence, new status, new
    verification).

    Always child of `Person` (a case file is per-person). Verification
    uses `VerificationStatusUpdate` (5-state) — distinct from the
    case-level `VerificationLevel` ladder; an update may be
    Unverified or Pending without retroactively changing the case
    ladder.
    """

    person = models.ForeignKey(
        'Person', on_delete=models.CASCADE,
        related_name='updates',
    )
    update_date = models.DateField(null=True, blank=True)
    new_information = models.TextField(blank=True, default='')
    source = models.CharField(max_length=500, blank=True, default='')
    evidence = models.TextField(blank=True, default='')
    verification = models.CharField(
        max_length=20, blank=True, default='',
        choices=VerificationStatusUpdate.choices,
    )
    status_changes = models.CharField(
        max_length=20, blank=True, default='',
        choices=YesNoUnknown.choices,
        help_text='Does this update change the case status?',
    )
    new_status = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Free-text new status (Section Q).',
    )
    website_updated = models.CharField(
        max_length=20, blank=True, default='',
        choices=YesNoUnknown.choices,
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='case_updates_verified',
    )
    verified_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Newest update first — the dashboard "what's changed
        # recently?" view.
        ordering = ['-update_date', '-created_at']

    def __str__(self):
        return f'Update on {self.person.name} ({self.update_date})'


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
        indexes = [
            # AuditLog is the canonical "what happened to object X?" log —
            # (target_type, target_id) is the lookup that powers that view.
            models.Index(
                fields=['target_type', 'target_id'],
                name='audit_target_idx',
            ),
            # "Show me everything user U did, newest first" — the
            # accountability surface for advocates reviewing their own
            # activity.
            models.Index(
                fields=['user', '-timestamp'],
                name='audit_user_time_idx',
            ),
            # Standalone -timestamp for the default /api/audit-logs/
            # list page, which sorts by -timestamp without a user
            # filter (so audit_user_time_idx doesn't apply).
            models.Index(fields=['-timestamp'], name='audit_timestamp_desc_idx'),
        ]

    def __str__(self):
        return f'{self.user} {self.action} {self.target_type}#{self.target_id}'
