// Universal load for the /reports global feed. SSR-first so a fresh
// visit renders the unfiltered first page of reports instead of a
// skeleton. The visible filter UI (search, source_type, date range,
// page) lives entirely in component $state — we deliberately do
// NOT read filter values from the URL, matching the convention at
// /contacts and /casework (see the page's header comment).
//
// We DO hard-code `ordering=-created_at` in the SSR fetch because
// the page's default visible order is "newest first" — without that
// default, a fresh visit could land on a different sort than
// subsequent client refetches, which would be jarring.
//
// Error shape: returns { reports: [], reportCount: 0, error: '...' }
// instead of throwing, so the existing state-card UI can render.
// Anonymous SSR returns 401 before the layout's `loadSession()`
// hydrates; the page retries once via `onMount`.
import { base } from '$app/paths';
import type { Paginated, Report } from '$lib/types';

export async function load({ fetch }) {
    try {
        const res = await fetch(`${base}/api/reports/?ordering=-created_at`);
        if (!res.ok) {
            return {
                reports: [] as Report[],
                reportCount: 0,
                error: `HTTP ${res.status}`,
            };
        }
        const data = (await res.json()) as Paginated<Report>;
        return {
            reports: data.results ?? [],
            reportCount: data.count ?? 0,
            error: null,
        };
    } catch (e) {
        return {
            reports: [] as Report[],
            reportCount: 0,
            error: e instanceof Error ? e.message : "Couldn't load reports.",
        };
    }
}
