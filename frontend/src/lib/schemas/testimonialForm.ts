/**
 * Client-side validation schema for the new-testimonial form.
 *
 * The backend enforces the same rules server-side via the
 * TestimonialWrite serializer; this schema exists so the user doesn't
 * round-trip on obvious errors (gibberish, blank required fields,
 * missing source label) and so the validation rules live in ONE place
 * instead of a wall of if/else branches inside the page component.
 *
 * Field names mirror the form's `bind:value` identifiers, which means
 * the Zod `issue.path[0]` lines up with the `<input id="...">`
 * attributes used by the page's focus-on-first-error helper. No
 * translation table required.
 *
 * The visibility enums are sourced from the Orval-generated schema so
 * the validator stays in lockstep with the backend serializer — any
 * new visibility value added to the backend appears here the next time
 * the API is regenerated.
 */
import { z } from 'zod';
import {
	TestimonialSourceVisibilityEnum,
	TestimonialLocationVisibilityEnum,
} from '$lib/api/generated/endpoints.schemas';

const sourceVisibilityEnum = z.enum(
	Object.values(TestimonialSourceVisibilityEnum) as [
		'public_named',
		'public_anonymous',
		'hidden',
	],
);

const locationVisibilityEnum = z.enum(
	Object.values(TestimonialLocationVisibilityEnum) as [
		'public_precise',
		'public_region',
		'public_country',
		'hidden',
	],
);

/** `incident_date_precision` isn't surfaced in the Orval-generated
 *  `TestimonialWriteRequest` (drf-spectacular skipped it during
 *  introspection — see the page comment for the workaround). The
 *  backend accepts the same three-value literal. */
const incidentDatePrecisionEnum = z.enum(['exact', 'approximate', 'unknown']);

/** Reject pure-punctuation / whitespace-only strings AND
 *  one-character-repeated spam like 'aaaaa' or '-----'. Used as a
 *  `.refine` predicate on free-text fields where a placeholder
 *  would otherwise pass a length check. */
function isNotGibberish(s: string): boolean {
	return !/^[\W_]+$/.test(s) && !/^(.)\1{4,}$/.test(s);
}

const gibberishMessage = (label: string): string =>
	`${label} looks like gibberish — please write a real description.`;

/** Validate the new-testimonial form. Use `safeParse`; convert the
 *  resulting `ZodError` to a `Record<string, string>` of the first
 *  message per field for inline display. */
export const newTestimonialSchema = z
	.object({
		title: z
			.string()
			.trim()
			.min(1, 'Title is required.')
			// zod's chained `.min()` short-circuits on the first failing
			// constraint, so an empty title surfaces "Title is required."
			// rather than the length message below.
			.min(
				5,
				'Title needs at least 5 characters — a single letter or a placeholder is not enough context.',
			),
		country: z
			.string()
			.trim()
			.min(1, 'Country is required.')
			.min(2, 'Country needs at least 2 characters.'),
		region: z.string().trim(),
		incidentDate: z.string(),
		incidentDatePrecision: incidentDatePrecisionEnum,
		language: z.string(),
		summary: z
			.string()
			.trim()
			.min(1, 'Summary is required for readers.')
			.min(
				20,
				'Summary should be at least 20 characters — a sentence, not a placeholder.',
			)
			.refine(isNotGibberish, { message: gibberishMessage('Summary') }),
		narrative: z
			.string()
			.trim()
			.min(1, 'Narrative is required.')
			.min(
				50,
				'Narrative should be at least 50 characters — even a short testimony needs a paragraph.',
			)
			.refine(isNotGibberish, { message: gibberishMessage('Narrative') }),
		outcome: z.string().trim(),
		verificationLevel: z.string(),
		sourceVisibility: sourceVisibilityEnum,
		publicSourceLabel: z.string().trim(),
		locationVisibility: locationVisibilityEnum,
		familyProtected: z.boolean(),
		contactProtected: z.boolean(),
	})
	.superRefine((data, ctx) => {
		// Cross-field rule: when the source is shown to readers (i.e.
		// anything other than 'hidden'), the public label needs to
		// describe their role.
		if (
			data.sourceVisibility !== 'hidden' &&
			data.publicSourceLabel.length < 3
		) {
			ctx.addIssue({
				code: 'custom',
				path: ['publicSourceLabel'],
				message:
					'Public source label is required when source is not hidden — describe the role (e.g. "Family member", "Local witness").',
			});
		}
	});

export type NewTestimonialInput = z.infer<typeof newTestimonialSchema>;

/** Flatten a `ZodError` into a per-field message map.
 *  - First message wins per field (later issues on the same field are
 *    dropped so the user sees the most important problem first).
 *  - Top-level issues only: nested paths are surfaced under the parent
 *    key so the existing `aria-describedby`/`id` lookup works.
 *  - Cross-field issues produced by `.superRefine` already carry their
 *    target field in `path`, so they show up under the right key. */
export function zodToFieldErrors(
	error: z.ZodError,
): Record<string, string> {
	const out: Record<string, string> = {};
	for (const issue of error.issues) {
		const key = issue.path[0];
		if (typeof key === 'string' && !(key in out)) {
			out[key] = issue.message;
		}
	}
	return out;
}