"""CaseEvent model — Documentation Form Section E (Timeline).

Child of Person. Soft-linked to Report.
"""

import django.db.models.deletion

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0010_media_evidence_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='CaseEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_date', models.DateField(blank=True, null=True)),
                ('event_kind', models.CharField(blank=True, choices=[('incident', 'Incident'), ('detention', 'Detention'), ('transfer', 'Transfer'), ('court_hearing', 'Court hearing'), ('release', 'Release'), ('status_change', 'Status change'), ('other', 'Other')], default='', max_length=30)),
                ('description', models.TextField(blank=True, default='')),
                ('source', models.CharField(blank=True, default='', max_length=500)),
                ('verification', models.CharField(blank=True, choices=[('level_1_reported', 'Level 1 — Reported'), ('level_2_partially_verified', 'Level 2 — Partially verified'), ('level_3_corroborated', 'Level 3 — Corroborated'), ('level_4_documented', 'Level 4 — Documented')], default='', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='timeline_events', to='cases.person')),
                ('report', models.ForeignKey(blank=True, help_text='Optional soft link back to the originating Report.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='events', to='cases.report')),
            ],
            options={
                'ordering': ['event_date', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='caseevent',
            index=models.Index(fields=['person', '-event_date'], name='caseevent_person_date_idx'),
        ),
    ]
