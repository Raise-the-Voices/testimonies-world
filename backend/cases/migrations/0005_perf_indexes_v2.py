# Performance optimization v2. Adds standalone indexes for fields
# used in Meta.ordering / ordering_fields that didn't get one in
# 0003_perf_indexes. The production-deployment caveat from 0003
# applies verbatim:
#
# On a live Postgres table with significant row counts, plain
# AddIndex takes an ACCESS EXCLUSIVE lock for the duration of the
# index build. To avoid that, the production operator should:
#
#     1. Pre-create the indexes manually with CREATE INDEX
#        CONCURRENTLY using the exact names defined below. Each
#        statement runs outside any transaction and never takes a
#        write-blocking lock.
#     2. Apply this migration with `python manage.py migrate --fake
#        cases 0005_perf_indexes_v2` so Django records the indexes
#        in model state without re-running the DDL.
#
# On SQLite (CI / test runner) and small dev Postgres tables, plain
# AddIndex is fine — the lock is brief and harmless.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0004_alter_media_file'),
    ]

    operations = [
        # Report — default Meta.ordering is ['-date_start',
        # '-created_at'] and ReportFilter exposes date_from/date_to
        # lookups on date_start. Without these indexes, every
        # /api/reports/ list is a full scan + sort. The existing
        # report_person_private_idx covers the per-person
        # is_private filter but not the default ordering path.
        migrations.AddIndex(
            model_name='report',
            index=models.Index(
                fields=['-date_start'], name='report_date_start_desc_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='report',
            index=models.Index(
                fields=['-created_at'], name='report_created_at_desc_idx',
            ),
        ),
        # Person — ?ordering=-created_at is a documented sort path
        # on /api/persons/; the existing -updated_at index doesn't
        # help that filter. Standalone index for the "newest cases"
        # landing page.
        migrations.AddIndex(
            model_name='person',
            index=models.Index(
                fields=['-created_at'], name='person_created_at_desc_idx',
            ),
        ),
        # AuditLog — audit_user_time_idx covers user-scoped
        # timestamp queries, but the default /api/audit-logs/ list
        # has no user filter and just sorts by -timestamp. A
        # standalone timestamp index turns the default page render
        # from a full table sort into an index scan.
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['-timestamp'], name='audit_timestamp_desc_idx',
            ),
        ),
    ]
