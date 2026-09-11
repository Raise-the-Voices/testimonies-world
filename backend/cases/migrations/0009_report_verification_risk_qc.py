"""Report extensions for Case Documentation Form Sections L, M, O.

- L: Verification level (3 fields)
- M: Internal risk / security (4 fields — gated in serializer)
- O: Quality control (12 booleans + reviewer FK + review date + decision)
"""

import django.db.models.deletion

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0008_report_detention_sources_legal_response'),
    ]

    operations = [
        # ----- Section L: VERIFICATION LEVEL -----
        migrations.AddField(
            model_name='report',
            name='verification_level',
            field=models.CharField(blank=True, choices=[('level_1_reported', 'Level 1 — Reported'), ('level_2_partially_verified', 'Level 2 — Partially verified'), ('level_3_corroborated', 'Level 3 — Corroborated'), ('level_4_documented', 'Level 4 — Documented')], default='', help_text='Case-level verification ladder (Section L).', max_length=50),
        ),
        migrations.AddField(
            model_name='report',
            name='verification_reason',
            field=models.TextField(blank=True, default='', help_text='Why this level was assigned (Section L).'),
        ),
        migrations.AddField(
            model_name='report',
            name='unverified_information_remaining',
            field=models.TextField(blank=True, default='', help_text='Information that remains unverified (Section L).'),
        ),

        # ----- Section M: INTERNAL RISK / SECURITY -----
        migrations.AddField(
            model_name='report',
            name='risk_level',
            field=models.CharField(blank=True, choices=[('low', 'Low'), ('moderate', 'Moderate'), ('high', 'High'), ('critical', 'Critical'), ('not_assessed', 'Not assessed')], default='', help_text='INTERNAL — Section M. Never exposed via public API.', max_length=20),
        ),
        migrations.AddField(
            model_name='report',
            name='risk_concerns',
            field=models.JSONField(blank=True, default=list, help_text='INTERNAL — Section M checklist.'),
        ),
        migrations.AddField(
            model_name='report',
            name='risk_concerns_other',
            field=models.CharField(blank=True, default='', help_text='INTERNAL — free-text when "other" is selected.', max_length=255),
        ),
        migrations.AddField(
            model_name='report',
            name='internal_notes',
            field=models.TextField(blank=True, default='', help_text='INTERNAL — Section M. Stripped from public API always.'),
        ),

        # ----- Section O: QUALITY CONTROL -----
        migrations.AddField(
            model_name='report',
            name='qc_name_checked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='report',
            name='qc_duplicate_check_completed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='report',
            name='qc_date_checked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='report',
            name='qc_location_checked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='report',
            name='qc_status_checked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='report',
            name='qc_sources_recorded',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='report',
            name='qc_evidence_checked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='report',
            name='qc_legal_information_checked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='report',
            name='qc_government_response_checked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='report',
            name='qc_allegations_identified',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='report',
            name='qc_consent_checked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='report',
            name='qc_sensitive_information_removed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='report',
            name='qc_verification_level_assigned',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='report',
            name='qc_reviewed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reports_qc_reviewed', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='report',
            name='qc_review_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='report',
            name='qc_review_decision',
            field=models.CharField(blank=True, choices=[('approved', 'Approved'), ('corrections_required', 'Corrections required'), ('more_verification_required', 'More verification required'), ('internal_only', 'Internal only'), ('do_not_publish', 'Do not publish')], default='', max_length=30),
        ),
    ]
