// Universal load function for the /statistics page. Runs server-side on
// the first request to that URL (SSR), then client-side on subsequent
// navigations. Returns the typed Statistics shape so the page renders
// with real data on first paint — no skeleton flash for a fresh visit.
//
// Error shape: returns { statistics: null, error: '...' } instead of
// throwing, so the page component's existing error UI can render. A
// thrown load() would bubble up to SvelteKit's error page, which is
// worse UX for what is a transient backend issue.
import { base } from '$app/paths';
import type { Statistics } from '$lib/types';

export async function load({ fetch }) {
    try {
        const res = await fetch(`${base}/api/persons/statistics/`);
        if (!res.ok) {
            return { statistics: null, error: `HTTP ${res.status}` };
        }
        const statistics = (await res.json()) as Statistics;
        return { statistics, error: null };
    } catch (e) {
        return {
            statistics: null,
            error: e instanceof Error ? e.message : 'Failed to load statistics.',
        };
    }
}