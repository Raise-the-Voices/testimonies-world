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
 *   - Input: ISO `YYYY-MM-DD` from the API (legacy day-precision rows
 *     and new month-only submissions, both stored on the 1st).
 *   - Output: `Mon YYYY` for display, `YYYY-MM` for the form input,
 *     `YYYY-MM-DD` for the API.
 */

const MONTH_YEAR_RE = /^\d{4}-\d{2}$/;

/**
 * Display formatter — `YYYY-MM-DD` → `Mon YYYY`.
 * Returns an empty string for nullish/empty input so callers can drop
 * the result straight into a template without a guard.
 */
export function formatMonthYear(iso: string | null | undefined): string {
	if (!iso) return '';
	const m = iso.match(MONTH_YEAR_RE);
	if (m) {
		// Already month-precision (e.g. raw form state) — format directly.
		return formatYearMonth(iso.slice(0, 4), iso.slice(5, 7));
	}
	const d = matchIsoDate(iso);
	if (!d) return iso;
	return formatYearMonth(d[1], d[2]);
}

/**
 * `YYYY-MM-DD` (wire) → `YYYY-MM` (form input value).
 * Defensive — if the input isn't a full ISO date, returns it unchanged
 * so the caller sees a sensible value rather than `undefined`.
 */
export function isoToMonthYear(iso: string | null | undefined): string {
	if (!iso) return '';
	const d = matchIsoDate(iso);
	return d ? `${d[1]}-${d[2]}` : iso;
}

/**
 * `YYYY-MM` (form) → `YYYY-MM-01` (wire).
 * The model is a `DateField`, so we send the 1st of the month — the
 * backend stores it; the day is no longer meaningful for this field.
 */
export function monthYearToIsoDate(yyyyMm: string | null | undefined): string {
	if (!yyyyMm) return '';
	if (!MONTH_YEAR_RE.test(yyyyMm)) return '';
	return `${yyyyMm}-01`;
}

/**
 * Form-side validity check for the month input.
 * Rejects empty (optional field), rejects anything that doesn't look
 * like `YYYY-MM`. The native `<input type="month">` already gates the
 * picker UI; this catches paste / autofill / programmatic input.
 */
export function isValidMonthYear(value: string): boolean {
	if (!value) return true;
	return MONTH_YEAR_RE.test(value);
}

function matchIsoDate(s: string): RegExpMatchArray | null {
	return s.match(/^(\d{4})-(\d{2})-\d{2}$/);
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
