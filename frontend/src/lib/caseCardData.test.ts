import { describe, it, expect } from 'vitest';
import {
	buildCaseCardData,
	pickAbductionReport,
	resolveParent,
	type CaseCardPerson,
} from './caseCardData';
import { formatFullDate } from './dateFormat';
import type { Report } from './types';

/**
 * Tests for the case-card resolver.
 *
 * The card is a poster, so the rules that matter are: which facts end
 * up on it, in what order, and which facts are left out entirely. A
 * row with an empty value is worse than no row — it reads as "we know
 * this and it is blank" instead of "we don't have this".
 *
 * The input is the case record the page already holds — the view of
 * the file for someone working it. The shareable, publication-facing
 * projection is a separate payload with its own masking rules
 * (`GET /api/persons/{id}/card/`), used when the card is exported.
 * These tests pin that the card prints the record it is given and
 * never invents a fact that is not in it.
 */

function makeReport(overrides: Partial<Report> = {}): Report {
	return {
		id: 1,
		person: 1,
		source_type: 'document' as const,
		narrative: 'Sighted being taken from the family home.',
		date_start: '2025-11-03',
		date_of_abduction: '2025-11-03',
		place_of_abduction: 'Old City, Alexandria',
		abductors: 'Security Service',
		created_at: '2025-11-10T00:00:00Z',
		updated_at: '2025-11-10T00:00:00Z',
		...overrides,
	};
}

function makePerson(overrides: Partial<CaseCardPerson> = {}): CaseCardPerson {
	return {
		id: 1,
		name: 'Ahmed Al-Hassan',
		country: 'Egypt',
		rough_location: 'Alexandria',
		current_status: 'disappeared',
		medical_status: 'unknown',
		created_at: '2026-03-14T09:00:00Z',
		updated_at: '2026-03-14T09:00:00Z',
		public_reference: 'ED-2026-0042',
		age_at_incident: 34,
		occupation: 'Teacher',
		case_received_date: '2026-02-02',
		father_name: 'Yusuf Al-Hassan',
		profile_image_url: 'https://example.org/public-media/profiles/face.jpg',
		family: [],
		reports: [makeReport()],
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
		const data = buildCaseCardData(makePerson());

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
		expect(valueOf(data, 'Residence')).toBe('Alexandria, Egypt');
		expect(valueOf(data, 'Profession')).toBe('Teacher');
		expect(valueOf(data, 'Father')).toBe('Yusuf Al-Hassan');
		expect(valueOf(data, 'Abduction date')).toBe('3 Nov 2025');
		expect(valueOf(data, 'Abduction place')).toBe('Old City, Alexandria');
		expect(valueOf(data, 'Perpetrators')).toBe('Security Service');
	});

	it('omits a row entirely when the value is missing', () => {
		const data = buildCaseCardData(
			makePerson({
				age_at_incident: null,
				occupation: '',
				father_name: null,
				family: [],
				reports: [],
			}),
		);
		// No age, no occupation, no father, no incident block.
		expect(labels(data)).toEqual(['Residence']);
		expect(valueOf(data, 'Residence')).toBe('Alexandria, Egypt');
	});

	it('shows the country alone when no rough location is recorded', () => {
		const data = buildCaseCardData(makePerson({ rough_location: '' }));
		expect(valueOf(data, 'Residence')).toBe('Egypt');
	});

	it('shows the rough location and the country', () => {
		const data = buildCaseCardData(makePerson({ rough_location: 'Alexandria' }));
		expect(valueOf(data, 'Residence')).toBe('Alexandria, Egypt');
	});

	it('never prints the precise location', () => {
		// The precise location is the private field on the record. The
		// card reads the rough one only.
		const data = buildCaseCardData(
			makePerson({ precise_location: '12 Rue de la Paix, Alexandria' }),
		);
		expect(valueOf(data, 'Residence')).toBe('Alexandria, Egypt');
		expect(JSON.stringify(data)).not.toContain('Rue de la Paix');
	});

	it('has no photo when the record has none', () => {
		const data = buildCaseCardData(makePerson({ profile_image_url: null }));
		expect(data.photo).toBeNull();
	});

	it('has a photo when the record has one', () => {
		const data = buildCaseCardData(makePerson());
		expect(data.photo).toEqual({
			src: 'https://example.org/public-media/profiles/face.jpg',
			alt: '',
		});
	});

	it('uses the received date in the header', () => {
		expect(buildCaseCardData(makePerson()).date).toBe('2 Feb 2026');
	});

	it('falls back to the entry date when the received date is unset', () => {
		const data = buildCaseCardData(makePerson({ case_received_date: null }));
		expect(data.date).toBe('14 Mar 2026');
	});

	it('has no reference when the case has none', () => {
		expect(buildCaseCardData(makePerson({ public_reference: null })).reference).toBeNull();
		expect(buildCaseCardData(makePerson({ public_reference: '' })).reference).toBeNull();
		expect(buildCaseCardData(makePerson({ public_reference: '  ED-1  ' })).reference).toBe(
			'ED-1',
		);
	});
});

describe('resolveParent', () => {
	it('uses the name the server resolved', () => {
		const parent = resolveParent(makePerson({ father_name: 'Yusuf Al-Hassan' }));
		expect(parent).toEqual({ label: 'Father', name: 'Yusuf Al-Hassan' });
	});

	it('falls back to a parent when the server resolved no father', () => {
		// The relation only says "parent". Naming someone a father
		// when the record does not say so would be a guess about a
		// person, so the row says "Parent" instead.
		const parent = resolveParent(
			makePerson({
				father_name: null,
				family: [
					{
						person_id: 2,
						person_name: 'Amina Al-Hassan',
						relationship: 'Parent',
						relationship_type: 'parent',
					},
				],
			}),
		);
		expect(parent).toEqual({ label: 'Parent', name: 'Amina Al-Hassan' });
	});

	it('has no parent row when the case records none', () => {
		expect(resolveParent(makePerson({ father_name: null, family: [] }))).toBeNull();
	});
});

describe('pickAbductionReport', () => {
	it('picks the earliest report that carries an abduction date', () => {
		const report = pickAbductionReport([
			makeReport({ id: 2, date_of_abduction: '2025-12-01' }),
			makeReport({ id: 1, date_of_abduction: '2025-11-03' }),
		]);
		expect(report?.id).toBe(1);
	});

	it('falls back to the earliest report by start date', () => {
		const report = pickAbductionReport([
			makeReport({ id: 2, date_of_abduction: null, date_start: '2025-12-01' }),
			makeReport({ id: 1, date_of_abduction: null, date_start: '2025-11-03' }),
		]);
		expect(report?.id).toBe(1);
	});

	it('has no report when the case records none', () => {
		expect(pickAbductionReport([])).toBeNull();
	});
});
