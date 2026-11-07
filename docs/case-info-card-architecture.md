# Case Information Card — Architecture & UX Report

**Date:** 2026-11-06 · **Branch:** `refactor/unified-media-section` · **Status:** report only — no implementation code written.
**Sources:** backend `cases/` app (models, serializers, views, testimonials subpackage), `scripts/nginx/rtv-cases`, live PostgreSQL `testimonies_world` (read-only queries), `frontend/src/` (app.css, `routes/persons/[id]/`, `lib/`), `frontend/package.json`, `vitest.config.ts`, `playwright.config.ts`.

---

## 0. Findings that change the brief — read before the sections

These are verified facts, not opinions. Each one changes what gets built.

### 0.1 Tailwind CSS is not installed in this project

`frontend/package.json` has **no `tailwindcss` dependency**; there is no `tailwind.config.*`, no `postcss.config.*`, and no `@theme` block. `grep -rn "tailwind" frontend/src frontend/vite.config.ts` → **0 hits**. The design system is hand-rolled CSS: a `:root` token block in `frontend/src/app.css:25-101` plus component classes (`.card`, `.badge`, `.view-title`, `.summary-card`, `.btn`, …).

**Consequence:** section 2 specifies plain CSS selectors against the existing tokens, not Tailwind classes. Installing Tailwind to serve one card would put a second styling system in a codebase whose README calls `app.css` "the single source of truth" (`README.md:376-380`). **If Tailwind is genuinely wanted, that is a project-wide decision, not a card decision, and it should be its own branch.**

### 0.2 I have not seen the reference poster

No reference image exists in the repo (`find` for png/jpg/pdf/webp outside `node_modules`/`build` → only `backend/public_media/*` case uploads), and no "infographic" string appears anywhere in the repo. The layout below is built from **your description** in the brief ("header with Ref and Date, bold red title, two-column split for the framed profile image and styled metadata list, footer with hashtags and organization branding"). Field labels like "R/O" are therefore **unmapped** — see §5.1.

### 0.3 The live database cannot fill the poster today

Read-only counts against the live DB (`testimonies_world`, 218 persons, 208 published, 414 reports, 46 testimonials):

| Field | Fill rate |
|---|---|
| `Person.name`, `country`, `ethnicity`, `medical_status`, `summary_narrative`, `case_id` | 100% |
| `Person.rough_location` | 93% |
| `Person.last_known_date` | 95% |
| `Person.quality_tier` | 66% |
| `Person.authoritative_source` / `authoritative_url` | 66% |
| `Person.legal_name` | 58% |
| **`Person.profile_image`** | **55%** |
| `Person.age_at_incident` | 39% |
| `Person.occupation` | 35% |
| `Person.aliases` | 25% |
| `Person.date_of_birth` | 17% |
| `Person.district`, `province` | **0%** |
| `Person.public_summary`, `public_status_text`, `public_verification_level`, `public_identity_level`, `public_location_level`, `photograph_public`, `consent_public_publication`, `case_received_date`, `current_status_date`, `current_status_source`, `entry_date`, `entered_in_world`, `final_date` | **0%** |
| `Report.date_start`, `narrative`, `source_attribution`, `source_type` | 99–100% |
| `Report.rough_location` | 36% |
| `Report.suspected_reason` / `official_reason` | 19% / 18% |
| **`Report.incident_date`, `incident_date_precision`, `last_known_location`, `incident_district`, `incident_province`, `detention_alleged`, `alleged_detention_location`, `detention_acknowledged`, `detention_information`, `case_types`, `verification_level`, `source_consistency`, `primary_source_type`, `fir_number`, `case_number`, `current_legal_status`** | **0% of 414 rows** |
| `FamilyRelationship` rows | **6 total** (across 218 persons) |
| Persons with ≥1 `CaseCategory` | 153 (70%) |
| `Testimonial.public_location_display`, `incident_types` | 0% |
| `Testimonial.incident_date` / `summary` / `public_source_label` / `verification_level` / `published_at` | 86% / 100% / 69% / 67% / 58% |

**Consequence:** every *structured* documentation-form field (Sections C–M on `Report`, Sections A/K/N/P on `Person`) is empty. The poster's "abduction metadata" block has **no structured source today** — the nearest populated fields are `Person.last_known_date` (95%), `Report.date_start` (99%), `Report.rough_location` (36%), and free-text `summary_narrative` (100%). Any design that assumes `incident_date` / `last_known_location` / `detention_alleged` will render an empty card for all 218 cases.

### 0.4 There is no publication-consent gate on the data

`consent_public_publication`, `photograph_public`, `public_identity_level`, `public_location_level`, `information_restricted_from_publication` exist on the model (`backend/cases/models.py:447-476`) and are **0% populated**. `is_published` (100%/95%) controls *catalog listing*, not *publication of a shareable image*.

**Consequence:** a "Download poster" feature has nothing to check today. Building it without a consent gate would let an advocate generate and publish a shareable image containing a disappeared person's name, photograph and location — the exact harm `cases/storage.py` was written to prevent ("the protected tree is the default; publishing is the explicit act, not protecting"). §1.4 specifies the gate.

### 0.5 No export, print, preview or share infrastructure exists

Verified in `frontend/src`: `canvas` / `toDataURL` / `getContext(` → 0 hits; `html-to-image` / `html2canvas` / `dom-to-image` / `jspdf` → 0 hits in `package.json` and `package-lock.json`; `navigator.share` → 0 hits; `window.print` / `@media print` → 0 hits; `download` attribute → 0 hits. `navigator.clipboard` appears once (`src/lib/Toast.svelte:81`) and only copies a JSON error blob.

The only `Blob`/`createObjectURL` uses are local upload previews (`routes/persons/[id]/edit/+page.svelte:167`, `routes/submit/+page.svelte:493`).

**Consequence:** §3 is greenfield, and the only reusable precedent is the *server-side* testimonial export contract (`backend/cases/testimonials/export.py`, `export_schema.json`) — a pattern worth copying, not the client side.

---

## 1. Data Requirements & API Mapping (Backend)

### 1.1 Poster row → data source map

Fill rates are live-DB counts. "Card row" is the poster line; "S" = on-screen preview, "E" = export payload.

| Card row | Model field | API field | Fill | S | E |
|---|---|---|---|:--:|:--:|
| **Ref** (top-left) | **none exists** — `Person.case_id` is a `UUIDField` (`models.py:372-375`) | `case_id` | 100% (UUID) | ✗ | ✗ |
| **Date** (top-right) | no populated candidate | `case_received_date` 0% · `entry_date` 0% · `current_status_date` 0% · testimonial `published_at` 58% | — | ✗ | ✗ |
| **Title** (bold red) | `Person.name` | `name` | 100% | ✓ | masked |
| Subtitle (status) | `Person.current_status` (14-value enum, `models.py:256-273`) | `current_status` | 100% | ✓ | ✓ |
| **Father's name** | `FamilyRelationship` where `relationship_type='parent'` → the related Person's `gender`; `RelationType` has only PARENT/CHILD/SIBLING/SPOUSE/OTHER (`models.py:977-982`) — no father/mother | `family[] = {person_id, person_name, relationship}` | **6 rows total** | ✓ | masked |
| **Age** | `Person.age_at_incident` (distinct from DOB by design, `models.py:407-410`) | `age_at_incident` | 39% | ✓ | masked |
| **Residence / R/O** | `Person.country` + `Person.rough_location` | `country`, `rough_location` | 100% / 93% | ✓ | masked |
| **Profession** | `Person.occupation` | `occupation` | 35% | ✓ | masked |
| **Abduction date** | `Report.date_start` (legacy, the only populated date) — `Report.incident_date` is 0% | `reports[].date_start` | 99% | ✓ | ✓ |
| **Abduction place** | `Report.rough_location` (36%) or `Person.rough_location` (93%) | `reports[].rough_location` | 36% | ✓ | masked |
| **Last seen** | `Person.last_known_date` + `Person.rough_location` | `last_known_date` | 95% | ✓ | masked |
| **Profile image** | `Person.profile_image` → `profile_image_url` (`serializers.py:442-453`) | `profile_image_url` | 55% | ✓ | gated |
| **Hashtags** (footer) | `Person.categories` M2M → `CaseCategory.name` | `categories[]` | 70% have ≥1 | ✓ | ✓ |
| **Verification** | `Person.public_verification_level` 0% → fallback `Person.quality_tier` (1/2/3) | `public_verification_level`, `quality_tier` | 66% (tier) | ✓ | ✓ |
| **Source line** | `Report.source_attribution` (99%) or testimonial `public_source_label` (69%) | `reports[].source_attribution` | 99% | ✓ | ✓ |
| **Org branding** | none — no logo asset, no settings key | — | — | ✗ | ✗ |

### 1.2 What the API already returns — the on-screen preview needs zero new endpoints

`PersonDetailSerializer` (`backend/cases/serializers.py:418-531`) uses `fields = '__all__'` and already serializes `categories`, `reports` (via `SerializerMethodField`), `media_files`, `family`, `profile_image_url`, `status_history`. The `/persons/[id]` page already loads exactly this object via `getPerson()` (`frontend/src/lib/api.ts:222-237`) → Zod `PersonDetailSchema` (`frontend/src/lib/schemas/overlays.ts:29-63`, which converts `created_at` / `updated_at` / `date_of_birth` / `last_known_date` to `Date` objects).

**Therefore the on-screen card preview is a pure client-side derivation of data already in memory — one API call fewer, not more.** It also means the card must *not* introduce a second fetch, or the page pays a redundant round trip.

Two consequences to design around:

- **`reports[]` ordering is not guaranteed** for "the abduction event". `PersonDetailSerializer.get_reports` returns `obj.reports.all()` — the model's `Report.Meta.ordering` applies. The card must pick the *earliest* `date_start` (the abduction) and the *latest* (last known) explicitly, not take `reports[0]`.
- **The person detail page has no `+page.ts` load function** — data loads client-side through `createLoader` (`frontend/src/lib/dataLoader.svelte.ts:38`, `routes/persons/[id]/+page.svelte:212-273`). The card renders client-side only. There is no server-rendered HTML to screenshot or to derive an OG image from.

### 1.3 What must be added: a dedicated, masked card projection

**Do not build the export payload from `PersonDetailSerializer` data in the browser.** For an authenticated advocate that payload contains `precise_location`, `medical_notes`, `aliases`, `reporter_name`, `reporter_contact`, `internal_notes` and Section-M risk fields. A poster built client-side from it would render whatever the browser happened to have — and `PRIVATE_PERSON_FIELDS` / `PRIVATE_REPORT_FIELDS` (`serializers.py:15-16`) only strip for *anonymous* callers, so a logged-in advocate sees the private fields too.

Instead, mirror the pattern `backend/cases/testimonials/serializers.py` already uses, whose own docstring states the rule: *"Server-side masking is the security boundary. The frontend never sees redacted fields in the first place."*

**New backend package** `backend/cases/card/` (matching the `cases/testimonials/` package layout):

```
backend/cases/card/
  __init__.py
  serializers.py      # CaseCardPayloadSerializer — the masked public projection
  views.py            # CardViewSet / PersonViewSet.card action
  export.py           # EXPORT_SCHEMA (JSON Schema draft-07) + CaseCardExportSerializer
  export_schema.json  # v1, byte-identical to EXPORT_SCHEMA
  tests.py
```

**Endpoint** `GET /api/persons/{id}/card/` — a `@action(detail=True)` on `PersonViewSet` (`backend/cases/views.py:162`), registered in `backend/testimonies/urls.py` (router, `basename='person'`).

Payload shape (v1):

```jsonc
{
  "schema_version": 1,
  "reference": "ED-2024-0042",          // see §1.5
  "publication_date": "2026-03-14",     // see §1.6
  "title": "Ahmed Al-Hassan",
  "status": "disappeared",
  "status_label": "Disappeared",
  "identity": {
    "display_name": "Ahmed Al-Hassan",  // masked per public_identity_level
    "father_name": "Yusuf Al-Hassan",   // null when unavailable
    "age": 34,                          // null when unknown
    "occupation": "Teacher"
  },
  "location": {
    "country": "Egypt",
    "display": "Alexandria Governorate",
    "precision": "province"             // province | district | city | withheld
  },
  "incident": {
    "date": "2025-11-03",
    "date_precision": "exact",
    "place": "Alexandria",
    "detail": ""                        // free-text only if already public
  },
  "photo": { "url": "https://…/public-media/profiles/x.jpg", "alt": "" },
  "categories": ["Enforced disappearance"],
  "verification": { "level": "level_3_corroborated", "label": "Corroborated" },
  "source_label": "Family",
  "exportable": true,
  "withheld": ["precise location", "father's name"]
}
```

`withheld` is deliberate: the card shows *"Location withheld"* rather than silently dropping the row. A person reading a poster should be able to tell the difference between "we have no such data" and "we are not disclosing it".

**Version pinning.** Mirror the testimonial contract exactly: `schema_version` on the row/response, a JSON Schema with a matching `$id` (`https://testimonies.world/schemas/case-card-v1.json`), and the documented bump protocol (update `CaseCardExportSerializer.Meta.fields` + the JSON Schema + a changelog entry **atomically**). `backend/cases/testimonials/tests.py::SchemaVersionPinTests` is the test to copy.

### 1.4 The publication gate (server-side, default-deny)

`exportable` is computed on the server. Rules, all from `Person` fields:

| Condition | Effect |
|---|---|
| `is_published` is false | `exportable: false`; for anonymous callers the endpoint returns **404** (matches `PersonViewSet.get_queryset`, `views.py:267+`, which filters unpublished rows out of the anonymous queryset) |
| `consent_public_publication != 'yes'` | `exportable: false` |
| `public_identity_level` blank | treated as `anonymous` → `display_name` = "Identity withheld"; `exportable: false` |
| `public_identity_level == 'partial'` | first name + initial, or `aliases` if present |
| `public_identity_level == 'anonymous'` | no name, no age, no occupation, no father, no photo |
| `photograph_public != 'yes'` | `photo` omitted entirely from the payload (not just from the export) |
| `public_location_level` blank | treat as `province` — country only, no district/city |
| `public_location_level == 'do_not_disclose'` | location omitted; `withheld` records it |
| `information_restricted_from_publication` non-empty | free-text list of withheld items; parse and re-check each against the payload (it is documented as "Free-text list of items withheld from publication" — `models.py:473-476`) |
| any source `Report.is_private == true` | that report is excluded from the payload entirely |
| any `Media.visibility != 'public'` | excluded from the payload |

**Default when a field is blank = most restrictive.** This is the repository's own stated posture in `cases/storage.py`: *"the protected tree is the default: anything written without a deliberate choice of storage lands behind the gate. Publishing is the explicit act, not protecting."*

**Practical effect today:** with the 0% fill rates in §0.3, every existing case returns `exportable: false`. That is the correct outcome, and §4.2 adds a publication checklist so an advocate can see exactly which fields are blocking a case.

### 1.5 The "Ref" needs a new field

`Person.case_id` is a `UUIDField(default=uuid.uuid4, unique=True, editable=False)` (`models.py:372-375`), documented as "External / website case ID (Section A)". A UUID is not a poster reference number — nobody can read `3f7c1e28-…` aloud on a radio broadcast or transcribe it from a printed poster.

**Recommendation:** add `Person.public_reference` — `CharField(max_length=32, unique=True, null=True, blank=True, db_index=True)`, human-assigned, e.g. `ED-2024-0042` (prefix per category, year, sequence). It is **not** the primary key and does not replace `case_id`; it is the citable identifier.

Requires: model field + migration, `PersonDetailSerializer` (inherits `__all__` automatically) and `PersonWriteSerializer` (add to the writable set), the person form (`frontend/src/routes/persons/[id]/edit/+page.svelte` + `frontend/src/lib/schemas/personForm.ts`), and a uniqueness validator with a friendly error. Auto-generation is possible but must not overwrite a human-assigned value.

### 1.6 The header date

Five candidates, four empty. The recommendation depends on what the date *means* on the poster (publication date vs. incident date) — that is a human decision (§5.2). If "publication date" means *when this poster went out*, the only populated candidate is `Testimonial.published_at` (58%) — but that is a Testimonial field, not a Person field, and `/persons/[id]` has no testimonial attached. `Person.created_at` (100%, always populated) is a third option: "case entered the database". `case_received_date` (0%) and `entry_date` (0%) are the semantically correct fields but empty.

### 1.7 Backend changes summary

| Change | Type | Risk |
|---|---|---|
| `Person.public_reference` | migration + field | low — nullable, unique |
| `CaseCardPayloadSerializer` + `EXPORT_SCHEMA` v1 | new package | low — read-only |
| `GET /api/persons/{id}/card/` | new action | low — read-only, default-deny |
| `Person.public_reference` in write serializer + form | field + validation | medium — uniqueness UX |
| `CardViewSet` audit log (`VIEWED`) | required by `SYSTEM_RULES §5` | — |
| Backfill `public_*` / `consent_*` fields | **data entry, not code** | the real blocker |

**No change to `PersonDetailSerializer` is needed** for the on-screen preview — it already returns every field the preview uses.

---

## 2. UI/UX Component Architecture (Frontend)

### 2.1 Component tree

```
src/lib/CaseInfoCard.svelte        — presentational, props-only, no fetching, no export logic
src/lib/caseCardData.ts            — types + buildCaseCardData(person) resolver + label maps
src/lib/caseCardData.test.ts       — vitest (node env, pure functions — matches repo convention)
src/lib/caseCardExport.ts          — html-to-image pipeline, dynamically imported so the
                                     ~20 KB library never enters the main bundle
src/routes/persons/[id]/+page.svelte — renders <CaseInfoCard> + the Download button
```

Why separate resolver from component: the field mapping, the masking labels, and the "which report is the abduction event" logic are pure functions and therefore unit-testable in the existing `environment: 'node'` vitest setup (`frontend/vitest.config.ts`), which **cannot render components** — there is no jsdom, and `@testing-library/svelte` is installed but imported by zero files. Component rendering must be covered by Playwright (`frontend/tests/*.spec.ts`), where an `anon` project and an `advocate` project already exist (`frontend/playwright.config.ts`).

### 2.2 Data contract (strict TypeScript — `SYSTEM_RULES §4`, no `any`)

```ts
// src/lib/caseCardData.ts
import type { PersonDetail } from '$lib/api/generated/endpoints.schemas';

export type CardPhoto = { src: string; alt: string } | null;

export interface CardMetaRow {
  label: string;
  value: string;        // already formatted; '' means "not shown"
  kind?: 'meta' | 'status' | 'date';
}

export interface CaseCardData {
  reference: string | null;      // null until Person.public_reference exists
  referenceLabel: string;        // "Ref" or the poster's own label
  dateLabel: string | null;
  title: string;
  statusLabel: string;
  photo: CardPhoto;
  rows: CardMetaRow[];           // ordered exactly as the poster prints them
  hashtags: string[];
  sourceLabel: string | null;
  verificationLabel: string | null;
  exportable: boolean;
  withheld: string[];
}
```

`buildCaseCardData(person: PersonDetail): CaseCardData` is the only place that knows the mapping. It must:

- derive the abduction date as the **earliest** non-null `reports[].date_start` and the last-known date as the **latest** — never `reports[0]` (no guaranteed ordering);
- format dates with the existing helper `formatMonthYear` (`frontend/src/lib/dateFormat.ts`) rather than a second `toLocaleDateString` call, so the card and the list page agree;
- humanise `current_status` — the existing `statusPresentation.ts` helper only covers **testimonial** statuses (`draft`, `under_review`, `published`, `rejected`, `archived`), **not** the 14 person statuses, so a new `PERSON_STATUS_LABEL` map is required (the enum is at `backend/cases/models.py:256-273`);
- read `person.family` for the father row: pick the entry with `relationship === 'Parent'` and confirm the related person is male — but `family[]` only carries `{person_id, person_name, relationship}` (`serializers.py:483-504`), **no gender**, so "father" vs "mother" is not decidable from the current payload. Two options: (a) add `person_gender` to the `family` serializer method field (small backend addition), or (b) label the row "Parent" instead of "Father". **Recommend (a) if the poster must say "Father"; (b) otherwise** (§5.3);
- skip rows whose value is empty, and never render a label with an empty value.

### 2.3 Layout — the poster body

Desktop (poster proportions), from the brief's description:

```
┌──────────────────────────────────────────────┐
│ REF: ED-2026-0042             7 NOVEMBER 2026│  ← .case-card-header
├──────────────────────────────────────────────┤
│ ENFORCED DISAPPEARANCE                       │  ← .case-card-title (teal, uppercase)
│ [ DISAPPEARED ]                              │  ← .case-card-status
├───────────────────────┬──────────────────────┤
│  ┌─────────────────┐  │  NAME:        Ahmed…  │  ← .case-card-body
│  │                 │  │  FATHER NAME: Yusuf…  │     (2-col grid)
│  │   [ photograph] │  │  AGE:         34      │
│  │                 │  │  RESIDENCE (R/O): …   │
│  └─────────────────┘  │  PROFESSION:  Teacher │
│                       │  DATE OF ABDUCTION: … │
├───────────────────────┴──────────────────────┤
│ #EnforcedDisappearance   Testimonies.world…  │  ← .case-card-footer
└──────────────────────────────────────────────┘
```

The heading is **the kind of violation the case records** (`Enforced disappearance`), not the person's name — the name is the first row of the metadata list, and is dropped from that list when it would repeat the heading. The brief's field order is fixed and is the order the card prints: name, father's name, age, residence (R/O), profession, date / time / place of abduction, abductors.

Two-column split: photo column ~38%, metadata column ~62%, `grid-template-columns: 38% 1fr; gap: 1.4em`.

The photo sits in a **framed portrait**: a 2px solid `var(--color-primary)` frame with 0.45em of paper inside it, `object-fit: cover`, `object-position: center 20%`. The frame is not a fixed ratio — it takes the height of the facts column beside it (the photo column is a flex container, the frame takes the row's height), so the photograph stands as tall as the list and the sheet keeps its portrait proportion at any number of rows. Below 560px the frame takes a 3/4 ratio instead, because the facts are no longer beside it.

The metadata column is a `<dl>` (the app already uses `dt`/`dd` pairs in `.sidebar-fields` / `.sidebar-field`, `routes/persons/[id]/+page.svelte:1526-1559`): `<div class="case-card-meta-row"><dt class="case-card-meta-label">Age</dt><dd class="case-card-meta-value">34</dd></div>`. Label = uppercase 0.78em `var(--color-primary)`, ending in a colon drawn by `::after` so the label text itself stays plain; value = 1.1em `var(--color-text)`. The rows are separated by hairline rules (`--color-card-rule`), not boxes.

### 2.4 CSS — tokens, not Tailwind

All sizing in `em`, all colour from `app.css` tokens. New tokens to add to the `:root` block (`app.css:25-101`) — the file's own rule: *"If you need a new color / radius / spacing, add a token here first; don't reach for the raw value in a component."*

| Token | Value | Why |
|---|---|---|
| `--card-base-font` | `16px` (screen) / `24px` (export) | the scale driver |
| `--card-poster-width` | `calc(var(--card-base-font) * 45)` | 720px on screen, 1080px for the export — one rule, two scales |
| `--card-poster-width-export` | `calc(var(--card-base-font-export) * 45)` | the export instance re-points the width token; see §2.5 |
| `--color-card-paper` | `#fcfbf9` (+ `--card-paper-wash`, `--card-paper-grain`) | the archival paper the sheet is printed on, not a white web card |
| `--color-card-rule` | `rgba(26, 26, 26, 0.18)` | the hairline between the metadata rows |
| `--radius-card-poster` | `0` | poster frames are square; `--radius-card` is 8px and reads "web card" |

The title is `var(--color-primary)` (deep teal, `#25646a`) — the brand accent, per the brief. The earlier plan's separate red token was dropped: the brief asks for the title in the brand accent, and the status badge already carries the red.

Selector plan (flat hyphenated, matching `.testimonial-card-*` / `.person-card`):

```css
.case-card { font-size: var(--card-base-font); width: var(--card-poster-width);
             max-width: 100%; background-color: var(--color-card-paper);
             border: 1px solid var(--color-text); border-top: 4px solid var(--color-primary);
             border-radius: var(--radius-card-poster); color: var(--color-text); }
.case-card-header  { display:flex; justify-content:space-between; align-items:baseline;
                     padding: .75em 1.25em .6em; border-bottom: 2px solid var(--color-text);
                     font-family: var(--font-mono); font-size: .8em; letter-spacing: .14em;
                     text-transform: uppercase; }
.case-card-ref     { font-weight: 700; white-space: nowrap; }
.case-card-date    { font-weight: 700; color: var(--color-text-muted); white-space: nowrap; }
.case-card-title   { color: var(--color-primary); font-weight: 700; text-transform: uppercase;
                     font-size: 2.6em; line-height: 1.04; text-decoration: underline;
                     hyphens: auto; overflow-wrap: break-word; }
.case-card-status  { font-size: .95em; font-weight: 700; letter-spacing: .18em;
                     text-transform: uppercase; color: var(--color-danger-text-strong);
                     background: var(--color-danger-bg); border: 1px solid var(--color-danger-border); }
.case-card-body    { display:grid; grid-template-columns: 38% 1fr; gap: 1.4em;
                     padding: 1.2em 1.25em 1.3em; border-top: 2px solid var(--color-text); }
.case-card-photo-column { display:flex; }
.case-card-photo-frame { flex: 1; min-height: 12em;
                     border: 2px solid var(--color-primary); padding: .45em; }
.case-card-photo   { display:block; width:100%; height:100%; object-fit: cover;
                     object-position: center 20%; }
.case-card-photo-placeholder { display:flex; flex-direction:column; gap:.6em;
                     align-items:center; justify-content:center; min-height: 11em;
                     color: var(--color-text-muted); background: var(--color-surface); }
.case-card-meta     { margin:0; display:grid; align-content:start; }
.case-card-meta-row { display:grid; grid-template-columns: 11em 1fr; gap: .6em;
                      align-items:baseline; padding: .5em 0;
                      border-bottom: 1px solid var(--color-card-rule); }
.case-card-meta-label { font-size: .78em; font-weight:700; text-transform:uppercase;
                        letter-spacing:.07em; color: var(--color-primary); margin:0; }
.case-card-meta-label::after { content: ':'; }
.case-card-meta-value { font-size: 1.1em; margin:0; overflow-wrap:anywhere; }
.case-card-footer   { border-top: 2px solid var(--color-text); padding: .9em 1.25em 1.1em;
                      display:flex; flex-wrap:wrap; align-items:center;
                      justify-content:space-between; gap:.6em 1em; }
.case-card-tags     { display:flex; flex-wrap:wrap; flex: 1 1 0; min-width: 0; gap: .45em; }
.case-card-tag      { font-size:.8em; font-weight:700; letter-spacing:.05em;
                      text-transform:uppercase; color:var(--color-primary);
                      background:var(--color-primary-tint);
                      border:1px solid var(--color-primary); padding:.2em .55em; }
.case-card-brand    { flex: 0 0 auto; font-size:.8em; letter-spacing:.06em;
                      color: var(--color-text-muted); white-space: nowrap; }
```

The footer needs the tags row to be a **flex item that takes the room the signature leaves** (`flex: 1 1 0; min-width: 0`), not one that claims its own width. Two items whose widths exactly fill a row can land on either side of a line break in two copies of the same sheet — and the exported file *is* a copy (`html-to-image` re-lays-out the clone, and a 1/64-px difference in the available width is enough to push the last tag onto its own line and clip the footer).

Also required: add `.case-card` to the entrance-animation list at `app.css:206-215` and to the reduced-motion block at `app.css:250-269`, or the card will not animate with its siblings and will not honour `prefers-reduced-motion`.

### 2.5 Responsive strategy — one DOM, two scales

The card must render at **fixed 1080px** for export and **fluid** on screen, from identical markup. That is achieved with the `em`-based scale, not with two layouts:

- **Screen:** `--card-base-font: 16px` → card is 720px wide, capped by `max-width: 100%`.
- **Export:** `--card-base-font: 24px` → card is 1080px wide, exported at `pixelRatio: 2` → 2160px PNG.

The width token cannot simply follow the font token: a custom property is substituted where it is *used* but resolved against the element that *declares* it, so `--card-poster-width` computes once, on `:root`, and inherits that computed 720px everywhere. The export instance therefore re-points the width token as well:

```css
.case-card--export {
  --card-base-font: var(--card-base-font-export);
  --card-poster-width: var(--card-poster-width-export);
}
```

Mobile: below 560px the two-column body collapses to one column (photo above the metadata list) and the heading drops to 2.1em so the longest word still fits the narrow sheet. Use a **container query** so the collapse depends on the card's own width, not the viewport — the card may later live in the narrow sidebar:

```css
.case-card-wrap { container-type: inline-size; }
@container (max-width: 560px) {
  .case-card-body { grid-template-columns: 1fr; }
  .case-card-photo { height: auto; aspect-ratio: 3 / 4; }
  .case-card-photo-frame { min-height: 0; }
  .case-card-title { font-size: 2.1em; }
  .case-card-header { flex-wrap: wrap; row-gap: .25em; }
  .case-card-date { margin-left: auto; }
  .case-card-meta-row { grid-template-columns: 1fr; gap: .2em; }
}
```

**Export-path hardening:** the export clone must not depend on a container query evaluating (a clone inside an SVG `foreignObject` has no reliable container size). Give the export instance an explicit modifier that forces the two-column grid:

```css
.case-card--export .case-card-body { grid-template-columns: 38% 1fr; }
```

### 2.6 Placement on `/persons/[id]`

The page is a two-column grid: main column (`.victim-item-container`, grid-area `main`) and sidebar (`.sidebar-container`, grid-area `sidebar`). The sidebar already holds the person header block (`.sidebar-top`, `routes/persons/[id]/+page.svelte:959-1066`) with the name, photo (`.profile-photo`, 180×180, 1:1), status badge, and a `dt`/`dd` field list.

Two placements, and they serve different jobs:

- **Sidebar, replacing/augmenting `.sidebar-top`** — the card becomes the case's visual identity on the page; the photo and the metadata rows are already there in a different form. Risk: the sidebar is ~320px wide, which is below the card's natural 720px, so the card would always render in its collapsed mobile layout inside the sidebar. **Not recommended as the primary placement.**
- **Main column, above the Summary section** (`:702-741`) — full width of the main column (~700px+), so the poster proportions hold, and the card reads as the headline artefact of the case. **Recommended.**

Either way the card is **preview-only** by default; the Download action is a separate button beside it (see §3.7), not inside the card, so the exported image never contains the button.

### 2.7 Missing-data behaviour (this is the common case, not the edge case)

45% of persons have no profile image and 65% have no occupation. Rules:

| Missing | Behaviour |
|---|---|
| No photo | render `.case-card-photo-placeholder` — a neutral silhouette block, **not** a broken image and **not** a crop of the case categories card. `MediaImage.svelte` already has a fallback path (`src/lib/MediaImage.svelte:116-127`) but it renders a *link*; the poster needs a distinct placeholder. |
| No occupation / age / father | the row is omitted entirely — no empty label, no em dash. |
| No `public_reference` yet | the header shows `Ref: Not assigned` in the preview and the card is marked not-exportable. |
| No date | the header date slot is omitted; the header keeps its two-column alignment via `justify-content: space-between` with one child. |
| No categories | the hashtag strip is omitted, keeping its top border (the poster's frame stays intact). |
| Long text | `summary_narrative` is **not** on the card (it is case narrative, not poster metadata). Any value that could run long (occupation, location, source label) gets `overflow-wrap: anywhere`; the heading gets `hyphens: auto` and `overflow-wrap: break-word`, so it breaks at a hyphen rather than past the edge of the sheet. The card's height is content-driven; at export it is measured, not fixed at 1350px. |

### 2.8 Accessibility

- The card is a `<article>` with `aria-labelledby` pointing at the title element; the metadata column is a real `<dl>`.
- `alt` on the photo: the photo is the person's face next to their name — the name is already in text, so `alt=""` is correct (decorative, per `SYSTEM_RULES §4`: "alt text on `<img>` only when not redundant").
- The title is `var(--color-primary)` `#25646a` on the paper tone `#fcfbf9` → contrast ratio **6.4:1**, passes WCAG AA for body text and comfortably for large text. The status badge is the only red on the sheet (`--color-danger-text-strong` on `--color-danger-bg`).
- The Download button needs a disabled state with a reason, not a silent hide: "Publication not approved — consent fields not set". The reason names the field to go and set; the server still decides whether the case may be exported.
- The card must render with `prefers-reduced-motion: reduce` honoured (add it to the `app.css:250-269` block).

---

## 3. Export & Sharing Strategy

### 3.1 Options

| Option | Fidelity | Cost | Verdict |
|---|---|---|---|
| **Client-side `html-to-image`** (`toPng` on a DOM clone) | High — pixel-identical to what the user sees | ~20 KB dep, one dynamic import, no infra | **Recommended** |
| Backend headless browser (Playwright/Chromium on the VM) | High | +300–500 MB browser on the VM; needs auth session; needs a job queue for latency | Rejected for v1 — the infra rules discourage new heavy services, and it duplicates the layout |
| Server-side PIL/WeasyPrint image drawing | Medium | Layout implemented twice (CSS + Python), font + RTL work duplicated, two sources of truth | Rejected |
| `window.print()` + user screenshots | Low (no output file) | zero | Not a feature |

The client-side approach also matches the deployment reality: the app is SSR'd SvelteKit behind nginx, and the backend is a Django API. Adding a rendering service for one card is disproportionate.

### 3.2 Recommended pipeline

```
1. User clicks "Download poster" on /persons/[id]
2. GET /api/persons/{id}/card/  →  CaseCardPayload (masked, exportable: true|false)
3. If !exportable → show the reason + link to the publication checklist. Stop.
4. Build the poster DOM: render <CaseInfoCard> with variant="export" into an
   off-screen container:
       position: fixed; left: -20000px; top: 0; width: 1080px;
   → one component, one data source, no second layout.
5. const { toPng } = await import('html-to-image');   // dynamic — keeps the dep out of the main bundle
   const dataUrl = await toPng(node, {
     pixelRatio: 2,          // 1080 → 2160px
     backgroundColor: getComputedStyle(document.documentElement).getPropertyValue('--color-bg-white'),
     cacheBust: true,
     filter: (el) => !el.hasAttribute('data-html2canvas-ignore'),   // skip any controls
   });
6. Trigger download via an <a download="case-ED-2024-0042.png"> + object URL.
7. Revoke the object URL; unmount the off-screen container.
```

`html-to-image` is the right library here rather than `html2canvas`: it clones the node into an SVG `foreignObject` and inlines computed styles, so the `em`-based scale, the `var()` tokens and the PT Sans webfont all survive — `html2canvas` re-implements layout and historically breaks on modern CSS (`:is()`, `oklch()`, container queries, `aspect-ratio`).

### 3.3 Cross-origin canvas taint — verified problem, with the fix

`html-to-image` must read the photo's pixels into the canvas. If the photo is cross-origin **without CORS headers**, the canvas is tainted and `toDataURL()` throws `SecurityError: Tainted canvases may not be exported`.

**Production:** `profile_image_url` is built by `_absolute_media_url` (`backend/cases/serializers.py:117-163`) from `settings.SITE_URL` → `https://cases.raisethevoices.org/testimonies/public-media/profiles/x.jpg`, served by nginx `location /testimonies/public-media/` (`scripts/nginx/rtv-cases`). The app and the image share an origin → **not tainted**.

**Dev:** `frontend/vite.config.ts` proxies `/testimonies/api` to `https://cases.raisethevoices.org` by default, and the API returns an absolute `SITE_URL` URL → the photo is cross-origin in dev. nginx sends **no** `Access-Control-Allow-Origin` for `/public-media/`. → **tainted in dev**.

**Fix (both directions, no server change):** in the card, resolve the photo to a **same-origin path** before rendering:

```ts
// same-origin path for the poster, so the canvas is never tainted
const toSameOrigin = (url: string) => {
  const p = new URL(url, window.location.origin).pathname;  // e.g. /testimonies/public-media/profiles/x.jpg
  return `${base}${p.replace(/^\/testimonies/, '')}`;         // re-apply the SPA base path
};
```

If the media host ever differs from the app host, this breaks — so it must be guarded by a check (`new URL(url).origin !== window.location.origin` → fall back to a proxied fetch). That check is worth writing explicitly rather than assuming.

### 3.4 CSP interaction — verified

`scripts/nginx/rtv-cases` sets, for every location:

```
Content-Security-Policy: default-src 'self'; img-src 'self' data: blob: https:;
  script-src 'self' 'unsafe-inline' https://accounts.google.com;
  style-src 'self' 'unsafe-inline'; font-src 'self' data:;
  connect-src 'self' https://accounts.google.com; ...
```

- `html-to-image` fetches the image and the font to inline them → governed by `connect-src 'self'`. A **same-origin** photo and the bundled PT Sans woff2 are fine; a cross-origin photo is blocked by CSP *before* the canvas-taint problem even arrives. §3.3's fix satisfies both.
- `style-src 'unsafe-inline'` is present → the `<style>` block `html-to-image` injects is allowed.
- `img-src` allows `data:` and `blob:` → the resulting data URL renders.
- `script-src 'self'` → the library is bundled, not loaded from a CDN. **Do not** load `html-to-image` from a CDN.

No CSP change is required.

### 3.5 Output size

1080×1350 at `pixelRatio: 2` → 2160×2700 PNG ≈ 3–8 MB depending on the photo. At `pixelRatio: 3` → 3240×4050, noticeably larger with no practical gain after social-platform compression. **Recommendation: `pixelRatio: 2`, PNG.** Add a JPEG option (`quality: 0.92`, `backgroundColor: '#fff'`) only if file size proves to be a problem in use — the PNG is the right default for text-heavy posters because JPEG fringing on red-on-white type is visible.

### 3.6 "Share" vs "Download"

`navigator.share` (Web Share API) is not present anywhere in the frontend and is **not** supported on desktop browsers in a useful form (files can be shared only via `navigator.canShare({files})`, which Chrome on desktop does not support). **Recommendation: ship Download (PNG) + Copy link. Do not build a Share sheet.** The clipboard precedent already exists at `frontend/src/lib/Toast.svelte:77-93` (with a graceful ⌘C fallback) — reuse that pattern for the "Copy link" action.

For the link to be meaningful, the case needs a **public URL**. `/persons/<id>` is publicly reachable for published persons (the `anon` Playwright project visits `/testimonies/persons/<id>`), so the copyable link is `https://cases.raisethevoices.org/testimonies/persons/<id>`. The card's OG tags already exist at `routes/persons/[id]/+page.svelte:635-641` (`og:type="profile"`).

### 3.7 The export button

- Not inside the card (it would be captured in the export).
- Rendered **only** when the server says `exportable: true`. Otherwise render a disabled button carrying the reason.
- The server is the only authority on `exportable` — the client must not compute it, or a user could patch the client and export an unapproved card.

---

## 4. Implementation Plan & Risks

### 4.1 Atomic steps

Each step leaves the tree working (tests pass, migrations apply) — `SYSTEM_RULES §3`.

| # | Step | Scope | Depends on |
|---|---|---|---|
| 0 | **Human decisions** (§5) — poster language, Ref format, header date, branding, "father" vs "parent" | — | — |
| 1 | `Person.public_reference` field + migration + unique validator + write-serializer entry | backend | 0 |
| 2 | `public_reference` in the person edit form + Zod form schema (`frontend/src/lib/schemas/personForm.ts`) + unit test | frontend | 1 |
| 3 | `backend/cases/card/` package: `CaseCardPayloadSerializer`, `EXPORT_SCHEMA` v1 + `export_schema.json` | backend | 1 |
| 4 | `GET /api/persons/{id}/card/` action on `PersonViewSet`, default-deny gate, `VIEWED` audit log | backend | 3 |
| 5 | Backend tests: masking matrix (one test per row of §1.4), anonymous 404 on unpublished, private report/media exclusion, schema-version pin (copy `SchemaVersionPinTests`) | backend | 4 |
| 6 | `src/lib/caseCardData.ts` — types + `buildCaseCardData` + `PERSON_STATUS_LABEL` + father/parent logic | frontend | 0, 2 |
| 7 | `src/lib/caseCardData.test.ts` — vitest, node env: earliest-report selection, empty-value row omission, missing photo, missing reference | frontend | 6 |
| 8 | `src/lib/CaseInfoCard.svelte` + the CSS in §2.4 + new tokens in `app.css:25-101` + animation list | frontend | 6 |
| 9 | Render `<CaseInfoCard>` in the main column of `/persons/[id]` above the Summary | frontend | 8 |
| 10 | Playwright spec: card renders on the detail page; anon project sees it; a person with no photo shows the placeholder; the row set matches the fixture | frontend | 9 |
| 11 | `src/lib/caseCardExport.ts` + `html-to-image` dependency + off-screen poster instance + same-origin photo URL | frontend | 10 |
| 12 | Download button gated on `exportable`; disabled state shows the missing-field reason | frontend | 11 |
| 13 | Playwright spec: export produces a PNG file (`page.waitForEvent('download')`) for an exportable fixture | frontend | 12 |
| 14 | Publication checklist panel listing the blank consent fields blocking a case | frontend | 5 |
| 15 | *(optional, later)* server-rendered OG image for the public case page; `(optional)` print stylesheet for A4/PDF | — | 12 |

### 4.2 Edge cases

| Edge case | Handling |
|---|---|
| Missing profile image (45%) | `.case-card-photo-placeholder`; photo row still occupies the grid cell so the two-column rhythm holds |
| Missing occupation (65%) / age (61%) / father (97%) | row omitted entirely |
| No `public_reference` | header shows "Ref: Not assigned"; export disabled |
| `reports[]` empty or all `date_start` null | abduction date row omitted |
| `date_start` after `last_known_date` | both rendered as stored; the card does not reorder or "correct" the data |
| Very long occupation / location / source label | `overflow-wrap: anywhere`, 2-line clamp; card height is content-driven, so the export is 1080px wide × measured height |
| Arabic or RTL content | **The app has no RTL support at all** — `dir="rtl"`, `:dir()` and RTL-aware CSS: 0 hits across `frontend/src`; `app.html` is `<html lang="en">`; physical properties (`left`/`right`) are used in places. Only 3 of 46 testimonials are non-English (`ar` ×2, `fr` ×1). A poster with `dir="rtl"` needs: `dir` on the card root, logical properties in the card CSS, and an Arabic-capable font (PT Sans has no Arabic coverage — `@fontsource/pt-sans` only). **Blocking for an Arabic poster.** |
| `public_identity_level == 'anonymous'` | name, age, occupation, father, photo all suppressed; "Identity withheld" replaces the title |
| `photograph_public == 'no'` | photo omitted from the **payload**, not just hidden in the UI |
| A private report (`is_private=True`) | excluded from the payload before any date/place is read from it |
| `Media.visibility != 'public'` | excluded from the payload |
| Browser blocks the download (Safari) | `a.download` + object URL; fall back to opening the data URL in a new tab |
| `html-to-image` throws (tainted canvas / font CORS) | catch → surface a plain message + "Copy link" as the fallback path; never a silent failure |
| A case with a 5 MB photo | downscale before embedding, or the export PNG exceeds browser canvas limits (Safari: 16.7 M px) |
| Two users exporting the same case | stateless; no server state — but `is_exported`-style flags, if added later, must not gate re-export |

### 4.3 Risk register

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | **The consent/publication fields are 0% populated.** The export button never appears until data entry happens. | **High** — blocks the feature's purpose | Step 14's checklist; surface the fill-rate gap to the humans before committing to the build; consider a backfill from `authoritative_source` rows (146 persons carry an external source + URL) |
| 2 | A shareable image of a disappeared person is generated without consent | **Critical** | Server-side default-deny gate (§1.4); `exportable` computed server-side only; the client never decides |
| 3 | The poster is a **new public surface** for data that was never meant to leave the casework UI | High | The card payload is a separate, masked projection — not a new serializer over the same model; every field in it is opted in explicitly |
| 4 | An Arabic reference poster cannot be built on this frontend today | High | §4.2 RTL row; decide the language in step 0 before any CSS is written |
| 5 | Dev-time canvas taint breaks the export during development | Medium | §3.3 same-origin URL resolution |
| 6 | `html-to-image` adds a runtime dependency to a dependency-light frontend | Low | Dynamic `import()` so it is a separate chunk, loaded only on click; `package.json` gains one dependency |
| 7 | The card renders client-side only (no SSR load fn) → no server-rendered OG image | Medium | Optional step 15; the copy-link fallback covers it |
| 8 | Two layout implementations (screen + export) drift | Low | One component, one stylesheet, `em`-based scale, `case-card--export` modifier for the export clone |
| 9 | `Person.public_reference` uniqueness collisions | Low | Validator with a friendly message; optional auto-generation that never overwrites a human value |
| 10 | The card grows the person detail page past one screen | Low | The card replaces the sidebar's redundant photo+field list rather than duplicating it |

### 4.4 Test plan

- **Backend (pytest):** the masking matrix (§1.4) — one test per rule, each asserting the payload for a **published** person and for an **unpublished** one (404 for anonymous); private report and non-public media exclusion; `public_identity_level` variants; schema-version pin test copied from `cases/testimonials/tests.py`.
- **Frontend unit (vitest, `environment: node`):** `buildCaseCardData` — earliest/latest report selection, empty-row omission, missing photo → `null`, missing reference → `null`, label mapping for every `current_status` value, hashtag slugification.
- **Frontend E2E (Playwright):** the card renders on `/persons/[id]` in the `anon` and `advocate` projects; the metadata rows match the fixture; the placeholder appears for a person with no photo; the export produces a file for an exportable fixture and is disabled with a reason otherwise. Existing specs to keep green: `tests/family-link.spec.ts` (untracked, currently in the working tree), `tests/dashboard.spec.ts`, `tests/form-audit.spec.ts`, `tests/testimonial-workflow.spec.ts`.
- **Commands:** `cd frontend && npm run check && npm test`; `cd backend && .venv/bin/python manage.py test cases`; `npm run gen:api:check` if the OpenAPI schema changes (it will — a new endpoint).
- **Manual:** load the page as a person on a 375px viewport and at 1440px; export at both; open the PNG and confirm the type is correct, the photo is present, and nothing was cut off.

---

## 5. Open decisions — required before implementation

Per the project rule *"Never design UX without human input"*, these need a human answer, not an inference:

1. **Language and direction.** Is the poster Arabic, English, or both? Is the reference poster RTL? (The app has no RTL support and only 3 of 46 testimonials are non-English.) This decision changes the CSS, the font, and the data pipeline.
2. **The poster's field legend.** I have not seen the reference image, so rows like "R/O", "S/O" and the exact abduction fields are unmapped. Send the image and I will map every row.
3. **"Father's name" — father or parent?** `FamilyRelationship.RelationType` has only `parent`/`child`/`sibling`/`spouse`/`other` (`models.py:977-982`), and the API's `family[]` payload carries no gender, so "father" is not derivable today. Either add gender to the family payload (small backend change) or label the row "Parent".
4. **The header date's meaning** — date the case was received, date entered into the platform, date of publication, or date of the incident? The four candidate Person fields are 0% populated; `created_at` is the only 100% one.
5. **The "Ref" format and who assigns it** — `ED-2024-0042` (prefix per category + year + sequence)? Human-assigned or auto-generated? §1.5 proposes a new `Person.public_reference` field.
6. **Footer branding** — organisation name, logo file, and link target. There is **no logo asset** in the repo (only `frontend/src/lib/assets/favicon.svg`), so a logo must be supplied.
7. **Whether the poster shows the person's full name by default**, and what happens when `public_identity_level` is blank — recommended: "Identity withheld", export disabled, until someone explicitly sets the level.
8. **Export dimensions and format** — 1080×1350 PNG at `pixelRatio: 2` recommended; JPEG as an option.
9. **Whether an advocate-facing "publication checklist" (step 14) is in scope** — with the consent fields at 0%, this is the only way a human learns what is blocking a case.

---

## Appendix — evidence index

| Fact | Where |
|---|---|
| `Person` model, all fields | `backend/cases/models.py:255-535` |
| `Report` model, all fields | `backend/cases/models.py:546-840` |
| `Media` model + visibility tiers | `backend/cases/models.py:886-975` |
| `FamilyRelationship` + relation types | `backend/cases/models.py:976-1030` |
| `Testimonial` model | `backend/cases/models.py:1271-1420` |
| `PersonDetailSerializer` (`fields='__all__'`) | `backend/cases/serializers.py:418-531` |
| Private-field stripping | `backend/cases/serializers.py:15-16`, `:525-531`, `:306-324` |
| Absolute media URL resolution | `backend/cases/serializers.py:117-163` |
| `PersonViewSet` (permissions, queryset) | `backend/cases/views.py:162-320` |
| Media trees + default-deny philosophy | `backend/cases/storage.py` |
| Testimonial export contract + JSON Schema v1 | `backend/cases/testimonials/export.py`, `export_schema.json` |
| Server-side masking doctrine | `backend/cases/testimonials/serializers.py:32-46` |
| Design tokens | `frontend/src/app.css:25-101` |
| `.card`, `.badge`, fade-in list | `frontend/src/app.css:345-391`, `:206-215` |
| Person detail page structure | `frontend/src/routes/persons/[id]/+page.svelte:643-1178` |
| Existing card patterns | `frontend/src/lib/PersonCard.svelte`, `frontend/src/lib/TestimonialCard.svelte` |
| Photo component + fallbacks | `frontend/src/lib/MediaImage.svelte:76-140` |
| API client | `frontend/src/lib/api.ts:85-320` |
| Zod overlays (Date conversion) | `frontend/src/lib/schemas/overlays.ts:29-88` |
| Test setup | `frontend/vitest.config.ts`, `frontend/playwright.config.ts`, `frontend/tests/` |
| CSP + media routing + base path | `scripts/nginx/rtv-cases` |
| Dev proxy targets | `frontend/vite.config.ts` |
