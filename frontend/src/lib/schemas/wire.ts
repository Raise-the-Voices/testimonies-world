/**
 * Wire-format primitives.
 *
 * The wire is JSON. JSON does not have:
 *   - `Date`         → serialized as ISO strings, timezone intent lost
 *   - `Decimal`      → serialized as either string or number; precision at risk
 *   - `BigInt`       → not in the JSON spec at all
 *   - `undefined`    → silently dropped by JSON.stringify
 *   - the difference between "missing" and "explicitly null"
 *
 * These primitives convert wire strings into real runtime types at the
 * parse boundary. Everything below the boundary sees parsed values;
 * everything above the boundary sees wire strings. The boundary is the
 * Zod schema in each route's `parseResponse` call.
 */
import { z } from 'zod';
import { Decimal } from 'decimal.js';

/**
 * Wire ISO datetime. Accepts:
 *   - "2026-01-01T00:00:00Z"          (Django default — UTC 'Z' suffix)
 *   - "2026-01-01T00:00:00+09:00"     (offset)
 *   - "2026-01-01T00:00:00.123456Z"  (microsecond precision Django emits)
 *
 * Rejects:
 *   - "2026-01-01"                    (date-only — use `isoDate` for that)
 *   - "01/01/2026"                    (locale formats)
 *
 * Returns a real `Date` so timezone math works correctly downstream.
 * Don't construct Date from string anywhere else — go through this.
 */
export const isoDateTime = z
	.string()
	.datetime({ offset: true })
	.transform((s) => new Date(s));

/**
 * Wire ISO date — for fields the backend models as date-only (DOB,
 * last_known_date, last_report_date). DRF serializes DateField as
 * "YYYY-MM-DD" with no time component.
 *
 * Returns a Date pinned to UTC midnight. This matters: parsing
 * "2026-01-01" without a TZ is locale-dependent, and most date pickers
 * treat date-only fields as UTC by convention.
 */
export const isoDate = z
	.string()
	.regex(/^\d{4}-\d{2}-\d{2}$/, 'Expected YYYY-MM-DD')
	.transform((s) => new Date(`${s}T00:00:00Z`));

/** Nullable variant of isoDate. */
export const isoDateNullable = isoDate.nullable();

/**
 * Wire decimal string — for monetary / high-precision numeric fields.
 *
 * DRF `DecimalField(max_digits=12, decimal_places=2)` serializes as
 * string (good — JSON has no decimal type). The string is exact.
 *
 * If you cast this to `number`, you lose precision. The discipline:
 * never do `parseFloat(invoice.total)` or `Number(x)`. Use Decimal
 * math directly.
 *
 * Returns a `Decimal` instance. Compare with `.equals()`, sum with
 * `.plus()`, format for display with `.toFixed(2)`.
 */
export const decimalString = z
	.string()
	.regex(/^-?\d+(\.\d+)?$/, 'Expected decimal string')
	.transform((s) => new Decimal(s));

/** Nullable variant. */
export const decimalStringNullable = decimalString.nullable();

/**
 * Wire ISO datetime that's allowed to be null (e.g. `last_known_date`
 * may not be known). Parses to `Date | null`.
 */
export const isoDateTimeNullable = isoDateTime.nullable();

/**
 * Wire integer — defends against a backend bug where a numeric field
 * is accidentally serialized as a string ("5" instead of 5). Coerce
 * rather than reject; the wire is supposed to be a number but coercion
 * is forgiving enough to survive a single bad serializer.
 */
export const intCoerce = z.coerce.number().int();

/**
 * Wire boolean — accepts JSON booleans. Used for `is_published`,
 * `is_private`, `is_read`, etc.
 */
export const boolStrict = z.boolean();