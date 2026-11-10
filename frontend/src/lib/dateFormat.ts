/**
 * Date formatting helpers for fields whose precision has been reduced
 * from day-level to month-level on the form (e.g. `last_known_date`).
 *
 * Why a dedicated helper instead of inline `toLocaleDateString`:
 *   - keeps the display format ("Mar 2024") consistent across
 *     PersonCard, /persons list, and /persons/[id] detail
 *   - centralizes the wire ↔ form conversion for the new month-picker
 *     input. The wire stays `YYYY-MM-DD` (Django DateField contract);
 *     the form holds `YYYY-MM`.
 *
 * Conventions:
 *   - Input: a `Date` (what the Zod boundary produces — see `isoDate`
 *     in `schemas/wire.ts`) or an ISO `YYYY-MM-DD` / `YYYY-MM` string
 *     (the raw payload on the list and watchdog pages, which don't run
 *     the parse). Legacy day-precision rows and new month-only
 *     submissions are both stored on the 1st.
 *   - Output: `Mon YYYY` for display, `YYYY-MM` for the form input,
 *     `YYYY-MM-DD` for the API.
 */

const MONTH_YEAR_RE = /^\d{4}-\d{2}$/;

/**
 * Full-date formatter — day-precision dates for surfaces that state the
 * day (the case card's header date and abduction date).
 *
 * Accepts both shapes a date arrives in:
 *   - a `Date`, for fields the Zod boundary converts (`created_at`,
 *     `case_received_date` — see `isoDate` / `isoDateTime` in
 *     `schemas/wire.ts`);
 *   - an ISO `YYYY-MM-DD` string, for fields the boundary leaves alone
 *     (a report's `date_of_abduction` arrives inside `reports[]`,
 *     which the detail schema keeps as `z.any()`).
 *
 * Output is `14 Mar 2026` — day first, `en-GB` ordering. It reads as
 * a date on a document rather than as a US form field, and it is
 * unambiguous to a reader who does not share the author's locale.
 * Everything is rendered in UTC so the day never shifts.
 *
 * Returns an empty string for anything it cannot read, so callers can
 * drop the result into a template without a guard.
 */
export function formatFullDate(value: unknown): string {
	const d = toUtcDate(value);
	if (!d) return '';
	return d.toLocaleDateString('en-GB', {
		day: 'numeric',
		month: 'short',
		year: 'numeric',
		timeZone: 'UTC',
	});
}

/**
 * Editorial date formatter — the date stamp on the case poster.
 *
 * Output is `2 February 2026`: day, full month name, year. The month
 * is spelled out because the poster sets the date in an editorial
 * line, where an abbreviated month reads as a form field rather than
 * as a date on a document. The caller uppercases it.
 *
 * Accepts the same shapes as `formatFullDate` and returns an empty
 * string for anything it cannot read.
 */
export function formatEditorialDate(value: unknown): string {
	const d = toUtcDate(value);
	if (!d) return '';
	return d.toLocaleDateString('en-GB', {
		day: 'numeric',
		month: 'long',
		year: 'numeric',
		timeZone: 'UTC',
	});
}

/**
 * Coerce a date-ish value to a UTC-midnight Date, or null if it cannot
 * be read. `YYYY-MM` is accepted and pinned to the 1st.
 */
function toUtcDate(value: unknown): Date | null {
	if (value instanceof Date) {
		return Number.isNaN(value.getTime()) ? null : value;
	}
	if (typeof value !== 'string' || !value) return null;
	const m = value.match(/^(\d{4})-(\d{2})(?:-(\d{2}))?/);
	if (!m) return null;
	const day = m[3] ?? '01';
	const d = new Date(`${m[1]}-${m[2]}-${day}T00:00:00Z`);
	return Number.isNaN(d.getTime()) ? null : d;
}

/**
 * Split a date-ish value into its UTC year and month.
 *
 * Accepts the shapes a date arrives in:
 *   - a `Date`, for fields the Zod boundary converts (`last_known_date`
 *     — see `isoDateNullable` in `schemas/wire.ts`);
 *   - an ISO `YYYY-MM-DD` / `YYYY-MM` string, for fields the boundary
 *     leaves alone (the list and watchdog pages read the raw payload).
 *
 * Returns null when the value cannot be read.
 */
function toYearMonth(value: unknown): { year: string; month: string } | null {
	const d = toUtcDate(value);
	if (!d) return null;
	return {
		year: String(d.getUTCFullYear()).padStart(4, '0'),
		month: String(d.getUTCMonth() + 1).padStart(2, '0'),
	};
}

/**
 * Display formatter — a date → `Mon YYYY`.
 *
 * Accepts both shapes a date arrives in: a `Date` (what the Zod
 * boundary produces for `last_known_date`) or an ISO `YYYY-MM-DD` /
 * `YYYY-MM` string.
 *
 * Returns an empty string for nullish/empty input so callers can drop
 * the result straight into a template without a guard. An unreadable
 * string is passed through unchanged — a single bad row should not
 * blank a list.
 */
export function formatMonthYear(value: unknown): string {
	const ym = toYearMonth(value);
	if (ym) return formatYearMonth(ym.year, ym.month);
	return typeof value === 'string' ? value : '';
}

/**
 * A date → `YYYY-MM` (form input value).
 *
 * Accepts the same shapes as `formatMonthYear`. Defensive — if the
 * input isn't readable, returns it unchanged so the caller sees a
 * sensible value rather than `undefined`.
 */
export function isoToMonthYear(value: unknown): string {
	const ym = toYearMonth(value);
	if (ym) return `${ym.year}-${ym.month}`;
	return typeof value === 'string' ? value : '';
}

/**
 * `YYYY-MM` (form) → `YYYY-MM-01` (wire).
 * The model is a `DateField`, so we send the 1st of the month — the
 * backend stores it; the day is no longer meaningful for this field.
 */
export function monthYearToIsoDate(yyyyMm: unknown): string {
	if (typeof yyyyMm !== 'string' || !yyyyMm) return '';
	if (!MONTH_YEAR_RE.test(yyyyMm)) return '';
	return `${yyyyMm}-01`;
}

/**
 * Form-side validity check for the month input.
 * Rejects empty (optional field), rejects anything that doesn't look
 * like `YYYY-MM`. The native `<input type="month">` already gates the
 * picker UI; this catches paste / autofill / programmatic input.
 */
export function isValidMonthYear(value: unknown): boolean {
	if (!value) return true;
	if (typeof value !== 'string') return false;
	return MONTH_YEAR_RE.test(value);
}

function formatYearMonth(year: string, month: string): string {
	const d = new Date(Date.UTC(Number(year), Number(month) - 1, 1));
	if (Number.isNaN(d.getTime())) return `${year}-${month}`;
	return d.toLocaleDateString('en-US', {
		year: 'numeric',
		month: 'short',
		timeZone: 'UTC',
	});
}
