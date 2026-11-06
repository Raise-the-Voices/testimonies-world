/**
 * Case card data — the resolver behind the interactive "Case Information
 * Card" modal.
 *
 * The card is a *poster*: a flat, ordered list of facts about one case.
 * This module turns the MASKED card payload into that list, and
 * nothing else — no fetching, no formatting of presentation, no DOM.
 *
 * Why the payload is the only input: the card is the artefact that
 * leaves the platform. It gets rendered to an image and shared, so
 * what may appear on it is decided by the consent flags on the case —
 * publication consent, identity level, photograph clearance, location
 * precision — and that decision is made on the SERVER, in
 * `backend/cases/card/serializers.py`. The browser is handed only what
 * is cleared for publication.
 *
 * Building the card from the person detail record instead would put
 * the advocate's view of the case file on the poster — the name, the
 * age, the occupation, the photograph, the precise location — which
 * is exactly what the server-side masking exists to prevent. So the
 * person detail payload is not an input here at all.
 *
 * Why a separate module rather than logic inside the component: the
 * decisions here (which rows to drop when empty, how the location
 * reads) are pure functions, so they are unit-testable in the repo's
 * existing `environment: 'node'` vitest setup, which cannot render
 * components. Component rendering is covered by Playwright instead.
 */

import { formatFullDate } from './dateFormat';

/**
 * The masked card payload.
 *
 * Mirrors `CaseCardPayload` in the generated OpenAPI client
 * (`src/lib/api/generated/endpoints.schemas.ts`), which is the source
 * of truth — this interface is declared here only because the vitest
 * config runs the library tests in plain node with no `$lib` alias.
 * The modal hands the generated payload straight into
 * `buildCaseCardData`, so `npm run check` fails if the two drift.
 *
 * `location` and `photo` are OPTIONAL: the server omits them
 * entirely when they are withheld, and "this was withheld" is a
 * different fact from "this was empty".
 */
export interface CaseCardPayload {
	schema_version: number;
	reference: string | null;
	generated_date: string;
	headline: string;
	title: string;
	status: string;
	status_label: string;
	identity: {
		display_name: string;
		father_name: string | null;
		age: number | null;
		occupation: string | null;
	};
	location?: {
		country: string;
		display: string | null;
		precision: string;
	};
	incident: {
		date: string | null;
		time: string | null;
		place: string | null;
		abductors: string | null;
		detail: string | null;
	};
	photo?: { url: string; alt: string };
	categories: readonly string[];
	verification: { level: string | null; label: string | null };
	source_label: string | null;
	exportable: boolean;
	withheld: readonly string[];
}

export interface CardPhoto {
	src: string;
	alt: string;
}

export interface CardMetaRow {
	label: string;
	value: string;
}

export interface CaseCardData {
	/** Citable public reference, or null when the case has none yet. */
	reference: string | null;
	/** Header date — the day the card was generated. */
	date: string | null;
	title: string;
	statusLabel: string | null;
	photo: CardPhoto | null;
	/** Metadata rows in print order. Rows with no value are omitted
	 *  entirely — never rendered with an empty value. */
	rows: CardMetaRow[];
	/**
	 * The server's publication gate, carried through untouched.
	 *
	 * Any "Download poster" affordance MUST be driven by this flag and
	 * by nothing else: the client never computes it, or a user could
	 * patch the client and export a card the case was never cleared
	 * for. See `docs/case-info-card-architecture.md` §1.4 and §3.2.
	 */
	exportable: boolean;
}

/**
 * Build the card's data from the masked payload.
 *
 * Row order is fixed by the poster layout, not by the data: Age,
 * Residence, Profession, Father, then the abduction block.
 */
export function buildCaseCardData(payload: CaseCardPayload): CaseCardData {
	const rows: CardMetaRow[] = [];
	const add = (label: string, value: unknown) => {
		const v = clean(value);
		if (v) rows.push({ label, value: v });
	};

	add('Age', payload.identity.age ?? '');
	add('Residence', formatResidence(payload));
	add('Profession', payload.identity.occupation ?? '');
	add('Father', payload.identity.father_name ?? '');

	// The abduction event is one block on the server: the date, the
	// place and the perpetrators, already resolved from the case's
	// public reports. The card prints what it is given.
	add('Abduction date', formatFullDate(payload.incident.date ?? ''));
	add('Abduction place', payload.incident.place ?? '');
	add('Perpetrators', payload.incident.abductors ?? '');

	return {
		reference: clean(payload.reference) || null,
		date: formatFullDate(payload.generated_date) || null,
		title: clean(payload.title),
		statusLabel: clean(payload.status_label) || null,
		photo: payload.photo ? { src: payload.photo.url, alt: payload.photo.alt } : null,
		rows,
		exportable: payload.exportable,
	};
}

/**
 * Residence reads "Alexandria, Smouha, Egypt".
 *
 * The server decides how fine the location may be — `province` gives
 * the country alone, `city` adds the district and the rough location —
 * and the card prints what it is given. A withheld location is not a
 * blank one: the whole key is absent from the payload, and this
 * returns '' so the row is left off the card.
 */
function formatResidence(payload: CaseCardPayload): string {
	if (!payload.location) return '';
	return [payload.location.display, payload.location.country]
		.map((part) => clean(part))
		.filter((part) => part.length > 0)
		.join(', ');
}

/** Trim to a non-empty string; anything else becomes ''. */
function clean(value: unknown): string {
	if (typeof value === 'number') return Number.isFinite(value) ? String(value) : '';
	if (typeof value !== 'string') return '';
	return value.trim();
}
