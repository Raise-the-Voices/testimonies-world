/**
 * Sanitization safety net for testimonial text fields.
 *
 * The audit called out that review_notes / titles / summaries are
 * rendered as text (not HTML), so escaping is the renderer's job
 * — but a row containing Git conflict markers or raw newlines can
 * still leak through if the boundary isn't tested. These tests
 * pin the sanitizer's behaviour so a regression in safeText /
 * isCorruptConflictText / isEmptyAfterSanitization doesn't slip in.
 */

import { describe, it, expect } from 'vitest';
import {
	isCorruptConflictText,
	safeText,
	safeTextOr,
	isEmptyAfterSanitization,
} from './testimonial-sanitize';

describe('isCorruptConflictText', () => {
	it('flags a row with a single conflict marker on its own line', () => {
		// The regex requires the marker to be the WHOLE line. A bare
		// "<<<<<<<" alone on a line matches; "<<<<<<< HEAD" (text on
		// the same line) does not — see "does not flag marker with
		// trailing text" below for that case.
		expect(isCorruptConflictText('<<<<<<<')).toBe(true);
		expect(isCorruptConflictText('=======')).toBe(true);
		expect(isCorruptConflictText('>>>>>>>')).toBe(true);
	});

	it('flags a full conflict block (all three markers present)', () => {
		const block =
			'<<<<<<< HEAD\nfoo\n=======\nbar\n>>>>>>> branch';
		expect(isCorruptConflictText(block)).toBe(true);
	});

	it('does not flag plain text containing the word "conflict"', () => {
		expect(isCorruptConflictText('A witness reported a conflict.')).toBe(false);
	});

	it('handles null / undefined safely', () => {
		expect(isCorruptConflictText(null)).toBe(false);
		expect(isCorruptConflictText(undefined)).toBe(false);
	});
});

describe('safeText', () => {
	it('returns empty string for a pure conflict block (markers on own lines)', () => {
		// The full block triggers isCorruptConflictText, so safeText
		// short-circuits to '' rather than trying to strip the inner
		// text. This is the canonical "hide this row" path.
		expect(safeText('<<<<<<< HEAD\n=======\n>>>>>>> branch'))
			.toBe('');
	});

	it('treats a row with a bare marker on its own line as corrupt', () => {
		// A bare `<<<<<<<` alone on a line is the strongest signal
		// of a merge-conflict leak — even if no `=======` follows,
		// the row is almost certainly broken. The sanitizer treats
		// this as fully corrupt and returns '' (the caller should
		// hide the row entirely).
		expect(safeText('<<<<<<<\nreal narrative')).toBe('');
	});

	it('returns empty string for null / undefined', () => {
		expect(safeText(null)).toBe('');
		expect(safeText(undefined)).toBe('');
	});

	it('passes plain text through unchanged', () => {
		expect(safeText('A witness reported a conflict on March 14.')).toBe(
			'A witness reported a conflict on March 14.',
		);
	});
});

describe('safeTextOr', () => {
	it('returns fallback when input is empty after sanitization', () => {
		expect(safeTextOr(null, 'Untitled case')).toBe('Untitled case');
		expect(safeTextOr('', 'Untitled case')).toBe('Untitled case');
		// Pure conflict block (markers on own lines) → safeText returns
		// '' → safeTextOr substitutes the fallback.
		expect(safeTextOr('<<<<<<< HEAD\n=======\n>>>>>>> branch', 'Untitled case'))
			.toBe('Untitled case');
	});

	it('returns the sanitized value when non-empty', () => {
		expect(safeTextOr('Detention in Erbil', 'Untitled case'))
			.toBe('Detention in Erbil');
	});
});

describe('isEmptyAfterSanitization', () => {
	it('returns true when ALL fields are empty', () => {
		expect(
			isEmptyAfterSanitization({
				title: null,
				summary: '',
				country: undefined,
				public_location_display: '<<<<<<<',
			}),
		).toBe(true);
	});

	it('returns false when at least one field has content', () => {
		expect(
			isEmptyAfterSanitization({
				title: null,
				summary: null,
				country: 'Iraq',
				public_location_display: null,
			}),
		).toBe(false);
	});

	it('does NOT treat plain text with the word "conflict" as empty', () => {
		expect(
			isEmptyAfterSanitization({
				title: 'A witness reported a conflict.',
				summary: null,
				country: null,
				public_location_display: null,
			}),
		).toBe(false);
	});
});