"""
Field-weighted search for the persons catalog.

Replaces DRF's flat ``SearchFilter`` on ``PersonViewSet``. The previous
configuration (``search_fields = ['name', 'legal_name', 'aliases',
'country', 'summary_narrative']``) built a flat ``Q(...) | Q(...) | ...``
across five fields with no ranking, which caused short substrings to
leak into irrelevant columns:

* ``?search=pakis`` returned all 61 cases from Pakistan because
  ``country__icontains='pakis'`` matches "Pakistan". No relevance signal
  told Postgres "this came from the country column, not the name
  column".
* ``?search=moh`` returned matches in ``summary_narrative`` (free-text
  narratives containing "mother", "Mohsin", etc.) ranked the same as
  direct name matches.

This filter:

* Searches **only identity fields** — ``name``, ``legal_name``,
  ``aliases``. ``country`` is excluded (it has its own dropdown filter)
  and ``summary_narrative`` is excluded (it has its own FTS path,
  ``cases_person.search_vector``, see migration 0022).
* Assigns **field weights** so a direct hit on ``name`` always outranks
  a substring hit on ``aliases``.
* Annotates ``search_score`` and orders by ``-search_score,
  deceased_rank, -created_at`` so ties resolve to the same ordering the
  catalog uses everywhere else.
* Enforces a **minimum query length** (``MIN_LENGTH``) so 1-2 character
  queries return an empty page rather than a noisy substring match.
  The frontend (``persons/+page.svelte``) also gates below this
  threshold to avoid the round-trip, but the server is the source of
  truth — a direct API call still gets the safe behavior.

Designed to drop into a ``filter_backends`` slot on a ``ViewSet``.
"""

from __future__ import annotations

from django.db.models import Case, F, IntegerField, Q, Value, When
from rest_framework.filters import BaseFilterBackend


class PersonSearchFilter(BaseFilterBackend):
    """Field-weighted substring search over identity fields only.

    Each matching row is annotated with ``search_score``:

    * +100 if ``name`` is an exact (case-insensitive) match
    * +25  if ``name`` contains the query as a substring
    * +80  if ``legal_name`` is an exact match
    * +20  if ``legal_name`` contains the query
    * +60  if ``aliases`` contains the query (substring OK — aliases
      are comma-separated so a substring may legitimately fall across
      a boundary)

    Ordering: ``-search_score, deceased_rank, -created_at`` — the same
    secondary ordering the catalog uses without a search.
    """

    #: (field, exact_weight, substring_weight, exact_only)
    #: ``exact_only=True`` means substring matches are excluded from
    #: scoring entirely (still allowed in the WHERE clause to give the
    #: user results, but the score is 0 — they sink below exact hits).
    FIELD_WEIGHTS: tuple[tuple[str, int, int, bool], ...] = (
        ('name', 100, 25, True),
        ('legal_name', 80, 20, True),
        ('aliases', 60, 0, False),
    )

    MIN_LENGTH = 3

    def filter_queryset(self, request, queryset, view):
        q = (request.query_params.get('search') or '').strip()
        if not q:
            return queryset
        if len(q) < self.MIN_LENGTH:
            # Below the minimum: return nothing. Frontend also gates on
            # this, but a direct API call must be safe.
            return queryset.none()

        # WHERE: any identity field contains the query (icontains).
        # Keep this loose so the user gets results; the scoring below
        # decides what bubbles to the top.
        filter_q = Q()
        for field, _exact_w, _sub_w, exact_only in self.FIELD_WEIGHTS:
            if exact_only:
                # For exact-only fields, also accept substring matches
                # in the WHERE clause — otherwise "moh" wouldn't find
                # "Mohammed" at all. We just don't score them.
                filter_q |= Q(**{f'{field}__icontains': q})
            else:
                filter_q |= Q(**{f'{field}__icontains': q})

        # Score: for each row, sum the weights of every field that
        # matches. Built as a Case expression so it lives in SQL rather
        # than Python — works on the full paginated queryset.
        score = Value(0, output_field=IntegerField())
        for field, exact_w, sub_w, _exact_only in self.FIELD_WEIGHTS:
            # +exact_w if name ILIKE 'q' exactly, +sub_w if name
            # contains q as a substring, +0 otherwise. For aliases
            # (sub_w=0) we collapse this to a single Case.
            if sub_w > 0:
                score = score + Case(
                    When(**{f'{field}__iexact': q}, then=Value(exact_w)),
                    When(**{f'{field}__icontains': q}, then=Value(sub_w)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            else:
                score = score + Case(
                    When(**{f'{field}__icontains': q}, then=Value(exact_w)),
                    default=Value(0),
                    output_field=IntegerField(),
                )

        return (
            queryset.filter(filter_q)
            .annotate(search_score=score)
            .order_by('-search_score', F('deceased_rank'), '-created_at')
        )