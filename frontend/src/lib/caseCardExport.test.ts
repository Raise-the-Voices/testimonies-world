import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { posterFilename, sameOriginMediaUrl, freezeMotion } from './caseCardExport';

/**
 * Tests for the export helpers.
 *
 * The two pure functions here are the ones with a decision in them:
 * the file's name, and whether a media URL may be pulled onto the
 * page's own origin. The rest of the export pipeline is the browser's
 * work and is covered by the Playwright spec.
 */

const ORIGIN = 'https://cases.raisethevoices.org';
const BASE = '/testimonies';

const srcDir = fileURLToPath(new URL('..', import.meta.url));
const appCss = readFileSync(join(srcDir, 'app.css'), 'utf8');
const cardSource = readFileSync(join(srcDir, 'lib/CaseInfoCard.svelte'), 'utf8');

describe('posterFilename', () => {
	it('names the file after the case reference', () => {
		expect(posterFilename('ED-2026-0042')).toBe('case-ED-2026-0042.png');
	});

	it('falls back to a neutral name when the case has no reference', () => {
		expect(posterFilename(null)).toBe('case-card.png');
		expect(posterFilename(undefined)).toBe('case-card.png');
		expect(posterFilename('   ')).toBe('case-card.png');
	});

	it('keeps anything that is not a filename character out of the name', () => {
		expect(posterFilename('ED/2026 #42')).toBe('case-ED-2026-42.png');
	});
});

describe('sameOriginMediaUrl', () => {
	it('leaves a URL that is already on this origin alone', () => {
		const url = `${ORIGIN}${BASE}/public-media/profiles/x.jpg`;
		expect(sameOriginMediaUrl(url, ORIGIN, BASE)).toBe(url);
	});

	it('leaves a root-relative URL alone', () => {
		expect(sameOriginMediaUrl(`${BASE}/public-media/profiles/x.jpg`, ORIGIN, BASE)).toBe(
			`${BASE}/public-media/profiles/x.jpg`,
		);
	});

	it('pulls a foreign media URL onto this origin', () => {
		// The API builds media URLs from SITE_URL, which in development
		// is a different host from the app.
		const url = 'https://demos.linkedtrust.us/testimonies/public-media/profiles/x.jpg';
		expect(sameOriginMediaUrl(url, ORIGIN, BASE)).toBe(
			`${BASE}/public-media/profiles/x.jpg`,
		);
	});

	it('adds the app base path when the URL does not carry it', () => {
		const url = 'https://demos.linkedtrust.us/public-media/profiles/x.jpg';
		expect(sameOriginMediaUrl(url, ORIGIN, BASE)).toBe(
			`${BASE}/public-media/profiles/x.jpg`,
		);
	});

	it('keeps the query string', () => {
		const url = 'https://demos.linkedtrust.us/public-media/profiles/x.jpg?v=2';
		expect(sameOriginMediaUrl(url, ORIGIN, BASE)).toBe(
			`${BASE}/public-media/profiles/x.jpg?v=2`,
		);
	});

	it('leaves a foreign URL that is not the app’s own media alone', () => {
		// Pointing somebody else's image at this host would turn a
		// working photograph into a 404.
		const url = 'https://cdn.example.org/photos/x.jpg';
		expect(sameOriginMediaUrl(url, ORIGIN, BASE)).toBe(url);
	});

	it('leaves an empty URL alone', () => {
		expect(sameOriginMediaUrl('', ORIGIN, BASE)).toBe('');
	});
});

/**
 * The capture-time freeze.
 *
 * `html-to-image` inlines the computed styles of what it clones, so
 * anything moving at that moment ships inside the poster. The
 * stylesheet kills the CSS motion; this kills the Web Animations
 * motion, which no CSS rule can touch.
 */
describe('freezeMotion', () => {
	/** A sheet whose `getAnimations()` hands back one round per call. */
	function sheetWith(rounds: { name: string; fails?: boolean }[][]) {
		const finished: string[] = [];
		let call = 0;
		const node = {
			getAnimations: () =>
				(rounds[call++] ?? []).map((spec) => ({
					finish: () => {
						if (spec.fails) throw new Error('This animation has no effect left.');
						finished.push(spec.name);
					},
				})),
		} as unknown as HTMLElement;
		return { node, finished };
	}

	it('finishes every animation running inside the sheet', () => {
		const { node, finished } = sheetWith([[{ name: 'fade' }, { name: 'slide' }]]);

		freezeMotion(node);

		expect(finished).toEqual(['fade', 'slide']);
	});

	it('follows an animation that a delay phase starts', () => {
		// Svelte runs a dummy animation through the delay, and finishing
		// that is what starts the real one.
		const { node, finished } = sheetWith([[{ name: 'delay' }], [{ name: 'fade' }]]);

		freezeMotion(node);

		expect(finished).toEqual(['delay', 'fade']);
	});

	it('keeps going when one animation cannot be finished', () => {
		const { node, finished } = sheetWith([
			[{ name: 'broken', fails: true }, { name: 'fade' }],
		]);

		freezeMotion(node);

		expect(finished).toEqual(['fade']);
	});
});

/**
 * The poster guard.
 *
 * The poster is captured from the off-screen export copy of the card,
 * and `html-to-image` inlines the computed styles of whatever it finds
 * — so anything moving at that moment ships inside the file. The guard
 * is in the stylesheet because that is where the motion lives.
 */
describe('the poster guard', () => {
	const guard =
		/\.case-card--export,\s*\.case-card--export \* \{([^}]*)\}/.exec(appCss)?.[1] ?? '';

	it('switches off every animation and transition inside the export copy', () => {
		expect(guard).toMatch(/animation:\s*none\s*!important/);
		expect(guard).toMatch(/transition:\s*none\s*!important/);
	});

	it('never captures the card in its hidden reveal state', () => {
		// The export copy sits 20 000px off-screen: a revealed element
		// inside it would never reach the viewport, and the file would
		// be a blank sheet.
		expect(appCss).toContain(".case-card--export [data-reveal='pending']");
	});

	it('gives the card itself nothing that could be caught mid-flight', () => {
		// A Svelte transition is a Web Animations animation, and no CSS
		// rule can switch one off — so the card must not carry one.
		expect(cardSource).not.toMatch(/(?:^|[\s;{])transition:/);
		expect(cardSource).not.toMatch(/(?:^|[\s;{])animation:/);
		expect(cardSource).not.toContain('use:reveal');
	});
});
