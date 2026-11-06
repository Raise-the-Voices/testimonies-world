#!/usr/bin/env node
/**
 * Capture the screenshots used in README.md.
 *
 * Renders the live public app in Chromium and writes PNGs to
 * docs/assets/. Only public pages are captured — no login, no
 * authenticated surface, no case data that isn't already public
 * at the URL the screenshot points to.
 *
 * Usage:
 *   node scripts/capture-readme-screenshots.mjs [baseUrl]
 *
 * Defaults to the local instance so the capture never touches
 * production. Pass the public URL explicitly to shoot the live site.
 *
 * Env:
 *   CHROME_PATH  path to a Chromium binary (defaults to the
 *                 Playwright-managed build, then to a local copy).
 */
import { chromium } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';

const BASE = (process.argv[2] ?? 'http://127.0.0.1:3040/testimonies').replace(/\/$/, '');
const OUT = path.resolve(import.meta.dirname, '..', '..', 'docs', 'assets');

const CHROME_CANDIDATES = [
	process.env.CHROME_PATH,
	`${process.env.HOME}/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome`,
	'/usr/bin/chromium',
	'/usr/bin/google-chrome'
].filter(Boolean);

const executablePath = CHROME_CANDIDATES.find((p) => existsSync(p));

/** name → { path, fullPage } */
const PAGES = [
	{ name: 'landing', path: '/', fullPage: false },
	{ name: 'cases', path: '/persons', fullPage: false },
	{ name: 'case-detail', path: '/persons/285', fullPage: true },
	{ name: 'statistics', path: '/statistics', fullPage: false },
	{ name: 'testimonials', path: '/testimonials', fullPage: false },
	{ name: 'testimonial-detail', path: '/testimonials/62', fullPage: true }
];

const viewport = { width: 1440, height: 900 };

const browser = await chromium.launch({
	executablePath,
	args: ['--disable-dev-shm-usage', '--force-color-profile=srgb']
});

await mkdir(OUT, { recursive: true });
const context = await browser.newContext({
	viewport,
	deviceScaleFactor: 2,
	locale: 'en-US',
	reducedMotion: 'reduce' // freeze the entrance animations at their end state
});

for (const spec of PAGES) {
	const page = await context.newPage();
	const url = `${BASE}${spec.path}`;
	try {
		const res = await page.goto(url, { waitUntil: 'load', timeout: 60_000 });
		// The dev server keeps an HMR websocket open, so 'networkidle'
		// never fires — wait for the DOM to settle instead.
		await page.waitForTimeout(3000);
		const status = res ? res.status() : 0;
		await page.screenshot({ path: path.join(OUT, `${spec.name}.png`), fullPage: spec.fullPage });
		console.log(`${spec.name.padEnd(20)} ${status}  ${url}`);
	} catch (err) {
		console.error(`${spec.name.padEnd(20)} FAIL ${url} :: ${err.message}`);
	} finally {
		await page.close();
	}
}

// --- README banner ------------------------------------------------------
// Rendered from a static HTML file that reuses the app's brand tokens
// (frontend/src/app.css) so the banner and the product stay in one palette.
{
	const page = await context.newPage();
	const bannerFile = path.join(import.meta.dirname, 'readme-banner.html');
	await page.setViewportSize({ width: 1200, height: 360 });
	await page.goto(`file://${bannerFile}`, { waitUntil: 'load' });
	await page.waitForTimeout(600);
	await page.screenshot({ path: path.join(OUT, 'banner.png') });
	console.log(`${'banner'.padEnd(20)} ok    ${bannerFile}`);
	await page.close();
}

await browser.close();
console.log(`\nwrote to ${OUT}`);
