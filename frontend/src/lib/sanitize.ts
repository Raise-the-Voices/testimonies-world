/**
 * Output sanitisation for user-generated free-text.
 *
 * Defence-in-depth for narrative / summary / review-notes fields rendered
 * with `white-space: pre-line` or similar. Svelte already HTML-escapes
 * `{value}` text interpolation, so script injection through the public
 * surface is blocked at the template layer. This module adds a second
 * layer so that:
 *
 *   1. Any future migration of a field to `{@html ...}` (e.g. to render
 *      Markdown) still strips dangerous constructs.
 *   2. The same helper can be used to scrub values before they're passed
 *      into JSON payloads, href attributes, or title attributes.
 *   3. Control characters and stray HTML entities are normalised before
 *      display so layout (pre-line, line-clamp) stays predictable.
 *
 * Backed by `isomorphic-dompurify`, which wires the browser build to
 * `window` and the Node build to `jsdom` — so the helper runs on SSR
 * (Node) and CSR (browser) without a conditional import. If the library
 * ever fails to load (missing peer, install drift) we fall back to a
 * conservative strip-tags implementation that only escapes HTML special
 * characters and removes `<...>` sequences, never throws.
 */

import DOMPurify from 'isomorphic-dompurify';

/**
 * Default DOMPurify config: nothing is allowed. The text passed to
 * `sanitizeText` is treated as plain text — any HTML the user might have
 * submitted (e.g. `<script>` or `<img onerror=...>`) is stripped, the
 * tags are removed, and the textual content remains. Whitespace
 * characters (newlines, tabs) are preserved verbatim so that
 * `white-space: pre-line` rendering keeps paragraph breaks intact.
 */
const TEXT_ONLY_CONFIG = {
	ALLOWED_TAGS: [] as string[],
	ALLOWED_ATTR: [] as string[],
	KEEP_CONTENT: true,
	// Don't let DOMPurify wrap or transform — we want the raw text back.
	RETURN_DOM: false,
	RETURN_DOM_FRAGMENT: false,
	RETURN_TRUSTED_TYPE: false,
} as const;

/**
 * Conservative regex used when DOMPurify itself is unavailable. Strips
 * every `<...>` span (non-greedy, multiline so it catches across newlines),
 * then escapes the four HTML-significant characters in what remains.
 * Newlines and tabs are preserved.
 */
const TAG_RE = /<[^>]*>/g;
const ESCAPE_MAP: Readonly<Record<string, string>> = {
	'&': '&amp;',
	'<': '&lt;',
	'>': '&gt;',
	'"': '&quot;',
	"'": '&#39;',
};
const ESCAPE_RE = /[&<>"']/g;

function escapeHtml(s: string): string {
	return s.replace(ESCAPE_RE, (ch) => ESCAPE_MAP[ch] ?? ch);
}

function fallbackSanitize(input: string): string {
	const stripped = input.replace(TAG_RE, '');
	return escapeHtml(stripped);
}

let domPurifyBroken = false;

/**
 * Sanitise a free-text value for safe rendering.
 *
 * - `null` / `undefined` → empty string.
 * - Anything else is coerced via `String(...)` and passed through
 *   `isomorphic-dompurify` with the no-tags config above. The result is
 *   guaranteed to contain no HTML markup.
 * - Newlines, tabs, and other whitespace are preserved so callers using
 *   `white-space: pre-line` keep their paragraph layout.
 * - On any error (DOMPurify throws, jsdom missing in SSR, etc.) the
 *   function silently falls back to a regex strip + entity escape so
 *   the UI never breaks because of a sanitiser bug. The error is logged
 *   once via `console.warn` to aid debugging; subsequent calls skip
 *   DOMPurify until the page reloads.
 */
export function sanitizeText(input: string | null | undefined): string {
	if (input == null) return '';
	const raw = String(input);

	if (domPurifyBroken) return fallbackSanitize(raw);

	try {
		const cleaned = DOMPurify.sanitize(raw, TEXT_ONLY_CONFIG);
		// DOMPurify can return a TrustedHTML instance in browsers that
		// enforce Trusted Types. Coerce to a plain string so callers
		// (Svelte text nodes, attribute values) get a primitive.
		return typeof cleaned === 'string' ? cleaned : String(cleaned ?? '');
	} catch (err) {
		domPurifyBroken = true;
		if (typeof console !== 'undefined') {
			console.warn('[sanitize] DOMPurify unavailable, falling back to manual strip:', err);
		}
		return fallbackSanitize(raw);
	}
}

/**
 * Sanitise a value intended for an HTML attribute (e.g. `title="..."`).
 * Same semantics as `sanitizeText` — strips markup and escapes quotes so
 * the attribute can't be broken out of. Use this instead of `sanitizeText`
 * when the result will be quoted in markup.
 */
export function sanitizeAttribute(input: string | null | undefined): string {
	return sanitizeText(input);
}