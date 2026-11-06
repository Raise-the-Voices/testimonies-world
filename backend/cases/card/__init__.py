"""Case card module — the masked, publication-facing projection of a case.

The card is a poster: one case, rendered as a shareable image. The
package mirrors `cases/testimonials/` — the payload is assembled on
the server, so the browser only ever receives what has been cleared
for publication.

  serializers.py      the masking contract + CaseCardPayloadSerializer
  export.py           CaseCardExportSerializer + EXPORT_SCHEMA (v1)
  export_schema.json  the v1 JSON Schema, byte-identical to EXPORT_SCHEMA
  tests.py            one test per rule of the masking matrix

Mounted on the existing `cases` app per project convention (one Django
app per project, not one per module). The endpoint is a detail action
on `PersonViewSet` — `GET /api/persons/{id}/card/` — so the
anonymous publication filter of `PersonViewSet.get_queryset` already
applies: an unpublished person is a 404 for an anonymous caller.
"""
