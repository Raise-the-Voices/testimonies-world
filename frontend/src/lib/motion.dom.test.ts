// @vitest-environment jsdom
/**
 * The motion contract, at the DOM level.
 *
 * `motion.test.ts` pins the tokens and the site-wide invariants by reading
 * source files. This file pins what the reader actually gets: that a
 * transition asked for reduced motion does not move, that content hidden
 * for a scroll reveal is never left hidden, and that a counter lands on
 * the exact number.
 *
 * The environment is jsdom for this file only — the rest of the suite
 * stays on node so it stays fast.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { countUp, drop, fade, MOTION_TOKEN_FALLBACKS, reveal } from './motion';

/** A matchMedia stub whose answer can be changed mid-test. */
function stubMatchMedia(initial: boolean) {
	const listeners = new Set<(event: MediaQueryListEvent) => void>();
	let matches = initial;

	const mql = {
		get matches() {
			return matches;
		},
		media: '(prefers-reduced-motion: reduce)',
		onchange: null,
		addEventListener: (_type: string, cb: (event: MediaQueryListEvent) => void) => {
			listeners.add(cb);
		},
		removeEventListener: (_type: string, cb: (event: MediaQueryListEvent) => void) => {
			listeners.delete(cb);
		},
		addListener: (cb: (event: MediaQueryListEvent) => void) => listeners.add(cb),
		removeListener: (cb: (event: MediaQueryListEvent) => void) => listeners.delete(cb),
		dispatchEvent: () => false
	};

	vi.stubGlobal('matchMedia', vi.fn(() => mql));

	return {
		set(next: boolean) {
			matches = next;
			for (const cb of listeners) {
				cb({ matches: next } as MediaQueryListEvent);
			}
		}
	};
}

/** A minimal IntersectionObserver that lets a test fire the callback. */
function stubIntersectionObserver() {
	const instances: Array<(entries: Partial<IntersectionObserverEntry>[]) => void> = [];

	class Fake {
		constructor(private callback: (entries: Partial<IntersectionObserverEntry>[]) => void) {
			instances.push(callback);
		}
		observe() {}
		unobserve() {}
		disconnect() {}
		takeRecords() {
			return [];
		}
		root = null;
		rootMargin = '';
		thresholds = [];
	}

	vi.stubGlobal('IntersectionObserver', Fake);
	return instances;
}

/** An element the viewport has not reached yet. */
function belowTheFold(): HTMLElement {
	const el = document.createElement('div');
	el.getBoundingClientRect = () =>
		({ top: 5000, bottom: 5100, left: 0, right: 0, width: 0, height: 100 }) as DOMRect;
	document.body.appendChild(el);
	return el;
}

beforeEach(() => {
	document.body.innerHTML = '';
});

afterEach(() => {
	vi.unstubAllGlobals();
});

describe('the reduced-motion guard', () => {
	it('turns a transition into a no-op when the reader asked for reduced motion', () => {
		stubMatchMedia(true);
		const config = drop(document.createElement('div'));

		expect(config.duration).toBe(0);
		// An empty style means no travel and no fade — the element is
		// simply there.
		expect(config.css?.(0.5, 1)).toBe('');
	});

	it('gives a transition a duration and a curve when motion is allowed', () => {
		stubMatchMedia(false);
		const config = drop(document.createElement('div'));

		expect(config.duration).toBe(MOTION_TOKEN_FALLBACKS.overlay);
		expect(config.easing).toBeDefined();
		// The curve decelerates: at the midpoint it is already past half
		// way, which is what separates it from a linear transition.
		expect(config.easing?.(0.5)).toBeGreaterThan(0.5);
	});

	it('reads the setting when the transition starts, not when the module loads', () => {
		const media = stubMatchMedia(false);

		expect(drop(document.createElement('div')).duration).toBe(MOTION_TOKEN_FALLBACKS.overlay);

		media.set(true);

		expect(drop(document.createElement('div')).duration).toBe(0);
	});

	it('guards the fade as well as the moving transitions', () => {
		stubMatchMedia(true);
		expect(fade(document.createElement('div')).duration).toBe(0);
	});
});

describe('the scroll reveal', () => {
	it('never hides content that is already on screen', () => {
		stubMatchMedia(false);
		stubIntersectionObserver();
		const node = document.createElement('div');
		document.body.appendChild(node);

		reveal(node);

		expect(node.dataset.reveal).toBe('in');
	});

	it('waits for the viewport before hiding content that is below the fold', () => {
		stubMatchMedia(false);
		const observers = stubIntersectionObserver();
		const node = belowTheFold();

		reveal(node);

		expect(node.dataset.reveal).toBe('pending');
		expect(observers.length).toBe(1);

		observers[0]([{ isIntersecting: true, target: node }]);
		expect(node.dataset.reveal).toBe('in');
	});

	it('never hides content when the reader asked for reduced motion', () => {
		stubMatchMedia(true);
		stubIntersectionObserver();
		const node = belowTheFold();

		reveal(node);

		expect(node.dataset.reveal).toBe('in');
	});

	it('reveals everything when the reader turns reduced motion on mid-session', () => {
		const media = stubMatchMedia(false);
		stubIntersectionObserver();
		const node = belowTheFold();

		reveal(node);
		expect(node.dataset.reveal).toBe('pending');

		media.set(true);

		expect(node.dataset.reveal).toBe('in');
	});
});

describe('the counter', () => {
	it('lands on the exact value', () => {
		stubMatchMedia(false);
		const node = document.createElement('span');
		document.body.appendChild(node);

		countUp(node, { value: 42, duration: 0 });

		expect(node.textContent).toBe('42');
	});

	it('shows the final value at once under reduced motion', () => {
		stubMatchMedia(true);
		const node = document.createElement('span');
		document.body.appendChild(node);

		countUp(node, { value: 128, duration: 900 });

		expect(node.textContent).toBe('128');
	});
});
