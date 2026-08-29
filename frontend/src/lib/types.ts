/**
 * Domain types for testimonies.world.
 *
 * These mirror the Django backend serializers closely enough for the
 * SvelteKit frontend to stay type-safe without runtime overhead. Where
 * the backend returns paginated lists, the wrapper type is `Paginated<T>`.
 *
 * IMPORTANT: when you add a field on the backend, add it here too — and
 * audit every consumer in a route or component.
 */

import type { StatusValue } from './StatusBadge.svelte';

/* ============================================================================
   User / session
   ========================================================================== */

export type GroupName = 'Volunteer' | 'Advocate' | string;

export interface User {
	authenticated: boolean;
	username?: string;
	email?: string;
	groups?: GroupName[];
	is_staff?: boolean;
}

/* ============================================================================
   Categories
   ========================================================================== */

export interface PersonCategory {
	id: number;
	name: string;
	slug?: string;
	description?: string;
}

export interface Paginated<T> {
	count: number;
	next: string | null;
	previous: string | null;
	results: T[];
}

/* ============================================================================
   Media
   ========================================================================== */

export type MediaType = 'photo' | 'video' | 'document' | 'link';
export type Visibility = 'public' | 'restricted' | 'sensitive';

export interface Media {
	id: number;
	media_type: MediaType;
	visibility: Visibility;
	url?: string | null;
	file?: string | null;
	description?: string;
}

/* ============================================================================
   Reports
   ========================================================================== */

export type SourceType = 'firsthand' | 'secondhand' | 'news' | 'document';

export interface Report {
	id: number;
	person: number;
	source_type: SourceType;
	source_attribution?: string;
	reporter_name?: string;
	reporter_contact?: string;
	date_start?: string | null;
	date_end?: string | null;
	rough_location?: string;
	narrative: string;
	suspected_reason?: string;
	official_reason?: string;
	created_at: string;
	updated_at: string;
	media_files?: Media[];
}

/* ============================================================================
   Person (the central record)
   ========================================================================== */

export type MedicalStatus =
	| 'unknown'
	| 'healthy'
	| 'health_concerns'
	| 'critical'
	| 'deceased';

export type Gender = 'M' | 'F' | 'O' | 'U' | string;

export interface FamilyRelationship {
	person_id: number;
	person_name: string;
	relationship: string;
}

export interface Person {
	id: number;
	name: string;
	legal_name?: string;
	aliases?: string;
	country: string;
	rough_location?: string;
	precise_location?: string;
	current_status: StatusValue;
	medical_status: MedicalStatus;
	ethnicity?: string;
	gender?: Gender;
	date_of_birth?: string | null;
	last_known_date?: string | null;
	summary_narrative?: string;
	authoritative_source?: string;
	authoritative_url?: string;
	quality_tier?: string;
	profile_image_url?: string | null;
	report_count?: number;
	categories?: PersonCategory[];
	reports?: Report[];
	media_files?: Media[];
	family?: FamilyRelationship[];
	created_at: string;
	updated_at: string;
}

/** Shape returned by /persons/statistics/ */
export interface Statistics {
	total: number;
	by_status: Partial<Record<StatusValue, number>>;
	by_country: Array<[string, number]> | Record<string, number> | Array<{ country: string; count: number }>;
	by_category: Array<{ name: string; count: number }>;
	by_medical: Partial<Record<MedicalStatus, number>>;
}

/* ============================================================================
   Casework records
   ========================================================================== */

export type CaseworkActionType =
	| 'outreach'
	| 'legal_filing'
	| 'media'
	| 'advocacy'
	| 'investigation'
	| 'other';

export type CaseworkStatus = 'open' | 'in_progress' | 'done';

export interface CaseworkRecord {
	id: number;
	action_type: CaseworkActionType;
	status: CaseworkStatus;
	description: string;
	date: string;
	next_steps?: string;
	notes?: string;
	performed_by_name?: string;
	persons?: number[];
}

/* ============================================================================
   Contacts
   ========================================================================== */

export type ContactRole =
	| 'family'
	| 'advocate'
	| 'lawyer'
	| 'official'
	| 'journalist'
	| 'reporter'
	| 'other';

export interface Contact {
	id: number;
	name: string;
	role: ContactRole;
	email?: string;
	phone?: string;
	signal?: string;
}
