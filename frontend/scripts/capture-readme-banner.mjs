#!/usr/bin/env node
/**
 * Render the README banner to docs/assets/banner.png.
 *
 * The banner is a static local HTML file (scripts/readme-banner.html)
 * that reuses the app's brand tokens. No network access, no live
 * data — it only draws the project's own colours and type.
 *
 * Usage: node scripts/capture-readme-banner.mjs
 */
import { chromium } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';

const OUT = path.resolve(import.meta.dirname, '..', '..', 'docs', 'assets');
const BANNER = path.join(import.meta.dirname, 'readme-banner.html');

const CHROME_CANDIDATES = [
	process.env.CHROME_PATH,
	`${process.env.HOME}/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome`,
	'/usr/bin/chromium',
	'/usr/bin/google-chrome'
].filter(Boolean);

const executablePath = CHROME_CANDIDATES.find((p) => existsSync(p));

const browser = await chromium.launch({
	executablePath,
	args: ['--disable-dev-shm-usage', '--force-color-profile=srgb']
});

await mkdir(OUT, { recursive: true });

const context = await browser.newContext({
	viewport: { width: 1200, height: 360 },
	deviceScaleFactor: 2
});
const page = await context.newPage();
await page.goto(`file://${BANNER}`, { waitUntil: 'load' });
await page.waitForTimeout(500);
await page.screenshot({ path: path.join(OUT, 'banner.png') });
await page.close();
await browser.close();

console.log(`banner -> ${path.join(OUT, 'banner.png')}`);
