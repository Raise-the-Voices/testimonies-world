/**
 * Status presentation — central label + class lookup.
 *
 * Pins the STATUS_LABEL table that TestimonialCard and
 * WorkflowActions consume. A typo here would surface as a generic
 * "draft" / "published" string in the UI; these tests are the
 * contract.
 */

import { describe, it, expect } from 'vitest';
import { STATUS_LABEL, statusLabel, statusPillClass } from './statusPresentation';

describe('STATUS_LABEL', () => {
	it('includes the five current statuses', () => {
		for (const k of ['draft', 'under_review', 'published', 'rejected', 'archived']) {
			expect(STATUS_LABEL[k]).toBeTruthy();
		}
	});
});

describe('statusLabel', () => {
	it('returns the friendly label for known statuses', () => {
		expect(statusLabel('draft')).toBe('Draft');
		expect(statusLabel('under_review')).toBe('Under review');
		expect(statusLabel('published')).toBe('Published');
	});

	it('falls back to a humanised slug for unknown statuses', () => {
		expect(statusLabel('flagged_for_review')).toBe('flagged for review');
	});

	it('handles empty / undefined gracefully', () => {
		expect(statusLabel('')).toBe('');
	});
});

describe('statusPillClass', () => {
	it('produces a deterministic modifier token', () => {
		expect(statusPillClass('draft')).toBe('status-pill-draft');
		expect(statusPillClass('under_review')).toBe('status-pill-under_review');
	});
});