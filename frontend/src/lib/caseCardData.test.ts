import { describe, it, expect } from 'vitest';
import { buildCaseCardData, type CaseCardPayload } from './caseCardData';
import { formatFullDate } from './dateFormat';

/**
 * Tests for the case-card resolver.
 *
 * The card is a poster, so the rules that matter are: which facts end
 * up on it, in what order, and which facts are left out entirely. A
 * row with an empty value is worse than no row — it reads as "we know
 * this and it is blank" instead of "we don't have this".
 *
 * The input is the MASKED payload the server returns. Nothing here
 * derives a fact the server did not send: the whole point of the
 * masked endpoint is that the browser cannot re-derive the card from
 * the person record, and these tests pin that the card prints what it
 * is given.
 */

function makePayload(overrides: Partial<CaseCardPayload> = {}): CaseCardPayload {
	return {
		schema_version: 1,
		reference: 'ED-2026-0042',
		generated_date: '2026-03-14',
		headline: 'Enforced Disappearance',
		title: 'Ahmed Al-Hassan',
		status: 'disappeared',
		status_label: 'Disappeared',
		identity: {
			display_name: 'Ahmed Al-Hassan',
			father_name: 'Yusuf Al-Hassan',
			age: 34,
			occupation: 'Teacher',
		},
		location: {
			country: 'Egypt',
			display: 'Alexandria, Smouha',
			precision: 'city',
		},
		incident: {
			date: '2025-11-03',
			time: '21:30',
			place: 'Old City, Alexandria',
			abductors: 'Security Service',
			detail: null,
		},
		photo: { url: 'https://example.org/public-media/profiles/face.jpg', alt: '' },
		categories: ['Enforced disappearance'],
		verification: { level: 'level_3_corroborated', label: 'Corroborated' },
		source_label: 'Family',
		exportable: true,
		withheld: [],
		...overrides,
	};
}

/** The labels of the rows the card produced, in order. */
function labels(data: ReturnType<typeof buildCaseCardData>): string[] {
	return data.rows.map((r) => r.label);
}

/** The value of the first row with this label, or undefined. */
function valueOf(
	data: ReturnType<typeof buildCaseCardData>,
	label: string,
): string | undefined {
	return data.rows.find((r) => r.label === label)?.value;
}

describe('formatFullDate', () => {
	it('renders a day-precision date', () => {
		expect(formatFullDate('2026-03-14')).toBe('14 Mar 2026');
	});

	it('accepts a Date — the shape the Zod boundary produces', () => {
		expect(formatFullDate(new Date('2026-03-14T00:00:00Z'))).toBe('14 Mar 2026');
	});

	it('accepts a month-precision string', () => {
		expect(formatFullDate('2026-03')).toBe('1 Mar 2026');
	});

	it('returns an empty string for nullish and unreadable input', () => {
		expect(formatFullDate(null)).toBe('');
		expect(formatFullDate(undefined)).toBe('');
		expect(formatFullDate('')).toBe('');
		expect(formatFullDate('not-a-date')).toBe('');
		expect(formatFullDate(new Date('nope'))).toBe('');
	});

	it('does not shift the day across time zones', () => {
		// A UTC-midnight date must render as that date everywhere.
		expect(formatFullDate(new Date('2026-01-01T00:00:00Z'))).toBe('1 Jan 2026');
	});
});

describe('buildCaseCardData', () => {
	it('renders the core facts in poster order', () => {
		const data = buildCaseCardData(makePayload());

		expect(data.reference).toBe('ED-2026-0042');
		expect(data.title).toBe('Ahmed Al-Hassan');
		expect(data.statusLabel).toBe('Disappeared');
		expect(labels(data)).toEqual([
			'Age',
			'Residence',
			'Profession',
			'Father',
			'Abduction date',
			'Abduction place',
			'Perpetrators',
		]);
		expect(valueOf(data, 'Age')).toBe('34');
		expect(valueOf(data, 'Residence')).toBe('Alexandria, Smouha, Egypt');
		expect(valueOf(data, 'Profession')).toBe('Teacher');
		expect(valueOf(data, 'Father')).toBe('Yusuf Al-Hassan');
		expect(valueOf(data, 'Abduction date')).toBe('3 Nov 2025');
		expect(valueOf(data, 'Abduction place')).toBe('Old City, Alexandria');
		expect(valueOf(data, 'Perpetrators')).toBe('Security Service');
	});

	it('omits a row entirely when the value is missing', () => {
		const data = buildCaseCardData(
			makePayload({
				identity: {
					display_name: 'Ahmed Al-Hassan',
					father_name: null,
					age: null,
					occupation: null,
				},
				incident: {
					date: null,
					time: null,
					place: null,
					abductors: null,
					detail: null,
				},
			}),
		);
		// No age, no occupation, no father, no incident block.
		expect(labels(data)).toEqual(['Residence']);
		expect(valueOf(data, 'Residence')).toBe('Alexandria, Smouha, Egypt');
	});

	it('leaves the residence row off when the location is withheld', () => {
		// A withheld location is not a blank one: the key is ABSENT
		// from the payload, and the row goes with it.
		const data = buildCaseCardData(makePayload({ location: undefined }));
		expect(labels(data)).not.toContain('Residence');
	});

	it('shows the country alone when the server discloses no more', () => {
		const data = buildCaseCardData(
			makePayload({
				location: { country: 'Egypt', display: null, precision: 'province' },
			}),
		);
		expect(valueOf(data, 'Residence')).toBe('Egypt');
	});

	it('prints the display the server sent, at its own precision', () => {
		const data = buildCaseCardData(
			makePayload({
				location: { country: 'Egypt', display: 'Alexandria', precision: 'district' },
			}),
		);
		expect(valueOf(data, 'Residence')).toBe('Alexandria, Egypt');
	});

	it('has no photo when the payload has none', () => {
		// The photo key is OMITTED when the photograph is withheld —
		// it is never sent as an empty value.
		const data = buildCaseCardData(makePayload({ photo: undefined }));
		expect(data.photo).toBeNull();
	});

	it('has a photo when the payload has one', () => {
		const data = buildCaseCardData(makePayload());
		expect(data.photo).toEqual({
			src: 'https://example.org/public-media/profiles/face.jpg',
			alt: '',
		});
	});

	it('prints the withheld identity as the title', () => {
		const data = buildCaseCardData(
			makePayload({
				title: 'Identity withheld',
				identity: {
					display_name: 'Identity withheld',
					father_name: null,
					age: null,
					occupation: null,
				},
			}),
		);
		expect(data.title).toBe('Identity withheld');
	});

	it('uses the generated date in the header', () => {
		expect(buildCaseCardData(makePayload()).date).toBe('14 Mar 2026');
	});

	it('has no reference when the case has none', () => {
		expect(buildCaseCardData(makePayload({ reference: null })).reference).toBeNull();
		expect(buildCaseCardData(makePayload({ reference: '' })).reference).toBeNull();
		expect(
			buildCaseCardData(makePayload({ reference: '  ED-1  ' })).reference,
		).toBe('ED-1');
	});

	it('carries the server publication gate through untouched', () => {
		// The client never computes `exportable` — a user could patch
		// the client and export a card the case was never cleared for.
		expect(buildCaseCardData(makePayload({ exportable: true })).exportable).toBe(true);
		expect(buildCaseCardData(makePayload({ exportable: false })).exportable).toBe(false);
	});
});
