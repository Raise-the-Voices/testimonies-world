// Universal load for the landing page. Returns the platform statistics
// summary used by the stats bar — first paint shows real numbers
// instead of an empty skeleton.
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
            error: e instanceof Error ? e.message : 'Could not load platform statistics.',
        };
    }
}