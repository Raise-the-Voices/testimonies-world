/**
 * Toast — small store-based notification system.
 *
 * Use cases:
 *   - "Testimonial published." after a workflow action navigates away.
 *   - "Saved." after an async save elsewhere.
 *   - Cross-page feedback (the destination page reads the toast store
 *     on mount and shows it).
 *
 * Design constraints:
 *   - No external deps (matches the rest of the lib).
 *   - SSR-safe: no-op on the server, the UI mounts on hydration.
 *   - Auto-dismiss after `durationMs` (default 4000ms).
 *   - One toast at a time — replacing is the right UX for action
 *     confirmations; stacking is for noisy notifications, which we
 *     don't have here.
 */

import { writable } from 'svelte/store';

export type ToastVariant = 'success' | 'error' | 'info' | 'warning';

export interface Toast {
	id: number;
	message: string;
	variant: ToastVariant;
	durationMs: number;
}

const _toast = writable<Toast | null>(null);
export const toast = { subscribe: _toast.subscribe };

let _nextId = 1;
let _currentTimer: ReturnType<typeof setTimeout> | null = null;

function clearTimer(): void {
	if (_currentTimer !== null) {
		clearTimeout(_currentTimer);
		_currentTimer = null;
	}
}

export function showToast(
	message: string,
	options: { variant?: ToastVariant; durationMs?: number } = {},
): number {
	clearTimer();
	const id = _nextId++;
	const next: Toast = {
		id,
		message,
		variant: options.variant ?? 'info',
		durationMs: options.durationMs ?? 4000,
	};
	_toast.set(next);
	_currentTimer = setTimeout(() => {
		_toast.update((t) => (t && t.id === id ? null : t));
		_currentTimer = null;
	}, next.durationMs);
	return id;
}

export function dismissToast(): void {
	clearTimer();
	_toast.set(null);
}