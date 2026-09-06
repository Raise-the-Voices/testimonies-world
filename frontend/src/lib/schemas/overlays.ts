/**
 * Schema overlays — extend orval-generated types with runtime parsing.
 *
 * The orval-generated interfaces describe the *wire* shape (dates as
 * strings, decimals as strings). These overlays add Zod transforms so
 * the same JSON payload parses into a richer runtime type:
 *
 *   - `created_at: string`  →  `Date` (via `isoDateTime`)
 *   - `date_of_birth: string | null`  →  `Date | null` (via `isoDateNullable`)
 *   - `last_known_date: string | null`  →  `Date | null`
 *
 * Use these schemas at the API boundary; everything below sees the
 * parsed types. If the wire drifts, `.parse()` throws a typed error.
 *
 * The cast approach (`as z.ZodType<Mutable<WireType>>`) doesn't work
 * because the parsed output intentionally differs from the wire shape
 * (string → Date). Instead, each overlay is a free-standing
 * `z.object(...)` whose output type is inferred via `z.infer<typeof X>`.
 */
import { z } from 'zod';
import {
	isoDateTime,
	isoDateTimeNullable,
	isoDateNullable,
} from './wire';

// --- Person overlays ----------------------------------------------------

export const PersonDetailSchema = z.object({
	id: z.number().int(),
	categories: z.array(z.any()),
	reports: z.array(z.any()),
	media_files: z.array(z.any()),
	days_since_last_report: z.number(),
	family: z.array(z.any()),
	profile_image_url: z.string().nullable(),
	name: z.string(),
	legal_name: z.string().optional(),
	aliases: z.string().optional(),
	country: z.string(),
	ethnicity: z.string().optional(),
	gender: z.string().optional(),
	date_of_birth: isoDateNullable.optional(),
	current_status: z.string().optional(),
	medical_status: z.string().optional(),
	medical_notes: z.string().optional(),
	rough_location: z.string().optional(),
	precise_location: z.string().optional(),
	last_known_date: isoDateNullable.optional(),
	summary_narrative: z.string().optional(),
	profile_image: z.string().nullable().optional(),
	authoritative_source: z.string().optional(),
	authoritative_url: z.string().optional(),
	quality_tier: z.union([z.number(), z.null()]).optional(),
	is_published: z.boolean().optional(),
	created_at: isoDateTime,
	updated_at: isoDateTime,
	created_by: z.number().nullable(),
});

export type PersonDetail = z.infer<typeof PersonDetailSchema>;

export const PersonListSchema = z.object({
	id: z.number().int(),
	name: z.string(),
	country: z.string(),
	rough_location: z.string().optional(),
	current_status: z.string().optional(),
	medical_status: z.string().optional(),
	last_known_date: isoDateNullable.optional(),
	updated_at: isoDateTime,
	created_at: isoDateTime,
	profile_image_url: z.string().nullable(),
	report_count: z.number().optional(),
});

export type PersonList = z.infer<typeof PersonListSchema>;

export const PaginatedPersonListSchema = z.object({
	count: z.number(),
	next: z.string().nullable(),
	previous: z.string().nullable(),
	results: z.array(PersonListSchema),
});

export type PaginatedPersonList = z.infer<typeof PaginatedPersonListSchema>;

// --- Media overlay ------------------------------------------------------

export const MediaSchema = z.object({
	id: z.number().int(),
	person: z.number().int(),
	media_type: z.string(),
	visibility: z.string(),
	description: z.string().optional(),
	url: z.string().nullable().optional(),
	file: z.string().nullable().optional(),
	report: z.number().nullable().optional(),
	uploaded_by: z.number().nullable().optional(),
	created_at: isoDateTime,
});

export type Media = z.infer<typeof MediaSchema>;

export const PaginatedMediaSchema = z.object({
	count: z.number(),
	next: z.string().nullable(),
	previous: z.string().nullable(),
	results: z.array(MediaSchema),
});

export type PaginatedMedia = z.infer<typeof PaginatedMediaSchema>;

// --- Contact overlay ----------------------------------------------------

export const ContactSchema = z.object({
	id: z.number().int(),
	name: z.string(),
	role: z.string(),
	email: z.string().optional(),
	phone: z.string().optional(),
	signal: z.string().optional(),
	whatsapp: z.string().optional(),
	notes: z.string().optional(),
	created_by: z.number().nullable(),
	created_at: isoDateTime,
	updated_at: isoDateTime,
});

export type Contact = z.infer<typeof ContactSchema>;

export const PaginatedContactSchema = z.object({
	count: z.number(),
	next: z.string().nullable(),
	previous: z.string().nullable(),
	results: z.array(ContactSchema),
});

export type PaginatedContact = z.infer<typeof PaginatedContactSchema>;

// --- Casework overlay ---------------------------------------------------

export const CaseworkRecordSchema = z.object({
	id: z.number().int(),
	action_type: z.string(),
	description: z.string(),
	date: z.string(),
	status: z.string(),
	next_steps: z.string().optional(),
	notes: z.string().optional(),
	persons: z.array(z.number()),
	performed_by: z.number().nullable(),
	performed_by_name: z.string().optional(),
	seen_by: z.array(z.any()).optional(),
	created_at: isoDateTime,
	updated_at: isoDateTime,
});

export type CaseworkRecord = z.infer<typeof CaseworkRecordSchema>;

export const PaginatedCaseworkSchema = z.object({
	count: z.number(),
	next: z.string().nullable(),
	previous: z.string().nullable(),
	results: z.array(CaseworkRecordSchema),
});

export type PaginatedCasework = z.infer<typeof PaginatedCaseworkSchema>;

// --- Notification overlay ----------------------------------------------

export const NotificationSchema = z.object({
	id: z.number().int(),
	recipient: z.number().int(),
	actor: z.number().nullable(),
	actor_name: z.string().optional(),
	kind: z.string(),
	casework: z.number().nullable(),
	casework_action_type: z.string().optional(),
	casework_persons: z.array(z.string()).optional(),
	is_read: z.boolean(),
	read_at: isoDateTimeNullable.optional(),
	created_at: isoDateTime,
});

export type Notification = z.infer<typeof NotificationSchema>;