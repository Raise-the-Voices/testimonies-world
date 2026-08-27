/**
 * Debounce — call `fn` only after `delay` ms of silence.
 *
 * Usage:
 *   const onSearch = debounce(() => applyFilters(), 300);
 *   <input oninput={onSearch} />
 *
 * Returns a wrapper that also exposes `.flush()` to invoke the pending
 * call immediately (useful right before a navigation, to avoid dropping
 * the last keystroke). If no call is pending, `.flush()` is a no-op.
 */
export type Debounced<T extends (...args: any[]) => void> = ((...args: Parameters<T>) => void) & {
	flush: () => void;
};

export function debounce<T extends (...args: any[]) => void>(fn: T, delay: number): Debounced<T> {
	let timer: ReturnType<typeof setTimeout> | null = null;

	const wrapped = (...args: Parameters<T>) => {
		if (timer) clearTimeout(timer);
		timer = setTimeout(() => {
			timer = null;
			fn(...args);
		}, delay);
	};

	wrapped.flush = () => {
		if (timer) {
			clearTimeout(timer);
			timer = null;
			fn();
		}
	};

	return wrapped as Debounced<T>;
}
