# Performance optimization v2. Same shape and prod-deploy caveat
# as cases/migrations/0005_perf_indexes_v2.py — see that file for
# the CREATE INDEX CONCURRENTLY + migrate --fake recipe.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('casework', '0002_userpreference_notification'),
    ]

    operations = [
        # CaseworkRecord — default Meta.ordering is
        # ['-date', '-created_at']; both fields need standalone
        # indexes for /api/casework/ list page sort.
        migrations.AddIndex(
            model_name='caseworkrecord',
            index=models.Index(
                fields=['-date'], name='casework_date_desc_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='caseworkrecord',
            index=models.Index(
                fields=['-created_at'], name='casework_created_at_desc_idx',
            ),
        ),
        # Notification — the existing (recipient, is_read,
        # -created_at) composite covers the inbox path, but the
        # email-dedupe query in casework/notifications.py filters
        # by (casework, created_at) which doesn't match any
        # existing composite. Standalone -created_at also helps
        # the per-casework notification listing if it ever grows.
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(
                fields=['-created_at'], name='notif_created_at_desc_idx',
            ),
        ),
    ]
