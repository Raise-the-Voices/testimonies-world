# Motion report — testimonies.world

**Date:** 2026-11-08 · **Scope:** `frontend/` (SvelteKit 2 / Svelte 5.57.1) · 21 pages, 61 components
**Status:** the finding stands as written; the work is now partly built. Phases 0–2, the status timeline, the token layer, the nav drawer and the view toggle are on `feat/motion-system` (PR #196). Every "current state" line cites a file and line as it was on 2026-11-07; every "proposal" line is mine, not the repo's. Character and scope confirmed 2026-11-07 (§8).

---

## 1. The finding in one paragraph

The project already has motion — but it is **ad-hoc, not a system**. There is exactly **one** motion token (`--transition-card`) against roughly **fifteen** hardcoded durations and easings, and **eight** Svelte `transition:` directives that **ignore `prefers-reduced-motion`** because Svelte runs them through the Web Animations API, which no CSS media query can switch off. 22 of 61 components and 7 of 21 pages have no motion at all, including the chart and the timeline — the two surfaces where motion carries the most meaning. The work is not "add animation"; it is **make the existing motion consistent, make it obey the accessibility setting, and then spend it where a person actually feels it**.

---

## 2. What is there today (verified)

### 2.1 Primitives in use

| Primitive | Where | Count |
|---|---|---|
| Svelte `fly` / `fade` transitions | `Modal.svelte:29`, `Toast.svelte:19`, `Banner.svelte:14`, `ReportForm.svelte:48`, `MediaUploadModal.svelte:15`, `dashboard/+page.svelte:42`, `casework/+page.svelte:32`, `persons/[id]/report/+page.svelte:22` | 8 files |
| Svelte `animate:` directive | — | **0** |
| `svelte/motion` (`spring`, `tweened`) | — | **0** |
| `svelte/easing` | — | **0** |
| CSS `@keyframes` | `app.css:255,259`, `Skeleton.svelte:172`, `ReportForm.svelte:817,1110`, `ConfirmModal.svelte:148`, `+layout.svelte:527`, `persons/[id]/edit:1325`, `casework/+page.svelte:674`, `casework/new:923`, `submit/+page.svelte:2226` | 9 files |
| CSS `transition:` | spread across 25 files | — |
| Third-party animation library | — | **none** (`package.json` has no animation dependency) |

Everything is hand-rolled and built on Svelte's built-ins. Nothing to uninstall, nothing to license.

### 2.2 The token layer is one line deep

> This section is a snapshot of the code before the motion system landed on
> this branch. Every literal listed here is now a token — see §4.1 and §9.

`src/app.css:102`

```css
--transition-card: 0.2s ease;
```

Everything else is a literal at the point of use:

```
0.15s ease   Bell.svelte:223, FilterToolbar.svelte:180,199, app.css:518,
             MediaImage.svelte:159, WorkflowActions.svelte:491,650,685,
             ActivityItem.svelte:151, watchdog:272, persons/[id]:1665
0.18s ease   ViewToggle.svelte:93, app.css:765
0.2s ease    TestimonialCard.svelte:152, +layout.svelte:351,428
0.25s ease   +layout.svelte:466  (nav drawer)
0.35s ease   app.css:281  (stagger)
0.4s ease    app.css:266  (entrance)
150/200/220 ms (JS)   Modal.svelte:135,147; Toast.svelte; Banner.svelte:57;
                      ReportForm.svelte:430
```

### 2.3 Easing

Svelte's transition default is **`linear`** — `node_modules/svelte/src/internal/client/dom/elements/transitions.js:382`:

```js
const { delay = 0, css, tick, easing = linear } = options;
```

No file in `src/` imports `svelte/easing`. Every JS-driven transition in the project therefore animates **linearly**, while the hand-written CSS uses `ease`. The two systems do not match.

### 2.4 Reduced motion — present in 28 files, ineffective where it matters

28 files carry an `@media (prefers-reduced-motion: reduce)` block. The pattern is:

```css
@media (prefers-reduced-motion: reduce) {
  .modal, .modal-overlay { transition: none; }   /* Modal.svelte:266-271 */
}
```

This kills **CSS** transitions. It cannot kill Svelte's `transition:` directives, because Svelte 5 applies them with the Web Animations API — `transitions.js:476`:

```js
animation = element.animate(keyframes, { duration, fill: 'forwards' });
```

WAAPI animations are not CSS animations; a CSS media query does not reach them. `dashboard/+page.svelte:870` goes further and sets `animation-duration: 0s !important` on every descendant — that also does not touch WAAPI. **Net effect: a user with "reduce motion" enabled still gets the modal slide, the toast fly-in, the banner drop, the form-error slide and the dashboard fade.** The current reduced-motion handling is honest-looking and does not work.

Svelte ships the fix and this repo is on a version that has it — `node_modules/svelte/src/motion/index.js:31`:

```js
export const prefersReducedMotion = new MediaQuery('(prefers-reduced-motion: reduce)');
```

(added in Svelte 5.7.0; installed here: **5.57.1**).

### 2.5 The entrance animation is one hardcoded class list

`src/app.css:255-300` defines `fadeSlideUp` / `fadeSlideUpSmall` and applies them to a fixed list of **eight** class names:

```css
.summary-card, .media-item-card, .meta-card, .incident-container,
.sidebar-top, .sidebar-bot, .profile-photo, .profile-photo-placeholder {
  animation: fadeSlideUp 0.4s ease both;
}
```

These are person-detail page classes. Every other page gets nothing from it.

The stagger is CSS `nth-child`, hardcoded to eight children (`app.css:281-290`). A ninth item gets **no delay rule** and therefore animates at 0ms, out of order with the rest.

### 2.6 Coverage map

Zero motion, verified by grep over `transition:`, `animation:`, `@keyframes`, `transform: translate`:

**Pages with no motion (7 of 21)** — `contacts/new`, `dashboard/audit-logs`, `statistics`, `testimonials` (list), `testimonials/[id]` (detail), `testimonials/[id]/edit`, `testimonials/new`.

**Components with no motion (22 of 61)** — including two that most deserve it:

- `StatusBreakdownChart.svelte` — renders an SVG bar chart with static segment widths (`StatusBreakdownChart.svelte:64,86`). The chart tells a story about how many people are in each custody status; a one-shot bar growth makes that legible in a way a static bar does not.
- `StatusHistoryTimeline.svelte` — renders an ordered list of status changes (`:114-147`) with no entrance, no connect-the-dots line between events. It has also never reached the page: `PersonDetailSchema` strips every key it does not declare, `status_history` was not among them, and the feed has been empty on every case since it was added in `96d634f`. Found while building the timeline; see G10.
- Also: `StatusTransitionBanner.svelte`, `DashboardCard.svelte`, `ErrorCard.svelte`, `ErrorState.svelte`, `TestimonialForm.svelte`, `PersonPicker.svelte`, `PersonMultiPicker.svelte`, `MediaField.svelte`, `SourcesField.svelte`, `StatusBadge.svelte`, `AuditLogsFilters.svelte`, `Icon.svelte`, `+error.svelte`.

**Motion that exists but is inconsistent:**

- Three modal systems, three behaviours. `Modal.svelte` and `MediaUploadModal.svelte` animate in (`fly` + `fade`); `ConfirmModal.svelte` and `CaseInfoCardModal.svelte` do not animate at all.
- The nav drawer (`+layout.svelte:465-473`) slides with `transform` at 0.25s and its scrim fades in (`+layout.svelte:525`). It is the **mobile** off-canvas mirror of the desktop nav (`@media (max-width: 767px)` hides `.main-navigation`, `+layout.svelte:459-462`), and an off-canvas panel overlaying the page is the intended mobile behaviour — not a gap.
- `ViewToggle.svelte:93` animates its selected-tab pill with a 0.18s background transition; the underlying `ViewToggle` in list pages flips a grid/list layout with no cross-fade between the two layouts.

### 2.7 The export path is a live constraint

`CaseInfoCardModal.svelte:110-114` captures the **always-mounted off-screen** copy of the card (`CaseInfoCard.svelte:87`, `class:case-card--export`) via `renderPosterBlob` → `html-to-image` (`caseCardExport.ts:96-118`).

`html-to-image` clones the node and inlines **computed** styles. Computed style reflects the current value of a running animation. So if the poster subtree ever animates opacity, transform or layout, the captured PNG ships that mid-flight value — a faded or half-shifted poster file.

Today the poster classes (`.case-card*`) are not in the global entrance list, so nothing is at risk. That is luck, not a guard: `app.css:266` couples motion to a hand-maintained class list, and the next person adding a card animation will not know to check the exporter.

---

## 3. Gaps, ranked by what a person notices

| # | Gap | Evidence | User-visible effect |
|---|---|---|---|
| **G1** | Reduced motion does not work for JS transitions | `Modal.svelte:135,147`; `transitions.js:476`; `svelte/motion/index.js:31` | A user who asked for less motion gets slides and fades anyway |
| **G2** | No duration/easing tokens | `app.css:102` (1 token) vs 15 literals | Inconsistent feel; every new animation invents a number |
| **G3** | All JS transitions ease linearly | `transitions.js:382`; no `svelte/easing` import anywhere | Motion reads mechanical; entrances should decelerate, exits should accelerate |
| **G4** | Motion coverage is ~40% of pages, 0% on the chart and the timeline | §2.6 | The data surfaces — the reason this tool exists — feel like static forms |
| **G5** | Stagger is hardcoded to 8 children in CSS | `app.css:281-290` | Item 9+ animates out of order; cannot extend without editing CSS |
| **G6** | Three modal behaviours | `Modal` / `MediaUploadModal` / `ConfirmModal` / `CaseInfoCardModal` | Same action, different physical response depending on which modal |
| **G7** | ~~Nav drawer does not move the page~~ | `+layout.svelte:459-473` | **Not a gap** — the drawer is the mobile off-canvas mirror; overlaying the page there is correct |
| **G8** | Poster capture has no motion guard | `caseCardExport.ts:96`; `CaseInfoCard.svelte:87` | A future card animation silently corrupts downloaded posters — **closed**: the export subtree is pinned still in `app.css`, and `caseCardExport.test.ts` fails if the card grows a transition |
| **G9** | No motion tests | `frontend/tests/` has no animation spec | G1–G8 can regress silently |
| **G10** | The status history never reached the page — `PersonDetailSchema` stripped `status_history` | `schemas/overlays.ts` (the key is not declared); `api.ts:230-237` (Zod strips undeclared keys) | The timeline and the transition banner have never been visible on any case |

---

## 4. Proposed motion system

### 4.1 Tokens (the foundation — Phase 0)

Replace the single token with a small, named set in `app.css`. Durations on a 60/120/200/320 ladder; one easing per intent.

> The token names below are the proposal as written. What shipped is `--motion-duration-enter` / `-drawer` / `-overlay` / `-accordion` / `-reveal` / `-count` / `-grow` / `-ambient` / `-fast` / `-press` / `-spin` / `-shimmer` and `--motion-ease-editorial` / `-overlay` / `-count` / `-loop` / `-spin`, with the JS constants in `$lib/motion.ts` pinned to them by `motion.test.ts`. Same shape, one extra ladder step, and a `--motion-stagger-step` of 90ms instead of 40ms.
>
> The layer is now **closed**: every duration and every easing in the stylesheets is a token, and `motion.test.ts` fails if one is spelled out at a call site. The two loop easings (`-loop`, `-spin`) are CSS-only, because no JS transition loops.

```css
:root {
  /* durations */
  --motion-fast:   120ms;   /* hover, focus, colour */
  --motion-base:   200ms;   /* most entrances/exits */
  --motion-slow:   320ms;   /* drawer, large surfaces */
  --motion-stagger: 40ms;   /* per-item delay increment */

  /* easing */
  --ease-standard: cubic-bezier(0.2, 0, 0, 1);  /* anything that moves on screen */
  --ease-entrance: cubic-bezier(0, 0, 0, 1);    /* decelerate into place */
  --ease-exit:     cubic-bezier(0.3, 0, 1, 1);  /* accelerate away */

  /* keep the old name as an alias so nothing breaks */
  --transition-card: var(--motion-base) var(--ease-standard);
}
```

Plus a global kill switch so CSS motion obeys the setting in one place:

```css
@media (prefers-reduced-motion: reduce) {
  :root {
    --motion-fast: 0.01ms; --motion-base: 0.01ms;
    --motion-slow: 0.01ms; --motion-stagger: 0ms;
  }
}
```

The `0.01ms` idiom (rather than `0`) keeps `transitionend` / `animationend` listeners firing, so nothing that waits on an event hangs.

### 4.2 The JS gate (fixes G1)

One module, `src/lib/motion.ts`:

```ts
import { prefersReducedMotion } from 'svelte/motion';
import { cubicOut, cubicIn } from 'svelte/easing';
import { fly, fade } from 'svelte/transition';

export const reduced = () => prefersReducedMotion.current;

/** fly/fade that become instant when the user asked for reduced motion */
export const flyIn  = (opts = {}) => fly({ easing: cubicOut, ...opts });
export const flyOut = (opts = {}) => fly({ easing: cubicIn,  ...opts });
export const fadeIn = (opts = {}) => fade({ easing: cubicOut, ...opts });
```

The sketch above is what this section proposed. What shipped is close in shape and different in detail: `svelte/motion`'s `prefersReducedMotion` is a function, not a reactive object, so the module reads the setting itself and listens for the change — `onReducedMotionChange` — instead of importing a store. The transitions are guarded per surface (`fade`, `rise`, `drop`, `lift`, `expand`, `panel`) and each returns `{ duration: 0, css: () => '' }` when the reader has asked for reduced motion. The curves come from a `cubicBezier` solver that mirrors the CSS curves, so a JS transition and a CSS transition cannot drift apart.

Two ways to use it, both valid — pick per case:

- **Duration** — `transition:flyIn={{ y: -8, duration: reduced() ? 0 : 200 }}` — the element still transitions, it just does not move.
- **Displacement** — `transition:flyIn={{ y: reduced() ? 0 : -8 }}` — the element fades in place, keeping a visual cue that *something* happened.

The second is the better default for anything that enters a region of the screen the user was not looking at.

### 4.3 Per-surface spec

"Content below the fold" vs "content above the fold" is the line that matters: **anything above the fold must be readable with no animation and no JavaScript**. Entrance motion is for content that arrives after the user is already reading.

| Surface | Motion | Duration / easing | Reduced motion |
|---|---|---|---|
| Buttons, chips, links | background + border-colour on hover/focus | `--motion-fast` / `--ease-standard` | colour change only, no movement |
| Card hover lift | `box-shadow` + `border-color` (already exists, `app.css:298`) | `--motion-fast` | keep shadow, drop the border-colour shift |
| Modal (all four) | scrim fade + panel rise 8px | `--motion-base` / `--ease-entrance` | fade only, 0px travel |
| Nav drawer (mobile off-canvas) | panel `translateX` + scrim fade | `--motion-slow` / `--ease-entrance` | instant show/hide |
| Toast | rise 12px + fade, auto-dismiss unchanged | `--motion-base` / `--ease-entrance` | fade in place |
| Banner / form error | drop 8px + fade (already `fly`) | `--motion-base` / `--ease-entrance` | fade only |
| List rows (persons, contacts, testimonials, notifications, watchdog, casework) | per-item fade + 4px rise, staggered `--motion-stagger`, capped at 8 items | `--motion-base` / `--ease-entrance` | no stagger, no rise |
| **Status breakdown chart** | bar segments grow from 0 to their width, left to right, once on mount | `--motion-slow` / `--ease-entrance` | bars render at final width |
| **Status history timeline** | each event row fades in as it enters the viewport; a vertical rule draws down between events | `--motion-base` / `--ease-entrance` | rows render static, rule full height |
| Skeleton shimmer | shimmer only while the load is genuinely pending | `--motion-slow` loop | static block (already correct, `Skeleton.svelte:371`) |
| View toggle | pill slides between segments + content cross-fade | `--motion-base` / `--ease-standard` | instant swap |

The drawer row shipped as `--motion-duration-drawer` (320ms) with `--motion-ease-editorial`, and the scrim fades through `$lib/motion` so it fades **out** as well as in — the old CSS keyframe could only fade in, so the scrim vanished the instant the drawer closed. The page does not shift aside (G7): an off-canvas panel over the page is the intended mobile behaviour. The links inside the panel do not shift either; the panel's arrival is the motion, and a second movement inside a control the reader is already using would be decoration.

**The view toggle shipped without a FLIP.** A FLIP exists to move a pill between segments of unequal width: measure, invert, play. Equal segments remove the need for it. The two buttons are the same width (`flex: 1 1 0`, `min-width: 92px`), the pill is exactly one of them (`width: calc(50% - 0.25rem)`, `left: 0.25rem`), and it moves with `transform: translateX(100%)` on `--motion-duration-overlay` / `--motion-ease-overlay`. The selection lives on the container as `data-mode`, so CSS owns the position: nothing is measured, nothing re-lays out, and the pill is in place from the first paint. Under reduced motion the transition is off and the pill jumps. The content cross-fade was already there (`in:fade` through `$lib/motion`). The control is about 40px wider than before, because both segments are the same width.

### 4.4 Stagger without CSS `nth-child` (fixes G5)

Replace the eight hardcoded rules with a CSS custom property set per item:

```svelte
{#each items as item, i}
  <li style="--stagger-index: {Math.min(i, 8)}">…</li>
{/each}
```

```css
.stagger-item {
  animation: fadeSlideUpSmall var(--motion-base) var(--ease-entrance) both;
  animation-delay: calc(var(--stagger-index) * var(--motion-stagger));
}
```

One rule, unlimited items, and the cap is explicit in the template rather than implied by how many `nth-child` rules someone remembered to write.

### 4.5 The export guard (fixes G8)

Two lines, both in the exporter's path:

1. In `CaseInfoCard.svelte`, the export variant already carries `case-card--export`. Add to the export stylesheet:

   ```css
   .case-card--export, .case-card--export * {
     animation: none !important;
     transition: none !important;
   }
   ```

2. In `caseCardExport.ts`, belt and braces — pass a `filter` to `html-to-image` that drops motion from the clone:

   ```ts
   filter: (node) => !(node instanceof HTMLElement && node.dataset.caseCard === 'export')
   ```

Rule for anything added later: **no motion inside the poster subtree, ever.** The poster is a file that gets printed, pasted, and published; it must be identical every time.

**What shipped.** The guard is in the stylesheet, where the motion lives:

```css
.case-card--export,
.case-card--export * {
	animation: none !important;
	transition: none !important;
}
.case-card--export [data-reveal='pending'] {
	opacity: 1 !important;
	transform: none !important;
}
```

The second rule is not decoration: the export copy sits 20 000px off-screen, so a revealed element inside it would never reach the viewport and the captured file would be a blank sheet. `caseCardExport.test.ts` pins both rules, and fails if the card component grows a transition — a Svelte transition is a Web Animations animation, which no CSS rule can switch off.

One piece is still open: cancelling whatever is still running at the moment of capture, inside `caseCardExport.ts`. That file is being rewritten on `fix/case-card-poster-csp`, so the call goes in when that branch lands.

---

## 5. Guardrails

- **Nothing animates layout properties.** `width`, `height`, `margin`, `top` cause reflow on every frame. The chart bar growth and the timeline rule are the only exceptions worth making, and both are `transform`-based (`scaleX`, `scaleY`) with the final size reserved by the layout.
- **CI budgets are already enforced** — `.lighthouserc.json`: performance ≥ 0.85, accessibility ≥ 0.95, best-practices ≥ 0.90, SEO ≥ 0.90. A motion change that pushes a score below the floor fails the build. Treat these as the motion budget.
- **Respect the audience.** This is a tool for people documenting enforced disappearances and arbitrary detention. Motion should be restrained: no bounce, no elastic, no attention-seeking loops. The easing set above is deliberately dull — that is the correct register for this product.
- **No motion on content the user is reading.** Entrance animations belong to content that arrives late. Primary content must be in the DOM and readable without JavaScript (SSR already does this — `+layout.ts`).
- **Nothing loops forever.** The only continuous animation permitted is the skeleton shimmer, and only while a load is pending.

---

## 6. Rollout

The plan is written as five phases. What shipped is one branch and one PR, `feat/motion-system` → #196, because the contract test — "no component imports from `svelte/transition`" — only passes when every component has moved. Splitting it across five PRs would mean five branches where every one of them is red.

| Phase | Branch | Contents | Visual change | Risk |
|---|---|---|---|---|
| 0 | `feat/motion-tokens` | Duration/easing tokens in `app.css`; global reduced-motion kill switch; replace the 15 literals | none | none |
| 1 | `fix/motion-reduced-motion` | `src/lib/motion.ts`; rewrite the 8 `transition:` call sites to use it | none (only under `prefers-reduced-motion`) | low |
| 2 | `feat/motion-primitives` | `.stagger-item` pattern; modal parity across all four modals; the nav drawer keeps its overlay (G7) | low | medium |
| 3 | `feat/motion-data-surfaces` | Chart bar growth, timeline reveal, view-toggle FLIP | medium | medium |
| 4 | `test/motion-a11y` | Playwright spec: with `prefers-reduced-motion: reduce`, no element changes position between two frames; poster export PNG is byte-stable across two runs | none | low |

Phases 0–2 and the timeline half of Phase 3 are in #196, together with the token layer (Phase 0's "replace the 15 literals" is finished and enforced by a test), the nav drawer and the view toggle (§4.3). The chart (Phase 3, §8.3) and all of Phase 4 are not.

Phase 4's poster test is the one worth writing regardless: it pins G8 shut.

---

## 7. Tests worth adding

- **Reduced motion is honoured** — Playwright with `reducedMotion: 'reduce'`; sample the bounding box of the modal before and after it opens; assert it did not translate.
- **Content is readable without motion** — with JS disabled, assert the primary heading and first paragraph of each key page are in the DOM.
- **Poster determinism** — export the same card twice; assert the PNG bytes are identical. Catches any motion that leaked into the capture.
- **Stagger order** — assert item *n* starts after item *n-1* on a 12-item list (this is what G5 breaks).

---

## 8. Decisions

**Taken (2026-11-07, Aya):**

1. **Character — restrained editorial.** 200–320ms, decelerating easing, no bounce, no elastic, no attention loops. The token set and per-surface table in §4 are written to this register and need no revision.
2. **Scope — internal casework surfaces first.** Person detail (status chart, status timeline), the modals, the nav drawer, and list stagger. Phases 0–3 as written. The public pages (`/testimonials`, landing) are untouched by this plan and get their own pass later, if at all.
3. **The chart stays still.** `StatusBreakdownChart.svelte` is left exactly as it is. Its own header records a "human-first & practical" decision against animating it, and that decision stands.
4. **One branch, one PR.** `feat/motion-system` → PR #196. The draft's own test suite makes the migration one atomic unit — "no component imports from `svelte/transition`" only passes when every component has moved — so it is one feature commit rather than one commit per phase.

**Taken (2026-11-08, Aya):**

5. **The view toggle's pill: equal segments, pure slide.** Cards and List are the same width; the pill moves with a transform only, and CSS places it from the first paint. The cost is a control about 40px wider than the one that shipped before.

**Still open — neither blocks the work that is done:**

6. **Print.** The poster and the browser print stylesheet must stay static. Assumed out of scope for all motion work; §4.5 makes it a rule rather than a hope.
7. **Fidelity.** No reference product named. The token set in §4.1 is the proposal to react to.

---

## 9. What is verified, and what is not

**Verified in this repo, by reading the files:** every file and line reference in §2 and §3. Svelte's `linear` default easing and its WAAPI-based transitions (`node_modules/svelte/src/internal/client/dom/elements/transitions.js:382,476`); the existence of `prefersReducedMotion` in the installed Svelte (`node_modules/svelte/src/motion/index.js:31`, version 5.57.1); the absence of `svelte/easing`, `svelte/motion` and any animation dependency in `src/` and `package.json`; the CI Lighthouse thresholds in `.lighthouserc.json`; that `html-to-image` receives the always-mounted off-screen export copy.

**Verified by running it:** `npm run check` (0 errors, 0 warnings over 650 files), `npm run test` (264 tests, 15 files), `npm run build` (clean). The reduced-motion contract, the reveal contract and the counter are pinned in `motion.dom.test.ts`; the status timeline is pinned end to end — wire payload, parse, rows, badges, and the guarantee that no row of case history is left hidden — in `statusHistory.test.ts`; the token layer is pinned in `motion.test.ts` — every duration in `app.css` has a key in `$lib/motion.ts`, and the test fails if a stylesheet spells out a duration or an easing at a call site; the view toggle is pinned in `viewToggle.test.ts` — the pill exists, the two segments are the same width, the pill moves by a transform on a token, and the selection is on the container as `data-mode`.

**Not verified, and stated as belief:** that `html-to-image` inlines *animated* computed values into the clone (the basis of G8's severity). This is the standard behaviour of the library, but it has not been reproduced in this repo. The Phase 4 poster-determinism test is what would settle it — and it is cheap.

**Not verified: the motion itself.** Playwright's browser binary is not installed on this machine and the download is blocked, so nothing has been *seen* moving. The DOM tests cover the contract; the register of the movement is still a judgement that needs a human eye in a browser. The dev server for this branch is at `http://127.0.0.1:3141/testimonies`.

**Not done:** the status chart (§8.3), the capture-time freeze inside `caseCardExport.ts` (§4.5), and the Phase 4 Playwright spec — reduced motion end to end, and poster determinism. The public pages are untouched, as §8.2 says.

