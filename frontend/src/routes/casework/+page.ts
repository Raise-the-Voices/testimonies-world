// Universal load for the /casework list. SSR-first so deep-linked
// visits render with results instead of a skeleton flash. Filters
// (status, action_type) are owned by the page component —
// intentionally not read from the URL, matching the existing
// convention at /contacts and /reports.
//
// Error shape: returns { records: [], error: '...' } instead of
// throwing, so the existing state-card UI can render. A thrown load
// would bubble up to SvelteKit's error page, which is worse UX for
// what is almost always a transient backend hiccup.
//
// SSR cookie note: SvelteKit's `fetch` forwards the browser's
// session cookie for same-origin /api/* calls. Anonymous users hit
// this load with no cookie and the backend returns 401 — we
// surface that as a soft error and let the page retry once the
// layout's `loadSession()` has hydrated (see +page.svelte's
// `onMount` retry).
import { base } from '$app/paths';
import type { Paginated, CaseworkRecord } from '$lib/types';

export async function load({ fetch }) {
    try {
        const res = await fetch(`${base}/api/casework/`);
        if (!res.ok) {
            return { records: [] as CaseworkRecord[], error: `HTTP ${res.status}` };
        }
        const data = (await res.json()) as Paginated<CaseworkRecord> | CaseworkRecord[];
        const records = Array.isArray(data) ? data : data.results ?? [];
        return { records, error: null };
    } catch (e) {
        return {
            records: [] as CaseworkRecord[],
            error: e instanceof Error ? e.message : "Couldn't load casework records.",
        };
    }
}
