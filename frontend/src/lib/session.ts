import { writable } from 'svelte/store';
import { getSession } from './api';
import type { User } from './types';

export const user = writable<User>({ authenticated: false });

// `ready` flips true the first time loadSession() resolves (success OR
// failure). Used by the root layout to gate child route render so we
// don't flash "you must be logged in" or "couldn't load (HTTP 0)"
// during the brief window between mount and /api/session/ returning —
// most visible on hard refresh.
//
// Default true on subsequent navigations: the root +layout.ts seeds the
// store on first render, and stays true for the rest of the session.
export const ready = writable<boolean>(false);

export async function loadSession(): Promise<void> {
	try {
		const data = await getSession();
		user.set(data);
	} catch (e) {
		console.error('[session] failed:', e);
		user.set({ authenticated: false });
	} finally {
		// Always mark ready — failing to load the session is itself an
		// answer the UI must be able to render against.
		ready.set(true);
	}
}

export function hasGroup(u: User, group: string): boolean {
	return u.groups?.includes(group) || u.is_staff === true || false;
}

export function isVolunteer(u: User): boolean {
	return (
		u.authenticated &&
		(hasGroup(u, 'Volunteer') || hasGroup(u, 'Advocate') || u.is_staff === true)
	);
}

export function isAdvocate(u: User): boolean {
	return u.authenticated && (hasGroup(u, 'Advocate') || u.is_staff === true);
}

export function isAdmin(u: User): boolean {
	return u.authenticated && u.is_staff === true;
}
