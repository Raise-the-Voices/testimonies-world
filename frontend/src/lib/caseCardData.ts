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
 * functions, so they are unit-testable in the repo's existing
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
 * (`backend/cases/card/serializers.py`, `GET /api/persons/{id}/card/`).
 */

import { statusLabels } from './StatusBadge.svelte';
import { formatFullDate } from './dateFormat';
import type { FamilyRelationship, Person, Report } from './types';

export interface CardPhoto {
	src: string;
	/** Empty by design — the person's name sits directly above the
	 *  photograph, so a description would only repeat it. */
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
	/** Header date — the day the case entered the platform. */
	date: string | null;
	title: string;
	statusLabel: string | null;
	photo: CardPhoto | null;
	/** Metadata rows in print order. Rows with no value are omitted
	 *  entirely — never rendered with an empty value. */
	rows: CardMetaRow[];
}

/**
 * Build the card's data from a person record.
 *
 * Row order is fixed by the poster layout, not by the data: Age,
 * Residence, Profession, Father, then the abduction block.
 */
export function buildCaseCardData(person: CaseCardPerson): CaseCardData {
	const rows: CardMetaRow[] = [];
	const add = (label: string, value: unknown) => {
		const v = clean(value);
		if (v) rows.push({ label, value: v });
	};

	add('Age', person.age_at_incident ?? '');
	add('Residence', formatResidence(person));
	add('Profession', person.occupation ?? '');

	const parent = resolveParent(person);
	if (parent) add(parent.label, parent.name);

	// The abduction event lives on a Report, not on the Person: one
	// case file can carry several reports of the same incident. The
	// report's own start date stands in for the abduction date when
	// the dedicated field has not been filled in.
	const abduction = pickAbductionReport(person.reports ?? []);
	add(
		'Abduction date',
		formatFullDate(abduction?.date_of_abduction ?? abduction?.date_start ?? ''),
	);
	add('Abduction place', abduction?.place_of_abduction ?? '');
	add('Perpetrators', abduction?.abductors ?? '');

	return {
		reference: clean(person.public_reference) || null,
		// The date the case file was received is the semantically right
		// date but is rarely filled in, so the platform's own record of
		// when the case was entered stands in for it.
		date: formatFullDate(person.case_received_date ?? '') || formatFullDate(person.created_at),
		title: clean(person.name),
		statusLabel: clean(statusLabels[person.current_status] ?? '') || null,
		photo: person.profile_image_url ? { src: person.profile_image_url, alt: '' } : null,
		rows,
	};
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
 * Find the father for the "Father" row.
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
	if (father) return { label: 'Father', name: father };

	const family: FamilyRelationship[] = person.family ?? [];
	const parents = family.filter(
		(rel) => rel.relationship_type === 'parent' || rel.relationship === 'Parent',
	);
	if (parents.length === 0) return null;

	return { label: 'Parent', name: clean(parents[0].person_name) };
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
