"""Case card export — the canonical schema for downstream consumers.

The card is a publication artifact. Whoever receives the JSON (a
partner NGO, a press desk, an archiving project) needs to know what
the fields mean and what may not be there at all, so the shape is
pinned the same way the testimonial export is pinned: a JSON Schema
(draft-07) that mirrors the payload, versioned together with the
`schema_version` the payload carries.

Two artifacts in this module:

  - CaseCardExportSerializer — DRF serializer producing the canonical
    JSON shape for one case.
  - EXPORT_SCHEMA — JSON Schema (draft-07) describing that shape. The
    on-disk `export_schema.json` is generated from this dict and the
    two must stay byte-identical; `tests.py` pins that.

Bump protocol (same as the testimonial export): change the payload →
bump `schema_version` → update this dict AND `export_schema.json` in
the same commit → re-export the downstream consumers pinned to the
previous `$id`.
"""

from rest_framework import serializers

from cases.card.serializers import (
    CaseCardPayloadSerializer,
    LOCATION_PRECISION_VALUES,
    PERSON_STATUS_VALUES,
    VERIFICATION_LABELS,
)


class CaseCardExportSerializer(CaseCardPayloadSerializer):
    """Stable, versioned export shape for one case card.

    At v1 the export contract and the API payload are the same shape:
    a card is only publishable in its masked form, so there is no
    "full" variant to export. The class exists so the export has its
    own name in the schema, and so a future version can split them
    without moving the payload's shape out from under consumers.

    Audit is intentionally not included — it is internal to our
    infrastructure and partners do not need it.
    """


# JSON Schema (draft-07) for the export shape. Generated to match
# CaseCardExportSerializer above; versioned together so consumers can
# pin a schema_url in their intake pipelines. Update on every
# schema_version bump.
EXPORT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://testimonies.world/schemas/case-card-v1.json",
    "title": "CaseCard",
    "description": (
        "Canonical export shape for a Case Information Card. Pinned at "
        "schema_version=1. Bumping to v2 requires updating this schema "
        "and the EXPORT_SCHEMA dict in cases/card/export.py atomically."
    ),
    "type": "object",
    "required": [
        "schema_version", "reference", "generated_date", "headline",
        "title", "status", "status_label", "identity", "incident",
        "categories", "verification", "source_label", "exportable",
        "withheld",
    ],
    "properties": {
        "schema_version": {"type": "integer", "const": 1},
        "reference": {"type": ["string", "null"]},
        "generated_date": {"type": "string", "format": "date"},
        "headline": {"type": "string"},
        "title": {"type": "string"},
        "status": {
            "type": "string",
            "enum": list(PERSON_STATUS_VALUES),
        },
        "status_label": {"type": "string"},
        "identity": {
            "type": "object",
            "required": [
                "display_name", "father_name", "age", "occupation",
            ],
            "properties": {
                "display_name": {"type": "string"},
                "father_name": {"type": ["string", "null"]},
                "age": {"type": ["integer", "null"]},
                "occupation": {"type": ["string", "null"]},
            },
            "additionalProperties": False,
        },
        "location": {
            "type": "object",
            "required": ["country", "display", "precision"],
            "properties": {
                "country": {"type": "string"},
                "display": {"type": ["string", "null"]},
                "precision": {
                    "type": "string",
                    "enum": list(LOCATION_PRECISION_VALUES),
                },
            },
            "additionalProperties": False,
        },
        "incident": {
            "type": "object",
            "required": ["date", "time", "place", "abductors", "detail"],
            "properties": {
                "date": {"type": ["string", "null"], "format": "date"},
                "time": {"type": ["string", "null"]},
                "place": {"type": ["string", "null"]},
                "abductors": {"type": ["string", "null"]},
                "detail": {"type": ["string", "null"]},
            },
            "additionalProperties": False,
        },
        "photo": {
            "type": "object",
            "required": ["url", "alt"],
            "properties": {
                "url": {"type": "string", "format": "uri"},
                "alt": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "categories": {
            "type": "array",
            "items": {"type": "string"},
        },
        "verification": {
            "type": "object",
            "required": ["level", "label"],
            "properties": {
                "level": {
                    "type": ["string", "null"],
                    "enum": list(VERIFICATION_LABELS.keys()) + [None],
                },
                "label": {"type": ["string", "null"]},
            },
            "additionalProperties": False,
        },
        "source_label": {"type": ["string", "null"]},
        "exportable": {"type": "boolean"},
        "withheld": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "additionalProperties": False,
}
