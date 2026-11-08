/**
 * The motion system.
 *
 * One vocabulary for every animation on the site. Public pages use the
 * editorial register (scroll reveals, count-ups); internal tools use the
 * functional register (dropdowns, crossfades, accordions).
 *
 * House rules: nothing bounces, nothing springs, nothing scales. Motion is
 * movement and opacity only.
 *
 * Durations and easings live in `app.css` as `--motion-*` custom properties
 * so they can be read at runtime. `motion.test.ts` pins the CSS tokens and
 * these constants to each other so they cannot drift.
 */

import {
	fade as svelteFade,
	fly as svelteFly,
	slide as svelteSlide,
	type EasingFunction,
	type FadeParams,
	type FlyParams,
	type SlideParams,
	type TransitionConfig
} from 'svelte/transition';

export const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';

/** True when the reader asked the OS to reduce motion. Always false on the server. */
export function prefersReducedMotion(): boolean {
	if (typeof window === 'undefined') return false;
	if (typeof window.matchMedia !== 'function') return false;
	return window.matchMedia(REDUCED_MOTION_QUERY).matches;
}

/**
 * Fires when the reader toggles the OS setting mid-session.
 * Returns an unsubscribe function.
 */
export function onReducedMotionChange(callback: (reduced: boolean) => void): () => void {
	if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return () => {};

	const mq = window.matchMedia(REDUCED_MOTION_QUERY);
	const handler = (event: MediaQueryListEvent) => callback(event.matches);

	if (typeof mq.addEventListener === 'function') {
		mq.addEventListener('change', handler);
		return () => mq.removeEventListener('change', handler);
	}
	// Safari < 14 only has the deprecated API.
	mq.addListener(handler);
	return () => mq.removeListener(handler);
}

export interface MotionTokens {
	/** Above-the-fold settle on load. */
	enter: number;
	/** Off-canvas drawer panel. */
	drawer: number;
	/** Dropdown, modal, toast, banner. */
	overlay: number;
	/** Accordion height. */
	accordion: number;
	/** Scroll reveal. */
	reveal: number;
	/** Numeric counter. */
	count: number;
	/** Stat bar grow. */
	grow: number;
	/** Small UI feedback (toggle thumb, button press). */
	fast: number;
	/** Button press feedback. */
	press: number;
	/** Loading spinner. */
	spin: number;
	/** Skeleton shimmer. */
	shimmer: number;
	/** Delay between consecutive reveals. */
	stagger: number;
	/** Travel distance for entrances. */
	riseEnter: number;
	/** Travel distance for overlays. */
	riseOverlay: number;
	/** Travel distance for scroll reveals. */
	riseReveal: number;
	/** Travel distance for toasts. */
	riseToast: number;
}

/**
 * Mirrors the `--motion-*` block in `app.css`. Used on the server and as the
 * fallback when the stylesheet has not loaded yet.
 */
export const MOTION_TOKEN_FALLBACKS: MotionTokens = {
	enter: 400,
	drawer: 320,
	overlay: 240,
	accordion: 280,
	reveal: 700,
	count: 900,
	grow: 700,
	fast: 180,
	press: 120,
	spin: 800,
	shimmer: 1400,
	stagger: 90,
	riseEnter: 8,
	riseOverlay: 8,
	riseReveal: 12,
	riseToast: 16
};

let tokenCache: MotionTokens | null = null;

/** Reads the `--motion-*` custom properties off `:root`. Cached per page load. */
export function motionTokens(): MotionTokens {
	if (typeof document === 'undefined') return MOTION_TOKEN_FALLBACKS;
	if (tokenCache) return tokenCache;

	const styles = getComputedStyle(document.documentElement);
	const duration = (name: string, fallback: number) => {
		const raw = styles.getPropertyValue(name).trim();
		if (!raw) return fallback;
		const value = Number.parseFloat(raw);
		if (!Number.isFinite(value)) return fallback;
		// 's' is seconds, 'ms' is milliseconds.
		return raw.endsWith('ms') || !raw.endsWith('s') ? value : value * 1000;
	};
	const length = (name: string, fallback: number) => {
		const raw = styles.getPropertyValue(name).trim();
		if (!raw) return fallback;
		const value = Number.parseFloat(raw);
		return Number.isFinite(value) ? value : fallback;
	};

	tokenCache = {
		enter: duration('--motion-duration-enter', MOTION_TOKEN_FALLBACKS.enter),
		drawer: duration('--motion-duration-drawer', MOTION_TOKEN_FALLBACKS.drawer),
		overlay: duration('--motion-duration-overlay', MOTION_TOKEN_FALLBACKS.overlay),
		accordion: duration('--motion-duration-accordion', MOTION_TOKEN_FALLBACKS.accordion),
		reveal: duration('--motion-duration-reveal', MOTION_TOKEN_FALLBACKS.reveal),
		count: duration('--motion-duration-count', MOTION_TOKEN_FALLBACKS.count),
		grow: duration('--motion-duration-grow', MOTION_TOKEN_FALLBACKS.grow),
		fast: duration('--motion-duration-fast', MOTION_TOKEN_FALLBACKS.fast),
		press: duration('--motion-duration-press', MOTION_TOKEN_FALLBACKS.press),
		spin: duration('--motion-duration-spin', MOTION_TOKEN_FALLBACKS.spin),
		shimmer: duration('--motion-duration-shimmer', MOTION_TOKEN_FALLBACKS.shimmer),
		stagger: duration('--motion-stagger-step', MOTION_TOKEN_FALLBACKS.stagger),
		riseEnter: length('--motion-rise-enter', MOTION_TOKEN_FALLBACKS.riseEnter),
		riseOverlay: length('--motion-rise-overlay', MOTION_TOKEN_FALLBACKS.riseOverlay),
		riseReveal: length('--motion-rise-reveal', MOTION_TOKEN_FALLBACKS.riseReveal),
		riseToast: length('--motion-rise-toast', MOTION_TOKEN_FALLBACKS.riseToast)
	};
	return tokenCache;
}

/**
 * Builds the cubic-bezier easing used by the CSS tokens.
 * Svelte transitions take a JS function, not a CSS string, so the CSS
 * `cubic-bezier(.16,1,.3,1)` is solved numerically here.
 */
export function cubicBezier(x1: number, y1: number, x2: number, y2: number): EasingFunction {
	const A = (a: number, b: number) => 1 - 3 * b + 3 * a;
	const B = (a: number, b: number) => 3 * b - 6 * a;
	const C = (a: number) => 3 * a;

	const calc = (t: number, a: number, b: number) => ((A(a, b) * t + B(a, b)) * t + C(a)) * t;
	const slope = (t: number, a: number, b: number) => 3 * A(a, b) * t * t + 2 * B(a, b) * t + C(a);

	return (t: number) => {
		if (t <= 0) return 0;
		if (t >= 1) return 1;

		// Newton-Raphson on x, falling back to bisection when the slope
		// collapses (which happens at the endpoints of steep curves).
		let guess = t;
		for (let i = 0; i < 8; i += 1) {
			const currentX = calc(guess, x1, x2) - t;
			if (Math.abs(currentX) < 1e-6) return calc(guess, y1, y2);
			const currentSlope = slope(guess, x1, x2);
			if (Math.abs(currentSlope) < 1e-6) break;
			guess -= currentX / currentSlope;
		}

		let low = 0;
		let high = 1;
		guess = t;
		while (high - low > 1e-6) {
			const currentX = calc(guess, x1, x2);
			if (Math.abs(currentX - t) < 1e-6) break;
			if (currentX > t) high = guess;
			else low = guess;
			guess = (low + high) / 2;
		}
		return calc(guess, y1, y2);
	};
}

/** `--motion-ease-editorial` — the slow, weighted entrance curve. */
export const EASE_EDITORIAL = cubicBezier(0.16, 1, 0.3, 1);
/** `--motion-ease-overlay` — quick and neutral, for things that open on top. */
export const EASE_OVERLAY = cubicBezier(0.2, 0, 0, 1);
/** `--motion-ease-count` — ease-out, for numeric counters. */
export const EASE_COUNT = cubicBezier(0, 0, 0.58, 1);

/**
 * Wraps a transition so it becomes a true no-op under reduced motion.
 *
 * `{ duration: 0, css: () => '' }` has neither a duration nor a delay, so
 * Svelte's runtime short-circuits and never schedules a keyframe animation
 * (`svelte/src/internal/client/dom/elements/transitions.js`). The element is
 * simply present, with no travel and no rAF.
 *
 * The check runs when the transition starts, not when the module loads, so a
 * reader who toggles the OS setting mid-session is honoured immediately.
 */
function guarded<P extends object>(
	build: (node: Element, params: P) => TransitionConfig
): (node: Element, params?: P) => TransitionConfig {
	return (node, params) => {
		if (prefersReducedMotion()) return { duration: 0, css: () => '' };
		return build(node, (params ?? {}) as P);
	};
}

/** Fade only. Overlays, skeleton→data swaps, tab panels. */
export const fade = guarded<FadeParams>((node, params) =>
	svelteFade(node, {
		duration: motionTokens().overlay,
		easing: EASE_OVERLAY,
		...params
	})
);

/**
 * Moves UP into place: the surface starts 8px below its final position and
 * travels up. Surfaces that arrive from below.
 */
export const rise = guarded<FlyParams>((node, params) =>
	svelteFly(node, {
		y: motionTokens().riseOverlay,
		duration: motionTokens().overlay,
		easing: EASE_EDITORIAL,
		opacity: 0,
		...params
	})
);

/**
 * Moves DOWN into place: the surface starts 8px above its final position and
 * travels down. Dropdowns and listboxes that open downward, modals, banners,
 * inline errors.
 */
export const drop = guarded<FlyParams>((node, params) =>
	svelteFly(node, {
		y: -motionTokens().riseOverlay,
		duration: motionTokens().overlay,
		easing: EASE_EDITORIAL,
		opacity: 0,
		...params
	})
);

/**
 * The dialog panel.
 *
 * `direction: 'up'` for a surface that rises into place from below — the
 * poster, which is a full-page artefact that settles upward. `'down'` for
 * the small dialogs, which drop in from above, where the eye already is.
 *
 * The direction is a parameter rather than two separate transitions so the
 * variant can change while the dialog is open without the entrance
 * direction being frozen at mount.
 */
export const panel = guarded<FlyParams & { direction?: 'up' | 'down' }>((node, params) => {
	const direction = params.direction ?? 'down';
	const rise = motionTokens().riseOverlay;
	return svelteFly(node, {
		duration: motionTokens().overlay,
		easing: EASE_EDITORIAL,
		opacity: 0,
		...params,
		y: direction === 'up' ? rise : -rise
	});
});

/** Lifts 16px into place. Toasts. */
export const lift = guarded<FlyParams>((node, params) =>
	svelteFly(node, {
		y: motionTokens().riseToast,
		duration: motionTokens().overlay,
		easing: EASE_EDITORIAL,
		opacity: 0,
		...params
	})
);

/** Animates height. The report accordion. */
export const expand = guarded<SlideParams>((node, params) =>
	svelteSlide(node, {
		duration: motionTokens().accordion,
		easing: EASE_EDITORIAL,
		...params
	})
);

/* ------------------------------------------------------------------ */
/* Scroll reveals                                                      */
/* ------------------------------------------------------------------ */

export interface RevealOptions {
	/** Position in the list; drives the stagger delay. */
	index?: number;
	/** How much of the element must be visible before it reveals. */
	threshold?: number;
	/** Grows the root bounds so an element reveals slightly before it enters. */
	rootMargin?: string;
	/** Set false to hide the element again when it leaves the viewport. */
	once?: boolean;
}

export interface RevealHandle {
	update(options: RevealOptions): void;
	destroy(): void;
}

const DEFAULT_REVEAL_ROOT_MARGIN = '0px 0px -10% 0px';

const revealHandlers = new WeakMap<Element, (entry: IntersectionObserverEntry) => void>();
const countHandlers = new WeakMap<Element, (entry: IntersectionObserverEntry) => void>();

/** One observer per (threshold, rootMargin) pair for the whole site. */
const observerCache = new Map<string, IntersectionObserver>();

function sharedObserver(threshold: number, rootMargin: string): IntersectionObserver {
	const key = `${threshold}|${rootMargin}`;
	const cached = observerCache.get(key);
	if (cached) return cached;

	const observer = new IntersectionObserver(
		(entries) => {
			for (const entry of entries) {
				revealHandlers.get(entry.target)?.(entry);
				countHandlers.get(entry.target)?.(entry);
			}
		},
		{ threshold, rootMargin }
	);
	observerCache.set(key, observer);
	return observer;
}

/**
 * Reveals an element once it scrolls into view.
 *
 * The hidden state is applied by JavaScript, never by CSS default: the
 * server-rendered HTML carries no `data-reveal` attribute, so a reader with
 * JavaScript disabled — or a hydration failure — sees the full page rather
 * than a blank one. Elements already at or above the fold are never hidden.
 */
export function reveal(node: HTMLElement, options: RevealOptions = {}): RevealHandle | void {
	let current: RevealOptions = { ...options };
	let observer: IntersectionObserver | null = null;
	let revealed = false;

	// The index is written before anything else, so an element that is
	// already on screen still carries it. CSS that reads it — a stagger
	// delay, a column cascade — then has the same answer in the very
	// first style resolution, before the browser paints.
	node.style.setProperty('--reveal-index', String(current.index ?? 0));

	const markIn = () => {
		revealed = true;
		node.dataset.reveal = 'in';
		observer?.unobserve(node);
	};

	// Reduced motion, or a browser without IntersectionObserver: show it.
	if (prefersReducedMotion() || typeof IntersectionObserver === 'undefined') {
		node.dataset.reveal = 'in';
		return;
	}

	// Already on screen: never hide it, so the first paint is complete.
	const bounds = node.getBoundingClientRect();
	if (bounds.top < window.innerHeight) {
		node.dataset.reveal = 'in';
		return;
	}

	node.dataset.reveal = 'pending';

	const threshold = current.threshold ?? 0;
	const rootMargin = current.rootMargin ?? DEFAULT_REVEAL_ROOT_MARGIN;
	observer = sharedObserver(threshold, rootMargin);

	const onIntersect = (entry: IntersectionObserverEntry) => {
		if (entry.isIntersecting) {
			if (!revealed) {
				revealed = true;
				node.dataset.reveal = 'in';
			}
			if (current.once !== false) observer?.unobserve(node);
			return;
		}
		if (current.once === false) {
			revealed = false;
			node.dataset.reveal = 'pending';
		}
	};

	revealHandlers.set(node, onIntersect);
	observer.observe(node);

	// If the reader turns reduced motion on mid-session, nothing stays hidden.
	const stopListening = onReducedMotionChange((reduced) => {
		if (reduced) markIn();
	});

	return {
		update(next: RevealOptions) {
			current = { ...current, ...next };
			node.style.setProperty('--reveal-index', String(current.index ?? 0));
		},
		destroy() {
			stopListening();
			revealHandlers.delete(node);
			observer?.unobserve(node);
		}
	};
}

/* ------------------------------------------------------------------ */
/* Count-up                                                            */
/* ------------------------------------------------------------------ */

export interface CountUpOptions {
	/** The final number. */
	value: number;
	/** How long the count takes. Defaults to `--motion-duration-count`. */
	duration?: number;
	/** Renders the current value. Defaults to a rounded integer. */
	format?: (value: number) => string;
	/** Hold-off before counting, in milliseconds. */
	delay?: number;
	/** 'visible' waits for the element to scroll into view; 'now' starts at once. */
	when?: 'now' | 'visible';
}

export interface CountUpHandle {
	update(options: CountUpOptions): void;
	destroy(): void;
}

type TickerFn = (delta: number) => void;

const tickerFns = new Set<TickerFn>();
let tickerFrame = 0;
let tickerLast = 0;

function runTicker(now: number) {
	const delta = tickerLast ? now - tickerLast : 0;
	tickerLast = now;
	for (const fn of tickerFns) fn(delta);
	if (tickerFns.size > 0) {
		tickerFrame = requestAnimationFrame(runTicker);
	} else {
		tickerFrame = 0;
		tickerLast = 0;
	}
}

/** One rAF loop for every counter on the page. */
function subscribeTicker(fn: TickerFn): () => void {
	tickerFns.add(fn);
	if (!tickerFrame) {
		tickerLast = 0;
		tickerFrame = requestAnimationFrame(runTicker);
	}
	return () => {
		tickerFns.delete(fn);
	};
}

/**
 * Counts a number up to its value.
 *
 * Starts from the currently displayed number, so a changed value counts from
 * where the reader last saw it rather than restarting at zero. A value that
 * has not changed is never re-animated.
 */
export function countUp(node: HTMLElement, options: CountUpOptions): CountUpHandle {
	let current: CountUpOptions = { ...options };
	let displayed = 0;
	let unsubscribe: (() => void) | null = null;
	let observer: IntersectionObserver | null = null;
	let started = false;

	const paint = (value: number) => {
		node.textContent = (current.format ?? ((n: number) => String(Math.round(n))))(value);
	};

	const stop = () => {
		unsubscribe?.();
		unsubscribe = null;
	};

	const run = (target: number, duration: number, delay: number) => {
		stop();
		if (prefersReducedMotion() || duration <= 0) {
			displayed = target;
			paint(target);
			return;
		}
		const from = displayed;
		let elapsed = 0;
		let waited = 0;
		unsubscribe = subscribeTicker((delta) => {
			waited += delta;
			if (waited < delay) return;
			elapsed += delta;
			const t = Math.min(1, elapsed / duration);
			displayed = from + (target - from) * EASE_COUNT(t);
			paint(displayed);
			if (t >= 1) {
				displayed = target;
				paint(target);
				stop();
			}
		});
	};

	const start = () => {
		if (started) return;
		started = true;
		run(current.value, current.duration ?? motionTokens().count, current.delay ?? 0);
	};

	if (current.when === 'visible') {
		if (typeof IntersectionObserver === 'undefined') {
			start();
		} else {
			observer = sharedObserver(0, DEFAULT_REVEAL_ROOT_MARGIN);
			const onIntersect = (entry: IntersectionObserverEntry) => {
				if (!entry.isIntersecting) return;
				start();
				observer?.unobserve(node);
			};
			countHandlers.set(node, onIntersect);
			observer.observe(node);
		}
	} else {
		start();
	}

	return {
		update(next: CountUpOptions) {
			const previous = current;
			current = { ...current, ...next };
			const unchanged =
				current.value === previous.value &&
				current.duration === previous.duration &&
				current.delay === previous.delay;
			if (unchanged) return;
			if (started) {
				run(current.value, current.duration ?? motionTokens().count, current.delay ?? 0);
			}
		},
		destroy() {
			stop();
			countHandlers.delete(node);
			observer?.unobserve(node);
		}
	};
}
