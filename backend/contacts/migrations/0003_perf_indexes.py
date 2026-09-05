# Performance optimization migration. Adds a single-column index on
# Contact.role to accelerate the `?role=lawyer` style filter on the
# contacts list.
#
# See backend/cases/migrations/0003_perf_indexes.py for the production
# deployment note about CREATE INDEX CONCURRENTLY on a live Postgres
# table. Same workflow applies here.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0003_perf_indexes'),
        ('contacts', '0002_contact_deleted_at'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='contact',
            index=models.Index(fields=['role'], name='contact_role_idx'),
        ),
    ]