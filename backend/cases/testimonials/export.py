"""Testimonial export — canonical schema for downstream consumers.

The export contract is consumed by international bodies and partner
NGOs (the 4-month horizon called out in the design). The contract
is pinned via `Testimonial.schema_version` — bumping is a manual,
deliberate action documented in the README.

Two artifacts in this module:
  - TestimonialExportSerializer — DRF serializer producing the
    canonical JSON shape for one row.
  - EXPORT_SCHEMA — JSON Schema (draft-07) describing the shape so
    external integrators can validate their intake pipelines
    programmatically. See the schema_version section in the README
    for the bump protocol.
"""

from rest_framework import serializers

from cases.models import Testimonial, TestimonialTag


class TestimonialExportSerializer(serializers.ModelSerializer):
    """Stable, versioned export shape. NOT for API consumers.

    Field set is deliberately a subset of the internal serializer —
    only fields external integrators should ever see. Schema-version-
    pinned: changes flow through `schema_version` on the row.

    Audit: intentionally NOT included. Audit is internal to our
    infrastructure; partners do not need it.
    """

    tags = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='name',
    )
    linked_case_id = serializers.UUIDField(
        source='person.case_id', read_only=True, allow_null=True,
    )

    class Meta:
        model = Testimonial
        fields = [
            'id',
            'schema_version',
            'slug',
            'language',
            'title',
            'summary',
            'narrative',
            'outcome',
            'country',
            'region',
            'public_location_display',
            'incident_date',
            'incident_types',
            'verification_level',
            'source_visibility',
            'public_source_label',
            'family_protected',
            'contact_protected',
            'published_at',
            'tags',
            'translation_group',
            'linked_case_id',
        ]
        read_only_fields = fields


# JSON Schema (draft-07) for the export shape. Generated to match
# TestimonialExportSerializer above; versioned together so consumers
# can pin a schema_url in their intake pipelines. Update on every
# schema_version bump.
EXPORT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://testimonies.world/schemas/testimonial-export-v1.json",
    "title": "TestimonialExport",
    "description": (
        "Canonical export shape for a Testimonial. Pinned at "
        "schema_version=1. Bumping to v2 requires updating this "
        "schema and the EXPORT_SCHEMA dict in cases/testimonials/"
        "export.py atomically."
    ),
    "type": "object",
    "required": [
        "id", "schema_version", "slug", "language", "status",
        "published_at",
    ],
    "properties": {
        "id": {"type": "integer"},
        "schema_version": {"type": "integer", "minimum": 1},
        "slug": {"type": "string"},
        "language": {"type": "string", "pattern": "^[a-z]{2}(-[A-Z]{2})?$"},
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "narrative": {"type": "string"},
        "outcome": {"type": "string"},
        "country": {"type": "string"},
        "region": {"type": "string"},
        "public_location_display": {"type": "string"},
        "incident_date": {"type": ["string", "null"], "format": "date"},
        "incident_types": {
            "type": "array",
            "items": {"type": "string"},
        },
        "verification_level": {
            "type": "string",
            "enum": [
                "level_1_reported", "level_2_partially_verified",
                "level_3_corroborated", "level_4_documented", "",
            ],
        },
        "source_visibility": {
            "type": "string",
            "enum": ["public_named", "public_anonymous", "hidden"],
        },
        "public_source_label": {"type": "string"},
        "family_protected": {"type": "boolean"},
        "contact_protected": {"type": "boolean"},
        "published_at": {
            "type": ["string", "null"],
            "format": "date-time",
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
        },
        "translation_group": {"type": "string", "format": "uuid"},
        "linked_case_id": {"type": ["string", "null"], "format": "uuid"},
    },
    "additionalProperties": False,
}
