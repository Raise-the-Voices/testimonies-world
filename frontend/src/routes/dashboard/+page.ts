/**
 * Universal load for the /dashboard page. Returns the role-scoped
 * dashboard payload from /api/dashboard/. Never throws — surfaces
 * errors as `{ data: null, error: "..." }` so the page can render the
 * friendly error-state card instead of SvelteKit's default error page.
 *
 * Auth gate: DashboardViewSet requires IsAuthenticated, so anonymous
 * callers get 401/403 from the server. We don't redirect here — the
 * header nav doesn't expose /dashboard to anonymous users (see
 * +layout.svelte), and SvelteKit's load returning an error lets the
 * page render the same error card it would for a server outage.
 *
 * SSR fetch: uses SvelteKit's wrapped `fetch` so cookies are forwarded
 * during SSR. The global fetch (used by api.ts's request() helper)
 * does NOT forward cookies during SSR — without this, the dashboard
 * would fail to load on hard refresh and the page would flicker
 * between the SSR error state and the client-side retry success.
 */
import { getDashboard, ApiError } from '$lib/api';

export async function load({ fetch: skFetch }) {
	try {
		const data = await getDashboard(skFetch);
		return { data, error: null as string | null };
	} catch (e) {
		const msg =
			e instanceof ApiError
				? e.isUnauthorized
					? 'Please sign in to view the dashboard.'
					: `Could not load dashboard (HTTP ${e.status}).`
				: e instanceof Error
					? e.message
					: 'Could not load dashboard.';
		return { data: null, error: msg };
	}
}