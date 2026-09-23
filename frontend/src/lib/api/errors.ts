/**
 * Pure error-parsing helpers used by both `src/lib/api.ts` (the manual
 * `request()` helper) and `src/lib/api/mutator.ts` (the orval-generated
 * `fetcher()`).
 *
 * This module deliberately has NO SvelteKit dependencies — no `$app/*`
 * imports, no DOM globals, no `document`. That makes it importable
 * from vitest in node mode (see `api.test.ts`) and keeps the parsing
 * logic portable if we ever extract a shared package.
 *
 * Public API:
 *   - `ApiError`              — the throwable error class
 *   - `STATUS_FALLBACK`       — generic messages keyed by status code
 *   - `parseApiErrorBody`     — body → {message, fieldErrors, messages}
 *   - `readErrorBody`         — Response → {body, contentType}
 */

export type FieldErrors = Record<string, string[]>;

/**
 * Status-based fallback messages used when the server body is empty or
 * unparseable. Kept here so both `request()` (api.ts) and `fetcher()`
 * (mutator.ts) stay in sync.
 */
export const STATUS_FALLBACK: Record<number, string> = {
	400: 'Some fields look off — please review and try again.',
	401: 'You need to log in to do that.',
	403: "You don't have permission to do that.",
	404: "We couldn't find what you were looking for.",
	500: 'The server hit a snag. Please try again in a moment.',
	502: 'The server is temporarily unreachable. Please try again.',
	503: 'The server is temporarily unreachable. Please try again.',
	504: 'The server took too long to respond. Please try again.',
};

/**
 * Error thrown by `request()` when the API returns a non-2xx response.
 * Carries enough context for callers to map server errors back to fields
 * (DRF sends `{ field: ["msg", ...] }` for 400s) and to write copy
 * tailored to auth failures.
 *
 * The shape is backward-compatible with the original (M0) class:
 *   - `message`    — single best headline (what every existing catch
 *                    block already consumes)
 *   - `status`     — HTTP status (0 for network/CORS failures)
 *   - `statusText` — HTTP status text
 *   - `fieldErrors`— DRF `{ field: ["msg", ...] }` map (also includes
 *                    `non_field_errors`, `detail`, etc.)
 *   - `body`       — raw parsed body (object, array, string, or null)
 *
 * M15 additions (all additive — no existing reader breaks):
 *   - `messages`   — flat list of every human-readable message we
 *                    pulled from the body, in the order we found them.
 *                    Useful for rendering "list of reasons" UIs that
 *                    need to show every server complaint, not just the
 *                    first.
 *   - `contentType`— the response Content-Type header (or '' on network
 *                    failure). Helps callers decide whether to show
 *                    raw HTML / plain text as-is.
 */
export class ApiError extends Error {
	status: number;
	statusText: string;
	fieldErrors: FieldErrors;
	body: unknown;
	/** Every individual error message we pulled out of the body. */
	messages: string[];
	/** Response Content-Type header, or '' when no response was received. */
	contentType: string;

	constructor(
		message: string,
		status: number,
		statusText: string,
		fieldErrors: FieldErrors = {},
		body: unknown = null,
		messages: string[] = [],
		contentType: string = '',
	) {
		super(message);
		this.name = 'ApiError';
		this.status = status;
		this.statusText = statusText;
		this.fieldErrors = fieldErrors;
		this.body = body;
		this.messages = messages.length > 0 ? messages : message ? [message] : [];
		this.contentType = contentType;
	}

	get isUnauthorized(): boolean {
		return this.status === 401 || this.status === 403;
	}
	get isServer(): boolean {
		return this.status >= 500;
	}
	get isValidation(): boolean {
		return this.status === 400 || this.status === 422;
	}
}

/**
 * Recursively collect every human-readable string from a parsed body,
 * respecting the shape conventions we see in practice:
 *
 *   - DRF default:           `{ field: ["msg", ...], detail: "..." }`
 *   - DRF single-message:    `{ field: "msg" }` (rare but legal)
 *   - DRF non-field errors:  `{ non_field_errors: ["msg"] }`
 *   - DRF nested serializer: `{ field: { sub: ["msg"] } }`
 *   - Custom envelopes:      `{ error: "..." }`, `{ message: "..." }`,
 *                            `{ detail: "..." }`
 *   - Top-level arrays:      `["msg1", "msg2"]`
 *
 * Anything that isn't a string or array of strings (numbers, booleans,
 * nested objects) is descended into — we don't pretend to know how to
 * format arbitrary data. The first scalar / array element wins the
 * priority used by `pickPrimaryMessage`.
 *
 * `seen` is a cycle guard: pathological bodies that reference
 * themselves would otherwise blow the stack.
 */
export function collectMessages(value: unknown, seen: WeakSet<object> = new WeakSet()): string[] {
	if (value == null) return [];
	if (typeof value === 'string') {
		const trimmed = value.trim();
		return trimmed ? [trimmed] : [];
	}
	if (typeof value === 'number' || typeof value === 'boolean') return [];
	if (Array.isArray(value)) {
		if (seen.has(value)) return [];
		seen.add(value);
		const out: string[] = [];
		for (const item of value) out.push(...collectMessages(item, seen));
		return out;
	}
	if (typeof value === 'object') {
		const obj = value as Record<string, unknown>;
		if (seen.has(obj)) return [];
		seen.add(obj);
		const out: string[] = [];
		for (const v of Object.values(obj)) out.push(...collectMessages(v, seen));
		return out;
	}
	return [];
}

/**
 * Pull the field-error map out of a parsed body, mirroring what DRF
 * actually sends. We only treat object values as field errors when
 * they themselves look like a `{ field: ... }` map or a flat string —
 * we don't recurse into nested serializer objects, because we can't
 * safely flatten `parent.child` paths from raw key names (DRF sometimes
 * uses dots in keys for nested errors but not always).
 */
export function extractFieldErrors(body: unknown): FieldErrors {
	if (!body || typeof body !== 'object' || Array.isArray(body)) return {};
	const out: FieldErrors = {};
	for (const [key, value] of Object.entries(body as Record<string, unknown>)) {
		if (Array.isArray(value) && value.every((v) => typeof v === 'string')) {
			out[key] = value as string[];
		} else if (typeof value === 'string') {
			out[key] = [value];
		}
	}
	return out;
}

/**
 * Pick the first human-readable message from a parsed body. Used for
 * the single-string `ApiError.message` slot that every existing catch
 * block already reads.
 *
 * Order of preference (matches how DRF and common custom envelopes
 * rank messages):
 *   1. `detail` — the canonical DRF single-error slot (PermissionDenied,
 *      NotAuthenticated, NotFound, Throttled, etc.)
 *   2. `message` — a few hand-rolled views use this instead of detail
 *   3. `error`   — a third-party convention we sometimes see
 *   4. `non_field_errors` — DRF cross-field validation
 *   5. The first key in `fieldErrors` — DRF per-field validation
 *   6. Any other string anywhere in the body (last resort)
 */
function pickPrimaryMessage(body: unknown, fieldErrors: FieldErrors): string | null {
	if (body && typeof body === 'object' && !Array.isArray(body)) {
		const obj = body as Record<string, unknown>;
		for (const key of ['detail', 'message', 'error'] as const) {
			const v = obj[key];
			if (typeof v === 'string' && v.trim()) return v.trim();
			if (
				Array.isArray(v) &&
				v.length > 0 &&
				typeof v[0] === 'string' &&
				(v[0] as string).trim()
			) {
				return (v[0] as string).trim();
			}
		}
		const nfe = (fieldErrors as FieldErrors).non_field_errors;
		if (nfe && nfe.length > 0 && nfe[0].trim()) return nfe[0].trim();
	}

	const fieldKeys = Object.keys(fieldErrors);
	if (fieldKeys.length > 0) {
		const firstField = fieldKeys[0];
		const firstMsg = fieldErrors[firstField][0];
		if (firstMsg) return `${firstField}: ${firstMsg}`;
	}

	// Last resort: any string anywhere in the body.
	const all = collectMessages(body);
	return all.length > 0 ? all[0] : null;
}

/**
 * Parse an API failure into the structured shape `ApiError` carries.
 *
 * `body` is whatever the response looked like AFTER best-effort JSON
 * parsing — it may be an object, array, plain string, or null. We don't
 * try to re-parse here: the caller already did (or tried to).
 *
 * Returned shape:
 *   - message      — single best headline (back-compat slot)
 *   - fieldErrors  — DRF field map (back-compat slot)
 *   - messages     — every individual string in the body, in order
 *   - body         — passed through verbatim
 *
 * Exported so the orval `fetcher()` in `api/mutator.ts` can use the
 * same parser without duplicating the (now larger) shape logic.
 */
export function parseApiErrorBody(
	body: unknown,
	status: number,
	statusText: string,
): {
	message: string;
	fieldErrors: FieldErrors;
	messages: string[];
} {
	const fieldErrors = extractFieldErrors(body);
	const primary = pickPrimaryMessage(body, fieldErrors);
	const messages = collectMessages(body);
	const message =
		primary ?? STATUS_FALLBACK[status] ?? `Request failed (${status} ${statusText}).`;
	return { message, fieldErrors, messages };
}

/**
 * Try to read `res.text()` and decide whether it's JSON or a plain
 * string. Returns the parsed body (object/array/string/null) plus the
 * raw text — callers want both, because:
 *
 *   - Plain Django HttpResponse("Authentication required.", status=401)
 *     gives us a text body with no JSON. If we silently treated that
 *     as "no body", the user would see a generic fallback ("You need
 *     to log in to do that.") instead of the actual server message.
 *
 *   - DRF responses always send JSON, but a malformed response (truncated
 *     proxy, 502 from nginx) might give us HTML or text we don't want
 *     to leak into a JSON.parse exception.
 */
export async function readErrorBody(res: Response): Promise<{
	body: unknown;
	contentType: string;
}> {
	const contentType = res.headers.get('content-type') ?? '';
	const rawText = await res.text();
	if (!rawText) return { body: null, contentType };

	// Only attempt JSON.parse when the server claims JSON. Some
	// proxies (nginx, Cloudflare) return HTML 5xx pages — parsing
	// those as JSON throws and we'd lose the raw text.
	if (contentType.includes('application/json') || contentType.includes('+json')) {
		try {
			return { body: JSON.parse(rawText), contentType };
		} catch {
			// Fall through and treat as plain text.
		}
	}

	// Plain-text body. Trim whitespace and use as a single message —
	// this is how Django's HttpResponse("...", status=4xx) reaches us.
	const trimmed = rawText.trim();
	return { body: trimmed || null, contentType };
}
