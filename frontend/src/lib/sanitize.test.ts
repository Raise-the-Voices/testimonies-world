/**
 * Tests for the output sanitiser.
 *
 * Pins the contract that the helper strips dangerous HTML while
 * preserving line breaks, never throws, and degrades gracefully on
 * `null` / `undefined`. Each test targets an XSS vector from the OWASP
 * cheat sheet (script tags, on* handlers, javascript: URLs, data: URLs,
 * svg-with-script). Newlines are the *reason* this module exists —
 * the user-facing rule is "pre-line layout must keep working".
 */

import { describe, it, expect } from 'vitest';
import { sanitizeText, sanitizeAttribute } from './sanitize';

describe('sanitizeText', () => {
	it('returns empty string for null / undefined', () => {
		expect(sanitizeText(null)).toBe('');
		expect(sanitizeText(undefined)).toBe('');
	});

	it('returns empty string for empty input', () => {
		expect(sanitizeText('')).toBe('');
	});

	it('passes plain text through unchanged', () => {
		const txt = 'A witness reported an incident on March 14, 2025.';
		expect(sanitizeText(txt)).toBe(txt);
	});

	it('preserves single newlines (pre-line layout)', () => {
		const txt = 'First paragraph.\nSecond paragraph.\n\nThird paragraph.';
		expect(sanitizeText(txt)).toBe(txt);
	});

	it('preserves tabs and trailing spaces', () => {
		const txt = 'col1\tcol2\ttrailing space   ';
		expect(sanitizeText(txt)).toBe(txt);
	});

	it('strips <script> tags but keeps the inner text', () => {
		const malicious = '<script>alert("xss")</script>visible text';
		const out = sanitizeText(malicious);
		expect(out).not.toMatch(/<script/i);
		expect(out).not.toMatch(/alert\(/);
		expect(out).toContain('visible text');
	});

	it('strips <img onerror=...> handlers', () => {
		const malicious = '<img src=x onerror="alert(1)">';
		const out = sanitizeText(malicious);
		expect(out).not.toMatch(/onerror/i);
		expect(out).not.toMatch(/<img/i);
	});

	it('strips <a href="javascript:..."> payloads', () => {
		const malicious = '<a href="javascript:alert(1)">click</a>';
		const out = sanitizeText(malicious);
		expect(out).not.toMatch(/javascript:/i);
		expect(out).not.toMatch(/<a /i);
		expect(out).toContain('click');
	});

	it('strips svg-with-script payloads', () => {
		const malicious = '<svg><script>alert(1)</script></svg>';
		const out = sanitizeText(malicious);
		expect(out).not.toMatch(/<svg/i);
		expect(out).not.toMatch(/<script/i);
		expect(out).not.toMatch(/alert\(/);
	});

	it('strips iframe payloads', () => {
		const malicious = '<iframe src="https://evil.example"></iframe>';
		const out = sanitizeText(malicious);
		expect(out).not.toMatch(/<iframe/i);
	});

	it('strips nested event handlers', () => {
		const malicious = '<div onmouseover="alert(1)" onclick="alert(2)">text</div>';
		const out = sanitizeText(malicious);
		expect(out).not.toMatch(/onmouseover/i);
		expect(out).not.toMatch(/onclick/i);
		expect(out).toContain('text');
	});

	it('handles mixed markup with preserved line breaks', () => {
		const malicious = 'paragraph one\n<p>html line</p>\nparagraph two\n<script>alert(1)</script>';
		const out = sanitizeText(malicious);
		// Newlines preserved
		expect(out.split('\n').length).toBe(malicious.split('\n').length);
		expect(out).not.toMatch(/<script/i);
		expect(out).not.toMatch(/<p>/i);
		// Visible text remains
		expect(out).toContain('paragraph one');
		expect(out).toContain('html line');
		expect(out).toContain('paragraph two');
	});

	it('coerces non-string input safely', () => {
		// @ts-expect-error — defensive runtime check
		expect(sanitizeText(42)).toBe('42');
		// @ts-expect-error — defensive runtime check
		expect(sanitizeText(true)).toBe('true');
	});

	it('does not throw on long input', () => {
		const big = 'lorem ipsum '.repeat(10_000) + '\n<script>x</script>';
		expect(() => sanitizeText(big)).not.toThrow();
		const out = sanitizeText(big);
		expect(out).not.toMatch(/<script/i);
	});

	it('preserves unicode characters (Arabic, emoji)', () => {
		const txt = 'شهد — مرحبا 🌍';
		expect(sanitizeText(txt)).toBe(txt);
	});
});

describe('sanitizeAttribute', () => {
	it('strips tags and angle brackets so the attribute cannot be broken out of', () => {
		const malicious = '"><script>alert(1)</script>';
		const out = sanitizeAttribute(malicious);
		// No raw < or > can leak through — those are the boundary
		// characters that close an attribute and start a new tag.
		expect(out).not.toMatch(/[<>]/);
		expect(out).not.toMatch(/alert\(/i);
	});

	it('returns empty for null / undefined', () => {
		expect(sanitizeAttribute(null)).toBe('');
		expect(sanitizeAttribute(undefined)).toBe('');
	});

	it('preserves safe text', () => {
		expect(sanitizeAttribute('Photo of victim')).toBe('Photo of victim');
	});

	it('preserves spaces and special characters that are not tag boundaries', () => {
		// Quotes can appear in legitimate titles. The helper only
		// guarantees tag-stripping; if a caller needs strictly-quoted
		// attributes they should additionally use HTML attribute
		// escaping at the call site.
		expect(sanitizeAttribute("O'Brien's case")).toContain("O'Brien");
	});
});