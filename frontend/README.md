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

## Media section (Case Details view)

The Media grid on the Case Details page renders each `person.media_files`
entry in a **refined card** that matches the Summary card's visual language:

- White background, light border (`--color-border-light`), 6px radius,
  subtle `box-shadow: 0 1px 2px rgba(0,0,0,0.04)`.
- Comfortable inner padding: `1.25rem 1.5rem`.
- `line-height: 1.65` for readable text.
- Cards are arranged in the existing `.media-grid` (200px min column, 1rem gap).
- Header still uses `.view-title` — consistent with Summary / Reports / Media.
- Images inside cards are capped at `max-width: 100%`, centered, with a 4px radius.
- Description text is muted (`var(--color-text-muted)`), 0.85rem.
- Links use the primary teal color, no underline until hover.

### Scope

This is a **CSS + structural** change only. The underlying data flow
(photo vs. URL rendering, description duplication, link targets) is
left exactly as it was for a separate fix.

### Classes added to the file-level `<style>` block

| Selector          | Purpose                                          |
|-------------------|--------------------------------------------------|
| `.media-card`     | Card wrapper (white bg, light border, subtle shadow) |
| `.media-card img` | Photo styling (centered, max-width, 4px radius)  |
| `.media-card p`   | Muted description text                           |
| `.media-card a`   | External link styling                            |
| `.media-card a:hover` | Underline on hover                          |

### Manual verification checklist

Before merging any change to the Media section:

1. Photo media cards render with white background, light border, 6px radius,
   and a subtle shadow (not heavy/harsh borders).
2. URL-only media cards render with the same refined wrapper.
3. Photo inside a card is centered, never exceeds the card width, and has a
   subtle 4px radius.
4. Description text below a photo/link is muted and not crowded against edges.
5. Cards in the grid have a 1rem gap between them.
6. Long URLs inside cards wrap cleanly (no overflow).
7. Hovering a URL link shows an underline.
8. The "Media" header still uses `.view-title` (primary-tone background).
9. No changes to `.incident-container` styling (Reports still use it).
10. No template/data logic changed — the existing URL+description duplication
    still renders exactly as before.
