/**
 * Flatten a `ZodError` into a per-field message map.
 *
 * Kept in its own module (rather than next to testimonialForm) so
 * other schemas (personForm, future schemas) can use it without
 * transitively pulling in the testimonial schema's `$lib`-aliased
 * generated imports — vitest runs in node mode without the SvelteKit
 * `$lib` resolver, and the import chain would otherwise fail to load.
 *
 * Rules:
 *   - First message wins per field (later issues on the same field
 *     are dropped so the user sees the most important problem first).
 *   - Top-level issues only: nested paths are surfaced under the
 *     parent key so the existing `aria-describedby`/`id` lookup works.
 *   - Cross-field issues produced by `.superRefine` already carry
 *     their target field in `path`, so they show up under the right
 *     key.
 */
import type { z } from 'zod';

export function zodToFieldErrors(error: z.ZodError): Record<string, string> {
	const out: Record<string, string> = {};
	for (const issue of error.issues) {
		const key = issue.path[0];
		if (typeof key === 'string' && !(key in out)) {
			out[key] = issue.message;
		}
	}
	return out;
}
