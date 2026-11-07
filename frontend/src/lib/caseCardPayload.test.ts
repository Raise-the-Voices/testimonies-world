import { describe, it, expect } from 'vitest';
import { buildCardDataFromPayload } from './caseCardPayload';
import type { CaseCardPayload } from './api/generated/endpoints.schemas';

/**
 * Tests for the masked-payload resolver.
 *
 * The payload is what the server has cleared for publication. The
 * browser's only job is to lay it out, so these tests pin two things:
 * the poster prints what the payload carries, and it never prints
 * anything the payload did not carry. A resolver that reached past the
 * payload — back to the case file, say — would put unapproved facts
 * into a file meant to be shared, which is the one thing the masking
 * exists to prevent.
 */

function makePayload(overrides: Partial<CaseCardPayload> = {}): CaseCardPayload {
	return {
		schema_version: 1,
		reference: 'ED-2026-0042',
		generated_date: '2026-02-02',
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
		location: { country: 'Egypt', display: 'Alexandria', precision: 'city' },
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

/** The labels of the rows the poster produced, in order. */
function labels(payload: CaseCardPayload): string[] {
	return buildCardDataFromPayload(payload).rows.map((r) => r.label);
}

describe('buildCardDataFromPayload', () => {
	it('renders the cleared facts in poster order', () => {
		const data = buildCardDataFromPayload(makePayload());

		expect(data.reference).toBe('ED-2026-0042');
		expect(data.title).toBe('Enforced Disappearance');
		expect(data.statusLabel).toBe('Disappeared');
		expect(data.date).toBe('2 February 2026');
		expect(labels(makePayload())).toEqual([
			'Name',
			'Father name',
			'Age',
			'Residence (R/O)',
			'Profession',
			'Date of abduction',
			'Time of abduction',
			'Place of abduction',
			'Abductors',
		]);
	});

	it('prints the residence as the place and the country', () => {
		const data = buildCardDataFromPayload(makePayload());
		expect(data.rows.find((r) => r.label === 'Residence (R/O)')?.value).toBe(
			'Alexandria, Egypt',
		);
	});

	it('prints the country alone when the place was withheld', () => {
		const payload = makePayload({
			location: { country: 'Egypt', display: null, precision: 'province' },
		});
		const data = buildCardDataFromPayload(payload);
		expect(data.rows.find((r) => r.label === 'Residence (R/O)')?.value).toBe('Egypt');
	});

	it('has no residence row when the location was withheld entirely', () => {
		const payload = makePayload({ location: undefined });
		expect(labels(payload)).not.toContain('Residence (R/O)');
	});

	it('omits the name row when the headline is the name', () => {
		// A case filed under no category has the person's name as its
		// headline. Printing it twice says nothing.
		const payload = makePayload({
			headline: 'Ahmed Al-Hassan',
			title: 'Ahmed Al-Hassan',
		});
		const data = buildCardDataFromPayload(payload);
		expect(data.title).toBe('Ahmed Al-Hassan');
		expect(labels(payload)).not.toContain('Name');
	});

	it('names what was withheld instead of dropping the row', () => {
		const payload = makePayload({ withheld: ['precise location', 'photograph'] });
		const data = buildCardDataFromPayload(payload);
		const row = data.rows.find((r) => r.label === 'Not disclosed');
		expect(row?.value).toBe('precise location, photograph');
	});

	it('has no photo when the payload carries none', () => {
		const payload = makePayload({ photo: undefined });
		expect(buildCardDataFromPayload(payload).photo).toBeNull();
	});

	it('has a photo when the payload carries one', () => {
		const data = buildCardDataFromPayload(makePayload());
		expect(data.photo).toEqual({
			src: 'https://example.org/public-media/profiles/face.jpg',
			alt: '',
		});
	});

	it('prints a hashtag for every category in the payload', () => {
		const payload = makePayload({
			categories: ['Enforced disappearance', 'Arbitrary detention'],
		});
		expect(buildCardDataFromPayload(payload).hashtags).toEqual([
			'#EnforcedDisappearance',
			'#ArbitraryDetention',
		]);
	});

	it('prints nothing the payload did not carry', () => {
		// The identity was withheld, so the poster must not invent one:
		// the name becomes the server's placeholder and the age, the
		// occupation and the father are simply absent.
		const payload = makePayload({
			identity: {
				display_name: 'Identity withheld',
				father_name: null,
				age: null,
				occupation: null,
			},
			withheld: ['identity'],
		});
		const data = buildCardDataFromPayload(payload);
		expect(labels(payload)).not.toContain('Age');
		expect(labels(payload)).not.toContain('Profession');
		expect(labels(payload)).not.toContain('Father name');
		expect(data.rows.find((r) => r.label === 'Name')?.value).toBe('Identity withheld');
	});
});
