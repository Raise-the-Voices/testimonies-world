/**
 * Reusable async-data loader that combines two race-condition defenses:
 *
 *   1. AbortController — cancels the in-flight fetch at the network so the
 *      browser stops sending bytes and the server can short-circuit.
 *   2. loadToken (request-ID guard) — discards the result of any async
 *      operation that resolves after a newer call (or an unmount) has
 *      happened. Works for any async source, not just `fetch` — IndexedDB,
 *      WebSocket frames, Promise.race, anything.
 *
 * Why both? AbortController is efficient but unreliable for the result
 * (a buffered response can still resolve). loadToken is bulletproof for
 * the result but doesn't cancel the network. Together: the network stops
 * ASAP, and any straggler response is discarded before it can touch state.
 *
 * Usage in a component:
 *
 *   const personLoader = createLoader((signal, id) => getPerson(id, { signal }));
 *
 *   $effect(() => {
 *     void personId;
 *     const p = await personLoader.load(personId);
 *     if (p === undefined) return;   // cancelled — don't touch state
 *     person = p;
 *   });
 *
 * The loader auto-cancels on component unmount via `onDestroy`.
 */
import { onDestroy } from 'svelte';

export interface Loader<TArgs extends unknown[], TResult> {
	/** Run the wrapped async fn with a fresh AbortSignal. Returns undefined when cancelled. */
	load(...args: TArgs): Promise<TResult | undefined>;
	/** Invalidate any in-flight call and abort its network request. */
	cancel(): void;
}

export function createLoader<TArgs extends unknown[], TResult>(
	fn: (signal: AbortSignal, ...args: TArgs) => Promise<TResult>,
): Loader<TArgs, TResult> {
	// Single counter; incremented on every load() and on cancel(). Any
	// async function that captured the previous value sees `myToken !== token`
	// and bails out. A simple number has no race-of-its-own — unlike a Promise.
	let token = 0;

	// One controller per in-flight request. Replaced on each load(); the
	// previous one is aborted so the network call stops.
	let controller: AbortController | null = null;

	async function load(...args: TArgs): Promise<TResult | undefined> {
		// 1. Invalidate any prior call.
		const myToken = ++token;
		controller?.abort();
		controller = new AbortController();
		const { signal } = controller;

		try {
			const result = await fn(signal, ...args);

			// 2. If a newer call (or unmount) has happened, drop the result.
			//    The AbortError might already have done it, but a buffered
			//    response can still resolve here — the token is the floor.
			if (myToken !== token) return undefined;

			return result;
		} catch (e) {
			// 3. AbortError is the expected outcome of cancellation; the
			//    caller treats it the same as a dropped result (returns
			//    undefined) so they don't render an error banner for a
			//    navigation the user has already moved past.
			if (e instanceof DOMException && e.name === 'AbortError') return undefined;
			throw e;
		}
	}

	function cancel(): void {
		// Bumping the token invalidates any pending resolution. Aborting the
		// controller cancels the network. Both are needed: cancel without
		// abort wastes bandwidth; abort without cancel leaves a buffered
		// response free to clobber state.
		token++;
		controller?.abort();
	}

	// Svelte 5 lifecycle hook — fires on component unmount (including when
	// SvelteKit tears down the component at the end of a navigation).
	// createLoader is only meant to be called during component init, so
	// `onDestroy` here correctly registers cleanup against the calling
	// component.
	onDestroy(cancel);

	return { load, cancel };
}