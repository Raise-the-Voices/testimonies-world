"""Report extensions for Case Documentation Form Section C (Incident).

Adds nine Report fields:
  case_types, case_type_other, incident_date, incident_date_precision,
  last_known_location, incident_district, incident_province,
  incident_information_source, incident_verification.

All values default to NULL / empty-list / empty-string so legacy
rows remain valid.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0006_person_case_form_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='case_types',
            field=models.JSONField(blank=True, default=list, help_text='Section C case-type checklist — list from {enforced_disappearance, arbitrary_detention, detention, release_following, death_following, other}.'),
        ),
        migrations.AddField(
            model_name='report',
            name='case_type_other',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='report',
            name='incident_date',
            field=models.DateField(blank=True, help_text='Date of incident / disappearance (Section C, 4-star field).', null=True),
        ),
        migrations.AddField(
            model_name='report',
            name='incident_date_precision',
            field=models.CharField(blank=True, choices=[('exact', 'Exact'), ('approximate', 'Approximate'), ('unknown', 'Unknown')], default='', help_text='Exact / Approximate / Unknown (Section C).', max_length=20),
        ),
        migrations.AddField(
            model_name='report',
            name='last_known_location',
            field=models.CharField(blank=True, default='', help_text='Last known location of the person (Section C, 4-star field).', max_length=500),
        ),
        migrations.AddField(
            model_name='report',
            name='incident_district',
            field=models.CharField(blank=True, default='', help_text='Administrative district of the incident (Section C).', max_length=255),
        ),
        migrations.AddField(
            model_name='report',
            name='incident_province',
            field=models.CharField(blank=True, default='', help_text='Administrative province of the incident (Section C).', max_length=255),
        ),
        migrations.AddField(
            model_name='report',
            name='incident_information_source',
            field=models.CharField(blank=True, default='', help_text='Source of this specific incident information (Section C).', max_length=500),
        ),
        migrations.AddField(
            model_name='report',
            name='incident_verification',
            field=models.CharField(blank=True, choices=[('level_1_reported', 'Level 1 — Reported'), ('level_2_partially_verified', 'Level 2 — Partially verified'), ('level_3_corroborated', 'Level 3 — Corroborated'), ('level_4_documented', 'Level 4 — Documented')], default='', help_text='Verification status of the incident (Section C).', max_length=50),
        ),
    ]
