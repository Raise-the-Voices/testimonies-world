"""CaseUpdate model — Documentation Form Section Q (Future Update).

Child of Person. Distinct from `CaseEvent`.
"""

import django.db.models.deletion

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0011_caseevent_model'),
    ]

    operations = [
        migrations.CreateModel(
            name='CaseUpdate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('update_date', models.DateField(blank=True, null=True)),
                ('new_information', models.TextField(blank=True, default='')),
                ('source', models.CharField(blank=True, default='', max_length=500)),
                ('evidence', models.TextField(blank=True, default='')),
                ('verification', models.CharField(blank=True, choices=[('unverified', 'Unverified'), ('pending', 'Pending'), ('partially_verified', 'Partially verified'), ('corroborated', 'Corroborated'), ('verified', 'Verified')], default='', max_length=20)),
                ('status_changes', models.CharField(blank=True, choices=[('yes', 'Yes'), ('no', 'No'), ('unknown', 'Unknown')], default='', help_text='Does this update change the case status?', max_length=20)),
                ('new_status', models.CharField(blank=True, default='', help_text='Free-text new status (Section Q).', max_length=255)),
                ('website_updated', models.CharField(blank=True, choices=[('yes', 'Yes'), ('no', 'No'), ('unknown', 'Unknown')], default='', max_length=20)),
                ('verified_date', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='updates', to='cases.person')),
                ('verified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='case_updates_verified', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-update_date', '-created_at'],
            },
        ),
    ]
