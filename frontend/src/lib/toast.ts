/**
 * Toast — small store-based notification system.
 *
 * Use cases:
 *   - "Testimonial published." after a workflow action navigates away.
 *   - "Saved." after an async save elsewhere.
 *   - Cross-page feedback (the destination page reads the toast store
 *     on mount and shows it).
 *   - Form submission responses — the volunteer-facing form submit
 *     shows the actual server JSON so the operator has visual
 *     confirmation of what was saved (id, timestamp, FK back to the
 *     case, etc.). Pass `details` with the API response object and
 *     the toast renders a collapsible JSON viewer + copy button.
 *
 * Design constraints:
 *   - No external deps (matches the rest of the lib).
 *   - SSR-safe: no-op on the server, the UI mounts on hydration.
 *   - Auto-dismiss after `durationMs` (default 6000ms; longer when
 *     details are present so the operator has time to read/copy).
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
	/**
	 * Optional structured payload to display in a collapsible JSON
	 * viewer inside the toast. Used for form-submit responses — the
	 * operator sees the actual server-returned record (id, timestamp,
	 * FK back to the case, etc.) for visual confirmation.
	 */
	details?: Record<string, unknown>;
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
	options: {
		variant?: ToastVariant;
		durationMs?: number;
		details?: Record<string, unknown>;
	} = {},
): number {
	clearTimer();
	const id = _nextId++;
	// Details-bearing toasts get a longer default so the operator has
	// time to read the JSON. They can still dismiss manually.
	const defaultDuration = options.details ? 12000 : 4000;
	const next: Toast = {
		id,
		message,
		variant: options.variant ?? 'info',
		durationMs: options.durationMs ?? defaultDuration,
		details: options.details,
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
