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

/** Every duration, and the CSS token that carries it. */
const durationTokens: Array<[keyof typeof MOTION_TOKEN_FALLBACKS, string]> = [
	['enter', '--motion-duration-enter'],
	['drawer', '--motion-duration-drawer'],
	['overlay', '--motion-duration-overlay'],
	['accordion', '--motion-duration-accordion'],
	['reveal', '--motion-duration-reveal'],
	['count', '--motion-duration-count'],
	['grow', '--motion-duration-grow'],
	['fast', '--motion-duration-fast'],
	['press', '--motion-duration-press'],
	['spin', '--motion-duration-spin'],
	['shimmer', '--motion-duration-shimmer'],
	['stagger', '--motion-stagger-step']
];

describe('motion tokens', () => {
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
});

/**
 * The vocabulary is closed.
 *
 * A duration or an easing is named in app.css and used by name. A
 * component that spells one out has opted out of the system by accident,
 * and the accident is invisible until two surfaces disagree about how
 * long a thing takes.
 */
describe('the token layer is closed', () => {
	/** Every stylesheet in the app: the global one and each component's. */
	function stylesheets(): Array<[string, string]> {
		const files: Array<[string, string]> = [['app.css', appCss]];
		for (const file of allSvelte) {
			const style = /<style[^>]*>([\s\S]*?)<\/style>/.exec(readFileSync(file, 'utf8'));
			if (style) files.push([file, style[1]]);
		}
		return files;
	}

	/**
	 * The durations and easings typed in at a call site, with the token
	 * references removed. What is left is a literal.
	 */
	function literals(css: string): string[] {
		const found: string[] = [];
		const declarations = css.matchAll(
			/(?:^|[;{])\s*(transition|animation)(?:-[a-z-]+)?\s*:\s*([^;}]+)/g
		);
		for (const [, property, raw] of declarations) {
			const value = raw.replace(/var\(\s*--[a-z-]+(?:\s*,\s*[^()]*)?\s*\)/g, '');
			const duration = /(?<![-\w.])\d*\.?\d+(?:ms|s)(?![-\w])/.exec(value);
			const easing =
				/(?<![-\w-])(?:ease-in-out|ease-in|ease-out|ease|linear)(?![-\w-])/.exec(value);
			if (duration) {
				// `0s` is a deliberate "no motion" — the reduced-motion
				// kill switch, not a duration.
				if (!/^0(?:\.0+)?(?:ms|s)$/.test(duration[0])) {
					found.push(`${property}: ${raw.trim()}`);
				}
			} else if (easing) {
				found.push(`${property}: ${raw.trim()}`);
			}
		}
		return found;
	}

	it('names every duration and easing at the call site', () => {
		const offenders: string[] = [];
		for (const [file, css] of stylesheets()) {
			for (const literal of literals(css)) offenders.push(`${file}: ${literal}`);
		}
		expect(offenders).toEqual([]);
	});

	it('gives every duration token in app.css a key in motion.ts', () => {
		const declared = [...appCss.matchAll(/(--motion-duration-[a-z-]+)\s*:/g)].map((m) => m[1]);
		const known = durationTokens
			.map(([, name]) => name)
			.filter((name) => name.startsWith('--motion-duration-'));
		expect([...new Set(declared)].sort()).toEqual([...new Set(known)].sort());
	});

	it('closes the easing vocabulary', () => {
		const declared = [...appCss.matchAll(/(--motion-ease-[a-z-]+)\s*:/g)].map((m) => m[1]);
		// The three the JS transitions use have JS twins; the two loops
		// are CSS-only, because no JS transition loops.
		const cssOnly = ['--motion-ease-loop', '--motion-ease-spin'];
		expect(declared.filter((name) => !cssOnly.includes(name)).sort()).toEqual([
			'--motion-ease-count',
			'--motion-ease-editorial',
			'--motion-ease-overlay'
		]);
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

describe('the status history timeline', () => {
	const source = readFileSync(join(srcDir, 'lib/StatusHistoryTimeline.svelte'), 'utf8');

	it('reveals each event row as it reaches the viewport', () => {
		expect(source).toContain('use:reveal={{ index }}');
	});

	it('draws the rule with a transform, never with a layout property', () => {
		const keyframes = /@keyframes status-history-rule \{([\s\S]*?)\n\t\}/.exec(source)?.[1] ?? '';
		expect(keyframes).toContain('transform: scaleY');
		expect(keyframes).not.toMatch(/\b(?:height|width|top|margin)\s*:/);
	});

	it('sizes the rule from the same gap the rows are separated by', () => {
		expect(source).toMatch(/--status-history-gap:\s*[\d.]+rem/);
		expect(source).toMatch(/gap:\s*var\(--status-history-gap\)/);
		expect(source).toMatch(/height:\s*var\(--status-history-gap\)/);
	});
});

describe('the nav drawer', () => {
	const source = readFileSync(join(srcDir, 'routes/+layout.svelte'), 'utf8');

	it('slides on the drawer duration, decelerating into place', () => {
		expect(source).toContain(
			'transition: transform var(--motion-duration-drawer) var(--motion-ease-editorial);'
		);
	});

	it('fades the scrim through the motion system, so it fades out too', () => {
		expect(source).toContain('transition:fade');
		// The old CSS keyframe could only fade in — the scrim vanished
		// the moment the drawer closed.
		expect(source).not.toContain('scrim-fade-in');
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
