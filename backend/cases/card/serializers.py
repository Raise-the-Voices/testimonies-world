"""Case card payload — the masked, publication-facing projection of a case.

The card is a poster: a flat summary of one case that can be rendered
to an image and shared. Everything it shows is decided HERE, on the
server, from the consent flags on the Person row. The browser never
receives a value that has not been cleared for publication — the
frontend's job is to lay out what it is given, not to decide what is
safe to show. Same posture as `cases/testimonials/serializers.py`:
"server-side masking is the security boundary".

The masking contract, one rule per line, each pinned by a test in
`tests.py`:

  - A blank consent / visibility flag means the MOST RESTRICTIVE
    option, never the permissive one. Same posture as
    `cases/storage.py`: "the protected tree is the default … publishing
    is the explicit act, not protecting."
  - A private Report contributes nothing. It is dropped before any of
    its fields are read, not filtered afterwards.
  - Media that is not `public` is never part of a card.
  - `withheld` names what was taken out. It never contains the
    withheld value itself.

Two payload keys can be ABSENT rather than null — `location` and
`photo`. "This was withheld" and "this was empty" are different
facts, and the key being gone is what says "withheld"; `withheld`
says which.
"""

from django.utils import timezone
from rest_framework import serializers

from cases.models import Person
from cases.models import PublicIdentityLevel, PublicLocationLevel
from cases.serializers import _absolute_media_url

# --- Vocabularies ------------------------------------------------------

# Human labels for `Person.current_status`. The frontend's
# `statusPresentation.ts` only covers the six TESTIMONIAL statuses, so
# the card needs its own map for the person statuses. Derived from the
# model's TextChoices so a new status shows up here without a second
# edit.
PERSON_STATUS_LABELS = dict(Person.Status.choices)
PERSON_STATUS_VALUES = [value for value, _label in Person.Status.choices]

# The public wording of the case-level verification ladder
# (`cases.models.VerificationLevel`). The ladder's own labels are
# written for the documentation form ("Level 3 — Corroborated"); the
# card publishes the short form.
VERIFICATION_LABELS = {
    'level_1_reported': 'Reported',
    'level_2_partially_verified': 'Partially verified',
    'level_3_corroborated': 'Corroborated',
    'level_4_documented': 'Documented',
}

# `Person.quality_tier` (evidence strength) translated into the public
# verification ladder. The tier is an internal judgement about how
# strong the evidence is; the ladder is the vocabulary the card
# publishes in, so the tier is translated rather than shown raw.
QUALITY_TIER_TO_VERIFICATION = {
    1: 'level_3_corroborated',
    2: 'level_2_partially_verified',
    3: 'level_1_reported',
}

# --- Editorial priority list -------------------------------------------

# The card's headline line, taken from the person's categories. The
# order is an EDITORIAL judgement — the most serious category a person
# is filed under leads the card — not a fact about the data, which is
# why it lives in code where a human can edit it rather than in a
# table nobody looks at.
#
# EDITABLE: reorder the tuple, or add a row, to change what the card
# leads with. Matching is case-insensitive; the headline is the
# matched category in title case.
CATEGORY_HEADLINE_PRIORITY = (
    'Enforced disappearance',
    'Arbitrary detention',
    'Extrajudicial violence',
    'Restricted movement',
    'Rights restricted',
    'Stateless',
    'Child rights violation',
    'Refugee / needs relocation',
    'Torture',
    'Other',
)

# --- Withholding vocabulary ---------------------------------------------

# The strings a card reader sees when something is withheld ("Location
# withheld"). They name the item and never the value behind it.
WITHHELD_LOCATION = 'precise location'
WITHHELD_IDENTITY = 'identity'
WITHHELD_PHOTO = 'photograph'

# The placeholder shown in place of a name that is not cleared for
# publication. Deliberately constant — the card must not leak the
# length or the shape of the real name.
WITHHELD_DISPLAY_NAME = 'Identity withheld'

# The generic marker for a restriction line that names an item the
# card cannot map to a payload block. The line itself is never copied
# — see `_parse_restrictions`.
WITHHELD_OTHER = 'other restricted information'

# Keyword → the payload block it withholds. `information_restricted_from_publication`
# is a free-text list of items a human wrote ("precise location",
# "family names", "photograph"); each line is matched
# case-insensitively against these keywords and the matching block is
# dropped from the payload.
#
# Deliberately short. Wider substring matching ("age", "date") fires
# on innocent words — "village" contains "age", "image" contains
# "age" — so the list holds only the three items the card can drop
# whole.
RESTRICTION_KEYWORDS = (
    ('location', WITHHELD_LOCATION),
    ('name', WITHHELD_IDENTITY),
    ('photo', WITHHELD_PHOTO),
)

# --- Location disclosure ------------------------------------------------

# Which Person fields each disclosure level may show, in display
# order, on top of the country (which is always in `location.country`
# and is never repeated in `location.display`).
#
# A level shows what it is named for and nothing finer: `province`
# discloses the country only, `district` adds the district, `city`
# adds the rough location on top of the district — a city name on its
# own ("Smouha") means nothing without the district it sits in.
LOCATION_DISCLOSURE = {
    'province': (),
    'district': ('district',),
    'city': ('district', 'rough_location'),
}

LOCATION_PRECISION_VALUES = ['province', 'district', 'city', 'withheld']


# --- Small helpers ------------------------------------------------------

def _clean(value):
    """Trimmed string, or None when there is nothing there.

    Blank CharFields are '' in the database; on a card they are
    absent. One helper so "no value" looks the same everywhere.
    """
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _title_case(text):
    """Capitalise the first letter of every word, leaving the rest of
    the word alone so acronyms and possessives survive
    ("children's rights" → "Children's rights")."""
    return ' '.join(word[:1].upper() + word[1:] for word in text.split())


def _partial_name(name):
    """First name plus the initial of the second: "Ahmed Al-Hassan" →
    "Ahmed A.". Used when the case is published at `partial`
    identity level."""
    parts = (name or '').split()
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return f'{parts[0]} {parts[1][0]}.'


# --- Field derivations --------------------------------------------------

def _public_reports(person):
    """The person's reports a card is allowed to read.

    Private reports are dropped HERE, before any of their fields are
    touched — not filtered afterwards. A private report's date, place,
    abductors and reason must never reach a card, and the only
    reliable way to guarantee that is not to look.
    """
    return [report for report in person.reports.all() if not report.is_private]


def _anchor_report(reports):
    """The report that describes the incident the card is about.

    `date_of_abduction` is the structured field for the abduction /
    taking-into-custody event; it wins whenever any report carries
    it. `date_start` is the legacy field and is populated on almost
    every row, so it is the fallback — but ONLY when no report has a
    structured abduction date, otherwise the two would be mixed and
    the card would show a date from a different event.

    The reports list is unordered with respect to the abduction date
    (`Report.Meta.ordering` sorts by `date_start`, not by
    `date_of_abduction`), so the earliest is selected explicitly.
    `reports[0]` would be wrong whenever the ordering disagrees with
    the abduction date.
    """
    with_abduction = [r for r in reports if r.date_of_abduction]
    if with_abduction:
        return min(with_abduction, key=lambda r: r.date_of_abduction)
    with_start = [r for r in reports if r.date_start]
    if with_start:
        return min(with_start, key=lambda r: r.date_start)
    return None


def _father_name(person):
    """The name of the person's father, or None.

    `FamilyRelationship.relationship_type` describes person_b relative
    to person_a, so the parent has to be read from the correct side:
    a 'parent' row where the subject is person_a, or a 'child' row
    where the subject is person_b.

    The relation only says "parent" — the API's family payload
    carries no gender, so father vs mother is not decidable from the
    relation row. The related Person's gender is read from the
    database instead, and anything that is not male answers None.
    Guessing would put a mother's name on a line labelled "Father".
    """
    candidates = []
    for relation in person.relationships_as_a.all():
        if relation.relationship_type == 'parent':
            candidates.append(relation.person_b)
    for relation in person.relationships_as_b.all():
        if relation.relationship_type == 'child':
            candidates.append(relation.person_a)
    for parent in candidates:
        if parent.gender == Person.Gender.MALE:
            return _clean(parent.name)
    return None


def _age(person, incident_date):
    """The person's age at the time of the incident.

    `age_at_incident` is recorded directly for most cases. Where it
    is missing the age is derived from `date_of_birth` — the age the
    card talks about is the age the person was when it happened, not
    their age today. With no incident date either, `last_known_date`
    is used, and failing that today.
    """
    if person.age_at_incident is not None:
        return person.age_at_incident
    if not person.date_of_birth:
        return None
    reference = incident_date or person.last_known_date or timezone.localdate()
    years = reference.year - person.date_of_birth.year
    if (reference.month, reference.day) < (
        person.date_of_birth.month, person.date_of_birth.day,
    ):
        years -= 1
    return max(years, 0)


def _headline(person):
    """The card's headline line, taken from the person's categories."""
    names = {category.name.strip().lower() for category in person.categories.all()}
    for candidate in CATEGORY_HEADLINE_PRIORITY:
        if candidate.strip().lower() in names:
            return _title_case(candidate)
    return None


def _effective_identity_level(person):
    """`public_identity_level`, with a blank treated as `anonymous`.

    Blank means the most restrictive option, never the permissive one.
    """
    level = (person.public_identity_level or '').strip()
    if level == PublicIdentityLevel.PARTIAL:
        return PublicIdentityLevel.PARTIAL
    if level == PublicIdentityLevel.FULL:
        return PublicIdentityLevel.FULL
    return PublicIdentityLevel.ANONYMOUS


def _effective_location_precision(person):
    """`public_location_level`, with a blank treated as `province`.

    A blank disclosure level grants the coarsest thing it can grant:
    the country, which is already public on the case page.
    """
    level = (person.public_location_level or '').strip()
    if level == PublicLocationLevel.DO_NOT_DISCLOSE:
        return 'withheld'
    if level in LOCATION_DISCLOSURE:
        return level
    return 'province'


def _parse_restrictions(person):
    """Split `information_restricted_from_publication` into the payload
    blocks it blocks and the labels the reader is shown.

    The field is documented as a free-text list of items withheld from
    publication. Each line is matched case-insensitively against
    RESTRICTION_KEYWORDS. A line that matches nothing blocks nothing —
    we cannot guess which field it meant — but it is still reported,
    under a fixed generic label.

    The raw line NEVER reaches the payload. It is free text a human
    typed, and it routinely names the very value that is being
    withheld ("precise location: 12 Rue de la Paix"). Copying it into
    `withheld` would publish the value inside the array that exists
    to say it was withheld. So a matching line contributes its
    canonical label ("precise location" / "identity" / "photograph"),
    and a line that matches nothing contributes the generic marker.
    """
    blocked = set()
    labels = []
    for raw in (person.information_restricted_from_publication or '').splitlines():
        line = raw.strip()
        if not line:
            continue
        lowered = line.lower()
        matched = False
        for keyword, block in RESTRICTION_KEYWORDS:
            if keyword in lowered:
                blocked.add(block)
                matched = True
                if block not in labels:
                    labels.append(block)
        if not matched and WITHHELD_OTHER not in labels:
            labels.append(WITHHELD_OTHER)
    return blocked, labels


def build_card_payload(person, request=None):
    """Build the masked card payload for one Person.

    Returns a plain dict. The keys that must not appear at all — the
    location and the photo — are simply absent from it.
    """
    blocked, restriction_labels = _parse_restrictions(person)
    withheld = list(restriction_labels)

    reports = _public_reports(person)
    anchor = _anchor_report(reports)

    # --- Identity --------------------------------------------------------
    # A restriction that names the identity withholds it exactly the
    # way an anonymous identity level does: the reader is told the
    # identity exists, not what it is.
    identity_level = _effective_identity_level(person)
    if WITHHELD_IDENTITY in blocked:
        identity_level = PublicIdentityLevel.ANONYMOUS

    if identity_level == PublicIdentityLevel.ANONYMOUS:
        display_name = WITHHELD_DISPLAY_NAME
    elif identity_level == PublicIdentityLevel.PARTIAL:
        display_name = _partial_name(person.name) or WITHHELD_DISPLAY_NAME
    else:
        display_name = _clean(person.name) or WITHHELD_DISPLAY_NAME

    if display_name == WITHHELD_DISPLAY_NAME:
        # No name to publish at all — fall back to the anonymous shape
        # rather than publishing age, occupation and father's name
        # next to a placeholder.
        identity_level = PublicIdentityLevel.ANONYMOUS

    if identity_level == PublicIdentityLevel.ANONYMOUS:
        father_name = None
        age = None
        occupation = None
    else:
        father_name = _father_name(person)
        age = _age(person, anchor.date_of_abduction if anchor else None)
        occupation = _clean(person.occupation)

    if identity_level == PublicIdentityLevel.ANONYMOUS:
        withheld.append(WITHHELD_IDENTITY)

    # --- Location --------------------------------------------------------
    precision = _effective_location_precision(person)
    if precision == 'withheld' or WITHHELD_LOCATION in blocked:
        location = None
        withheld.append(WITHHELD_LOCATION)
    else:
        parts = [
            _clean(getattr(person, field))
            for field in LOCATION_DISCLOSURE[precision]
        ]
        location = {
            'country': _clean(person.country),
            'display': ', '.join(part for part in parts if part) or None,
            'precision': precision,
        }

    # --- Incident --------------------------------------------------------
    incident = {
        'date': None,
        'time': None,
        'place': None,
        'abductors': None,
        'detail': None,
    }
    if anchor is not None:
        incident['date'] = (
            anchor.date_of_abduction.isoformat() if anchor.date_of_abduction
            else (anchor.date_start.isoformat() if anchor.date_start else None)
        )
        incident['time'] = (
            anchor.time_of_abduction.strftime('%H:%M')
            if anchor.time_of_abduction else None
        )
        incident['place'] = (
            _clean(anchor.place_of_abduction)
            or _clean(anchor.rough_location)
            or _clean(person.rough_location)
        )
        incident['abductors'] = _clean(anchor.abductors)
        incident['detail'] = (
            _clean(anchor.official_reason) or _clean(anchor.suspected_reason)
        )

    # --- Photo -----------------------------------------------------------
    # The photo key is OMITTED, not nulled: a card that shows a
    # placeholder where a photograph should be invites the reader to
    # assume the photograph exists. It exists — it is just not ours to
    # publish.
    photo = None
    if person.profile_image:
        photo_allowed = (
            person.photograph_public == 'yes'
            and WITHHELD_PHOTO not in blocked
            and identity_level != PublicIdentityLevel.ANONYMOUS
        )
        if photo_allowed:
            photo = {
                'url': _absolute_media_url(person.profile_image.url, request),
                'alt': '',
            }
        else:
            withheld.append(WITHHELD_PHOTO)

    # --- Verification ----------------------------------------------------
    verification_level = (
        _clean(person.public_verification_level)
        or QUALITY_TIER_TO_VERIFICATION.get(person.quality_tier)
    )
    verification = {
        'level': verification_level,
        'label': VERIFICATION_LABELS.get(verification_level),
    }

    # --- Source ----------------------------------------------------------
    source_label = _clean(anchor.source_attribution) if anchor else None
    source_label = source_label or _clean(person.authoritative_source)

    # --- Exportable ------------------------------------------------------
    # Computed on the server, from the consent flags only. The client
    # cannot influence it, and the conditions are the ones the
    # documentation form (Section K) collects:
    #   - the case is published;
    #   - consent for public publication is on file;
    #   - the identity is published at full or partial level;
    #   - the photograph is cleared for publication. A case with no
    #     photograph at all still needs the flag cleared, because the
    #     flag is the record of the decision, not a description of
    #     what happens to be attached.
    exportable = bool(
        person.is_published
        and person.consent_public_publication == 'yes'
        and identity_level in (
            PublicIdentityLevel.FULL, PublicIdentityLevel.PARTIAL,
        )
        and person.photograph_public == 'yes'
    )

    status_label = PERSON_STATUS_LABELS.get(person.current_status, person.current_status)

    payload = {
        'schema_version': 1,
        'reference': _clean(person.public_reference),
        'generated_date': timezone.localdate().isoformat(),
        'headline': _headline(person) or status_label,
        'title': display_name,
        'status': person.current_status,
        'status_label': status_label,
        'identity': {
            'display_name': display_name,
            'father_name': father_name,
            'age': age,
            'occupation': occupation,
        },
        'incident': incident,
        'categories': [category.name for category in person.categories.all()],
        'verification': verification,
        'source_label': source_label,
        'exportable': exportable,
        'withheld': withheld,
    }
    if location is not None:
        payload['location'] = location
    if photo is not None:
        payload['photo'] = photo
    # A restriction line and the block it withholds can name the same
    # item ("precise location"); the reader should see it once.
    payload['withheld'] = list(dict.fromkeys(withheld))
    return payload


# --- Serializers ---------------------------------------------------------
#
# The nested serializers below exist for the OpenAPI schema. The
# payload itself is assembled by `build_card_payload` — it is not a
# ModelSerializer projection, because what a card may show is a
# function of the consent flags, not of the model columns.


class CaseCardIdentitySerializer(serializers.Serializer):
    display_name = serializers.CharField(read_only=True)
    father_name = serializers.CharField(read_only=True, allow_null=True)
    age = serializers.IntegerField(read_only=True, allow_null=True)
    occupation = serializers.CharField(read_only=True, allow_null=True)


class CaseCardLocationSerializer(serializers.Serializer):
    country = serializers.CharField(read_only=True)
    display = serializers.CharField(read_only=True, allow_null=True)
    precision = serializers.ChoiceField(
        read_only=True, choices=LOCATION_PRECISION_VALUES,
    )


class CaseCardIncidentSerializer(serializers.Serializer):
    date = serializers.CharField(read_only=True, allow_null=True)
    time = serializers.CharField(read_only=True, allow_null=True)
    place = serializers.CharField(read_only=True, allow_null=True)
    abductors = serializers.CharField(read_only=True, allow_null=True)
    detail = serializers.CharField(read_only=True, allow_null=True)


class CaseCardPhotoSerializer(serializers.Serializer):
    url = serializers.URLField(read_only=True)
    alt = serializers.CharField(read_only=True)


class CaseCardVerificationSerializer(serializers.Serializer):
    level = serializers.CharField(read_only=True, allow_null=True)
    label = serializers.CharField(read_only=True, allow_null=True)


class CaseCardPayloadSerializer(serializers.Serializer):
    """The masked card payload.

    Read-only by construction: every field is `read_only` and the
    endpoint only answers GET. `to_internal_value` refuses input
    outright so the contract holds wherever the serializer is used.

    Two keys are NOT `read_only`: `location` and `photo`. They are
    genuinely ABSENT from the payload when they are withheld — that
    absence is the contract ("this was withheld", not "this was
    empty"). drf-spectacular marks every read-only field as required
    in the generated schema, so a `read_only` declaration here would
    publish a schema that promises a `photo` the payload does not
    contain, and a consumer that trusted it would read
    `payload.photo.url` on a card whose photograph was withheld.
    `required=False` puts both keys in the schema as optional, which
    is what they are. Input is still refused — `to_internal_value`
    raises before any field is read.
    """

    schema_version = serializers.IntegerField(read_only=True)
    reference = serializers.CharField(read_only=True, allow_null=True)
    generated_date = serializers.CharField(read_only=True)
    headline = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    status_label = serializers.CharField(read_only=True)
    identity = CaseCardIdentitySerializer(read_only=True)
    location = CaseCardLocationSerializer(required=False)
    incident = CaseCardIncidentSerializer(read_only=True)
    photo = CaseCardPhotoSerializer(required=False)
    categories = serializers.ListField(
        child=serializers.CharField(), read_only=True,
    )
    verification = CaseCardVerificationSerializer(read_only=True)
    source_label = serializers.CharField(read_only=True, allow_null=True)
    exportable = serializers.BooleanField(read_only=True)
    withheld = serializers.ListField(
        child=serializers.CharField(), read_only=True,
    )

    def to_representation(self, instance):
        return build_card_payload(instance, self.context.get('request'))

    def to_internal_value(self, data):
        raise serializers.ValidationError(
            'The case card is read-only — it accepts no input.',
        )
