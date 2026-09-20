/**
 * Error normalisation + toast dispatch for API failures.
 *
 * Two layers, kept split on purpose:
 *   - `normaliseError(err)` is PURE — maps any thrown value into a
 *     `NormalisedError`. Useful in places that want to inspect the
 *     shape (e.g. inline error UI) without firing a toast.
 *   - `handleApiError(err, opts)` adds the side effect — it calls
 *     `normaliseError` and, unless `silent: true`, fires a toast.
 *
 * `silent: true` is the right knob when the caller already renders
 * an inline error state (the toast would double up). For pages with
 * no inline error UI, leave it false and let the user see the toast
 * immediately.
 *
 * Status → toast variant mapping:
 *   - 0 (network/CORS)   → 'warning'  (often a transient blip)
 *   - 401, 403           → 'warning'  (often a session race, not user fault)
 *   - 4xx, 5xx, unknown  → 'error'    (action-required feedback)
 */
import { ApiError } from '../api';
import { showToast, type ToastVariant } from '../toast';

/**
 * Server-validated field errors (DRF: { field: [strings] }).
 * Forms map these onto inputs by field name.
 */
export type FieldErrors = Record<string, string[]>;

export interface NormalisedError {
	/** HTTP status from the response, or 0 for non-HTTP failures. */
	status: number;
	/** Human-readable message — safe to surface verbatim. */
	message: string;
	/** Per-field validation messages, if the server returned any. */
	fieldErrors: FieldErrors;
	/** Toast variant the dispatcher will use (unless silent). */
	variant: ToastVariant;
	/** True when the failure was a network / CORS / offline error. */
	isNetwork: boolean;
}

function variantForStatus(status: number): ToastVariant {
	if (status === 401 || status === 403) return 'warning';
	return 'error';
}

/**
 * Pure: normalise any thrown value into a NormalisedError.
 * Never shows a toast.
 */
export function normaliseError(err: unknown): NormalisedError {
	if (err instanceof ApiError) {
		return {
			status: err.status,
			message: err.message,
			fieldErrors: err.fieldErrors,
			variant: variantForStatus(err.status),
			isNetwork: false,
		};
	}
	if (err instanceof Error) {
		// The shared `request()` helper in api.ts throws an ApiError on
		// network failures with status 0, so a bare Error here usually
		// means a programming bug rather than a connectivity issue.
		return {
			status: 0,
			message: err.message,
			fieldErrors: {},
			variant: 'error',
			isNetwork: false,
		};
	}
	return {
		status: 0,
		message: 'Something went wrong.',
		fieldErrors: {},
		variant: 'error',
		isNetwork: false,
	};
}

/**
 * Show a toast for an error and return the normalised shape. Pass
 * `silent: true` when the caller already renders an inline error
 * state and a toast would double up.
 *
 * `fallback` is used when `err` couldn't be normalised to a useful
 * message — currently dead code, kept for API parity with future
 * call sites that wrap non-Error throws.
 */
export function handleApiError(
	err: unknown,
	ctx: { silent?: boolean; fallback?: string } = {},
): NormalisedError {
	const norm = normaliseError(err);
	if (!ctx.silent) {
		const msg = norm.message || ctx.fallback || 'Something went wrong.';
		showToast(msg, {
			variant: norm.variant,
			durationMs: norm.variant === 'error' ? 8000 : 5000,
		});
	}
	return norm;
}
