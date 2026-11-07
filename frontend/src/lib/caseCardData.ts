/**
 * Case card data — the resolver behind the interactive "Case Information
 * Card" modal.
 *
 * The card is a *poster*: a flat, ordered list of facts about one case,
 * rendered as a dossier rather than as a form. This module owns the
 * mapping from a `Person` record to that list, and nothing else — no
 * fetching, no formatting of presentation, no DOM.
 *
 * Why a separate module rather than logic inside the component:
 * the interesting decisions here (which report is the abduction event,
 * which relative is the father, which rows to drop when empty) are pure
 * functions, so they can be unit-tested in the repo's existing
 * `environment: 'node'` vitest setup, which cannot render components.
 * Component rendering is covered by Playwright instead.
 *
 * Every field is read from data already in memory. The card makes no
 * API call of its own — the person detail page has already loaded the
 * full record, and a second fetch would be a wasted round trip.
 *
 * This is the case-file view of a case, for someone working the file.
 * The shareable, publication-facing projection of the same case is a
 * separate payload with its own masking rules
 * (`backend/cases/card/serializers.py`, `GET /api/persons/{id}/card/`),
 * mapped by `caseCardPayload.ts`.
 */

import { statusLabels } from './StatusBadge.svelte';
import { formatEditorialDate, formatFullDate } from './dateFormat';
import type { FamilyRelationship, Person, PersonCategory, Report } from './types';

export interface CardPhoto {
	src: string;
	/** Empty by design — the person's name sits on the card, so a
	 *  description would only repeat it. */
	alt: string;
}

/**
 * The person shape the card reads.
 *
 * Dates arrive in one of two shapes depending on which endpoint
 * delivered the record: the list endpoint returns the raw JSON
 * (`created_at` is an ISO string), while the detail endpoint parses
 * through `PersonDetailSchema`, whose `isoDateTime` / `isoDateNullable`
 * transforms turn them into `Date` objects. `formatFullDate` accepts
 * either, so the card does not care which one it got.
 */
export type CaseCardPerson = Omit<Person, 'created_at' | 'case_received_date'> & {
	created_at: string | Date;
	case_received_date?: string | Date | null;
};

export interface CardMetaRow {
	label: string;
	value: string;
}

export interface CaseCardData {
	/** Citable public reference, or null when the case has none yet. */
	reference: string | null;
	/** The date the sheet was produced. */
	date: string | null;
	/** The headline. The case category — the kind of violation the file
	 *  is about — or, for a case filed under no category, the person's
	 *  name. */
	title: string;
	/** The person's name. Printed as a field row unless it is the
	 *  headline. */
	name: string;
	statusLabel: string | null;
	photo: CardPhoto | null;
	/** Metadata rows in print order. Rows with no value are omitted
	 *  entirely — never rendered with an empty value. */
	rows: CardMetaRow[];
	/** Hashtags for the poster's footer, one per case category. */
	hashtags: string[];
}

/**
 * Build the card's data from a person record.
 *
 * Row order is fixed by the poster layout, not by the data: Name, Father
 * name, Age, Residence, Profession, then the abduction block.
 *
 * `today` is the day the sheet is produced. It is a parameter so the
 * unit tests can pin it instead of asserting against the clock.
 */
export function buildCaseCardData(
	person: CaseCardPerson,
	today: Date = new Date(),
): CaseCardData {
	const rows: CardMetaRow[] = [];
	const add = (label: string, value: unknown) => {
		const v = clean(value);
		if (v) rows.push({ label, value: v });
	};

	const name = clean(person.name);
	const categories = categoryNames(person.categories);
	const category = leadCategory(categories);

	// The headline is the category: the poster is about the kind of
	// violation the file records. A case filed under no category falls
	// back to the person's name, and then the name is not repeated as a
	// field row.
	add('Name', category ? name : '');

	const parent = resolveParent(person);
	if (parent) add(parent.label, parent.name);

	add('Age', person.age_at_incident ?? '');
	add('Residence (R/O)', formatResidence(person));
	add('Profession', person.occupation ?? '');

	// The abduction event lives on a Report, not on the Person: one
	// case file can carry several reports of the same incident. The
	// report's own start date stands in for the abduction date when
	// the dedicated field has not been filled in.
	const abduction = pickAbductionReport(person.reports ?? []);
	add(
		'Date of abduction',
		formatFullDate(abduction?.date_of_abduction ?? abduction?.date_start ?? ''),
	);
	add('Time of abduction', abduction?.time_of_abduction ?? '');
	add('Place of abduction', abduction?.place_of_abduction ?? '');
	add('Abductors', abduction?.abductors ?? '');

	return {
		reference: clean(person.public_reference) || null,
		date: formatEditorialDate(today),
		title: category ?? name,
		name,
		statusLabel: clean(statusLabels[person.current_status] ?? '') || null,
		photo: person.profile_image_url ? { src: person.profile_image_url, alt: '' } : null,
		rows,
		hashtags: categories.map(categoryHashtag).filter(Boolean),
	};
}

/**
 * The order the poster's headline and hashtags follow.
 *
 * EDITORIAL: this is a judgement about which category is the most
 * serious, not a fact about the data, which is why it lives in code
 * where a human can edit it rather than in a table nobody looks at.
 *
 * It mirrors the list the publication-facing card payload uses
 * (`backend/cases/card/serializers.py` → `CATEGORY_HEADLINE_PRIORITY`)
 * so both views of the same case lead with the same category. Change
 * one, change the other.
 */
const CATEGORY_LEAD_ORDER = [
	'Enforced disappearance',
	'Arbitrary detention',
	'Extrajudicial violence',
	'Restricted movement',
	'Rights restricted',
	'Stateless',
	'Child rights violation',
	'Refugee / needs relocation',
	'Torture',
	'Other',
];

/**
 * The category names on the record, in the order the API returned them.
 * The API sends them through a loose schema, so each entry is read
 * defensively.
 */
function categoryNames(categories: PersonCategory[] | undefined): string[] {
	if (!Array.isArray(categories)) return [];
	return categories.map((c) => clean(c?.name)).filter(Boolean);
}

/**
 * The category the poster leads with — the most serious one the case
 * is filed under, in title case. Null when the case has no category.
 */
export function leadCategory(names: string[]): string | null {
	if (names.length === 0) return null;

	const byLower = new Map(names.map((n) => [n.toLowerCase(), n]));
	for (const candidate of CATEGORY_LEAD_ORDER) {
		const match = byLower.get(candidate.toLowerCase());
		if (match) return titleCase(match);
	}

	// A category the editorial list does not know about still leads,
	// so the headline is never empty when the case has one.
	return titleCase(names[0]);
}

/**
 * Capitalise the first letter of every word, leaving the rest of the
 * word alone so acronyms and possessives survive ("children's rights"
 * → "Children's rights"). Mirrors the backend's `_title_case`.
 */
function titleCase(text: string): string {
	return text
		.split(/\s+/)
		.filter(Boolean)
		.map((word) => word.charAt(0).toUpperCase() + word.slice(1))
		.join(' ');
}

/**
 * A category name as a hashtag: "Enforced disappearance" →
 * "#EnforcedDisappearance". Words that are not letters or digits
 * (a slash, a hyphen) are dropped rather than carried into the tag.
 */
export function categoryHashtag(name: string): string {
	const words = name.split(/[^a-zA-Z0-9]+/).filter(Boolean);
	if (words.length === 0) return '';
	return `#${words.map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join('')}`;
}

/**
 * Residence reads "Alexandria, Egypt" when a rough location is known
 * and just the country when it is not. `rough_location` is the coarse
 * region; `precise_location` is private and never reaches the card.
 */
function formatResidence(person: CaseCardPerson): string {
	const country = clean(person.country);
	const rough = clean(person.rough_location);
	if (rough && country) return `${rough}, ${country}`;
	return rough || country;
}

/**
 * Find the father for the "Father name" row.
 *
 * The relation only says "parent" — it is not gendered — so the
 * browser cannot tell a father from a mother on its own. The server
 * resolves it instead and sends the answer as `father_name` on the
 * person payload, which is the same resolution the publication card
 * uses (`backend/cases/serializers.py:father_name`).
 *
 * When the case records no father, the row falls back to a parent and
 * says "Parent": naming someone a father when the record does not say
 * so would be a guess about a person.
 */
export function resolveParent(
	person: CaseCardPerson,
): { label: string; name: string } | null {
	const father = clean(person.father_name);
	if (father) return { label: 'Father name', name: father };

	const family: FamilyRelationship[] = person.family ?? [];
	const parents = family.filter(
		(rel) => rel.relationship_type === 'parent' || rel.relationship === 'Parent',
	);
	if (parents.length === 0) return null;

	return { label: 'Parent name', name: clean(parents[0].person_name) };
}

/**
 * Pick the report that documents the abduction.
 *
 * `reports[]` comes back in the model's default order, which is not
 * guaranteed to be chronological, so "the abduction report" is chosen
 * explicitly: the earliest report with a `date_of_abduction`, or —
 * when no report has one — the earliest report by `date_start`.
 */
export function pickAbductionReport(reports: Report[]): Report | null {
	const dated = reports.filter((r) => !!r.date_of_abduction);
	if (dated.length > 0) {
		return dated.reduce((earliest, r) =>
			(r.date_of_abduction as string) < (earliest.date_of_abduction as string) ? r : earliest,
		);
	}

	const started = reports.filter((r) => !!r.date_start);
	if (started.length > 0) {
		return started.reduce((earliest, r) =>
			(r.date_start as string) < (earliest.date_start as string) ? r : earliest,
		);
	}

	return null;
}

/** Trim to a non-empty string; anything else becomes ''. */
function clean(value: unknown): string {
	if (typeof value === 'number') return Number.isFinite(value) ? String(value) : '';
	if (typeof value !== 'string') return '';
	return value.trim();
}
