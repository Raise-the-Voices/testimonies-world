# Generated for M8 — modernize FamilyRelationship constraints.
#
# Replaces the legacy `unique_together = ['person_a', 'person_b']`
# with an explicit `UniqueConstraint` (semantically identical at the
# DB level — same UNIQUE clause), and adds a `CheckConstraint` that
# rejects self-linking rows (`person_a == person_b`) at the schema
# layer. The serializer also rejects this case with a friendlier
# error message; the constraint is defense-in-depth for raw writes.
#
# ## Production deployment note
#
# `AlterUniqueTogether`, `AddConstraint(UniqueConstraint)`, and
# `AddConstraint(CheckConstraint)` each take an ACCESS EXCLUSIVE lock
# on `cases_familyrelationship` for the duration of the statement.
# Unlike `AddIndex`, there is no CONCURRENTLY equivalent for
# `ALTER TABLE ... ADD CONSTRAINT`, so this migration cannot avoid
# the lock.
#
# Verified against the live `testimonies_world` DB on VM 100: the
# table is currently empty, so the lock and constraint validation
# are both instantaneous. If that changes before deploy, run during
# a low-traffic window.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0019_add_case_event_created_by'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='familyrelationship',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='familyrelationship',
            constraint=models.UniqueConstraint(fields=('person_a', 'person_b'), name='familyrel_unique_pair'),
        ),
        migrations.AddConstraint(
            model_name='familyrelationship',
            constraint=models.CheckConstraint(condition=models.Q(('person_a', models.F('person_b')), _negated=True), name='familyrel_no_self_link'),
        ),
    ]
