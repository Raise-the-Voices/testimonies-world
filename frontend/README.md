# Frontend

This directory is the SvelteKit frontend for **Testimonies.world**.

**The main project README is at [`../README.md`](../README.md)** — start there
for project context (stack, dev URLs, data model, permissions, deployment).

This README is for **frontend-specific** concerns: development commands,
the design system, and per-component polish documentation for the Case
Details page.

---

## Quick reference (frontend only)

### Install + run

```sh
cd frontend
npm install                                  # first time / after package.json changes
npm run dev                                  # vite dev server (default :5173)
PUBLIC_BASE_PATH=/testimonies npm run dev -- --host 0.0.0.0 --port 3040
npm run check                                # type-check via svelte-check
npm run test                                 # vitest unit tests
npm run build                                # production build → ./build/
npm run preview                              # preview the production build locally
```

### Project layout (this directory)

```
frontend/
├── src/
│   ├── routes/             Pages (SvelteKit file-based routing)
│   ├── lib/                Components, stores, API client
│   ├── app.css             Global styles + design system tokens
│   ├── app.d.ts
│   └── hooks.server.ts
├── static/                 Static assets (favicon, etc.)
├── svelte.config.js
├── vite.config.ts
├── tsconfig.json
└── package.json
```

### Production build env vars (from `../SYSTEM_RULES.md` §3)

```sh
PUBLIC_BASE_PATH="" \
ORIGIN=https://cases.raisethevoices.org \
  npm run build
```

Missing these causes path-drifting and stale asset hashes after deploy.

---

## Case Details — design system & component polish

The Case Details page is the most-trafficked surface of the app. All sections
have been unified into a single design system. Each section below has a
**manual verification checklist** for future contributors.

- [Design system (global tokens, animation, hover)](#design-system-global)
- [Reports section](#reports-section-case-details-view)
- [Summary section](#summary-section-case-details-view)
- [Profile sidebar](#profile-sidebar-case-details-view)
- [Media section](#media-section-case-details-view)
- [Sidebar metadata cards](#sidebar-metadata-cards-case-details-view)

---

## Reports section (Case Details view)

The Reports list in the Case Details page (`src/routes/persons/[id]/+page.svelte`)
renders as a **single-open accordion** — each row collapses to a compact header
(badge + title + date + chevron), with the full narrative revealed on click.

### Source-type badges

Every report carries a `source_type` (`firsthand`, `secondhand`, `news`, `document`).
A colored badge is rendered for the row's type using these palette-matched
variants in `src/app.css` (same family as the existing status badges):

| source_type | Background | Text     |
|-------------|------------|----------|
| `firsthand` | `#fed7d7`  | `#c53030`|
| `secondhand`| `#feebc8`  | `#c05621`|
| `news`      | `#bee3f8`  | `#2b6cb0`|
| `document`  | `#e2e8f0`  | `#4a5568`|

Display labels live in a `sourceTypeLabels` map at the top of the
`+page.svelte` `<script>` block. When the backend adds a new `SourceType` value,
add it to that map and add a matching `.badge-source-<value>` rule.

### URL handling in narrative text

`scanNarrative(text)` parses the narrative into a `[{ kind: 'text' | 'url', value }]`
array. URLs become compact **external-link buttons** (`.report-link-btn`)
showing only the domain (e.g. `hrcp-web.org` + `↗`) and opening in a new tab.
Trailing punctuation (`,`, `.`, `;`, `)`) is stripped from the URL so
"see https://example.com)." renders as a button + a literal `.)`.

### Manual verification checklist

Before merging any change to the Reports section:

1. Open a case page with at least 2 reports → confirm only one is open at a time.
2. Click a collapsed row → chevron rotates 90°, body slides in.
3. Click the open row → body collapses, chevron returns.
4. Narrative containing a bare `https://example.com` renders as a button, not raw text.
5. Narrative containing `https://example.com).` → URL has no trailing punctuation;
   the `.)` appears as plain text after the button.
6. Narrative containing a bare `www.example.org/page` (no protocol) is detected and
   normalized to `https://www.example.org/page` on click.
7. Multiple URLs in one paragraph render as multiple buttons.
8. Narrative with no URLs is unchanged (passthrough).
9. Each source type renders with its correct badge color.
10. The `Add Report` button (volunteers) and `Edit Case` button (sidebar) still
    appear when the user has the right role — the accordion does not affect them.
11. Keyboard: `Tab` reaches each report header, `Enter`/`Space` toggles it,
    `aria-expanded` reflects state.

## Summary section (Case Details view)

The Summary card on the Case Details page renders `person.summary_narrative`
in a **polished, scannable** layout:

- Each newline-separated block is rendered as its own `<p>` with a 1rem
  bottom margin and `line-height: 1.65` (≈ Tailwind's `leading-relaxed`).
  The last paragraph has no bottom margin.
- Detected dates are wrapped in `<strong class="summary-date">` (teal,
  bold) for quick scanning. Covered formats:
  - `July 25, 2025` / `Jul 25 2025` / `July 25th, 2025` (US, with ordinals)
  - `25 July 2025` (international)
  - `2025-07-25` (ISO)
  Numeric dates like `7/25/2025` and bare years like `2025` are
  **not** auto-bolded (too ambiguous / too aggressive).
- If `person.authoritative_source` is set, a muted footer strip renders
  below the body: `Source: <name>` with a `↗` link to
  `person.authoritative_url` when present.

### Classes added in `src/app.css`

| Class                  | Purpose                                            |
|------------------------|----------------------------------------------------|
| `.summary-card`        | Refined card wrapper (lighter border, subtle shadow) |
| `.summary-card-body`   | Inner padding (`1.25rem 1.5rem`)                   |
| `.summary-narrative p` | Paragraph spacing + line-height                    |
| `.summary-date`        | Teal bold for detected dates                       |
| `.summary-footer`      | Muted footer strip with source attribution         |
| `.summary-footer-link` | External link styling                              |
| `.summary-footer-icon` | `↗` arrow icon                                     |

### Manual verification checklist

Before merging any change to the Summary section:

1. Narrative with one paragraph renders as a single `<p>` with no extra bottom margin.
2. Narrative with multiple newline-separated paragraphs renders multiple `<p>` elements,
   each with `1rem` bottom margin except the last.
3. `July 25, 2025` inside narrative is wrapped in `<strong class="summary-date">`
   and styled teal + bold.
4. `25 July 2025` (international) and `2025-07-25` (ISO) are also detected and bolded.
5. `7/25/2025` is **not** bolded (numeric ambiguity).
6. Year-only mentions like `2025` are **not** bolded.
7. Ordinals like `1st`, `25th` are detected (`April 1, 2026`).
8. Narrative with no dates renders unchanged (no false positives).
9. Case with `authoritative_source` + `authoritative_url` → footer renders
   with `Source:` label, link text, and `�` icon.
10. Case with `authoritative_source` but no URL → footer renders the text
    without a link.
11. Case with no `authoritative_source` → footer is absent (no empty box).
12. Card border + shadow render on white background; not affected by `.incident-container`
    styling of Reports/Media cards.

## Profile sidebar (Case Details view)

The right-hand profile sidebar (`<div class="sidebar-top">` in
`src/routes/persons/[id]/+page.svelte`) renders the person's identifying
metadata in a polished **label/value profile sheet**:

- **Profile photo**: 180×180, `border-radius: 8px` (≈ Tailwind `rounded-lg`),
  `object-fit: cover`. Placeholder (no image) is a same-size box with a
  dashed border so layout doesn't shift.
- **Aliases**: rendered italic at `0.75rem` with muted color — clearly
  differentiated from the legal name above.
- **Status badge**: own breathing room (`0.75rem 0 1rem 0` margin).
- **Field rows**: semantic `<dl>`/`<dt>`/`<dd>` pairs. Labels are small
  uppercase muted (`0.72rem`), values are right-aligned with
  `word-break: break-word` so long URLs/locations wrap.
- **Medical row**: hidden when `medicalLabels[person.medical_status] === 'Deceased'`
  to avoid duplicating the "DECEASED" status badge above. Other statuses
  (Healthy, Critical, Health Concerns, Unknown) still render.
- **Source footer**: separated from the field list by a top border,
  styled as a small uppercase label + the source name (with a `↗`
  external link when `authoritative_url` is present).

### Classes added in the file-level `<style>` block

| Class                       | Purpose                                    |
|-----------------------------|--------------------------------------------|
| `.profile-photo`            | 180×180 rounded photo                      |
| `.profile-photo-placeholder`| Matching rounded placeholder (dashed border) |
| `.sidebar-aliases`          | Italic muted aliases                       |
| `.sidebar-status`           | Margin around the status badge             |
| `.sidebar-fields`           | `<dl>` wrapper, resets default margins     |
| `.sidebar-field`            | Row flex container with bottom border      |
| `.sidebar-field dt`         | Small uppercase muted label                |
| `.sidebar-field dd`         | Right-aligned value                        |
| `.sidebar-source`           | Footer strip with top border separator     |
| `.sidebar-source-label`     | Small uppercase "SOURCE" label             |
| `.sidebar-source-link`      | External link styling                      |
| `.sidebar-source-icon`      | `↗` arrow icon                             |

### Manual verification checklist

Before merging any change to the profile sidebar:

1. Profile image renders rounded (8px), no stray border lines on the wrapper.
2. Placeholder (no image) renders a same-size box with a dashed border.
3. Aliases are italic, smaller (`0.75rem`), and visually subordinate to legal name.
4. Status badge has clear breathing room above the field list.
5. Each label (`Country`, `Location`, etc.) is small uppercase muted; each
   value is regular weight and right-aligned.
6. Each field row has a thin bottom border; the last field has none.
7. Long values wrap cleanly (no overflow off the sidebar edge).
8. Case with `medical_status: deceased` → the **Medical** row is **not**
   rendered (the DECEASED status badge above conveys it).
9. Case with `medical_status: critical` → the **Medical** row **is**
   rendered with label "Critical".
10. Case with no `medical_status` → the **Medical** row is **not** rendered.
11. Case with `authoritative_source` + URL → footer renders with `SOURCE`
    label, link, and `↗` icon.
12. Case with `authoritative_source` only (no URL) → footer renders plain text.
13. Case with no `authoritative_source` → footer is absent (no empty strip).
14. The other sidebar blocks (Categories, Evidence Tier, Family, Created/Updated)
    are untouched and still render with the old `.sidebar-bot` styling.

## Media section (Case Details view)

The Media list on the Case Details page renders each `person.media_files`
entry as a polished **vertical card** in a stacked list:

- **Vertical stack layout** (`.media-list` flex column, 1rem gap) — replaces
  the previous grid layout. Reads as a clean list rather than a chaotic gallery.
- Each item is a `.media-item-card`: white background, `--color-border-light`
  border, 6px radius, subtle `box-shadow: 0 1px 2px rgba(0,0,0,0.04)`, padding
  `1.25rem 1.5rem`.
- **Two-column inside each card** (only when the media has a photo file):
  120×120 thumbnail on the left (`.media-item-thumb`), body block on the right.
  Non-photo media takes just the body block at full width.
- **Body block** (`.media-item-body`):
  - **Meta row** (`.media-item-meta`): small uppercase `media_type` label +
    a `visibility` badge (only shown when not `public`, to avoid noise).
  - **Description** (`.media-item-description`): the media's `description`
    text at `line-height: 1.6`, `font-size: 0.92rem`. Appears once.
  - **Action button** (`.media-item-action`): a pill-shaped primary teal
    button labeled **"View Source ↗"**. Opens the URL in a new tab with
    `target="_blank"` and `rel="noopener noreferrer"`. Only renders when
    `media.url` is set.
- **No more raw URLs anywhere in the card body** — the URL is hidden
  inside the action button.
- **No more URL+description duplication** — previously the URL was rendered
  as `<a>{description}</a>` AND the description appeared again as `<p>`. The
  new structure renders each only once.
- **Header still uses `.view-title`** — consistent with Summary / Reports /
  Metadata section headers.

### Classes added to the file-level `<style>` block

| Selector                | Purpose                                              |
|-------------------------|------------------------------------------------------|
| `.media-list`           | Vertical stack wrapper (flex column, 1rem gap)       |
| `.media-item-card`      | Card wrapper (white bg, light border, subtle shadow) |
| `.media-item-thumb`     | 120×120 photo thumbnail                              |
| `.media-item-body`      | Right-side body block                                |
| `.media-item-meta`      | Meta row (type + visibility badges)                  |
| `.media-item-type`      | Small uppercase media-type label                     |
| `.media-item-visibility`| Visibility badge (only for restricted/sensitive)     |
| `.media-item-description` | Description text (line-height 1.6, 0.92rem)        |
| `.media-item-action`    | Pill-shaped "View Source ↗" button (primary teal)    |
| `.media-item-action-icon` | Icon font-size tweak                              |

### Removed (dead code after this PR)

- `.media-grid` — old grid wrapper, no longer used
- `.media-card` + `.media-card img/p/a/a:hover` — old card rules, replaced
  by `.media-item-card` family

### Manual verification checklist

Before merging any change to the Media section:

1. Media items render as a vertical stack (one card per row), not a grid.
2. Each card has white background, light border, 6px radius, subtle shadow,
   padding `1.25rem 1.5rem`.
3. Photo media shows a 120×120 thumbnail on the left of the card body.
4. Non-photo media (no file but URL) shows just the body block, full width
   — no empty thumbnail column.
5. Meta row shows the media type label (e.g. `photo`, `document`) in small
   uppercase muted text.
6. Visibility badge (`restricted` or `sensitive`) only renders when not
   `public` — no badge for public media.
7. Description renders once as a `<p>` with `line-height: 1.6`. Never
   duplicated.
8. When `media.url` is set, a **"View Source �"** pill button appears below
   the description, opens the URL in a new tab.
9. **No raw URL text appears anywhere in the card body.**
10. Long descriptions wrap cleanly inside the body block.
11. The "Media" header still uses `.view-title` (primary-tone background).
12. The old `.media-grid` and `.media-card*` classes are gone from the
    codebase (dead CSS removed).

## Sidebar metadata cards (Case Details view)

The three lower sidebar blocks — **Categories**, **Evidence Tier**, and
**Created/Updated** — now use a refined `.meta-card` wrapper that matches
the Summary card's visual language:

- White background, `--color-border-light` border, 6px radius,
  subtle `box-shadow: 0 1px 2px rgba(0,0,0,0.04)`.
- Internal padding `1.25rem 1.5rem`, `line-height: 1.65`.
- Header strip in `--color-primary` teal (same family as `.view-title` and
  `.sidebar-header-2`), uppercase letterspaced.
- Categories rendered as a semantic `<ul>` with bottom-border separators.
- Evidence Tier value rendered in primary teal at 1rem / 600 weight.
- Created/Updated rendered as `.meta-row` label/value pairs — the same
  pattern as the profile sidebar's field rows, so the whole sidebar reads
  as one design system.

### Scope

- **Categories**, **Evidence Tier**, and **Created/Updated** are polished.
- The **Family** block is intentionally left untouched (still uses the old
  `.sidebar-bot` styling). Follow-up if you want Family to match.

### Classes added to the file-level `<style>` block

| Class                | Purpose                                            |
|----------------------|----------------------------------------------------|
| `.meta-card`         | Card wrapper (white bg, light border, subtle shadow) |
| `.meta-card-header`  | Primary teal uppercase header strip                |
| `.meta-card-body`    | Inner padding + line-height                        |
| `.meta-list` + `li`  | Categories list (no bullets, bottom-border rows)   |
| `.meta-tier`         | Evidence Tier value styling                        |
| `.meta-row`          | Created/Updated flex row                           |
| `.meta-label`        | Small uppercase muted label                        |
| `.meta-value`        | Right-aligned value text                           |

### Manual verification checklist

Before merging any change to the sidebar metadata cards:

1. Categories card has white background, light border, subtle shadow, 6px radius.
2. Categories card has a primary teal uppercase header strip ("CATEGORIES").
3. Each category renders as an `<li>` in a `<ul>`, with no bullet markers.
4. Each category has a thin bottom border; the last one has none.
5. Evidence Tier card uses the same wrapper as Categories.
6. Evidence Tier value renders in primary teal at 1rem / bold.
7. Created/Updated card has no header strip (just body padding).
8. Created and Updated each render as a label/value row with the same pattern
   as the profile sidebar fields.
9. Labels (CREATED / UPDATED) are small uppercase muted; values right-aligned.
10. The Family block still uses the old `.sidebar-bot` styling (intentional).
11. No changes to `.summary-card`, `.incident-container`, `.media-card`, or
    `.view-title` (all other sections still render exactly as before).

## Design system (global)

The Case Details page uses a **single unified design system** for all
card-like surfaces (Summary, Reports, Media, Profile sidebar, Metadata
cards, Profile photo). Single source of truth via CSS variables in
`:root` of `src/app.css`.

### Tokens

| Variable               | Value                                       | Purpose                    |
|------------------------|---------------------------------------------|----------------------------|
| `--color-border-light` | `#e2e8f0`                                   | All light card borders     |
| `--radius-card`        | `8px`                                       | All card corner radius     |
| `--shadow-card`        | `0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06)` | Default subtle elevation   |
| `--shadow-card-hover`  | `0 4px 12px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04)` | Hover shadow elevation     |
| `--transition-card`    | `0.2s ease`                                 | Card transition timing     |
| `--card-padding`       | `1.25rem 1.5rem`                            | Standard inner card padding|

### Unified rules

All card surfaces:
- **Background**: pure white `#ffffff` (`var(--color-bg-white)`)
- **Border**: `1px solid var(--color-border-light)` (was `#ddd`, now `#e2e8f0`)
- **Radius**: `var(--radius-card)` (8px — was mixed 4px/6px/8px)
- **Shadow**: `var(--shadow-card)` (was `0 1px 2px rgba(0,0,0,0.04)` hardcoded)
- **Padding**: `var(--card-padding)` (where applicable)
- **Entrance animation**: `fadeSlideUp` 0.4s ease (opacity 0 → 1, translateY 8px → 0)
- **Hover** (except `.incident-container`): shadow elevation + border-color shift to
  primary teal, both at `0.2s ease`

### Cards covered

| Class                  | Where                  | What changed                          |
|------------------------|------------------------|---------------------------------------|
| `.summary-card`        | Summary                | Switched to `var(--shadow-card)` etc. |
| `.incident-container`  | Reports accordion      | Was `thin solid black`/`4px`/no shadow → unified white/light/8px/shadow |
| `.media-card`          | Media cards            | Switched to `var(--shadow-card)` etc. |
| `.sidebar-top`         | Profile sidebar        | Was `thin solid black`/`4px`/no shadow → unified |
| `.sidebar-bot`         | Family sidebar block   | Was `thin solid black`/`4px`/no shadow → unified |
| `.meta-card`           | Categories/Evidence Tier/Dates | Switched to `var(--shadow-card)` etc. |
| `.profile-photo` + `.profile-photo-placeholder` | Profile image | Switched to `var(--radius-card)` etc. |

### Animation rules

- `@keyframes fadeSlideUp` (0.4s) — major card sections
- `@keyframes fadeSlideUpSmall` (0.35s) — staggered list items
- `.fade-in-stagger > *:nth-child(N)` — applies 0.05s delay per item (up to 8)
- `@media (prefers-reduced-motion: reduce)` — all animations + transitions
  disabled for users who opt out at the OS level

### Scope notes

- **No template logic changes** (one CSS class added on the media grid wrapper
  for the staggered cascade; everything else is class-targeting in CSS).
- **Reports accordion hover is intentionally skipped** — the accordion has
  its own click behavior via `.report-card-header`; outer hover would
  confuse the expand/collapse mental model.
- **Sidebar `.sidebar-bot` (Family block) does get hover** — it has no
  internal interactivity so the elevation is purely informative.

### Manual verification checklist

Before merging any change to the design system:

1. `--color-border-light` value is `#e2e8f0` (not `#ddd`).
2. All major cards (Summary, Reports, Media, Profile sidebar, Metadata) render
   with **identical** white background, 8px radius, and subtle shadow.
3. No card uses `thin solid black` borders anywhere.
4. On page load, cards fade in from below (opacity 0 → 1, translateY 8px → 0).
5. Media list items fade in cascade (each item delayed 0.05s after the previous).
6. Hovering Summary / Media / Profile sidebar / Metadata cards elevates the
   shadow and shifts the border to teal — both transitions are smooth (0.2s).
7. Hovering a Reports accordion card does **not** elevate the shadow (intentional).
8. With OS-level "Reduce motion" enabled, no animations or hover transitions play.
9. CSS variables (`var(--radius-card)`, `var(--shadow-card)`, etc.) are
   defined exactly once in `:root` — no hardcoded duplicates in component styles.
10. Build succeeds with `PUBLIC_BASE_PATH=""` (production env).
