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
 */
import type { PageLoad } from './$types';
import { auditLogsList } from '$lib/api/generated/endpoints';
import { ApiError } from '$lib/api';

export const load: PageLoad = async ({ url }) => {
	const params: Record<string, string> = {};
	for (const [key, value] of url.searchParams.entries()) {
		// Drop empty values so the URL stays clean (?action= → ?action=foo
		// → clear button removes the param entirely).
		if (value) params[key] = value;
	}

	try {
		const response = await auditLogsList(params);
		return {
			logs: response.data,
			appliedFilters: params,
			error: null as string | null,
			// echo back the request params for downstream consumption
			requestParams: params,
		};
	} catch (e) {
		const msg =
			e instanceof ApiError
				? e.isUnauthorized
					? 'Please sign in as a staff member to view the audit log.'
					: `Could not load audit log (HTTP ${e.status}).`
				: e instanceof Error
					? e.message
					: 'Could not load audit log.';
		return {
			logs: null,
			appliedFilters: params,
			error: msg,
			requestParams: params,
		};
	}
};
