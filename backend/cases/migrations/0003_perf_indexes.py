# Performance optimization migration. Adds DB indexes for fields used in
# filter/ordering paths across Person, Report, Media,
# FamilyRelationship, and AuditLog.
#
# ## Production deployment note
#
# On a live Postgres table with significant row counts, plain AddIndex
# takes an ACCESS EXCLUSIVE lock for the duration of the index build —
# which blocks writes. To avoid that, the production operator should:
#
#     1. Pre-create the indexes manually with CREATE INDEX CONCURRENTLY
#        using the exact names defined below. Each statement runs
#        outside any transaction and never takes a write-blocking lock.
#     2. Apply this migration with `python manage.py migrate --fake
#        cases 0003_perf_indexes` so Django records the indexes in
#        model state without re-running the DDL.
#
# On SQLite (CI / test runner) and small dev Postgres tables, plain
# AddIndex is fine — the lock is brief and harmless.

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0002_add_authoritative_source'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # AuditLog — (target_type, target_id) is the canonical
        # "what happened to object X?" lookup; (user, -timestamp) is
        # the accountability surface.
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['target_type', 'target_id'],
                name='audit_target_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['user', '-timestamp'],
                name='audit_user_time_idx',
            ),
        ),
        # FamilyRelationship — relationship_type is low-cardinality but
        # cheap to index.
        migrations.AddIndex(
            model_name='familyrelationship',
            index=models.Index(
                fields=['relationship_type'],
                name='familyrel_type_idx',
            ),
        ),
        # Media — composites cover the common (person, visibility)
        # gallery filter and the (report, visibility) report-detail filter.
        migrations.AddIndex(
            model_name='media',
            index=models.Index(
                fields=['person', 'visibility'],
                name='media_person_visibility_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='media',
            index=models.Index(
                fields=['report', 'visibility'],
                name='media_report_visibility_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='media',
            index=models.Index(
                fields=['person', 'media_type'],
                name='media_person_type_idx',
            ),
        ),
        # Person — single-column indexes on heavily filtered/ordered
        # fields plus a composite for the (is_published, current_status)
        # statistics path.
        migrations.AddIndex(
            model_name='person',
            index=models.Index(fields=['country'], name='person_country_idx'),
        ),
        migrations.AddIndex(
            model_name='person',
            index=models.Index(
                fields=['current_status'],
                name='person_current_status_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='person',
            index=models.Index(
                fields=['is_published'],
                name='person_is_published_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='person',
            index=models.Index(
                fields=['-updated_at'],
                name='person_updated_desc_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='person',
            index=models.Index(
                fields=['is_published', 'current_status'],
                name='person_pub_status_idx',
            ),
        ),
        # Report — composite covers the default anonymous-viewer
        # filter (person__is_published=True AND is_private=False).
        migrations.AddIndex(
            model_name='report',
            index=models.Index(
                fields=['person', 'is_private'],
                name='report_person_private_idx',
            ),
        ),
    ]