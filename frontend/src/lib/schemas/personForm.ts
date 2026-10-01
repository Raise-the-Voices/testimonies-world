/**
 * Client-side validation schema for the /submit (new-person) form.
 *
 * The backend enforces the same rules server-side via
 * `PersonWriteSerializer` (`backend/cases/serializers.py`); this
 * schema exists so the user doesn't round-trip on obvious errors
 * (gibberish, blank required fields, bad date format) and so the
 * validation rules live in ONE place instead of a wall of
 * if/else branches inside the page component.
 *
 * Field names mirror the form's `bind:value` identifiers (camelCase),
 * which means the Zod `issue.path[0]` lines up with the
 * `<input id="...">` attributes used by the page's
 * focus-on-first-error helper. No translation table required.
 *
 * Why a separate `safeParse` instead of just letting DRF's 400
 * surface: the backend's 400 body has the per-field message list,
 * but a 400 from the schema runs before the network call — so the
 * user gets the inline message immediately instead of waiting for
 * the API round-trip. The backend validator remains the source of
 * truth; this schema just front-loads the cheap checks.
 */
import { z } from 'zod';

import { zodToFieldErrors } from './formErrors';

/** YYYY-MM-DD (the wire format for `last_known_date`). Empty string
 *  is allowed because the field is optional; the page already gates
 *  it behind a month-picker that emits either a valid string or ''. */
const dateString = z
	.union([z.literal(''), z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Use YYYY-MM-DD.')])
	.optional();

/** Same shape as backend `Person.Status` (cases/models.py:256). The
 *  full backend enum is exposed in the orval-generated enums; we
 *  hardcode the values here so a backend change has to update both
 *  places — surfacing accidental drift at code review. */
const currentStatusEnum = z.enum([
	'detained',
	'disappeared',
	'restricted_movement',
	'released',
	'deceased',
	'unknown',
	'stateless',
	'rights_restricted',
	'ongoing_enforced_disappearance',
	'found_alive',
	'found_dead',
	'case_closed',
	'other',
]);

/** Matches `Person.MedicalStatus`. */
const medicalStatusEnum = z.enum([
	'unknown',
	'healthy',
	'health_concerns',
	'critical',
	'deceased',
]);

/** Matches `Person.Gender` choices. The wire enum is the single
 *  letter; an empty string is allowed because the form's select
 *  default is blank. */
const genderEnum = z.enum(['M', 'F', 'O', 'U', '']);

/** Matches `Person.QualityTier` choices (1/2/3). Backend accepts null
 *  for "unset", so allow nullable here too. */
const qualityTier = z.union([z.literal(1), z.literal(2), z.literal(3), z.null()]).optional();

/** Backend rejects empty `category_ids` as a malformed list and 9999+
 *  as an unknown PK. We don't validate the PK range here — the
 *  backend does that and returns a 400 with `category_ids` keyed —
 *  we only need to ensure the shape is `number[]` so the JSON
 *  serializer doesn't blow up on a string. */
const categoryIds = z.array(z.number().int().positive()).optional();

/** `aliases` may include a comma-separated string or a list of
 *  trimmed tokens. The backend expects a single CharField(max_length=500),
 *  so we coerce the list to a comma-separated string before posting. */
const aliasesField = z.union([z.string(), z.array(z.string())]).optional();

/** Reject pure-punctuation / whitespace-only strings AND
 *  one-character-repeated spam like 'aaaaa' or '-----'. Same
 *  predicate the testimonial schema uses. */
function isNotGibberish(s: string): boolean {
	return !/^[\W_]+$/.test(s) && !/^(.)\1{4,}$/.test(s);
}

const gibberishMessage = (label: string): string =>
	`${label} looks like gibberish — please write a real description.`;

/** Validate the /submit form payload (the JSON path — FormData uploads
 *  aren't zod-friendly, so the multipart branch of handleSubmit
 *  bypasses this). Use `safeParse`; convert the result to the same
 *  `Record<string, string>` shape the rest of the page uses for
 *  inline errors. */
export const personWriteRequestSchema = z
	.object({
		name: z
			.string()
			.trim()
			.min(1, 'Name is required.')
			.min(2, 'Name needs at least 2 characters.')
			.max(255, 'Name is too long (max 255 characters).'),
		country: z
			.string()
			.trim()
			.min(1, 'Country is required.')
			.max(100, 'Country name is too long (max 100 characters).'),
		current_status: currentStatusEnum,
		medical_status: medicalStatusEnum,
		rough_location: z.string().trim().max(255, 'Rough location is too long (max 255 characters).'),
		precise_location: z.string().trim().max(500, 'Precise location is too long (max 500 characters).'),
		summary_narrative: z
			.string()
			.trim()
			.max(10_000, 'Summary is too long (max 10000 characters).'),
		ethnicity: z.string().trim().max(100, 'Ethnicity is too long (max 100 characters).'),
		gender: genderEnum.optional(),
		last_known_date: dateString,
		age_at_incident: z.number().int().min(0).max(150).optional(),
		occupation: z.string().trim().max(255, 'Occupation is too long (max 255 characters).'),
		legal_name: z.string().trim().max(255, 'Legal name is too long (max 255 characters).'),
		aliases: aliasesField,
		quality_tier: qualityTier,
		medical_notes: z.string().trim().max(5000, 'Medical notes are too long (max 5000 characters).'),
		authoritative_source: z.string().trim().max(255, 'Authoritative source is too long (max 255 characters).'),
		authoritative_url: z
			.string()
			.trim()
			.refine(
				(v) => v === '' || /^https?:\/\//i.test(v),
				'URL must start with http:// or https://',
			)
			.optional(),
		is_published: z.boolean(),
		category_ids: categoryIds,
	})
	.superRefine((data, ctx) => {
		// Cross-field rule: `summary_narrative` shouldn't be pure
		// gibberish. The backend would store it either way; rejecting
		// here saves a round-trip and tells the volunteer why their
		// submission felt off.
		const summary = data.summary_narrative?.trim() ?? '';
		if (summary.length > 0 && !isNotGibberish(summary)) {
			ctx.addIssue({
				code: 'custom',
				path: ['summary_narrative'],
				message: gibberishMessage('Summary'),
			});
		}
	});

export type PersonWriteRequestInput = z.infer<typeof personWriteRequestSchema>;

/** Validate and return either `{ ok: true, data }` or
 *  `{ ok: false, errors }` for the page to surface inline. */
export function validatePersonWriteRequest(
	payload: Record<string, unknown>,
):
	| { ok: true; data: PersonWriteRequestInput }
	| { ok: false; errors: Record<string, string> } {
	const result = personWriteRequestSchema.safeParse(payload);
	if (result.success) {
		return { ok: true, data: result.data };
	}
	return { ok: false, errors: zodToFieldErrors(result.error) };
}