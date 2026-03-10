import { writable } from 'svelte/store';
import { getSession } from './api';

interface User {
	authenticated: boolean;
	username?: string;
	email?: string;
	groups?: string[];
	is_staff?: boolean;
}

export const user = writable<User>({ authenticated: false });

export async function loadSession() {
	try {
		const data = await getSession();
		console.log('[session]', data);
		user.set(data);
	} catch (e) {
		console.error('[session] failed:', e);
		user.set({ authenticated: false });
	}
}

export function hasGroup(u: User, group: string): boolean {
	return u.groups?.includes(group) || u.is_staff || false;
}

export function isVolunteer(u: User): boolean {
	return u.authenticated && (hasGroup(u, 'Volunteer') || hasGroup(u, 'Advocate') || u.is_staff === true);
}

export function isAdvocate(u: User): boolean {
	return u.authenticated && (hasGroup(u, 'Advocate') || u.is_staff === true);
}
