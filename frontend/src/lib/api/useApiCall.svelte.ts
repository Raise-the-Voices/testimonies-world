/**
 * Reactive API wrapper for Svelte 5 runes pages.
 *
 *   const users = useApiCall(() => getUsers());
 *   {#if users.loading}…{/else if users.error}…{/else}{/each users.data ?? []}
 *
 * Auto-toasts errors via `handleApiError`. Pass `silent: true` to
 * suppress the toast when the caller renders the error inline.
 *
 * IMPORTANT — the `.svelte.ts` extension is required. Without it,
 * the `$state` rune would error at compile time because runes are
 * only allowed in component scripts and `.svelte.ts` modules.
 *
 * Why a factory function returning state, not a Svelte component:
 * callers consume the result as a plain object — `users.loading`,
 * `users.data` — and the reactivity flows through the getter
 * accessors. A component wrapper would force an extra layer in
 * templates and lose the `users.refetch()` ergonomics.
 */
import { handleApiError, type NormalisedError } from './handleError';

export interface ApiCallState<T> {
	readonly data: T | null;
	readonly error: NormalisedError | null;
	readonly loading: boolean;
	refetch: () => Promise<void>;
}

export interface UseApiCallOptions {
	/** Skip the error toast — use when the caller renders inline errors. */
	silent?: boolean;
}

export function useApiCall<T>(
	fn: () => Promise<T>,
	opts: UseApiCallOptions = {},
): ApiCallState<T> {
	let data = $state<T | null>(null);
	let error = $state<NormalisedError | null>(null);
	let loading = $state(false);

	async function run(): Promise<void> {
		loading = true;
		error = null;
		try {
			data = await fn();
		} catch (e) {
			error = handleApiError(e, { silent: opts.silent });
			data = null;
		} finally {
			loading = false;
		}
	}

	return {
		get data() {
			return data;
		},
		get error() {
			return error;
		},
		get loading() {
			return loading;
		},
		refetch: run,
	};
}
