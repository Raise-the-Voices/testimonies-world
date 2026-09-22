/**
 * formFocus — scroll-to-error helper for SvelteKit forms.
 *
 * Background:
 *   Every form in the app surfaces per-field errors inline (red text under
 *   the input). When the user clicks submit with missing required values,
 *   the inline errors appear but the page stays put — so a long form
 *   leaves the user staring at the submit button while the actual problem
 *   is several screens above.
 *
 *   This helper pulls the user's viewport to the topmost broken field and
 *   focuses it so they can start typing immediately. A bare toast can be
 *   missed or auto-dismissed; a viewport jump + focused input is
 *   unambiguous.
 *
 * Usage:
 *   import { focusFirstFormError } from '$lib/formFocus';
 *
 *   const errs = validate();
 *   if (Object.keys(errs).length) {
 *     errors = errs;
 *     focusFirstFormError(errs, {
 *       order: ['name', 'country', 'narrative'],
 *     });
 *     return;
 *   }
 *
 *   For forms with renamed input IDs (e.g. validator key `aliases` but
 *   DOM id `aliases-input`), pass `idMap`:
 *
 *   focusFirstFormError(errs, {
 *     order: ['aliases', ...],
 *     idMap: { aliases: ['aliases-input'] },
 *   });
 *
 * Lookup strategy, in order, for each errored field:
 *   1. Each candidate ID in `idMap[field] ?? [field]` via getElementById.
 *   2. Any `.field.has-error` element (catches server-side keys the
 *      caller didn't anticipate).
 *
 * The function focuses via `focus({ preventScroll: true })` so the
 * implicit focus-jump doesn't fight the smooth scrollIntoView that
 * follows it.
 */

export interface FocusFirstErrorOptions {
	/** Error keys in visual top-to-bottom order on the form. The first
	 *  key that appears in `errs` wins. */
	order: string[];
	/** Per-error-key override of the DOM IDs to try. Use this when the
	 *  input's `id` attribute doesn't match the validator's error key
	 *  (e.g. `aliases` → `aliases-input`). */
	idMap?: Record<string, string[]>;
}

export function focusFirstFormError(
	errs: Record<string, string>,
	options: FocusFirstErrorOptions,
): void {
	if (typeof document === 'undefined') return;
	const { order, idMap } = options;
	for (const field of order) {
		if (!errs[field]) continue;
		const candidates = idMap?.[field] ?? [field];
		let target: HTMLElement | null = null;
		for (const id of candidates) {
			const el = document.getElementById(id);
			if (el) {
				target = el as HTMLElement;
				break;
			}
		}
		// Last-resort: any .field.has-error wrapper. Catches server-side
		// keys the caller didn't list (e.g. a field renamed upstream).
		if (!target) {
			const fallback = document.querySelector('.field.has-error');
			if (fallback) target = fallback as HTMLElement;
		}
		if (!target) continue;
		// preventScroll so focus() doesn't fight the smooth scroll.
		try {
			target.focus({ preventScroll: true });
		} catch {
			/* element not focusable — still scroll to it. */
		}
		target.scrollIntoView({ behavior: 'smooth', block: 'center' });
		return;
	}
}