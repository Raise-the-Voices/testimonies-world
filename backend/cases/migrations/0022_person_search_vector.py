"""Generated tsvector column for narrative full-text search.

Adds ``search_vector`` on ``cases_person``, weighted as:

    A (highest): name, legal_name
    B          : aliases
    C          : summary_narrative

Backed by a GIN index for ``@@ to_tsquery`` matching. The frontend
catalog doesn't query this column directly yet — it is wired up so a
follow-up PR can add a long-tail "search in narratives" path on
``PersonViewSet`` (or a separate ``?in_narratives=1`` flag) without
needing another migration.

Postgres-only. The ``RunPython`` forward / reverse guards on
``schema_editor.connection.vendor`` so the test runner, which uses
SQLite (see ``settings.py`` ``DATABASES['default']`` under ``if
TESTING:``), skips the SQL cleanly. Django's migration state still
records the operation as applied — that's fine because no model field
or queryset touches ``search_vector`` outside this migration's own
SQL.
"""

from django.db import migrations


_ADD_COLUMN = (
    "ALTER TABLE cases_person "
    "ADD COLUMN search_vector tsvector "
    "GENERATED ALWAYS AS ("
    "  setweight(to_tsvector('simple', coalesce(name, '')), 'A') "
    "  || setweight(to_tsvector('simple', coalesce(legal_name, '')), 'A') "
    "  || setweight(to_tsvector('simple', coalesce(aliases, '')), 'B') "
    "  || setweight(to_tsvector('simple', coalesce(summary_narrative, '')), 'C')"
    ") STORED;"
)

_ADD_INDEX = (
    "CREATE INDEX cases_person_search_vector_idx "
    "ON cases_person USING GIN (search_vector);"
)

_DROP_INDEX = "DROP INDEX IF EXISTS cases_person_search_vector_idx;"
_DROP_COLUMN = "ALTER TABLE cases_person DROP COLUMN IF EXISTS search_vector;"


def _add_vector(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cur:
        cur.execute(_ADD_COLUMN)
        cur.execute(_ADD_INDEX)


def _drop_vector(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cur:
        cur.execute(_DROP_INDEX)
        cur.execute(_DROP_COLUMN)


class Migration(migrations.Migration):
    dependencies = [
        ('cases', '0021_preapprovedemail'),
    ]

    operations = [
        migrations.RunPython(_add_vector, _drop_vector),
    ]