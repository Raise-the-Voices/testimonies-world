/**
 * Tests for the /submit (new-person) Zod schema.
 *
 * The schema mirrors the backend's PersonWriteSerializer — it exists
 * to short-circuit obvious client-side errors so the volunteer sees
 * the message inline instead of waiting on a 400 round-trip. These
 * tests pin the cross-field rules (gibberish rejection, enums, date
 * format) and the per-field length caps.
 */

import { describe, it, expect } from 'vitest';

import {
	validatePersonWriteRequest,
	type PersonWriteRequestInput,
} from './personForm';

/** Minimal valid payload. Tests below mutate this to hit each branch. */
function basePayload(): Record<string, unknown> {
	return {
		name: 'Fatima al-Sayed',
		country: 'Iraq',
		current_status: 'detained',
		medical_status: 'unknown',
		rough_location: 'Baghdad',
		precise_location: '',
		summary_narrative: 'Detained at a checkpoint on March 14 after a protest.',
		ethnicity: '',
		last_known_date: '',
		occupation: 'teacher',
		legal_name: '',
		aliases: '',
		medical_notes: '',
		authoritative_source: '',
		authoritative_url: '',
		is_published: false,
	};
}

describe('validatePersonWriteRequest', () => {
	it('accepts a minimal valid payload', () => {
		const result = validatePersonWriteRequest(basePayload());
		expect(result.ok).toBe(true);
		if (result.ok) {
			expect(result.data.name).toBe('Fatima al-Sayed');
			expect(result.data.country).toBe('Iraq');
		}
	});

	it('rejects blank name', () => {
		const payload = basePayload();
		payload.name = '   ';
		const result = validatePersonWriteRequest(payload);
		expect(result.ok).toBe(false);
		if (!result.ok) {
			expect(result.errors.name).toBeTruthy();
		}
	});

	it('rejects single-character name (must be ≥ 2)', () => {
		const payload = basePayload();
		payload.name = 'A';
		const result = validatePersonWriteRequest(payload);
		expect(result.ok).toBe(false);
	});

	it('trims surrounding whitespace on name and country', () => {
		const payload = basePayload();
		payload.name = '  Fatima al-Sayed  ';
		payload.country = '  Iraq  ';
		const result = validatePersonWriteRequest(payload);
		expect(result.ok).toBe(true);
		if (result.ok) {
			expect(result.data.name).toBe('Fatima al-Sayed');
			expect(result.data.country).toBe('Iraq');
		}
	});

	it('rejects blank country', () => {
		const payload = basePayload();
		payload.country = '';
		const result = validatePersonWriteRequest(payload);
		expect(result.ok).toBe(false);
		if (!result.ok) {
			expect(result.errors.country).toBeTruthy();
		}
	});

	it('rejects unknown current_status enum value', () => {
		const payload = basePayload();
		// Cast through unknown to bypass the typed basePayload.
		(payload as Record<string, unknown>).current_status = 'banished_to_mars';
		const result = validatePersonWriteRequest(payload);
		expect(result.ok).toBe(false);
		if (!result.ok) {
			expect(result.errors.current_status).toBeTruthy();
		}
	});

	it('accepts every current_status enum value', () => {
		const valid = [
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
		];
		for (const s of valid) {
			const payload = basePayload();
			(payload as Record<string, unknown>).current_status = s;
			const result = validatePersonWriteRequest(payload);
			expect(result.ok).toBe(true);
		}
	});

	it('rejects malformed last_known_date (not YYYY-MM-DD)', () => {
		const payload = basePayload();
		payload.last_known_date = '03/14/2025';
		const result = validatePersonWriteRequest(payload);
		expect(result.ok).toBe(false);
		if (!result.ok) {
			expect(result.errors.last_known_date).toMatch(/YYYY-MM-DD/);
		}
	});

	it('accepts a well-formed last_known_date', () => {
		const payload = basePayload();
		payload.last_known_date = '2025-03-14';
		const result = validatePersonWriteRequest(payload);
		expect(result.ok).toBe(true);
	});

	it('accepts empty last_known_date (field is optional)', () => {
		const payload = basePayload();
		payload.last_known_date = '';
		const result = validatePersonWriteRequest(payload);
		expect(result.ok).toBe(true);
	});

	it('rejects authoritative_url without http(s) scheme', () => {
		const payload = basePayload();
		payload.authoritative_url = 'example.com/news';
		const result = validatePersonWriteRequest(payload);
		expect(result.ok).toBe(false);
		if (!result.ok) {
			expect(result.errors.authoritative_url).toMatch(/http/);
		}
	});

	it('accepts authoritative_url with https://', () => {
		const payload = basePayload();
		payload.authoritative_url = 'https://example.com/news/123';
		const result = validatePersonWriteRequest(payload);
		expect(result.ok).toBe(true);
	});

	it('accepts empty authoritative_url', () => {
		const payload = basePayload();
		payload.authoritative_url = '';
		const result = validatePersonWriteRequest(payload);
		expect(result.ok).toBe(true);
	});

	it('rejects pure-punctuation summary (gibberish guard)', () => {
		const payload = basePayload();
		payload.summary_narrative = '!!!??...---';
		const result = validatePersonWriteRequest(payload);
		expect(result.ok).toBe(false);
		if (!result.ok) {
			expect(result.errors.summary_narrative).toMatch(/gibberish/);
		}
	});

	it('rejects one-character-repeated summary (gibberish guard)', () => {
		const payload = basePayload();
		payload.summary_narrative = 'aaaaaaaaaa';
		const result = validatePersonWriteRequest(payload);
		expect(result.ok).toBe(false);
		if (!result.ok) {
			expect(result.errors.summary_narrative).toMatch(/gibberish/);
		}
	});

	it('allows blank summary (it is optional and may be empty)', () => {
		const payload = basePayload();
		payload.summary_narrative = '';
		const result = validatePersonWriteRequest(payload);
		expect(result.ok).toBe(true);
	});

	it('rejects category_ids containing non-integers', () => {
		const payload = basePayload();
		payload.category_ids = ['1', '2'];
		const result = validatePersonWriteRequest(payload);
		expect(result.ok).toBe(false);
		if (!result.ok) {
			expect(result.errors.category_ids).toBeTruthy();
		}
	});

	it('rejects negative category_ids', () => {
		const payload = basePayload();
		payload.category_ids = [-1, 2];
		const result = validatePersonWriteRequest(payload);
		expect(result.ok).toBe(false);
	});

	it('accepts category_ids as a positive integer array', () => {
		const payload = basePayload();
		payload.category_ids = [1, 2, 3];
		const result = validatePersonWriteRequest(payload);
		expect(result.ok).toBe(true);
	});

	it('rejects summary_narrative exceeding the 10000-char cap', () => {
		const payload = basePayload();
		payload.summary_narrative = 'a'.repeat(10_001);
		const result = validatePersonWriteRequest(payload);
		expect(result.ok).toBe(false);
		if (!result.ok) {
			expect(result.errors.summary_narrative).toMatch(/too long/i);
		}
	});

	it('rejects age_at_incident above 150', () => {
		const payload = basePayload();
		(payload as Record<string, unknown>).age_at_incident = 200;
		const result = validatePersonWriteRequest(payload);
		expect(result.ok).toBe(false);
	});

	it('rejects negative age_at_incident', () => {
		const payload = basePayload();
		(payload as Record<string, unknown>).age_at_incident = -1;
		const result = validatePersonWriteRequest(payload);
		expect(result.ok).toBe(false);
	});

	it('accepts quality_tier = 1, 2, 3, or null', () => {
		for (const tier of [1, 2, 3, null]) {
			const payload = basePayload();
			(payload as Record<string, unknown>).quality_tier = tier;
			const result = validatePersonWriteRequest(payload);
			expect(result.ok).toBe(true);
		}
	});

	it('rejects quality_tier = 4 (out of range)', () => {
		const payload = basePayload();
		(payload as Record<string, unknown>).quality_tier = 4;
		const result = validatePersonWriteRequest(payload);
		expect(result.ok).toBe(false);
	});

	it('returns ok:false with empty errors object when payload is a non-object', () => {
		const result = validatePersonWriteRequest(null as unknown as Record<string, unknown>);
		expect(result.ok).toBe(false);
		if (!result.ok) {
			expect(typeof result.errors).toBe('object');
		}
	});

	it('preserves the PersonWriteRequestInput type surface', () => {
		// Compile-time check that the inferred type contains the expected
		// optional fields. If a future change drops one, this test file
		// fails to compile and the reviewer sees it immediately.
		const sample: PersonWriteRequestInput = {
			name: 'A',
			country: 'B',
			current_status: 'detained',
			medical_status: 'unknown',
			rough_location: '',
			precise_location: '',
			summary_narrative: '',
			ethnicity: '',
			occupation: '',
			legal_name: '',
			aliases: '',
			medical_notes: '',
			authoritative_source: '',
			authoritative_url: '',
			is_published: false,
		};
		expect(sample.name).toBe('A');
	});
});
