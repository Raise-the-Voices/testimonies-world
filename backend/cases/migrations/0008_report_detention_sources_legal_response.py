"""Report extensions for Case Documentation Form Sections F, G, I, J.

- F: Detention (5 fields)
- G: Sources (6 fields)
- I: Legal Action (9 fields)
- J: Government / Authority Response (6 fields)
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0007_report_incident_fields'),
    ]

    operations = [
        # ----- Section F: DETENTION -----
        migrations.AddField(
            model_name='report',
            name='detention_alleged',
            field=models.CharField(blank=True, choices=[('yes', 'Yes'), ('no', 'No'), ('unknown', 'Unknown')], default='', help_text='Section F (4-star): Was detention alleged?', max_length=20),
        ),
        migrations.AddField(
            model_name='report',
            name='alleged_detention_location',
            field=models.CharField(blank=True, default='', help_text='Alleged detention location (Section F).', max_length=500),
        ),
        migrations.AddField(
            model_name='report',
            name='detention_acknowledged',
            field=models.CharField(blank=True, choices=[('yes', 'Yes'), ('no', 'No'), ('unknown', 'Unknown')], default='', help_text='Was the detention officially acknowledged? (Section F)', max_length=20),
        ),
        migrations.AddField(
            model_name='report',
            name='detention_information',
            field=models.TextField(blank=True, default='', help_text='Information / evidence about the detention (Section F).'),
        ),
        migrations.AddField(
            model_name='report',
            name='detention_verification',
            field=models.CharField(blank=True, choices=[('reported', 'Reported'), ('partially_verified', 'Partially verified'), ('corroborated', 'Corroborated'), ('documented', 'Documented')], default='', help_text='Per-detention verification status (Section F).', max_length=20),
        ),

        # ----- Section G: SOURCES -----
        migrations.AddField(
            model_name='report',
            name='primary_source_type',
            field=models.CharField(blank=True, choices=[('victim_survivor', 'Victim/survivor'), ('family', 'Family'), ('witness', 'Witness'), ('official_document', 'Official document')], default='', help_text='Primary source type (Section G).', max_length=30),
        ),
        migrations.AddField(
            model_name='report',
            name='primary_source_description',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='report',
            name='additional_source_type',
            field=models.CharField(blank=True, choices=[('lawyer', 'Lawyer'), ('ngo', 'NGO'), ('media', 'Media'), ('court', 'Court'), ('government', 'Government'), ('other', 'Other')], default='', help_text='Additional source type (Section G).', max_length=30),
        ),
        migrations.AddField(
            model_name='report',
            name='additional_source_description',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='report',
            name='source_consistency',
            field=models.CharField(blank=True, choices=[('consistent', 'Consistent'), ('some_differences', 'Some differences'), ('major_conflict', 'Major conflict'), ('requires_further_verification', 'Requires further verification')], default='', help_text='Consistency between primary and additional sources (Section G).', max_length=30),
        ),
        migrations.AddField(
            model_name='report',
            name='source_verification_notes',
            field=models.TextField(blank=True, default='', help_text='Free-text verification notes (Section G).'),
        ),

        # ----- Section I: LEGAL ACTION -----
        migrations.AddField(
            model_name='report',
            name='legal_fir_filed',
            field=models.CharField(blank=True, choices=[('yes', 'Yes'), ('no', 'No'), ('unknown', 'Unknown')], default='', help_text='Was an FIR filed? (Section I, starred on the form)', max_length=20),
        ),
        migrations.AddField(
            model_name='report',
            name='fir_number',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='report',
            name='police_station',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='report',
            name='legal_court_case',
            field=models.CharField(blank=True, choices=[('yes', 'Yes'), ('no', 'No'), ('unknown', 'Unknown')], default='', help_text='Was a court case / petition filed? (Section I, starred)', max_length=20),
        ),
        migrations.AddField(
            model_name='report',
            name='court_name',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='report',
            name='case_number',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='report',
            name='legal_commission_complaint',
            field=models.CharField(blank=True, choices=[('yes', 'Yes'), ('no', 'No'), ('unknown', 'Unknown')], default='', max_length=20),
        ),
        migrations.AddField(
            model_name='report',
            name='legal_lawyer_involved',
            field=models.CharField(blank=True, choices=[('yes', 'Yes'), ('no', 'No'), ('unknown', 'Unknown')], default='', max_length=20),
        ),
        migrations.AddField(
            model_name='report',
            name='current_legal_status',
            field=models.TextField(blank=True, default='', help_text='Current status of the legal process (Section I).'),
        ),

        # ----- Section J: GOVERNMENT / AUTHORITY RESPONSE -----
        migrations.AddField(
            model_name='report',
            name='official_response',
            field=models.CharField(blank=True, choices=[('yes', 'Yes'), ('no', 'No'), ('unknown', 'Unknown')], default='', max_length=20),
        ),
        migrations.AddField(
            model_name='report',
            name='responding_authority',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='report',
            name='response_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='report',
            name='response_type',
            field=models.CharField(blank=True, choices=[('confirmation', 'Confirmation'), ('denial', 'Denial'), ('investigation', 'Investigation'), ('detention_acknowledged', 'Detention acknowledged'), ('release_confirmed', 'Release confirmed'), ('other', 'Other')], default='', max_length=30),
        ),
        migrations.AddField(
            model_name='report',
            name='response_source_document',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='report',
            name='response_verification',
            field=models.CharField(blank=True, choices=[('reported', 'Reported'), ('partially_verified', 'Partially verified'), ('corroborated', 'Corroborated'), ('documented', 'Documented')], default='', help_text='Per-response verification status (Section J).', max_length=20),
        ),
    ]
