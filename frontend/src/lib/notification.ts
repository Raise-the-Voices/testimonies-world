/**
 * Notification client — typed wrapper around /api/notifications/ and
 * /api/preferences/. Mirrors the backend serializer shape, so when
 * backend types change, this should too.
 *
 * Uses the shared `request()` from `$lib/api` so notification calls
 * benefit from the same CSRF handling, ApiError shaping, and field-error
 * parsing that every other endpoint gets. We previously re-implemented
 * those here — that duplication is now removed.
 */
import { request } from './api';
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
	return request<Paginated<Notification>>(
		`/notifications/${qs ? '?' + qs : ''}`,
	);
}

export async function getUnreadCount(): Promise<{ count: number }> {
	return request<{ count: number }>('/notifications/unread-count/');
}

export async function markOneRead(id: number): Promise<Notification> {
	return request<Notification>(`/notifications/${id}/read/`, {
		method: 'POST',
	});
}

export async function markAllRead(): Promise<{ updated: number }> {
	return request<{ updated: number }>('/notifications/read-all/', {
		method: 'POST',
	});
}

export async function getPreferences(): Promise<UserPreferences> {
	return request<UserPreferences>('/preferences/');
}

export async function updatePreferences(
	patch: Partial<UserPreferences>,
): Promise<UserPreferences> {
	return request<UserPreferences>('/preferences/', {
		method: 'POST',
		body: JSON.stringify(patch),
	});
}