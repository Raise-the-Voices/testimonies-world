"""Person extensions for Case Documentation Form Sections A, B, D, K, N, P.

Adds 33 Person fields plus an AlterField that extends the existing
`Person.current_status` enum with the Section D vocabulary
(`ongoing_enforced_disappearance`, `found_alive`, `found_dead`,
`case_closed`, `other`). Legacy rows are unaffected — both the new
columns and the new enum values default to NULL / empty string /
unset, so existing rows pass validation unchanged.

The `case_id` UUIDField is added in three steps — see 0006_hand_uuid.md
style note in the module docstring of this file's predecessor:
  1. AddField with null=True, no default.
  2. RunPython backfills UUIDs for legacy rows.
  3. AlterField makes the column NOT NULL + UNIQUE + uuid.uuid4 default.

The 3-step dance avoids the SQLite / shared-host Postgres issue where
a callable default on ALTER TABLE assigns the same value to every
existing row, defeating the eventual UNIQUE constraint.
"""

import django.db.models.deletion
import uuid

from django.conf import settings
from django.db import migrations, models


def _backfill_case_id(apps, schema_editor):
    """Generate a unique UUID for every legacy Person row.

    Done in Python so we don't depend on Postgres-only `gen_random_uuid()`.
    """
    Person = apps.get_model('cases', 'Person')
    for p in Person.objects.filter(case_id__isnull=True).iterator():
        p.case_id = uuid.uuid4()
        p.save(update_fields=['case_id'])


def _noop_reverse(apps, schema_editor):
    return None


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0005_perf_indexes_v2'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ----- Section A: CASE IDENTIFICATION (Person) -----
        # case_id is added in 3 steps so legacy rows get unique UUIDs
        # before the UNIQUE constraint is enforced.
        migrations.AddField(
            model_name='person',
            name='case_id',
            field=models.UUIDField(null=True),
        ),
        migrations.RunPython(_backfill_case_id, _noop_reverse),
        migrations.AlterField(
            model_name='person',
            name='case_id',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False, help_text='External / website case ID (Section A).'),
        ),
        migrations.AddField(
            model_name='person',
            name='case_received_date',
            field=models.DateField(blank=True, help_text='Date the case file was received by the documentation officer (Section A).', null=True),
        ),
        migrations.AddField(
            model_name='person',
            name='case_received_by',
            field=models.ForeignKey(blank=True, help_text='Documentation officer who received the case (Section A).', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cases_received', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='person',
            name='case_source_types',
            field=models.JSONField(blank=True, default=list, help_text='Source-of-case checklist — list from {research_interview, family, victim_survivor, lawyer, ngo_cso, media, government_document, other} (Section A).'),
        ),
        migrations.AddField(
            model_name='person',
            name='case_source_other',
            field=models.CharField(blank=True, default='', help_text='Free-text when "other" is selected above (Section A).', max_length=255),
        ),
        migrations.AddField(
            model_name='person',
            name='duplicate_check',
            field=models.CharField(blank=True, choices=[('no_duplicate', 'No duplicate identified'), ('possible_duplicate', 'Possible duplicate'), ('existing_case', 'Existing case')], default='', help_text='Duplicate-check outcome (Section A).', max_length=20),
        ),
        migrations.AddField(
            model_name='person',
            name='duplicate_of',
            field=models.ForeignKey(blank=True, help_text='Set when duplicate_check = existing_case (Section A).', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='duplicates', to='cases.person'),
        ),

        # ----- Section B: PERSON identity fields -----
        migrations.AddField(
            model_name='person',
            name='age_at_incident',
            field=models.PositiveIntegerField(blank=True, help_text='Age at the time of the incident (Section B). Distinct from date_of_birth.', null=True),
        ),
        migrations.AddField(
            model_name='person',
            name='occupation',
            field=models.CharField(blank=True, default='', help_text='Occupation at time of incident (Section B).', max_length=255),
        ),
        migrations.AddField(
            model_name='person',
            name='district',
            field=models.CharField(blank=True, default='', help_text='Person-level administrative district (Section B). Distinct from Report.incident_district.', max_length=255),
        ),
        migrations.AddField(
            model_name='person',
            name='province',
            field=models.CharField(blank=True, default='', help_text='Person-level administrative province (Section B). Distinct from Report.incident_province.', max_length=255),
        ),
        migrations.AddField(
            model_name='person',
            name='identity_verified_methods',
            field=models.JSONField(blank=True, default=list, help_text='Identity-verification checklist — list from {interview, family, identity_document, court_document, other} (Section B).'),
        ),
        migrations.AddField(
            model_name='person',
            name='identity_verified_other',
            field=models.CharField(blank=True, default='', max_length=255),
        ),

        # ----- Section D: CURRENT STATUS metadata on Person -----
        migrations.AddField(
            model_name='person',
            name='current_status_date',
            field=models.DateField(blank=True, help_text='Date the current status was confirmed (Section D).', null=True),
        ),
        migrations.AddField(
            model_name='person',
            name='current_status_source',
            field=models.CharField(blank=True, default='', help_text='Source of the current-status claim (Section D).', max_length=500),
        ),
        migrations.AddField(
            model_name='person',
            name='current_status_verification',
            field=models.CharField(blank=True, choices=[('level_1_reported', 'Level 1 — Reported'), ('level_2_partially_verified', 'Level 2 — Partially verified'), ('level_3_corroborated', 'Level 3 — Corroborated'), ('level_4_documented', 'Level 4 — Documented')], default='', help_text='Verification level of the current status (Section D).', max_length=50),
        ),

        # ----- Section K: CONSENT / PUBLICATION (Person-level) -----
        migrations.AddField(
            model_name='person',
            name='consent_documentation',
            field=models.CharField(blank=True, choices=[('yes', 'Yes'), ('no', 'No'), ('pending', 'Pending')], default='', help_text='Consent for documentation — Yes / No / Pending (Section K).', max_length=20),
        ),
        migrations.AddField(
            model_name='person',
            name='consent_public_publication',
            field=models.CharField(blank=True, choices=[('yes', 'Yes'), ('no', 'No'), ('pending', 'Pending')], default='', help_text='Consent for public publication (Section K).', max_length=20),
        ),
        migrations.AddField(
            model_name='person',
            name='public_identity_level',
            field=models.CharField(blank=True, choices=[('full', 'Full name'), ('partial', 'Partial name'), ('anonymous', 'Anonymous')], default='', help_text='Full / Partial / Anonymous (Section K).', max_length=20),
        ),
        migrations.AddField(
            model_name='person',
            name='photograph_public',
            field=models.CharField(blank=True, choices=[('yes', 'Yes'), ('no', 'No'), ('pending', 'Pending')], default='', help_text='Yes / No / Pending (Section K).', max_length=20),
        ),
        migrations.AddField(
            model_name='person',
            name='public_location_level',
            field=models.CharField(blank=True, choices=[('province', 'Province'), ('district', 'District'), ('city', 'City / general area'), ('do_not_disclose', 'Do not disclose')], default='', help_text='Province / District / City / Do not disclose (Section K).', max_length=20),
        ),
        migrations.AddField(
            model_name='person',
            name='information_restricted_from_publication',
            field=models.TextField(blank=True, default='', help_text='Free-text list of items withheld from publication (Section K).'),
        ),

        # ----- Section N: PUBLIC CASE SUMMARY (Person) -----
        migrations.AddField(
            model_name='person',
            name='public_summary',
            field=models.TextField(blank=True, default='', help_text='Approved-for-publication summary (Section N).'),
        ),
        migrations.AddField(
            model_name='person',
            name='public_status_text',
            field=models.CharField(blank=True, default='', help_text='Public-facing status text (Section N).', max_length=255),
        ),
        migrations.AddField(
            model_name='person',
            name='public_verification_level',
            field=models.CharField(blank=True, choices=[('level_1_reported', 'Level 1 — Reported'), ('level_2_partially_verified', 'Level 2 — Partially verified'), ('level_3_corroborated', 'Level 3 — Corroborated'), ('level_4_documented', 'Level 4 — Documented')], default='', help_text='Mirror of Section L for the public-facing display (Section N).', max_length=50),
        ),

        # ----- Section P: WEBSITE ENTRY (Person) -----
        migrations.AddField(
            model_name='person',
            name='entered_in_world',
            field=models.CharField(blank=True, choices=[('yes', 'Yes'), ('no', 'No'), ('pending', 'Pending')], default='', help_text='Has the case been entered into Testimonies.World — Yes / No / Pending (Section P).', max_length=20),
        ),
        migrations.AddField(
            model_name='person',
            name='entry_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='person',
            name='entered_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='persons_entered', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='person',
            name='second_person_check_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='person',
            name='checked_against_original_documentation',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='person',
            name='final_reviewer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='persons_final_reviewed', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='person',
            name='final_date',
            field=models.DateField(blank=True, null=True),
        ),

        # ----- Section D: extend Person.current_status enum -----
        # Values appended (not reordered) so existing rows are unaffected.
        migrations.AlterField(
            model_name='person',
            name='current_status',
            field=models.CharField(choices=[('detained', 'Detained'), ('disappeared', 'Disappeared'), ('restricted_movement', 'Restricted Movement'), ('released', 'Released'), ('deceased', 'Deceased'), ('unknown', 'Unknown'), ('stateless', 'Stateless'), ('rights_restricted', 'Rights Restricted'), ('ongoing_enforced_disappearance', 'Ongoing alleged enforced disappearance'), ('found_alive', 'Found alive'), ('found_dead', 'Found dead'), ('case_closed', 'Case closed'), ('other', 'Other')], default='unknown', max_length=30),
        ),
    ]
