/**
 * Stub for `$app/paths`.
 *
 * The vitest config runs the plain Svelte plugin, not `svelteKit()`, so
 * SvelteKit's runtime modules aren't available inside a test. A route
 * component under test still imports them, so `vitest.config.ts` aliases
 * the three `$app/*` modules this app uses to the stubs in this folder.
 *
 * `base` is the app's base path (`/testimonies` in production). The
 * stub returns an empty base so the URLs a component builds stay
 * readable in a test.
 */
export const base = '';
export const assets = '';

/** Mirrors SvelteKit's `resolve` — a path with no params is its own path. */
export function resolve(path: string): string {
	return path;
}
