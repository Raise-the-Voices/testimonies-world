/**
 * Universal load for /dashboard/audit-logs/.
 *
 * Reads URL search params (deep-linking + reload preserves filters),
 * calls `auditLogsList()` from the generated client, and returns the
 * paginated response plus a normalized filters object the page uses
 * to keep the form state in sync with the URL.
 *
 * Auth gate: AuditLogViewSet requires IsAdminUser on the backend, so
 * non-staff callers get a 403. We surface that as `error` rather than
 * throw — the page renders a friendly message instead of SvelteKit's
 * default error page.
 *
 * Response-shape guard: even on a 2xx the generated client can hand
 * back a malformed body (e.g. an HTML error page from a misrouted
 * nginx block, or an HTML 404 that snuck through as 200). Without
 * validation the page would render blank below the header because
 * `data.logs.results.length` would throw on `undefined`. Validate
 * the shape and surface any failure as `error`.
 */
import type { PageLoad } from './$types';
import { auditLogsList } from '$lib/api/generated/endpoints';
import type { AuditLog } from '$lib/api/generated/endpoints.schemas';
import { ApiError } from '$lib/api';
import { asPaginated } from '$lib/api/drfCompat';
import type { Paginated } from '$lib/types';

type ErrorKind = 'auth' | 'network' | 'server' | 'validation';

function errorMessage(e: unknown): { msg: string; kind: ErrorKind } {
	if (e instanceof ApiError) {
		// 401 unauthenticated → tell them to sign in.
		if (e.status === 401) {
			return {
				kind: 'auth',
				msg: 'Please sign in as a staff member to view the audit log.',
			};
		}
		// 403 authenticated but not staff → tell them to ask an admin.
		if (e.status === 403) {
			return {
				kind: 'auth',
				msg: 'You are signed in but not a staff member. Ask an admin for access.',
			};
		}
		if (e.status >= 500) {
			return {
				kind: 'server',
				msg: `The audit log service is unavailable (HTTP ${e.status}). Try again in a moment.`,
			};
		}
		return {
			kind: 'validation',
			msg: `Could not load audit log (HTTP ${e.status}).`,
		};
	}
	if (e instanceof Error) {
		return { kind: 'network', msg: e.message || 'Could not load audit log.' };
	}
	return { kind: 'network', msg: 'Could not load audit log.' };
}

function hasPaginatedShape<T>(value: unknown): value is Paginated<T> {
	if (!value || typeof value !== 'object') return false;
	const v = value as Record<string, unknown>;
	return typeof v.count === 'number' && Array.isArray(v.results);
}

export const load: PageLoad = async ({ url }) => {
	const params: Record<string, string> = {};
	for (const [key, value] of url.searchParams.entries()) {
		// Drop empty values so the URL stays clean (?action= → ?action=foo
		// → clear button removes the param entirely).
		if (value) params[key] = value;
	}

	try {
		// orval-vs-DRF response shape: orval's generated types wrap the
		// body in `{ data, status, headers }`, but our mutator returns
		// the body itself (res.json() directly). `asPaginated` is the
		// single shim that handles both — see $lib/api/drfCompat.ts.
		// Without it `hasPaginatedShape(response.data)` checks
		// `response.data` which is `undefined` at runtime, and the
		// page renders the "response was not in the expected format"
		// error even on a perfectly normal 200 OK.
		const response = await auditLogsList(params);
		const body = asPaginated<AuditLog>(response);
		if (!hasPaginatedShape<AuditLog>(body)) {
			// 2xx but the body isn't a paginated envelope. Almost
			// always means an HTML page leaked through (e.g. nginx
			// 404 served with status 200 after a redirect, or a
			// SvelteKit fallback rendered by the API path). Surface
			// this so the page never renders blank.
			return {
				logs: null,
				appliedFilters: params,
				error:
					'The audit log response was not in the expected format. Try a hard refresh (Ctrl+Shift+R).',
				errorKind: 'validation' as ErrorKind,
				requestParams: params,
			};
		}
		return {
			logs: body,
			appliedFilters: params,
			error: null as string | null,
			errorKind: null as ErrorKind | null,
			requestParams: params,
		};
	} catch (e) {
		const { msg, kind } = errorMessage(e);
		return {
			logs: null,
			appliedFilters: params,
			error: msg,
			errorKind: kind,
			requestParams: params,
		};
	}
};
