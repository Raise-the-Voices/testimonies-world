/**
 * Root universal load — runs on every navigation, server-side AND
 * client-side, BEFORE any child +page.ts load. This is the canonical
 * SvelteKit place to hydrate cross-cutting state like auth.
 *
 * Why this lives at the layout, not the page:
 *   1. Single fetch per navigation, regardless of which page renders.
 *   2. Returns are forwarded to +layout.svelte as `data`, so children
 *      have a hydrated user state on first render — no "you must be
 *      logged in" flash on hard refresh.
 *   3. Server-side SSR uses SvelteKit's wrapped `fetch`, which
 *      forwards the request's cookies. The global `fetch` does NOT
 *      forward cookies during SSR; without this we'd hit auth-gated
 *      endpoints anonymously on hard refresh and get back HTTP 0 /
 *      401 / generic network errors.
 *
 * Anonymous users: we don't throw. Public pages (e.g. /persons)
 * must still render for anonymous visitors.
 */
import { getSession } from '$lib/api';
import type { User } from '$lib/types';

export async function load({ fetch: skFetch }) {
	try {
		const sessionUser = await getSession(skFetch);
		return { user: sessionUser, error: null as string | null };
	} catch (e) {
		// Anonymous or session-expired. Surface as a soft "no user" so
		// the page can still render the public-facing chrome.
		return {
			user: { authenticated: false } as User,
			error: e instanceof Error ? e.message : 'session-load-failed',
		};
	}
}