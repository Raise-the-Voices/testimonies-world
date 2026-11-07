"""Tests for the Case Information Card endpoint.

`GET /api/persons/{id}/card/` — the masked, publication-facing
projection of a case.

The masking matrix IS the contract, so it is the bulk of this suite:
one test per row, each asserting the payload a caller actually
receives rather than the serializer's internals. The rest covers the
field derivations and the pinned export schema.

Real DB tests, no mocks (per SYSTEM_RULES §7).
"""

import json
from datetime import date, time
from pathlib import Path

from django.conf import settings as dj_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from cases.card.export import EXPORT_SCHEMA, CaseCardExportSerializer
from cases.card.serializers import (
    CaseCardPayloadSerializer,
    build_card_payload,
)
from cases.models import (
    AuditLog, CaseCategory, FamilyRelationship, Media, Person, Report,
)
from cases.serializers import PersonDetailSerializer
from cases.tests import make_user
from testimonies.test_base import BaseTestCase


# Fields that must never reach a card, in any form. The endpoint is
# the one payload that leaves the platform, so the deny-list is
# asserted on keys AND on string values — a private value smuggled
# into a free-text field is as bad as a private column.
DENY_LIST = [
    'medical_notes',
    'precise_location',
    'reporter_name',
    'reporter_contact',
    'internal_notes',
    'risk_level',
    'risk_concerns',
    'aliases',
    'date_of_birth',
    'authoritative_url',
]


def make_person(**kwargs):
    """A case that is cleared for publication on every axis.

    Every masking test starts from this and turns ONE flag off, so a
    failing assertion points at the rule that broke rather than at
    the state of the fixture.
    """
    defaults = {
        'name': 'Ahmed Al-Hassan',
        'country': 'Egypt',
        'current_status': Person.Status.DISAPPEARED,
        'is_published': True,
        'consent_public_publication': 'yes',
        'public_identity_level': 'full',
        'public_location_level': 'province',
        'photograph_public': 'yes',
    }
    defaults.update(kwargs)
    return Person.objects.create(**defaults)


def attach_image(person, name='face.jpg'):
    """Give the person a profile image in the public media tree."""
    person.profile_image.save(
        name, SimpleUploadedFile(name, b'jpeg', 'image/jpeg'), save=True,
    )
    return person


class CardTestCase(BaseTestCase):
    """Shared plumbing: an anonymous client and a card URL helper."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def attach_image(self, person, name='face.jpg'):
        """Give the person a profile image, and clean the file up."""
        attach_image(person, name)
        self.addCleanup(person.profile_image.delete, save=False)
        return person

    def card_url(self, person):
        return f'/api/persons/{person.pk}/card/'

    def get_card(self, person):
        response = self.client.get(self.card_url(person))
        self.assertEqual(response.status_code, 200)
        return response.json()


# ---------------------------------------------------------------------------
# The masking matrix — one test per row.
# ---------------------------------------------------------------------------
class CardMaskingTests(CardTestCase):
    def test_unpublished_case_is_404_for_anonymous_caller(self):
        person = make_person(is_published=False)
        response = self.client.get(self.card_url(person))
        self.assertEqual(response.status_code, 404)

    def test_unpublished_case_is_not_exportable_for_authenticated_caller(self):
        person = make_person(is_published=False)
        self.client.force_login(make_user('adv', in_group='Advocate'))
        payload = self.get_card(person)
        self.assertFalse(payload['exportable'])

    def test_consent_for_publication_blocks_export(self):
        person = make_person(consent_public_publication='no')
        payload = self.get_card(person)
        self.assertFalse(payload['exportable'])

    def test_blank_consent_for_publication_follows_the_public_case_page(self):
        # The card publishes what the public page publishes. A blank
        # consent flag is the absence of a decision, not a refusal, so
        # it does not block the download.
        person = make_person(consent_public_publication='')
        payload = self.get_card(person)
        self.assertTrue(payload['exportable'])

    def test_blank_identity_level_publishes_the_full_name(self):
        # The public case page shows the full name. A blank identity
        # level is the absence of a decision, so the card shows what
        # the page shows.
        person = make_person(
            public_identity_level='', age_at_incident=34,
            occupation='Teacher',
        )
        payload = self.get_card(person)
        self.assertEqual(payload['identity']['display_name'], 'Ahmed Al-Hassan')
        self.assertEqual(payload['title'], 'Ahmed Al-Hassan')
        self.assertEqual(payload['identity']['age'], 34)
        self.assertEqual(payload['identity']['occupation'], 'Teacher')
        self.assertTrue(payload['exportable'])
        self.assertNotIn('identity', payload['withheld'])

    def test_partial_identity_level_publishes_first_name_and_initial(self):
        person = make_person(
            public_identity_level='partial', age_at_incident=34,
            occupation='Teacher',
        )
        payload = self.get_card(person)
        self.assertEqual(payload['identity']['display_name'], 'Ahmed A.')
        self.assertEqual(payload['title'], 'Ahmed A.')
        self.assertEqual(payload['identity']['age'], 34)
        self.assertEqual(payload['identity']['occupation'], 'Teacher')

    def test_partial_identity_level_without_a_name_falls_back_to_withheld(self):
        person = make_person(public_identity_level='partial', name='')
        payload = self.get_card(person)
        self.assertEqual(payload['identity']['display_name'], 'Identity withheld')
        # The poster is still downloadable: it says the identity is
        # withheld, which is a fact about the case, not a failure.
        self.assertTrue(payload['exportable'])

    def test_full_identity_level_publishes_the_full_name(self):
        person = make_person(public_identity_level='full')
        payload = self.get_card(person)
        self.assertEqual(payload['identity']['display_name'], 'Ahmed Al-Hassan')
        self.assertEqual(payload['title'], 'Ahmed Al-Hassan')

    def test_photo_is_omitted_when_not_cleared_for_publication(self):
        person = self.attach_image(make_person(photograph_public='no'))
        payload = self.get_card(person)
        self.assertNotIn('photo', payload)
        # A withheld photograph is named in `withheld` and nowhere
        # else; it does not stop the poster from being downloaded.
        self.assertTrue(payload['exportable'])
        self.assertIn('photograph', payload['withheld'])

    def test_photo_is_omitted_when_the_clearance_is_pending(self):
        person = self.attach_image(make_person(photograph_public='pending'))
        payload = self.get_card(person)
        self.assertNotIn('photo', payload)
        self.assertIn('photograph', payload['withheld'])

    def test_blank_photograph_clearance_publishes_the_photo(self):
        # The profile image is served from the public media tree, so
        # the public case page already shows it.
        person = self.attach_image(make_person(photograph_public=''))
        payload = self.get_card(person)
        self.assertIn('photo', payload)
        self.assertNotIn('photograph', payload['withheld'])

    def test_photo_is_omitted_when_the_identity_is_anonymous(self):
        person = self.attach_image(make_person(public_identity_level='anonymous'))
        payload = self.get_card(person)
        self.assertNotIn('photo', payload)
        self.assertIn('photograph', payload['withheld'])

    def test_photo_is_published_when_it_is_cleared(self):
        person = self.attach_image(make_person(photograph_public='yes'))
        payload = self.get_card(person)
        self.assertIn('photo', payload)
        self.assertIn('/public-media/profiles/face', payload['photo']['url'])
        self.assertTrue(payload['photo']['url'].endswith('.jpg'))
        self.assertEqual(payload['photo']['alt'], '')

    def test_blank_location_level_shows_the_public_case_page_location(self):
        # The public case page shows the district and the coarse
        # place. A blank level is the absence of a decision, so the
        # card shows the same.
        person = make_person(
            public_location_level='', province='Alexandria Governorate',
            district='Alexandria', rough_location='Smouha',
        )
        payload = self.get_card(person)
        self.assertEqual(payload['location']['country'], 'Egypt')
        self.assertEqual(payload['location']['precision'], 'city')
        self.assertEqual(payload['location']['display'], 'Alexandria, Smouha')

    def test_province_location_level_shows_the_country_only(self):
        # The province level discloses the country and nothing finer.
        person = make_person(
            public_location_level='province', province='Alexandria Governorate',
            district='Alexandria', rough_location='Smouha',
        )
        payload = self.get_card(person)
        self.assertEqual(payload['location']['precision'], 'province')
        self.assertEqual(payload['location']['country'], 'Egypt')
        self.assertIsNone(payload['location']['display'])

    def test_district_location_level_shows_the_district(self):
        person = make_person(
            public_location_level='district', province='Alexandria Governorate',
            district='Alexandria', rough_location='Smouha',
        )
        payload = self.get_card(person)
        self.assertEqual(payload['location']['precision'], 'district')
        self.assertEqual(payload['location']['display'], 'Alexandria')
        self.assertNotIn('Smouha', payload['location']['display'])

    def test_city_location_level_adds_the_rough_location(self):
        person = make_person(
            public_location_level='city', province='Alexandria Governorate',
            district='Alexandria', rough_location='Smouha',
        )
        payload = self.get_card(person)
        self.assertEqual(payload['location']['precision'], 'city')
        self.assertEqual(payload['location']['display'], 'Alexandria, Smouha')

    def test_do_not_disclose_location_omits_the_location(self):
        person = make_person(public_location_level='do_not_disclose')
        payload = self.get_card(person)
        self.assertNotIn('location', payload)
        self.assertIn('precise location', payload['withheld'])

    def test_restriction_on_the_location_omits_the_location(self):
        person = make_person(
            information_restricted_from_publication='precise location',
        )
        payload = self.get_card(person)
        self.assertNotIn('location', payload)
        self.assertIn('precise location', payload['withheld'])

    def test_restriction_on_the_name_withholds_the_identity(self):
        person = make_person(
            information_restricted_from_publication='family names',
            age_at_incident=34, occupation='Teacher',
        )
        payload = self.get_card(person)
        self.assertEqual(payload['identity']['display_name'], 'Identity withheld')
        self.assertIsNone(payload['identity']['age'])
        self.assertIsNone(payload['identity']['occupation'])
        self.assertIn('identity', payload['withheld'])

    def test_restriction_on_the_photograph_omits_the_photo(self):
        person = self.attach_image(make_person(
            information_restricted_from_publication='photograph',
        ))
        payload = self.get_card(person)
        self.assertNotIn('photo', payload)
        self.assertIn('photograph', payload['withheld'])

    def test_unmatched_restriction_line_blocks_nothing_but_is_reported(self):
        person = make_person(
            information_restricted_from_publication='medical history',
        )
        payload = self.get_card(person)
        self.assertIn('location', payload)
        # The line itself is not repeated — it is free text a human
        # typed, and it may name the value being withheld.
        self.assertIn('other restricted information', payload['withheld'])
        self.assertNotIn('medical history', json.dumps(payload))

    def test_restriction_line_never_reaches_the_payload(self):
        # The Section K field is free text a human typed. It routinely
        # names the very value that is being withheld ("precise
        # location: 12 Rue de la Paix"). `withheld` says WHAT was
        # taken out — copying the line would publish the value inside
        # the array that exists to say it was withheld.
        person = make_person(
            information_restricted_from_publication=(
                'precise location: 12 Rue de la Paix, Beirut'
            ),
            precise_location='12 Rue de la Paix, Beirut',
        )
        payload = self.get_card(person)
        blob = json.dumps(payload)
        self.assertNotIn('12 Rue de la Paix', blob)
        self.assertNotIn('Beirut', blob)
        self.assertIn('precise location', payload['withheld'])
        self.assertNotIn('location', payload)

    def test_restriction_line_on_a_name_never_reaches_the_payload(self):
        person = make_person(
            information_restricted_from_publication=(
                "the mother's full name must not appear"
            ),
            age_at_incident=34, occupation='Teacher',
        )
        payload = self.get_card(person)
        blob = json.dumps(payload)
        self.assertNotIn('mother', blob)
        self.assertIn('identity', payload['withheld'])
        self.assertEqual(payload['identity']['display_name'], 'Identity withheld')

    def test_restriction_line_naming_two_items_withholds_both(self):
        person = make_person(
            information_restricted_from_publication='name and photograph',
        )
        payload = self.get_card(person)
        self.assertIn('identity', payload['withheld'])
        self.assertIn('photograph', payload['withheld'])

    def test_card_masks_a_person_record_that_is_otherwise_complete(self):
        # The card is built from the case file, not from the person
        # record the browser already holds. Where the record carries
        # MORE than the card may show — here the identity is
        # explicitly anonymous — the browser must never be able to
        # re-derive the card from it.
        person = self.attach_image(make_person(
            public_identity_level='anonymous', age_at_incident=34,
            occupation='Teacher', rough_location='Smouha',
        ))
        father = Person.objects.create(
            name='Yusuf Al-Hassan', country='Egypt',
            gender=Person.Gender.MALE,
        )
        FamilyRelationship.objects.create(
            person_a=person, person_b=father,
            relationship_type=FamilyRelationship.RelationType.PARENT,
        )

        detail = PersonDetailSerializer(person).data
        self.assertEqual(detail['name'], 'Ahmed Al-Hassan')
        self.assertEqual(detail['age_at_incident'], 34)

        payload = self.get_card(person)
        blob = json.dumps(payload)
        self.assertEqual(payload['title'], 'Identity withheld')
        for secret in ('Ahmed Al-Hassan', 'Yusuf Al-Hassan', 'Teacher'):
            self.assertNotIn(secret, blob)
        self.assertNotIn('photo', payload)

    def test_private_report_contributes_nothing(self):
        person = make_person()
        Report.objects.create(
            person=person, narrative='public', is_private=False,
            date_of_abduction=date(2025, 1, 10),
            place_of_abduction='Public place',
            official_reason='Public reason',
            abductors='Public abductors',
        )
        Report.objects.create(
            person=person, narrative='private', is_private=True,
            date_of_abduction=date(2024, 1, 1),
            place_of_abduction='Secret place',
            official_reason='Secret reason',
            abductors='Secret abductors',
        )
        payload = self.get_card(person)
        self.assertEqual(payload['incident']['date'], '2025-01-10')
        self.assertEqual(payload['incident']['place'], 'Public place')
        self.assertEqual(payload['incident']['detail'], 'Public reason')
        self.assertNotIn('Secret', json.dumps(payload))

    def test_private_report_contributes_nothing_for_an_advocate_either(self):
        # The card is the same masked payload for every role — an
        # advocate reading the card is not reading the case file.
        person = make_person()
        Report.objects.create(
            person=person, narrative='public', is_private=False,
            date_of_abduction=date(2025, 1, 10),
        )
        Report.objects.create(
            person=person, narrative='private', is_private=True,
            date_of_abduction=date(2024, 1, 1),
            place_of_abduction='Secret place',
        )
        self.client.force_login(make_user('adv', in_group='Advocate'))
        payload = self.get_card(person)
        self.assertEqual(payload['incident']['date'], '2025-01-10')
        self.assertNotIn('Secret', json.dumps(payload))

    def test_non_public_media_is_excluded(self):
        person = make_person()
        Media.objects.create(
            person=person, media_type='photo', visibility='restricted',
            url='https://example.org/restricted-photo.jpg',
        )
        Media.objects.create(
            person=person, media_type='document', visibility='sensitive',
            url='https://example.org/sensitive-document.pdf',
        )
        payload = self.get_card(person)
        self.assertNotIn('restricted-photo', json.dumps(payload))
        self.assertNotIn('sensitive-document', json.dumps(payload))


# ---------------------------------------------------------------------------
# The endpoint's own contract.
# ---------------------------------------------------------------------------
class CardAccessTests(CardTestCase):
    def test_anonymous_request_for_an_unpublished_person_is_404(self):
        person = make_person(is_published=False)
        response = self.client.get(self.card_url(person))
        self.assertEqual(response.status_code, 404)

    def test_anonymous_request_for_a_published_person_is_200(self):
        person = make_person()
        response = self.client.get(self.card_url(person))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['schema_version'], 1)

    def test_card_writes_an_audit_log_row(self):
        person = make_person()
        self.client.get(self.card_url(person))
        rows = AuditLog.objects.filter(
            target_type='person', target_id=person.pk,
            action=AuditLog.Action.VIEWED,
        )
        self.assertEqual(rows.count(), 1)

    def test_a_404_writes_no_audit_log_row(self):
        person = make_person(is_published=False)
        self.client.get(self.card_url(person))
        self.assertFalse(
            AuditLog.objects.filter(
                target_type='person', target_id=person.pk,
                action=AuditLog.Action.VIEWED,
            ).exists()
        )

    def test_card_is_read_only(self):
        person = make_person()
        self.client.force_login(make_user('vol', in_group='Volunteer'))
        response = self.client.post(self.card_url(person), {}, format='json')
        self.assertEqual(response.status_code, 405)

    def test_anonymous_write_is_refused(self):
        person = make_person()
        response = self.client.post(self.card_url(person), {}, format='json')
        self.assertIn(response.status_code, (403, 405))

    def test_payload_carries_no_private_field(self):
        person = make_person(
            medical_notes='diabetes and hypertension',
            precise_location='12 Rue de la Paix',
            aliases='The Carpenter',
            date_of_birth=date(1991, 4, 2),
            authoritative_url='https://elsewhere.example.org/case/1',
        )
        Report.objects.create(
            person=person, narrative='n', is_private=False,
            reporter_name='A Reporter', reporter_contact='+20 000 000 000',
            risk_level='high', internal_notes='internal note',
            date_of_abduction=date(2025, 1, 10),
        )
        payload = self.get_card(person)
        blob = json.dumps(payload)
        for field in DENY_LIST:
            self.assertNotIn(field, payload, f'{field} leaked as a key')
            self.assertNotIn(field, blob, f'{field} leaked as a value')
        # And the values themselves are gone, not just the column names.
        for secret in (
            'diabetes and hypertension', '12 Rue de la Paix',
            'The Carpenter', 'A Reporter', 'internal note',
        ):
            self.assertNotIn(secret, blob)


# ---------------------------------------------------------------------------
# The write path for the Section K field.
# ---------------------------------------------------------------------------
class CardRestrictionWriteTests(CardTestCase):
    """`information_restricted_from_publication` is stored as plain text.

    It is free text written by a human and it is read back on the case
    file, so it is HTML-stripped on save like every other
    documentation-form field. It also decides what the card may show,
    which is why it is not a field the card can afford to carry raw
    markup in.
    """

    def test_restriction_field_is_html_stripped_on_save(self):
        self.client.force_login(make_user('cardvol', in_group='Volunteer'))
        response = self.client.post('/api/persons/', {
            'name': 'Restricted Person',
            'country': 'Egypt',
            'current_status': 'detained',
            'medical_status': 'unknown',
            'information_restricted_from_publication': (
                '<b>precise location</b><script>alert(1)</script>'
            ),
        }, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        row = Person.objects.get(pk=response.json()['id'])
        self.assertNotIn('<b>', row.information_restricted_from_publication)
        self.assertNotIn('<script', row.information_restricted_from_publication)
        self.assertIn('precise location', row.information_restricted_from_publication)


# ---------------------------------------------------------------------------
# Field derivations.
# ---------------------------------------------------------------------------
class CardFieldDerivationTests(CardTestCase):
    def test_reference_is_the_public_reference(self):
        person = make_person(public_reference='ED-2026-0042')
        payload = self.get_card(person)
        self.assertEqual(payload['reference'], 'ED-2026-0042')

    def test_reference_is_null_when_the_case_has_none(self):
        person = make_person()
        payload = self.get_card(person)
        self.assertIsNone(payload['reference'])

    def test_generated_date_is_today(self):
        person = make_person()
        payload = self.get_card(person)
        self.assertEqual(
            payload['generated_date'], timezone.localdate().isoformat(),
        )

    def test_status_and_status_label(self):
        person = make_person(current_status=Person.Status.ONGOING_ENFORCED_DISAPPEARANCE)
        payload = self.get_card(person)
        self.assertEqual(payload['status'], 'ongoing_enforced_disappearance')
        self.assertEqual(
            payload['status_label'], 'Ongoing alleged enforced disappearance',
        )

    def test_headline_comes_from_the_most_serious_category(self):
        person = make_person()
        person.categories.add(
            CaseCategory.objects.create(name='Arbitrary detention'),
            CaseCategory.objects.create(name='Enforced disappearance'),
        )
        payload = self.get_card(person)
        self.assertEqual(payload['headline'], 'Enforced Disappearance')

    def test_headline_falls_back_to_the_status_label(self):
        person = make_person(current_status=Person.Status.DETAINED)
        payload = self.get_card(person)
        self.assertEqual(payload['headline'], 'Detained')

    def test_categories_are_listed_as_they_are_stored(self):
        person = make_person()
        person.categories.add(
            CaseCategory.objects.create(name='Enforced disappearance'),
            CaseCategory.objects.create(name='Torture'),
        )
        payload = self.get_card(person)
        self.assertEqual(
            sorted(payload['categories']),
            ['Enforced disappearance', 'Torture'],
        )

    def test_age_is_the_recorded_age_at_incident(self):
        person = make_person(age_at_incident=34)
        payload = self.get_card(person)
        self.assertEqual(payload['identity']['age'], 34)

    def test_age_is_derived_from_the_date_of_birth_at_the_incident(self):
        person = make_person(date_of_birth=date(1991, 4, 2))
        Report.objects.create(
            person=person, narrative='n', is_private=False,
            date_of_abduction=date(2025, 11, 3),
        )
        payload = self.get_card(person)
        self.assertEqual(payload['identity']['age'], 34)

    def test_age_is_null_when_nothing_records_it(self):
        person = make_person()
        payload = self.get_card(person)
        self.assertIsNone(payload['identity']['age'])

    def test_father_name_comes_from_a_male_parent(self):
        person = make_person()
        father = Person.objects.create(
            name='Yusuf Al-Hassan', country='Egypt',
            gender=Person.Gender.MALE,
        )
        FamilyRelationship.objects.create(
            person_a=person, person_b=father,
            relationship_type=FamilyRelationship.RelationType.PARENT,
        )
        payload = self.get_card(person)
        self.assertEqual(payload['identity']['father_name'], 'Yusuf Al-Hassan')

    def test_father_name_is_null_when_the_parent_is_not_male(self):
        # The relationship only says "parent" — guessing would put a
        # mother's name on a line labelled "Father".
        person = make_person()
        mother = Person.objects.create(
            name='Amina Al-Hassan', country='Egypt',
            gender=Person.Gender.FEMALE,
        )
        FamilyRelationship.objects.create(
            person_a=person, person_b=mother,
            relationship_type=FamilyRelationship.RelationType.PARENT,
        )
        payload = self.get_card(person)
        self.assertIsNone(payload['identity']['father_name'])

    def test_verification_uses_the_published_level(self):
        person = make_person(public_verification_level='level_4_documented')
        payload = self.get_card(person)
        self.assertEqual(payload['verification']['level'], 'level_4_documented')
        self.assertEqual(payload['verification']['label'], 'Documented')

    def test_verification_is_derived_from_the_quality_tier(self):
        person = make_person(quality_tier=1)
        payload = self.get_card(person)
        self.assertEqual(payload['verification']['level'], 'level_3_corroborated')
        self.assertEqual(payload['verification']['label'], 'Corroborated')

    def test_verification_is_null_when_nothing_records_it(self):
        person = make_person()
        payload = self.get_card(person)
        self.assertIsNone(payload['verification']['level'])
        self.assertIsNone(payload['verification']['label'])

    def test_source_label_comes_from_the_report(self):
        person = make_person()
        Report.objects.create(
            person=person, narrative='n', is_private=False,
            source_attribution='Family', date_of_abduction=date(2025, 1, 10),
        )
        payload = self.get_card(person)
        self.assertEqual(payload['source_label'], 'Family')

    def test_source_label_falls_back_to_the_authoritative_source(self):
        person = make_person(authoritative_source='AAPP')
        payload = self.get_card(person)
        self.assertEqual(payload['source_label'], 'AAPP')

    def test_source_label_is_null_when_nothing_records_it(self):
        person = make_person()
        payload = self.get_card(person)
        self.assertIsNone(payload['source_label'])

    def test_incident_date_is_the_earliest_abduction(self):
        # The reports are deliberately ordered against the answer:
        # Report.Meta.ordering sorts by -date_start, so the report with
        # the LATEST legacy date comes first. Taking reports[0] would
        # return 2025-11-01 instead of 2024-03-03.
        person = make_person()
        Report.objects.create(
            person=person, narrative='n', is_private=False,
            date_start=date(2025, 12, 1), date_of_abduction=date(2025, 11, 1),
            place_of_abduction='Later place',
        )
        Report.objects.create(
            person=person, narrative='n', is_private=False,
            date_start=date(2024, 5, 5), date_of_abduction=date(2024, 3, 3),
            place_of_abduction='Earliest place',
        )
        Report.objects.create(
            person=person, narrative='n', is_private=False,
            date_start=date(2024, 8, 8), date_of_abduction=date(2024, 7, 7),
            place_of_abduction='Middle place',
        )
        payload = self.get_card(person)
        self.assertEqual(payload['incident']['date'], '2024-03-03')
        self.assertEqual(payload['incident']['place'], 'Earliest place')

    def test_incident_date_falls_back_to_the_legacy_date_start(self):
        person = make_person()
        Report.objects.create(
            person=person, narrative='n', is_private=False,
            date_start=date(2023, 4, 4), rough_location='Legacy place',
        )
        payload = self.get_card(person)
        self.assertEqual(payload['incident']['date'], '2023-04-04')
        self.assertEqual(payload['incident']['place'], 'Legacy place')

    def test_incident_carries_the_time_and_the_abductors(self):
        person = make_person()
        Report.objects.create(
            person=person, narrative='n', is_private=False,
            date_of_abduction=date(2025, 1, 10), time_of_abduction=time(14, 30),
            place_of_abduction='Alexandria', abductors='Security forces',
            suspected_reason='suspected', official_reason='official',
        )
        payload = self.get_card(person)
        self.assertEqual(payload['incident']['time'], '14:30')
        self.assertEqual(payload['incident']['abductors'], 'Security forces')
        self.assertEqual(payload['incident']['detail'], 'official')

    def test_incident_is_empty_without_a_report(self):
        person = make_person()
        payload = self.get_card(person)
        self.assertEqual(
            payload['incident'],
            {'date': None, 'time': None, 'place': None,
             'abductors': None, 'detail': None},
        )

    def test_exportable_is_true_for_a_fully_cleared_case(self):
        person = make_person()
        payload = self.get_card(person)
        self.assertTrue(payload['exportable'])


# ---------------------------------------------------------------------------
# The generated schema.
# ---------------------------------------------------------------------------
class CardOpenApiTests(CardTestCase):
    """The OpenAPI schema must match the shape of the payload.

    `location` and `photo` are ABSENT from the payload when they are
    withheld — that absence is the contract. drf-spectacular marks
    every read-only field as required, so a `read_only` declaration on
    those two would publish a schema promising keys the payload does
    not carry, and a consumer that trusted it would read
    `payload.photo.url` on a card whose photograph was withheld.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from drf_spectacular.generators import SchemaGenerator
        cls.schema = SchemaGenerator().get_schema(request=None, public=True)

    def _component(self):
        return self.schema['components']['schemas']['CaseCardPayload']

    def test_the_optional_keys_are_optional_in_the_schema(self):
        component = self._component()
        self.assertIn('location', component['properties'])
        self.assertIn('photo', component['properties'])
        self.assertNotIn('location', component['required'])
        self.assertNotIn('photo', component['required'])

    def test_the_keys_that_are_always_present_stay_required(self):
        component = self._component()
        for key in (
            'schema_version', 'reference', 'generated_date', 'headline',
            'title', 'status', 'status_label', 'identity', 'incident',
            'categories', 'verification', 'source_label', 'exportable',
            'withheld',
        ):
            self.assertIn(key, component['required'], key)

    def test_the_schema_required_list_matches_the_export_schema(self):
        # Two contracts, one shape: the OpenAPI schema and the pinned
        # JSON Schema must agree about what is always there.
        self.assertEqual(
            sorted(self._component()['required']),
            sorted(EXPORT_SCHEMA['required']),
        )


# ---------------------------------------------------------------------------
# The pinned export contract.
# ---------------------------------------------------------------------------
class CardSchemaPinTests(CardTestCase):
    def test_export_schema_file_matches_the_python_dict(self):
        # The on-disk schema is generated from EXPORT_SCHEMA; the two
        # must not drift. Byte-for-byte, not just semantically — a
        # reformatted file would still parse the same but would make
        # the next regeneration produce a noisy diff.
        schema_path = Path(dj_settings.BASE_DIR) / 'cases/card/export_schema.json'
        on_disk_text = schema_path.read_text(encoding='utf-8')
        self.assertEqual(
            on_disk_text,
            json.dumps(EXPORT_SCHEMA, indent=2, ensure_ascii=False) + '\n',
        )
        self.assertEqual(json.loads(on_disk_text), EXPORT_SCHEMA)

    def test_export_schema_id_is_versioned(self):
        self.assertEqual(
            EXPORT_SCHEMA['$id'],
            'https://testimonies.world/schemas/case-card-v1.json',
        )

    def test_export_schema_pins_schema_version_one(self):
        self.assertEqual(EXPORT_SCHEMA['properties']['schema_version']['const'], 1)

    def test_payload_validates_against_the_export_schema(self):
        import jsonschema
        person = make_person(
            public_reference='ED-2026-0042', age_at_incident=34,
            occupation='Teacher', public_location_level='city',
            province='Alexandria Governorate', district='Alexandria',
            rough_location='Smouha', quality_tier=1,
        )
        person.categories.add(CaseCategory.objects.create(name='Enforced disappearance'))
        Report.objects.create(
            person=person, narrative='n', is_private=False,
            date_of_abduction=date(2025, 1, 10), time_of_abduction=time(14, 30),
            place_of_abduction='Alexandria', abductors='Security forces',
            official_reason='official', source_attribution='Family',
        )
        payload = build_card_payload(person)
        jsonschema.validate(payload, EXPORT_SCHEMA)

    def test_export_serializer_produces_the_same_payload(self):
        person = make_person(age_at_incident=34)
        payload = CaseCardExportSerializer(person).data
        self.assertEqual(payload['schema_version'], 1)
        self.assertEqual(payload['identity']['age'], 34)

    def test_payload_serializer_refuses_input(self):
        serializer = CaseCardPayloadSerializer(data={'title': 'Injected'})
        self.assertFalse(serializer.is_valid())
