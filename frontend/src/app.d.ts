import type { User } from '$lib/types';

// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	namespace App {
		// Error shape passed to +error.svelte. +error.svelte reads
		// `error.message?` (the `?` is intentional — SvelteKit can
		// construct an Error without a message), so this mirrors
		// that exact contract to keep consumer-side types tight.
		interface Error {
			message?: string;
		}

		// Per-request locals populated in hooks.server.ts. Sentry init
		// there adds no `event.locals.*` fields today; declare
		// additions here only if a future handle() populates them
		// (e.g. a request ID for log correlation).
		interface Locals {}

		// Root +layout.ts return shape. Child +page.ts loads extend
		// this in their own `$types`; do NOT re-declare per-page
		// fields here. The `error` field is `string | null` even
		// though the catch branch always returns a `string` — the
		// declared shape is the published contract, not the inferred
		// per-branch return.
		interface PageData {
			user: User;
			error: string | null;
		}

		// No $page.state writes happen anywhere in the app today
		// (no pushState/replaceState with state). Declared to keep
		// the augmentation complete; extend if navigation state is
		// introduced.
		interface PageState {}

		// Platform customization is not used — request.platform is
		// not read anywhere. Kept commented; uncomment + extend if
		// a deployment target needs CF/IPv6/IPv4/etc. discrimination.
		// interface Platform {}
	}
}

export {};
