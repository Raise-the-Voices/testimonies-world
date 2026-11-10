import { describe, it, expect } from 'vitest';
import {
	formatEditorialDate,
	formatMonthYear,
	isoToMonthYear,
	monthYearToIsoDate,
	isValidMonthYear,
} from './dateFormat';

describe('dateFormat', () => {
	describe('formatMonthYear', () => {
		it('renders Mon YYYY for a wire-format ISO date', () => {
			expect(formatMonthYear('2024-03-14')).toBe('Mar 2024');
		});

		it('renders Mon YYYY for a form-format YYYY-MM string', () => {
			expect(formatMonthYear('2024-03')).toBe('Mar 2024');
		});

		it('accepts a Date — the shape the Zod boundary produces', () => {
			expect(formatMonthYear(new Date('2026-01-15T00:00:00Z'))).toBe('Jan 2026');
		});

		it('returns empty string for nullish input', () => {
			expect(formatMonthYear(null)).toBe('');
			expect(formatMonthYear(undefined)).toBe('');
			expect(formatMonthYear('')).toBe('');
		});

		it('passes through unrecognized input rather than throwing', () => {
			// Defensive: legacy rows from before the migration might carry
			// odd shapes; we don't want a single bad row to blank a list.
			expect(formatMonthYear('not-a-date')).toBe('not-a-date');
		});
	});

	describe('isoToMonthYear', () => {
		it('truncates wire YYYY-MM-DD to form YYYY-MM', () => {
			expect(isoToMonthYear('2024-03-14')).toBe('2024-03');
		});

		it('accepts a Date — the shape the Zod boundary produces', () => {
			expect(isoToMonthYear(new Date('2026-01-15T00:00:00Z'))).toBe('2026-01');
		});

		it('returns empty string for nullish input', () => {
			expect(isoToMonthYear(null)).toBe('');
			expect(isoToMonthYear('')).toBe('');
		});

		it('passes through unrecognized input', () => {
			expect(isoToMonthYear('2024-03')).toBe('2024-03');
		});
	});

	describe('monthYearToIsoDate', () => {
		it('appends -01 to form YYYY-MM', () => {
			expect(monthYearToIsoDate('2024-03')).toBe('2024-03-01');
		});

		it('returns empty string for empty / null / invalid input', () => {
			expect(monthYearToIsoDate('')).toBe('');
			expect(monthYearToIsoDate(null)).toBe('');
			expect(monthYearToIsoDate('2024-3')).toBe('');
			expect(monthYearToIsoDate('24-03')).toBe('');
			expect(monthYearToIsoDate('2024/03')).toBe('');
		});
	});

	describe('isValidMonthYear', () => {
		it('treats empty as valid (optional field)', () => {
			expect(isValidMonthYear('')).toBe(true);
		});

		it('accepts YYYY-MM', () => {
			expect(isValidMonthYear('2024-03')).toBe(true);
		});

		it('rejects full ISO dates and other shapes', () => {
			expect(isValidMonthYear('2024-03-01')).toBe(false);
			expect(isValidMonthYear('2024-3')).toBe(false);
			expect(isValidMonthYear('2024/03')).toBe(false);
		});
	});

	describe('formatEditorialDate', () => {
		it('spells the month out', () => {
			expect(formatEditorialDate('2026-03-14')).toBe('14 March 2026');
		});

		it('accepts a Date — the shape the Zod boundary produces', () => {
			expect(formatEditorialDate(new Date('2026-03-14T00:00:00Z'))).toBe('14 March 2026');
		});

		it('accepts a month-precision string', () => {
			expect(formatEditorialDate('2026-03')).toBe('1 March 2026');
		});

		it('returns an empty string for nullish and unreadable input', () => {
			expect(formatEditorialDate(null)).toBe('');
			expect(formatEditorialDate(undefined)).toBe('');
			expect(formatEditorialDate('')).toBe('');
			expect(formatEditorialDate('not-a-date')).toBe('');
		});

		it('does not shift the day across time zones', () => {
			expect(formatEditorialDate(new Date('2026-01-01T00:00:00Z'))).toBe('1 January 2026');
		});
	});
});
