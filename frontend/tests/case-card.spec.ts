import { test, expect, type Page, type Locator } from '@playwright/test';

/**
 * E2E: the interactive "Case Information Card" modal.
 *
 * The card is a poster — a flat, ordered sheet of the core facts — so
 * the things worth pinning are:
 *
 *   1. The card opens, is centred, and the backdrop behind it is
 *      blurred and dimmed (the requirement's "gorgeous, centred
 *      modal overlay").
 *   2. Every core fact lands on the card, in the poster's order, and
 *      the headline is the kind of violation the case records.
 *   3. A fact that is not recorded is left OFF the card entirely
 *      rather than rendered blank.
 *   4. The close control dismisses it, and Escape dismisses it.
 *   5. The poster downloads for a published case — the server's
 *      verdict, not the browser's.
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
	// Section K — the consent flags. Every case in the database today
	// has them blank, which is why no case may be exported yet.
	is_published: true,
	consent_public_publication: '',
	public_identity_level: '',
	photograph_public: '',
	// Envelope fields the detail page itself needs.
	created_at: '2026-03-14T09:00:00Z',
	updated_at: '2026-03-14T09:00:00Z',
	created_by: null,
	days_since_last_report: 12,
	profile_image_url: null,
	categories: [{ id: 1, name: 'Enforced disappearance', description: '' }],
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
 * The masked card payload the server answers with — the projection the
 * poster is exported from. `exportable` is the server's verdict.
 */
function cardPayload(overrides: Record<string, unknown> = {}) {
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
		photo: { url: '/testimonies/public-media/profiles/face.png', alt: '' },
		categories: ['Enforced disappearance'],
		verification: { level: 'level_3_corroborated', label: 'Corroborated' },
		source_label: 'Family',
		exportable: false,
		withheld: [],
		...overrides,
	};
}

/** A 1×1 PNG — enough for the browser to decode the photograph. */
const PIXEL_PNG = Buffer.from(
	'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
	'base64',
);

/**
 * The content security policy nginx sends in production.
 *
 * The dev server sends none, so a spec that runs against the dev
 * server alone cannot see the environment the app actually ships in.
 * The poster's download is the case in point: it once fetched the
 * rendered PNG as a `data:` URL, which `connect-src 'self'` refuses —
 * the poster rendered perfectly and still failed to download.
 */
const PRODUCTION_CSP = [
	"default-src 'self'",
	"img-src 'self' data: blob: https:",
	"script-src 'self' 'unsafe-inline' https://accounts.google.com",
	"style-src 'self' 'unsafe-inline'",
	"font-src 'self' data:",
	"connect-src 'self' https://accounts.google.com",
	"frame-src https://accounts.google.com",
	"frame-ancestors 'none'",
	"form-action 'self' https://accounts.google.com",
	"base-uri 'self'",
	"object-src 'none'",
].join('; ');

/**
 * Serve the person page with the production CSP header.
 */
async function withProductionCsp(page: Page, personId: number) {
	await page.route(
		(url) => url.pathname === `/testimonies/persons/${personId}`,
		async (route) => {
			const response = await route.fetch();
			const body = await response.body();
			const headers = { ...response.headers() };
			// The body handed back is already decoded; a stale
			// content-encoding would make the browser try to unpack it
			// again.
			delete headers['content-encoding'];
			delete headers['content-length'];
			await route.fulfill({
				response,
				body,
				headers: { ...headers, 'content-security-policy': PRODUCTION_CSP },
			});
		},
	);
}

/**
 * Intercept the calls the detail page makes and serve the given person
 * payload. Everything else is left to the real dev server.
 */
async function stubCase(page: Page, person: unknown, card: unknown = cardPayload()) {
	await page.route(`**/api/persons/${(person as { id: number }).id}/`, (route) =>
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(person),
		}),
	);
	await page.route(`**/api/persons/${(person as { id: number }).id}/card/`, (route) =>
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify(card),
		}),
	);
	// The photograph on the poster. It has to load for the export to
	// work, and it has to be same-origin for the canvas not to be
	// tainted — which is why the payload points at the app's own path.
	await page.route('**/public-media/**', (route) =>
		route.fulfill({ status: 200, contentType: 'image/png', body: PIXEL_PNG }),
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

/** Click the download button and read back the file it produced. */
async function capturePoster(page: Page, download: Locator): Promise<Buffer> {
	const [downloadEvent] = await Promise.all([
		page.waitForEvent('download'),
		download.click(),
	]);
	const stream = await downloadEvent.createReadStream();
	const chunks: Buffer[] = [];
	for await (const chunk of stream) chunks.push(Buffer.from(chunk));
	return Buffer.concat(chunks);
}

/** The day the poster is dated — the day the sheet was produced. */
function today(): string {
	return new Date().toLocaleDateString('en-GB', {
		day: 'numeric',
		month: 'long',
		year: 'numeric',
		timeZone: 'UTC',
	});
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

			// The sheet is a poster, not a panel: 720px wide, with room
			// around it inside the dialog.
			const cardBox = (await page.locator('.case-card').boundingBox())!;
			expect(Math.round(cardBox.width)).toBe(720);
			expect(box.width).toBeGreaterThanOrEqual(cardBox.width);

			// The close control is in the card's top corner and is big
			// enough to hit (WCAG 2.5.5 — 44px).
			const close = dialog.getByRole('button', { name: 'Close case information card' });
			await expect(close).toBeVisible();
			const closeBox = (await close.boundingBox())!;
			expect(closeBox.width).toBeGreaterThanOrEqual(44);
			expect(closeBox.height).toBeGreaterThanOrEqual(44);
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

			// Header: the citable reference and the day the sheet was
			// produced.
			await expect(dialog.locator('.case-card-ref')).toHaveText('Ref: ED-2026-0042');
			await expect(dialog.locator('.case-card-date')).toHaveText(today());

			// Title block: the kind of violation the file records, and
			// the person's condition.
			await expect(dialog.getByRole('heading', { name: 'Enforced Disappearance' })).toBeVisible();
			await expect(dialog.locator('.case-card-status')).toHaveText('Disappeared');

			// Metadata rows, in the order the poster prints them.
			const rows = dialog.locator('.case-card-meta-row');
			await expect(rows).toHaveCount(9);
			await expect(rows.locator('.case-card-meta-label')).toHaveText([
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
			await expect(rows.locator('.case-card-meta-value')).toHaveText([
				'Ahmed Al-Hassan',
				'Yusuf Al-Hassan',
				'34',
				'Alexandria, Egypt',
				'Teacher',
				'3 Nov 2025',
				'21:30',
				'Old City, Alexandria',
				'Security Service',
			]);

			// Footer: a hashtag per case category, and the signature.
			await expect(dialog.locator('.case-card-tag')).toHaveText([
				'#EnforcedDisappearance',
			]);
			await expect(dialog.locator('.case-card-brand')).toHaveText(
				'Testimonies.world · cases.raisethevoices.org',
			);
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
			// is worse than saying nothing. Only the name and the
			// country survive.
			const rows = dialog.locator('.case-card-meta-row');
			await expect(rows).toHaveCount(2);
			await expect(rows.locator('.case-card-meta-label')).toHaveText([
				'Name',
				'Residence (R/O)',
			]);
			await expect(rows.locator('.case-card-meta-value')).toHaveText([
				'Layla Haddad',
				'Pakistan',
			]);

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

	test(
		'will not download a poster the server has not cleared',
		{
			tag: ['@critical'],
			annotation: [{ type: 'ticket', description: 'case-info-card' }],
		},
		async ({ page }) => {
			// Publication consent refused on the case file. The poster
			// publishes what the public case page publishes, so the
			// refusal is the one thing that stops it.
			await stubCase(page, { ...FULL_PERSON, consent_public_publication: 'no' });
			const dialog = await openCard(page, PERSON_ID);

			const download = dialog.getByRole('button', { name: 'Download poster (PNG)' });
			await expect(download).toBeDisabled();
			// The reason says which field to go and set.
			await expect(dialog.locator('.case-card-export-note')).toHaveText(
				'Publication not approved — publication consent is declined.',
			);
		},
	);

	test(
		'downloads the poster for a published case',
		{
			tag: ['@critical'],
			annotation: [{ type: 'ticket', description: 'case-info-card' }],
		},
		async ({ page }) => {
			// The consent flags are blank on every case today. The
			// poster publishes what the public case page publishes, so
			// a published case downloads without any of them being set.
			await stubCase(page, FULL_PERSON, cardPayload({ exportable: true }));
			const dialog = await openCard(page, PERSON_ID);

			const download = dialog.getByRole('button', { name: 'Download poster (PNG)' });
			await expect(download).toBeEnabled();

			const [downloadEvent] = await Promise.all([
				page.waitForEvent('download'),
				download.click(),
			]);
			// The file is named after the case reference.
			expect(downloadEvent.suggestedFilename()).toBe('case-ED-2026-0042.png');

			// And it is a real PNG, not an empty file.
			const path = await downloadEvent.path();
			expect(path).toBeTruthy();
			const bytes = await downloadEvent.createReadStream();
			const chunks: Buffer[] = [];
			for await (const chunk of bytes) chunks.push(Buffer.from(chunk));
			const file = Buffer.concat(chunks);
			expect(file.length).toBeGreaterThan(1000);
			// PNG magic number.
			expect(file.subarray(0, 8).toString('hex')).toBe('89504e470d0a1a0a');
		},
	);

	test(
		'downloads the poster under the production content security policy',
		{
			tag: ['@critical'],
			annotation: [{ type: 'ticket', description: 'case-info-card' }],
		},
		async ({ page }) => {
			await withProductionCsp(page, PERSON_ID);
			await stubCase(page, FULL_PERSON, cardPayload({ exportable: true }));
			const dialog = await openCard(page, PERSON_ID);

			const download = dialog.getByRole('button', { name: 'Download poster (PNG)' });
			await expect(download).toBeEnabled();

			const [downloadEvent] = await Promise.all([
				page.waitForEvent('download'),
				download.click(),
			]);
			expect(downloadEvent.suggestedFilename()).toBe('case-ED-2026-0042.png');

			// The poster rendered; the download was not refused by the
			// browser's policy. The note stays the quiet one.
			await expect(dialog.locator('.case-card-export-note')).toHaveText(
				'The poster carries the same details as the public case page.',
			);
		},
	);

	test(
		'exports the same poster twice, byte for byte',
		{
			tag: ['@critical'],
			annotation: [{ type: 'ticket', description: 'case-info-card' }],
		},
		async ({ page }) => {
			await stubCase(page, FULL_PERSON, cardPayload({ exportable: true }));
			const dialog = await openCard(page, PERSON_ID);

			// The fonts have to be in before the first export: the
			// sheet is laid out with whatever the browser has at that
			// moment, and a poster drawn in a fallback font is a
			// different file.
			await page.evaluate(() => document.fonts.ready);

			const download = dialog.getByRole('button', { name: 'Download poster (PNG)' });
			const first = await capturePoster(page, download);
			const second = await capturePoster(page, download);

			expect(first.length).toBeGreaterThan(1000);
			// The poster is a published file. Anything moving when it
			// was captured — a reveal caught half-way, a transition
			// still running — would make the two exports differ, and
			// the same case would publish two different posters.
			expect(second.equals(first)).toBe(true);
		},
	);
});
