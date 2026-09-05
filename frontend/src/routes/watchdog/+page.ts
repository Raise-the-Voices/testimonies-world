// Universal load function for the /watchdog page. Returns the list of
// persons needing attention; the page renders the table with real data
// on first paint instead of a skeleton.
import { base } from '$app/paths';
import type { Person } from '$lib/types';

export async function load({ fetch }) {
    try {
        const res = await fetch(`${base}/api/persons/watchdog/`);
        if (!res.ok) {
            return { persons: [], error: `HTTP ${res.status}` };
        }
        const persons = (await res.json()) as Person[];
        return { persons, error: null };
    } catch (e) {
        return {
            persons: [],
            error: e instanceof Error ? e.message : 'Failed to load watchdog.',
        };
    }
}