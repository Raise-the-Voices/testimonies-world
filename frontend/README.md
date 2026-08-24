# sv

Everything you need to build a Svelte project, powered by [`sv`](https://github.com/sveltejs/cli).

## Creating a project

If you're seeing this, you've probably already done this step. Congrats!

```sh
# create a new project
npx sv create my-app
```

To recreate this project with the same configuration:

```sh
# recreate this project
npx sv@0.12.4 create --template minimal --types ts --no-install frontend
```

## Developing

Once you've created a project and installed dependencies with `npm install` (or `pnpm install` or `yarn`), start a development server:

```sh
npm run dev

# or start the server and open the app in a new browser tab
npm run dev -- --open
```

## Building

To create a production version of your app:

```sh
npm run build
```

You can preview the production build with `npm run preview`.

> To deploy your app, you may need to install an [adapter](https://svelte.dev/docs/kit/adapters) for your target environment.

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
