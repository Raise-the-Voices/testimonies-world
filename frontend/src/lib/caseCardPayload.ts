/**
 * Case card payload — the resolver for the masked, publication-facing
 * card.
 *
 * `GET /api/persons/{id}/card/` answers with what the server has
 * cleared for publication: the headline, the identity fields, the
 * incident, the photograph and the hashtags, plus the `exportable`
 * verdict and the list of what was withheld
 * (`backend/cases/card/serializers.py`).
 *
 * This module maps that payload onto the same `CaseCardData` the
 * on-screen card uses, so ONE component renders both: the case-file
 * card the advocate is looking at, and the publication poster that is
 * exported. The server decides what the poster may show; the browser
 * only lays it out.
 *
 * The two never disagree about style — they can disagree about
 * content, and that is the point: the publication poster carries only
 * the fields the server cleared.
 */

import {
	categoryHashtag,
	type CardMetaRow,
	type CaseCardData,
	type CardPhoto,
} from './caseCardData';
import { formatEditorialDate, formatFullDate } from './dateFormat';
import type { CaseCardPayload } from './api/generated/endpoints.schemas';

/**
 * Build the poster's data from the server's masked card payload.
 */
export function buildCardDataFromPayload(payload: CaseCardPayload): CaseCardData {
	const rows: CardMetaRow[] = [];
	const add = (label: string, value: unknown) => {
		const v = clean(value);
		if (v) rows.push({ label, value: v });
	};

	const name = clean(payload.identity.display_name);
	const headline = clean(payload.headline);

	// The headline is the category (or, for a case filed under none, the
	// server's own fallback). The name is a field of the poster, not
	// the headline — unless the two are the same string, in which case
	// printing it twice says nothing.
	add('Name', headline === name ? '' : name);
	add('Father name', payload.identity.father_name);
	add('Age', payload.identity.age);
	add('Residence (R/O)', formatResidence(payload));
	add('Profession', payload.identity.occupation);
	add('Date of abduction', formatFullDate(payload.incident.date));
	add('Time of abduction', payload.incident.time);
	add('Place of abduction', payload.incident.place);
	add('Abductors', payload.incident.abductors);

	// What the server took out, named. The poster says it is missing
	// rather than letting the reader assume the field was never
	// recorded.
	if (payload.withheld.length > 0) {
		add('Not disclosed', payload.withheld.join(', '));
	}

	return {
		reference: clean(payload.reference) || null,
		date: formatEditorialDate(payload.generated_date),
		title: headline,
		name,
		statusLabel: clean(payload.status_label) || null,
		photo: payload.photo ? { src: payload.photo.url, alt: payload.photo.alt } : null,
		rows,
		hashtags: payload.categories.map(categoryHashtag).filter(Boolean),
	};
}

/**
 * Residence reads "Alexandria, Egypt" when the server disclosed a
 * place, and just the country when it disclosed no more than that.
 * The payload's `location` is absent entirely when the location was
 * withheld.
 */
function formatResidence(payload: CaseCardPayload): string {
	const location = payload.location;
	if (!location) return '';
	const display = clean(location.display);
	const country = clean(location.country);
	if (display && country) return `${display}, ${country}`;
	return display || country;
}

/** Trim to a non-empty string; anything else becomes ''. */
function clean(value: unknown): string {
	if (typeof value === 'number') return Number.isFinite(value) ? String(value) : '';
	if (typeof value !== 'string') return '';
	return value.trim();
}
