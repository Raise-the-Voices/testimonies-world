import { writable } from 'svelte/store';
import { getSession } from './api';
import type { User } from './types';

export const user = writable<User>({ authenticated: false });

export async function loadSession(): Promise<void> {
	try {
		const data = await getSession();
		user.set(data);
	} catch (e) {
		console.error('[session] failed:', e);
		user.set({ authenticated: false });
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
