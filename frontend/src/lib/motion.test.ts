import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
	cubicBezier,
	EASE_COUNT,
	EASE_EDITORIAL,
	EASE_OVERLAY,
	MOTION_TOKEN_FALLBACKS,
	motionTokens,
	prefersReducedMotion
} from './motion';
import { isPublicRoute, stripBasePath } from './publicRoutes';

const srcDir = fileURLToPath(new URL('..', import.meta.url));
const appCss = readFileSync(join(srcDir, 'app.css'), 'utf8');

function svelteFiles(dir: string): string[] {
	return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
		const full = join(dir, entry.name);
		if (entry.isDirectory()) return svelteFiles(full);
		return entry.name.endsWith('.svelte') ? [full] : [];
	});
}

const allSvelte = svelteFiles(srcDir);

/** First declaration of a custom property in the stylesheet. */
function cssToken(name: string): string | undefined {
	const match = new RegExp(`${name}\\s*:\\s*([^;]+);`).exec(appCss);
	return match?.[1].trim();
}

/** '400ms' -> 400, '46s' -> 46000 */
function toMilliseconds(raw: string): number {
	const value = Number.parseFloat(raw);
	if (!Number.isFinite(value)) throw new Error(`Not a duration: ${raw}`);
	return raw.endsWith('ms') || !raw.endsWith('s') ? value : value * 1000;
}

function toPixels(raw: string): number {
	const value = Number.parseFloat(raw);
	if (!Number.isFinite(value)) throw new Error(`Not a length: ${raw}`);
	return value;
}

/** 'cubic-bezier(0.16, 1, 0.3, 1)' -> [0.16, 1, 0.3, 1] */
function parseBezier(raw: string): [number, number, number, number] {
	const match = /cubic-bezier\(([^)]+)\)/.exec(raw);
	if (!match) throw new Error(`Not a cubic-bezier: ${raw}`);
	const parts = match[1].split(',').map((part) => Number.parseFloat(part.trim()));
	if (parts.length !== 4 || parts.some((part) => !Number.isFinite(part))) {
		throw new Error(`Malformed cubic-bezier: ${raw}`);
	}
	return parts as [number, number, number, number];
}

describe('motion tokens', () => {
	const durationTokens: Array<[keyof typeof MOTION_TOKEN_FALLBACKS, string]> = [
		['enter', '--motion-duration-enter'],
		['overlay', '--motion-duration-overlay'],
		['accordion', '--motion-duration-accordion'],
		['reveal', '--motion-duration-reveal'],
		['count', '--motion-duration-count'],
		['grow', '--motion-duration-grow'],
		['ambient', '--motion-duration-ambient'],
		['fast', '--motion-duration-fast'],
		['stagger', '--motion-stagger-step']
	];

	it.each(durationTokens)('%s matches the %s token in app.css', (key, cssName) => {
		const raw = cssToken(cssName);
		expect(raw, `${cssName} is missing from app.css`).toBeDefined();
		expect(toMilliseconds(raw as string)).toBe(MOTION_TOKEN_FALLBACKS[key]);
	});

	const lengthTokens: Array<[keyof typeof MOTION_TOKEN_FALLBACKS, string]> = [
		['riseEnter', '--motion-rise-enter'],
		['riseOverlay', '--motion-rise-overlay'],
		['riseReveal', '--motion-rise-reveal'],
		['riseToast', '--motion-rise-toast']
	];

	it.each(lengthTokens)('%s matches the %s token in app.css', (key, cssName) => {
		const raw = cssToken(cssName);
		expect(raw, `${cssName} is missing from app.css`).toBeDefined();
		expect(toPixels(raw as string)).toBe(MOTION_TOKEN_FALLBACKS[key]);
	});

	it('keeps the ambient stops in color-mix, with a plain fallback', () => {
		expect(cssToken('--motion-ambient-stop-1')).toContain('color-mix');
		expect(cssToken('--motion-ambient-stop-2')).toContain('color-mix');
		expect(appCss).toContain('@supports not (color: color-mix(in srgb, red, blue))');
	});
});

describe('easing', () => {
	it('pins each JS curve to its CSS token', () => {
		const pairs: Array<[(t: number) => number, string]> = [
			[EASE_EDITORIAL, '--motion-ease-editorial'],
			[EASE_OVERLAY, '--motion-ease-overlay'],
			[EASE_COUNT, '--motion-ease-count']
		];
		for (const [curve, cssName] of pairs) {
			const raw = cssToken(cssName);
			expect(raw, `${cssName} is missing from app.css`).toBeDefined();
			const [x1, y1, x2, y2] = parseBezier(raw as string);
			const expected = cubicBezier(x1, y1, x2, y2);
			for (const t of [0, 0.1, 0.25, 0.5, 0.75, 0.9, 1]) {
				expect(curve(t)).toBeCloseTo(expected(t), 10);
			}
		}
	});

	it('starts at 0, ends at 1, and never overshoots', () => {
		for (const curve of [EASE_EDITORIAL, EASE_OVERLAY, EASE_COUNT]) {
			expect(curve(0)).toBe(0);
			expect(curve(1)).toBe(1);
			let previous = -1;
			for (let t = 0; t <= 1; t += 0.01) {
				const value = curve(t);
				expect(value).toBeGreaterThanOrEqual(previous);
				expect(value).toBeLessThanOrEqual(1);
				previous = value;
			}
		}
	});
});

describe('prefersReducedMotion', () => {
	it('is false where there is no window (server rendering)', () => {
		expect(typeof window).toBe('undefined');
		expect(prefersReducedMotion()).toBe(false);
	});

	it('falls back to the token values where there is no document', () => {
		expect(motionTokens()).toEqual(MOTION_TOKEN_FALLBACKS);
	});
});

describe('isPublicRoute', () => {
	const publicPaths = [
		'/',
		'/persons',
		'/persons/12',
		'/testimonials',
		'/testimonials/7'
	];
	it.each(publicPaths)('treats %s as public', (path) => {
		expect(isPublicRoute(path)).toBe(true);
	});

	const internalPaths = [
		'/persons/12/edit',
		'/persons/12/report',
		'/testimonials/new',
		'/testimonials/7/edit',
		'/dashboard',
		'/dashboard/audit-logs',
		'/casework',
		'/casework/new',
		'/contacts',
		'/contacts/new',
		'/reports',
		'/submit',
		'/settings',
		'/notifications',
		'/statistics/extra',
		'/watchdog/extra',
		'/unknown'
	];
	it.each(internalPaths)('treats %s as internal', (path) => {
		expect(isPublicRoute(path)).toBe(false);
	});

	it('ignores a trailing slash', () => {
		expect(isPublicRoute('/persons/')).toBe(true);
		expect(isPublicRoute('/testimonials/7/')).toBe(true);
	});
});

describe('stripBasePath', () => {
	it('removes the deployment base path', () => {
		expect(stripBasePath('/testimonies/persons', '/testimonies')).toBe('/persons');
		expect(stripBasePath('/testimonies', '/testimonies')).toBe('/');
		expect(stripBasePath('/testimonies/', '/testimonies')).toBe('/');
		expect(stripBasePath('/persons', '/testimonies')).toBe('/persons');
	});

	it('leaves the path alone when there is no base path', () => {
		expect(stripBasePath('/persons', '')).toBe('/persons');
		expect(stripBasePath('/persons', '/')).toBe('/persons');
	});

	it('does not strip a partial match', () => {
		expect(stripBasePath('/testimonies-extra/persons', '/testimonies')).toBe(
			'/testimonies-extra/persons'
		);
	});
});

describe('the motion system holds site-wide', () => {
	it('routes every Svelte transition through $lib/motion', () => {
		const offenders = allSvelte.filter((file) => file.includes("from 'svelte/transition'"));
		expect(offenders).toEqual([]);
	});

	it('leaves no inline transition parameters behind', () => {
		const offenders = allSvelte.filter((file) =>
			/(?:transition|in|out):(?:fade|fly|slide|scale|blur|draw|crossfade)=\{/.test(
				readFileSync(file, 'utf8')
			)
		);
		expect(offenders).toEqual([]);
	});

	it('defines the spin and skeleton-shimmer keyframes exactly once, globally', () => {
		for (const name of ['spin', 'skeleton-shimmer']) {
			const hits = allSvelte.filter((file) =>
				readFileSync(file, 'utf8').includes(`@keyframes ${name}`)
			);
			expect(hits, `@keyframes ${name} is declared in a component`).toEqual([]);
			expect(appCss.match(new RegExp(`@keyframes ${name}\\b`, 'g'))?.length).toBe(1);
		}
	});

	it('gives every component that animates in CSS a reduced-motion block', () => {
		const offenders: string[] = [];
		for (const file of allSvelte) {
			const source = readFileSync(file, 'utf8');
			const style = /<style[^>]*>([\s\S]*?)<\/style>/.exec(source);
			if (!style) continue;
			const css = style[1];
			const animates = /(^|[\s;{])(transition|animation)\s*:|@keyframes/.test(css);
			if (animates && !css.includes('prefers-reduced-motion')) offenders.push(file);
		}
		expect(offenders).toEqual([]);
	});
});
