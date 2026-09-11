"""Media extensions for Case Documentation Form Section H (Evidence).

Adds four classification fields on top of the existing file/visibility
pipeline. All defaults are empty-string so legacy rows remain valid.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0009_report_verification_risk_qc'),
    ]

    operations = [
        migrations.AddField(
            model_name='media',
            name='evidence_kind',
            field=models.CharField(blank=True, choices=[('fir', 'FIR'), ('court_petition_order', 'Court petition/order'), ('government_document', 'Government document'), ('identity_document', 'Identity document'), ('photograph', 'Photograph'), ('medical_document', 'Medical document'), ('interview_transcript', 'Interview/transcript'), ('media_report', 'Media report'), ('ngo_report', 'NGO report'), ('other', 'Other')], default='', help_text='Section H: FIR / Court petition / Photograph / etc.', max_length=40),
        ),
        migrations.AddField(
            model_name='media',
            name='evidence_kind_other',
            field=models.CharField(blank=True, default='', help_text='Free-text when evidence_kind = other.', max_length=255),
        ),
        migrations.AddField(
            model_name='media',
            name='evidence_reference_number',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='media',
            name='evidence_status',
            field=models.CharField(blank=True, choices=[('verified', 'Verified'), ('partially_verified', 'Partially verified'), ('unverified', 'Unverified'), ('pending', 'Pending')], default='', help_text='Section H: Verified / Partially / Unverified / Pending.', max_length=20),
        ),
    ]
