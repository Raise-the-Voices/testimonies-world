import { test, expect, type Page } from '@playwright/test';

/**
 * E2E: motion under the reader's own settings.
 *
 * The unit tests in `src/lib/motion.dom.test.ts` pin the contract
 * inside the component. This pins it in the browser: with "reduce
 * motion" turned on in the OS, nothing on the page may still be
 * travelling.
 *
 * The surface under test is the nav drawer, because it is the one
 * place where two kinds of motion meet: the panel slides by a CSS
 * transition, and the scrim fades by a Svelte transition. A CSS media
 * query can stop the first; only the JavaScript guard can stop the
 * second. Both have to be still.
 *
 * The API is intercepted rather than called. On a development box the
 * app's own API answers with a redirect to HTTPS that the browser
 * cannot follow, so an un-stubbed request hangs until it times out —
 * and a page whose load never settles is a page that never hydrates,
 * so its buttons do nothing.
 */

/** Keep the page's own data requests from hanging the load. */
async function stubPage(page: Page) {
	await page.route('**/api/session/', (route) =>
		route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({ authenticated: false, groups: [] }),
		}),
	);
	// The landing page reads the platform statistics. A failure is
	// handled by the page — it shows the stats bar in its error state —
	// and it settles the load, which is what lets the page hydrate.
	await page.route('**/api/persons/statistics/', (route) =>
		route.fulfill({
			status: 503,
			contentType: 'application/json',
			body: JSON.stringify({ detail: 'Unavailable in this test.' }),
		}),
	);
}

/**
 * Open the landing page and wait until it has hydrated.
 *
 * The root layout's universal load runs on the client as well as on
 * the server, so the browser's own session request is the signal that
 * the client router is alive. Until the page hydrates, its buttons do
 * nothing — and a click on a dead button would look like a drawer that
 * never opens.
 */
async function openLandingPage(page: Page) {
	const session = page.waitForResponse(
		(response) => response.url().includes('/api/session/') && response.ok(),
	);
	await page.goto('/testimonies/');
	await session;
}

/**
 * Open the drawer and report where the panel is over the next frames.
 *
 * The readings are taken inside the page, in the page's own task
 * queue: a click that goes through Playwright's actionability checks
 * can land a whole animation too late to see the movement.
 */
async function openDrawerAndRead(page: Page) {
	return page.evaluate(async () => {
		const drawer = document.querySelector('#primary-nav-drawer') as HTMLElement;
		const toggle = document.querySelector('.nav-toggle') as HTMLElement;
		const frame = () =>
			new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
		const x = () => drawer.getBoundingClientRect().x;

		toggle.click();
		// Two frames: one for the browser to apply the open state, one
		// for the first frame of the movement to be painted.
		await frame();
		await frame();
		const early = x();
		const scrim = document.querySelector('.nav-scrim') as HTMLElement | null;
		const scrimOpacity = scrim ? getComputedStyle(scrim).opacity : null;
		// Long enough for a 320ms transition to be over.
		await new Promise<void>((resolve) => setTimeout(resolve, 500));
		return { early, settled: x(), scrimOpacity };
	});
}

test.describe('reduced motion', () => {
	test.use({ reducedMotion: 'reduce' });

	test('the nav drawer opens without travelling', async ({ page }) => {
		await page.setViewportSize({ width: 390, height: 844 });
		await stubPage(page);
		await openLandingPage(page);

		const reading = await openDrawerAndRead(page);

		// The panel was already where it ended up two frames after the
		// tap, and it stayed there. It did not slide.
		expect(reading.early).toBeCloseTo(reading.settled, 1);
		// And it is on screen: the drawer opened at all.
		expect(reading.settled).toBeLessThan(390);
		// The scrim is fully opaque straight away. The scrim's fade is
		// a Svelte transition — a Web Animations animation — and only
		// the JavaScript guard can stop it.
		expect(reading.scrimOpacity).toBe('1');
	});
});

test.describe('motion allowed', () => {
	test('the nav drawer slides into place', async ({ page }) => {
		// The counter-test. If the drawer did not move at all, the
		// reduced-motion test above would pass for the wrong reason.
		await page.setViewportSize({ width: 390, height: 844 });
		await stubPage(page);
		await openLandingPage(page);

		const reading = await openDrawerAndRead(page);

		// It started off-screen and came in.
		expect(reading.early).toBeGreaterThan(reading.settled);
		expect(reading.settled).toBeLessThan(390);
	});
});
