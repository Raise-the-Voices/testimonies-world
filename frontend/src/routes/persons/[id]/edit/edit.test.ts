// @vitest-environment jsdom
/**
 * Editing a case must not empty the fields the editor did not touch.
 *
 * The bug this pins: the person detail payload goes through
 * `PersonDetailSchema`, which turns `last_known_date` into a `Date`
 * (see `isoDateNullable` in `schemas/wire.ts`). The edit form read it
 * with `isoToMonthYear`, which only understood strings — so the month
 * picker came up empty, and the save sent `last_known_date: null`,
 * wiping the stored date on every save.
 *
 * The form under test is the real one: the real `getPerson()`, the real
 * Zod parse, the real submit path. Only the network is stubbed, at the
 * `fetch` layer, so a mock of the API client can't hide the shape the
 * form actually sees.
 */
import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest';
import { cleanup, render, waitFor, fireEvent } from '@testing-library/svelte';
import EditCase from './+page.svelte';
import { page } from '../../../../test-stubs/app-state';
import { navigationCalls } from '../../../../test-stubs/app-navigation';
import type { User } from '$lib/types';

/** A volunteer — the edit form is not shown to anonymous readers. */
const volunteer: User = { authenticated: true, username: 'ada', groups: ['Volunteer'] };

/**
 * The wire shape of one case, as the API returns it: dates as ISO
 * strings, before the Zod boundary converts them.
 */
const wirePerson = {
	id: 1,
	name: 'Yawar Habib',
	country: 'Afghanistan',
	legal_name: '',
	aliases: '',
	ethnicity: 'Pashtun',
	gender: 'F',
	current_status: 'disappeared',
	medical_status: 'unknown',
	medical_notes: '',
	rough_location: 'Kabul',
	precise_location: '',
	last_known_date: '2026-01-15',
	summary_narrative: 'Last seen on the way to the office.',
	occupation: 'Teacher',
	age_at_incident: 42,
	authoritative_source: 'ACGT',
	authoritative_url: 'https://example.org/case/12345',
	quality_tier: 2,
	is_published: true,
	date_of_birth: null,
	case_received_date: null,
	profile_image_url: null,
	profile_image: null,
	consent_public_publication: 'pending',
	public_identity_level: 'anonymous',
	photograph_public: 'pending',
	categories: [],
	reports: [],
	media_files: [],
	family: [],
	father_name: null,
	days_since_last_report: null,
	status_history: [],
	created_by: 10,
	created_at: '2026-10-05T16:16:59.657486Z',
	updated_at: '2026-10-05T16:16:59.657486Z'
};

/** The body of the PATCH the form sent, once it has sent one. */
let patchBody: Record<string, unknown> | null = null;

function jsonResponse(body: unknown): Response {
	return {
		ok: true,
		status: 200,
		statusText: 'OK',
		headers: { get: () => 'application/json' },
		text: async () => JSON.stringify(body)
	} as unknown as Response;
}

beforeEach(() => {
	patchBody = null;
	page.params = { id: '1' };

	vi.stubGlobal(
		'fetch',
		vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
			const url = String(input);
			const method = (init?.method ?? 'GET').toUpperCase();

			if (url.includes('/categories/')) return jsonResponse([]);
			if (url.includes('/persons/1/')) {
				if (method === 'PATCH') {
					patchBody = JSON.parse(String(init?.body ?? '{}'));
				}
				return jsonResponse(wirePerson);
			}
			throw new Error(`unexpected request: ${method} ${url}`);
		})
	);
});

afterEach(() => {
	cleanup();
	vi.unstubAllGlobals();
	navigationCalls.length = 0;
});

/** Open the edit form for the case and wait for it to load. */
async function openEditForm() {
	const { container } = render(EditCase, {
		props: { data: { user: volunteer, error: null } }
	});
	await waitFor(() => {
		expect(container.querySelector('#last_known_date')).not.toBeNull();
	}, { timeout: 5000 });
	return container;
}

/** Press "Save changes" and wait for the PATCH to go out. */
async function saveEditForm(container: HTMLElement) {
	const form = container.querySelector('form');
	expect(form).not.toBeNull();
	await fireEvent.submit(form as HTMLFormElement);
	await waitFor(() => {
		expect(patchBody).not.toBeNull();
	}, { timeout: 5000 });
	return patchBody as unknown as Record<string, unknown>;
}

function fieldValue(container: HTMLElement, id: string): string {
	const input = container.querySelector<HTMLInputElement>(`#${id}`);
	expect(input).not.toBeNull();
	return input?.value ?? '';
}

describe('editing a case', () => {
	it('shows the last known month the case carries', async () => {
		const container = await openEditForm();

		expect(fieldValue(container, 'last_known_date')).toBe('2026-01');
	});

	it('keeps the last known date when the case is saved', async () => {
		const container = await openEditForm();

		const body = await saveEditForm(container);

		// The month picker is month-precision, so the day is the 1st. What
		// must not happen is the field arriving empty and being sent as
		// null — that is what erased the stored date.
		expect(typeof body.last_known_date).toBe('string');
		expect(body.last_known_date).toMatch(/^2026-01/);
	});

	it('keeps age, gender, source and source URL when the case is saved', async () => {
		const container = await openEditForm();

		expect(fieldValue(container, 'age_at_incident')).toBe('42');
		expect(fieldValue(container, 'gender')).toBe('F');
		expect(fieldValue(container, 'authoritative_source')).toBe('ACGT');
		expect(fieldValue(container, 'authoritative_url')).toBe('https://example.org/case/12345');

		const body = await saveEditForm(container);

		expect(body.age_at_incident).toBe(42);
		expect(body.gender).toBe('F');
		expect(body.authoritative_source).toBe('ACGT');
		expect(body.authoritative_url).toBe('https://example.org/case/12345');
	});

	it('returns to the case page after the save', async () => {
		const container = await openEditForm();

		await saveEditForm(container);

		expect(navigationCalls).toContain('/persons/1');
	});
});
