/**
 * Notification client — typed wrapper around /api/notifications/ and
 * /api/preferences/. Mirrors the backend serializer shape, so when
 * backend types change, this should too.
 */
// We call `fetch()` directly here since notification endpoints don't need
// the ApiError-shaping layer (they're all safe GET/POST JSON) and api.ts
// keeps its `request` helper module-private.
async function http<T>(path: string, options: RequestInit = {}): Promise<T> {
	const API_BASE = '/api';
	const method = (options.method ?? 'GET').toUpperCase();
	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		...(options.headers as Record<string, string> | undefined),
	};
	if (method !== 'GET') {
		const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
		if (m) headers['X-CSRFToken'] = decodeURIComponent(m[1]);
	}
	const res = await fetch(`${API_BASE}${path}`, {
		credentials: 'include',
		headers,
		...options,
	});
	const text = await res.text();
	if (!res.ok) {
		throw new Error(`Request failed (${res.status}): ${text || res.statusText}`);
	}
	return (text ? JSON.parse(text) : (undefined as unknown)) as T;
}
import type { Paginated } from './types';

export type NotificationKind =
	| 'record_created'
	| 'record_updated'
	| 'status_done'
	| 'record_seen';

export interface Notification {
	id: number;
	kind: NotificationKind;
	casework: number | null;
	actor: number | null;
	actor_name?: string | null;
	casework_action_type?: string | null;
	casework_persons?: string[];
	is_read: boolean;
	read_at: string | null;
	created_at: string;
}

export interface UserPreferences {
	notify_email: boolean;
	notify_inapp: boolean;
}

export async function getNotifications(
	params: { unread?: boolean; page?: number } = {},
): Promise<Paginated<Notification>> {
	const q: Record<string, string> = {};
	if (params.unread) q.unread = '1';
	if (params.page) q.page = String(params.page);
	const qs = new URLSearchParams(q).toString();
	return http<Paginated<Notification>>(
		`/notifications/${qs ? '?' + qs : ''}`,
	);
}

export async function getUnreadCount(): Promise<{ count: number }> {
	return http<{ count: number }>('/notifications/unread-count/');
}

export async function markOneRead(id: number): Promise<Notification> {
	return http<Notification>(`/notifications/${id}/read/`, {
		method: 'POST',
	});
}

export async function markAllRead(): Promise<{ updated: number }> {
	return http<{ updated: number }>('/notifications/read-all/', {
		method: 'POST',
	});
}

export async function getPreferences(): Promise<UserPreferences> {
	return http<UserPreferences>('/preferences/');
}

export async function updatePreferences(
	patch: Partial<UserPreferences>,
): Promise<UserPreferences> {
	return http<UserPreferences>('/preferences/', {
		method: 'POST',
		body: JSON.stringify(patch),
	});
}