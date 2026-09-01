import { writable } from 'svelte/store';

export type ToastKind = 'success' | 'error' | 'info' | 'warning';

export interface Toast {
	id: number;
	kind: ToastKind;
	title: string;
	body?: string;
	durationMs: number;
}

const _toasts = writable<Toast[]>([]);
let nextId = 1;

export const toasts = { subscribe: _toasts.subscribe };

export interface ToastInput {
	kind?: ToastKind;
	title: string;
	body?: string;
	durationMs?: number;
}

/**
 * Show a toast. Returns its id so the caller can dismiss early.
 * Defaults: kind='info', durationMs=4000. Pass durationMs=0 to make it
 * sticky (only dismissed by the user).
 */
export function toast(input: ToastInput): number {
	const id = nextId++;
	const full: Toast = {
		id,
		kind: input.kind ?? 'info',
		title: input.title,
		body: input.body,
		durationMs: input.durationMs ?? 4000,
	};
	_toasts.update((arr) => [...arr, full]);
	if (full.durationMs > 0 && typeof window !== 'undefined') {
		window.setTimeout(() => dismiss(id), full.durationMs);
	}
	return id;
}

export function dismiss(id: number): void {
	_toasts.update((arr) => arr.filter((t) => t.id !== id));
}

export function clearAll(): void {
	_toasts.set([]);
}

// Convenience shortcuts with sensible defaults.
export const toastSuccess = (title: string, body?: string) =>
	toast({ kind: 'success', title, body });
export const toastError = (title: string, body?: string) =>
	toast({ kind: 'error', title, body, durationMs: 6000 });
export const toastInfo = (title: string, body?: string) =>
	toast({ kind: 'info', title, body });
export const toastWarning = (title: string, body?: string) =>
	toast({ kind: 'warning', title, body, durationMs: 5000 });
