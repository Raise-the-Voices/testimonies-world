/* ============================================================================
   Testimonials — defensive text sanitisation
   --------------------------------------------------------------------------
   UI helper that protects rendered text against corrupted rows. The
   canonical bug we hit: a row whose `title` field contained a Git
   merge-conflict block (<<<<<<< / ======= / >>>>>>>) was rendered
   verbatim on the public testimonials list, leaking git workflow
   text into the UI and surfacing as a clickable card leading to
   a broken detail page.

   The fix has three layers:

   1. Form-side (validate() in /testimonials/new): reject submission of
      fields containing conflict markers — the cheapest gate, stops bad
      data at the source.

   2. List-side (TestimonialCard): sanitise every text field at render
      time via `safeText()`. Strip lines starting with conflict
      markers; treat a row whose sanitised title AND sanitised summary
      are both empty as "skip this card entirely" so a corrupt row
      disappears from the grid instead of displaying "[object Object]"
      or raw git text.

   3. Detail-side (/testimonials/[id]/+page.svelte): the load()
      already handles 404 and missing data.data. We additionally
      coerce null / empty title / summary fields to safe placeholders
      so a half-broken row doesn't leave the detail page blank.
   ============================================================================ */

// Matchers. Anchored to the start of a line (or the start of input)
// because git's <<<<<<<, =======, >>>>>>> always appear on their
// own line. We catch both orphan markers and balanced <<<<<<< blocks.
const CONFLICT_MARKER = /^\s*(<<<<<<<|=======|>>>>>>>)\s*$/m;
const CONFLICT_BLOCK = /<<<<<<<[\s\S]+?=======[\s\S]+?>>>>>>>/;
const CONFLICT_PREFIX = /^\s*(<<<<<<<|=======|>>>>>>>)\s*/gm;

export type TestimonialLikeText = string | null | undefined;

/**
 * True if the input text resembles a Git merge-conflict block.
 * Conservative — false positives are OK (we'd just hide a row that
 * had legit text starting with those chars), false negatives leave
 * raw text rendered.
 */
export function isCorruptConflictText(s: TestimonialLikeText): boolean {
	if (s == null) return false;
	const t = String(s);
	if (CONFLICT_MARKER.test(t)) return true;
	if (CONFLICT_BLOCK.test(t)) return true;
	return false;
}

/**
 * Strips Git conflict markers and surrounding whitespace. Returns
 * an empty string if the input looks like a conflict block (the
 * caller should treat empty as "skip rendering").
 */
export function safeText(s: TestimonialLikeText): string {
	if (s == null) return '';
	const t = String(s);
	if (isCorruptConflictText(t)) return '';
	return t.replace(CONFLICT_PREFIX, '').trim();
}

/**
 * Returns `safeText(s)` if non-empty, otherwise `fallback`.
 * Useful for places where we always want to render something
 * (e.g. a card title placeholder).
 */
export function safeTextOr(s: TestimonialLikeText, fallback: string): string {
	const v = safeText(s);
	return v === '' ? fallback : v;
}

/**
 * True if a testimonial row is so corrupted that ALL of its
 * display-relevant text fields are empty after sanitisation.
 * We hide such rows from lists and detail pages.
 */
export function isEmptyAfterSanitization(row: {
	title?: TestimonialLikeText;
	summary?: TestimonialLikeText;
	country?: TestimonialLikeText;
	public_location_display?: TestimonialLikeText;
}): boolean {
	return (
		safeText(row.title) === '' &&
		safeText(row.summary) === '' &&
		safeText(row.country) === '' &&
		safeText(row.public_location_display) === ''
	);
}
