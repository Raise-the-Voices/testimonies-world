import { test, expect, type Page } from '@playwright/test';

/**
 * E2E: the interactive "Case Information Card" modal.
 *
 * The card is opened from a case file at /persons/<id>/. It is a
 * poster — a flat, ordered sheet of the core facts — so the things
 * worth pinning are:
 *
 *   1. The card opens, is centred, and the backdrop behind it is
 *      blurred and dimmed (the requirement's "gorgeous, centred
 *      modal overlay").
 *   2. Every core fact lands on the card, in the poster's order.
 *   3. A fact that is not recorded is left OFF the card entirely
 *      rather than rendered blank.
 *   4. The close control dismisses it, and Escape dismisses it.
 *
 * The API is intercepted with page.route() rather than driven against
 * the live backend. Two reasons: the card's rows are only meaningful
 * with a fully-populated record (a real case file rarely has a public
 * reference, an age, an occupation AND a named parent AND a complete
 * abduction block all at once), and the check must not write to or
 * depend on real casework data.
 *
 * The intercepted payload carries exactly the fields the card reads,
 * with the same names the API uses, so a change to either the backend
 * serializer or the frontend overlay breaks this spec.
 */

/** A person id that cannot collide with a real record. */
const PERSON_ID = 999999;

/** A person payload with every field the card reads filled in. */
const FULL_PERSON = {
	id: PERSON_ID,
	name: 'Ahmed Al-Hassan',
	country: 'Egypt',
	rough_location: 'Alexandria',
	current_status: 'disappeared',
	medical_status: 'unknown',
	// Card-specific fields.
	public_reference: 'ED-2026-0042',
	age_at_incident: 34,
	occupation: 'Teacher',
	case_received_date: '2026-02-02',
	// The father's name, resolved on the server: the relation row says
	// "parent", so only the server can tell a father from a mother.
	father_name: 'Yusuf Al-Hassan',
	// Envelope fields the detail page itself needs.
	created_at: '2026-03-14T09:00:00Z',
	updated_at: '2026-03-14T09:00:00Z',
	created_by: null,
	days_since_last_report: 12,
	is_published: true,
	profile_image_url: null,
	categories: [],
	media_files: [],
	family: [
		{
			person_id: 888888,
			person_name: 'Yusuf Al-Hassan',
			relationship: 'Parent',
			relationship_type: 'parent',
		},
	],
	reports: [
		{
			id: 1,
			person: PERSON_ID,
			source_type: 'document',
			narrative: 'Sighted being taken from the family home.',
			date_start: '2025-11-03',
			date_of_abduction: '2025-11-03',
			time_of_abduction: '21:30',
			place_of_abduction: 'Old City, Alexandria',
			abductors: 'Security Service',
			is_private: false,
			created_at: '2025-11-10T00:00:00Z',
			updated_at: '2025-11-10T00:00:00Z',
		},
	],
};

/** A person payload with nothing optional filled in. */
const SPARSE_PERSON = {
	...FULL_PERSON,
	id: PERSON_ID + 1,
	name: 'Layla Haddad',
	country: 'Pakistan',
	rough_location: '',
	public_reference: null,
	age_at_incident: null,
	occupation: '',
	case_received_date: null,
	father_name: null,
	family: [],
	reports: [],
};

/**
 * Intercept the three calls the detail page makes and serve the given
 * person payload. Everything else is left to the real dev server.
 */
async function stubCase(page: Page, person: unknown) {
	await page.route(`**/api/persons/${(person as { id: number }).id}/`, (route) =>
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(person),
		}),
	);
	await page.route('**/api/media/**', (route) =>
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ count: 0, next: null, previous: null, results: [] }),
		}),
	);
	await page.route('**/api/relationships/**', (route) =>
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify([]),
		}),
	);
	// The root layout is a universal load: it fetches the session on the
	// client during hydration, and the child route only mounts once that
	// settles. On a dev box the API answers plain HTTP with a 301 to
	// HTTPS, so the browser follows the redirect, fails the TLS handshake
	// and the session request hangs until it times out — 30 seconds
	// before the person record is ever asked for. Stubbing the session
	// keeps the spec hermetic and fast.
	await page.route('**/api/session/', (route) =>
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ authenticated: false, groups: [] }),
		}),
	);
}

/** Open the case file and the card. */
async function openCard(page: Page, personId: number) {
	await page.goto(`/testimonies/persons/${personId}`);
	await page.getByRole('button', { name: 'Case card' }).click();
	const dialog = page.getByRole('dialog', { name: 'Case information card' });
	await expect(dialog).toBeVisible();
	return dialog;
}

test.describe('Case information card', () => {
	test(
		'opens as a centred modal over a blurred backdrop',
		{
			tag: ['@critical'],
			annotation: [{ type: 'ticket', description: 'case-info-card' }],
		},
		async ({ page }) => {
			await stubCase(page, FULL_PERSON);
			const dialog = await openCard(page, PERSON_ID);

			// The backdrop is a full-viewport layer that dims and blurs
			// the page behind the card. Both are on the overlay element,
			// not on the dialog.
			const overlay = page.locator('.modal-overlay--poster');
			await expect(overlay).toBeVisible();
			const overlayStyle = await overlay.evaluate((el) => {
				const cs = getComputedStyle(el);
				return {
					backdropFilter: cs.backdropFilter,
					background: cs.backgroundColor,
					position: cs.position,
				};
			});
			expect(overlayStyle.backdropFilter).toContain('blur(8px)');
			expect(overlayStyle.position).toBe('fixed');
			// A semi-transparent dark scrim — not an opaque one.
			expect(overlayStyle.background).toMatch(/rgba\(0, 0, 0, 0\.\d+\)/);

			// Centred: the dialog's own centre is the viewport's centre.
			const box = (await dialog.boundingBox())!;
			const viewport = page.viewportSize()!;
			const centreDelta = Math.abs(
				box.x + box.width / 2 - (viewport.width / 2),
			);
			expect(centreDelta).toBeLessThan(2);

			// The close control is in the card's top corner and is big
			// enough to hit (WCAG 2.5.5 — 44px).
			const close = dialog.getByRole('button', { name: 'Close case information card' });
			await expect(close).toBeVisible();
			const closeBox = (await close.boundingBox())!;
			expect(closeBox.width).toBeGreaterThanOrEqual(44);
			expect(closeBox.height).toBeGreaterThanOrEqual(44);
			const cardBox = (await page.locator('.case-card').boundingBox())!;
			expect(closeBox.x + closeBox.width).toBeGreaterThan(cardBox.x);
			expect(closeBox.y).toBeLessThan(cardBox.y + cardBox.height);
		},
	);

	test(
		'shows the core case facts in poster order',
		{
			tag: ['@critical'],
			annotation: [{ type: 'ticket', description: 'case-info-card' }],
		},
		async ({ page }) => {
			await stubCase(page, FULL_PERSON);
			const dialog = await openCard(page, PERSON_ID);

			// Header: reference and the date the case was received.
			await expect(dialog.locator('.case-card-ref')).toHaveText('Ref: ED-2026-0042');
			await expect(dialog.locator('.case-card-date')).toHaveText('2 Feb 2026');

			// Title block: the person's name and the status.
			await expect(dialog.getByRole('heading', { name: 'Ahmed Al-Hassan' })).toBeVisible();
			await expect(dialog.locator('.case-card-status')).toHaveText('Disappeared');

			// Metadata rows, in the order the poster prints them.
			const rows = dialog.locator('.case-card-meta-row');
			await expect(rows).toHaveCount(7);
			await expect(rows.locator('.case-card-meta-label')).toHaveText([
				'Age',
				'Residence',
				'Profession',
				'Father',
				'Abduction date',
				'Abduction place',
				'Perpetrators',
			]);
			await expect(rows.locator('.case-card-meta-value')).toHaveText([
				'34',
				'Alexandria, Egypt',
				'Teacher',
				'Yusuf Al-Hassan',
				'3 Nov 2025',
				'Old City, Alexandria',
				'Security Service',
			]);
		},
	);

	test(
		'leaves out the facts that are not recorded',
		{
			tag: ['@critical'],
			annotation: [{ type: 'ticket', description: 'case-info-card' }],
		},
		async ({ page }) => {
			await stubCase(page, SPARSE_PERSON);
			const dialog = await openCard(page, SPARSE_PERSON.id);

			// A blank row reads as "we know this and it is empty", which
			// is worse than saying nothing. Only Residence survives.
			const rows = dialog.locator('.case-card-meta-row');
			await expect(rows).toHaveCount(1);
			await expect(rows.locator('.case-card-meta-label')).toHaveText(['Residence']);
			await expect(rows.locator('.case-card-meta-value')).toHaveText(['Pakistan']);

			// No reference, so the header says so plainly rather than
			// rendering an empty gap.
			await expect(dialog.locator('.case-card-ref')).toHaveText('Ref: Not assigned');
		},
	);

	test(
		'closes on the X button and on Escape',
		{
			tag: ['@critical'],
			annotation: [{ type: 'ticket', description: 'case-info-card' }],
		},
		async ({ page }) => {
			await stubCase(page, FULL_PERSON);
			const dialog = await openCard(page, PERSON_ID);

			await dialog.getByRole('button', { name: 'Close case information card' }).click();
			await expect(dialog).toHaveCount(0);

			// Re-open and dismiss with the keyboard.
			await page.getByRole('button', { name: 'Case card' }).click();
			await expect(dialog).toBeVisible();
			await page.keyboard.press('Escape');
			await expect(dialog).toHaveCount(0);
		},
	);

	test(
		'stays readable on a phone',
		{
			tag: ['@critical'],
			annotation: [{ type: 'ticket', description: 'case-info-card' }],
		},
		async ({ page }) => {
			await page.setViewportSize({ width: 390, height: 844 });
			await stubCase(page, FULL_PERSON);
			const dialog = await openCard(page, PERSON_ID);

			// The card fits the viewport width without overflowing.
			const cardBox = (await page.locator('.case-card').boundingBox())!;
			expect(cardBox.width).toBeLessThanOrEqual(390);

			// The two-column body collapses to one column, so the photo
			// sits above the list and the labels keep their own column.
			const bodyColumns = await page
				.locator('.case-card-body')
				.evaluate((el) => getComputedStyle(el).gridTemplateColumns);
			expect(bodyColumns.split(' ')).toHaveLength(1);
		},
	);
});
