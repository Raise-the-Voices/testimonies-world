// Universal load for /notifications. Returns the default "all"
// list (the page exposes an All / Unread tab; the tab state lives
// in component $state and re-fetches client-side via
// getNotifications() from $lib/notification).
//
// Error shape: returns { notifications: [], error: '...' }
// instead of throwing. The notifications endpoint requires
// authentication, so anonymous SSR returns 401 before the layout's
// `loadSession()` hydrates; the page retries once via `onMount`
// once the session cookie is in scope.
//
// SSR note: do NOT import getNotifications() from $lib/notification
// here — that helper reads document.cookie for CSRF, which doesn't
// exist in SSR. Use the `fetch` argument from load() directly.
import { base } from '$app/paths';
import type { Notification } from '$lib/notification';

export async function load({ fetch }) {
    try {
        const res = await fetch(`${base}/api/notifications/`);
        if (!res.ok) {
            return {
                notifications: [] as Notification[],
                error: `HTTP ${res.status}`,
            };
        }
        const data = (await res.json()) as { results?: Notification[] };
        return {
            notifications: data.results ?? [],
            error: null,
        };
    } catch (e) {
        return {
            notifications: [] as Notification[],
            error: e instanceof Error ? e.message : "Couldn't load notifications.",
        };
    }
}
