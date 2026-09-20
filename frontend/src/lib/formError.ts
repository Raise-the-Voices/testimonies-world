/**
 * formError — shared error handling for SvelteKit forms.
 *
 * Background:
 *   - Every form in the app catches errors and surfaces them through a
 *     hand-rolled 5-way switch (validation / auth / network / server /
 *     generic) plus an inline `.form-error` banner.
 *   - Until now, the toast system (`$lib/toast`) was a success-only
 *     channel: `variant: 'error'` existed in the type and CSS but no
 *     call site ever fired it.
 *   - This module exposes a single entry point (`reportFormError`) that
 *     every form's catch block can call to fire a transient error toast
 *     alongside the inline banner.
 *
 * Conventions:
 *   - Validation errors stay inline only — firing a toast there would
 *     double-report the same problem (red banner + red toast).
 *   - Auth / network / server / generic errors fire a toast. The
 *     inline banner stays (it carries context and the "refresh session"
 *     CTA for auth).
 *   - The toast duration is 12s so the user has time to read the
 *     server's message before auto-dismiss.
 */
import { ApiError } from './api';
import { showToast } from './toast';

/**
 * The five error kinds the codebase already distinguishes in its
 * hand-rolled switches (e.g. `errorKind` in /casework/new). Keep the
 * string values in sync — they're the contract between this helper
 * and any form that renders an error banner with a kind class.
 */
export type FormErrorKind = 'validation' | 'auth' | 'network' | 'server' | 'generic';

export interface FormErrorShape {
	kind: FormErrorKind;
	message: string;
	/**
	 * First message per field, when the server returned DRF-style field
	 * errors. Forms merge this into their own `errors` record so per-field
	 * `aria-invalid` + `role="alert"` UI still works.
	 */
	fieldErrors?: Record<string, string>;
}

/**
 * Map any thrown value to the canonical {kind, message, fieldErrors}
 * triple. Pure: no side effects, no state, no UI. Safe to call from
 * any catch block.
 */
export function classifyFormError(e: unknown): FormErrorShape {
	if (e instanceof ApiError) {
		// Validation — DRF 400/422 with per-field messages.
		if (e.isValidation && e.fieldErrors && Object.keys(e.fieldErrors).length > 0) {
			const flat: Record<string, string> = {};
			for (const [field, msgs] of Object.entries(e.fieldErrors)) {
				if (msgs.length > 0) flat[field] = msgs[0];
			}
			return { kind: 'validation', message: e.message, fieldErrors: flat };
		}
		// Auth — 401/403. Always actionable (refresh session or log in).
		if (e.isUnauthorized) {
			return {
				kind: 'auth',
				message: 'Your session has expired. Please refresh and try again.',
			};
		}
		// Network — status 0 is the api.ts:170 sentinel for offline/CORS.
		if (e.status === 0) {
			return { kind: 'network', message: e.message };
		}
		// Server — 5xx.
		if (e.isServer) {
			return { kind: 'server', message: e.message };
		}
		// Other ApiError (e.g. 404 with a custom detail).
		return { kind: 'generic', message: e.message };
	}
	// Plain Error or unknown — fall back to a safe generic message.
	if (e instanceof Error) {
		return { kind: 'generic', message: e.message || 'Something went wrong.' };
	}
	return { kind: 'generic', message: 'Something went wrong.' };
}

/**
 * Fire a transient error toast for any non-validation failure.
 *
 * Call this AFTER updating the form's inline state (errors, errorKind,
 * formError) — the toast is the dismissible companion, the inline
 * banner is the persistent context.
 *
 * Validation errors are intentionally NOT toasted: per-field inline UI
 * is the right place for that information, and a toast on top of a red
 * banner would be double-reporting the same problem.
 *
 * @param e The thrown value from the form's catch block.
 * @param fallback Message used when the error carries no usable copy.
 */
export function reportFormError(e: unknown, fallback = 'Something went wrong.'): void {
	const shape = classifyFormError(e);
	// Validation is owned by inline UI — no toast.
	if (shape.kind === 'validation') return;
	// 12s default (vs the 4s for plain toasts) so the operator can read
	// the server message before it auto-dismisses.
	showToast(shape.message || fallback, { variant: 'error', durationMs: 12_000 });
}
