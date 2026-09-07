// Universal load for the /contacts list. SSR-first so deep-linked
// visits render with results instead of a skeleton flash. The
// role filter stays in component state, not the URL (existing
// convention — see /casework, /reports).
//
// Error shape: returns { contacts: [], error: '...' } instead of
// throwing, so the existing state-card UI can render. Anonymous
// SSR returns 401 before the layout's `loadSession()` has hydrated,
// which the page recovers from with an `onMount` retry.
import { base } from '$app/paths';
import type { Paginated, Contact } from '$lib/types';

export async function load({ fetch }) {
    try {
        const res = await fetch(`${base}/api/contacts/`);
        if (!res.ok) {
            return { contacts: [] as Contact[], error: `HTTP ${res.status}` };
        }
        const data = (await res.json()) as Paginated<Contact> | Contact[];
        const contacts = Array.isArray(data) ? data : data.results ?? [];
        return { contacts, error: null };
    } catch (e) {
        return {
            contacts: [] as Contact[],
            error: e instanceof Error ? e.message : "Couldn't load contacts.",
        };
    }
}
