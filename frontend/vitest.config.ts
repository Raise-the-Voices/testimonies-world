/// <reference types="vitest" />
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// Vitest config — see "Frontend test infrastructure" commit. Scope
// is intentionally narrow (lib/testimonial-sanitize.ts + the pure
// statusPresentation module) so the suite stays fast enough to run
// on every PR. Playwright E2E is a separate epic (per the audit's
// E2E gap; this commit only adds the runner + a smoke).
export default defineConfig({
	plugins: [svelte({ hot: false })],
	resolve: {
		alias: {
			// This config uses the plain Svelte plugin, not SvelteKit's,
			// so the `$lib` alias has to be spelled out. Without it a
			// component that imports a sibling through `$lib` cannot be
			// rendered in a test.
			$lib: fileURLToPath(new URL('./src/lib', import.meta.url))
		},
		// A file that asks for the jsdom environment (`// @vitest-environment
		// jsdom`) is transformed for the browser, so `svelte` has to resolve
		// to its client build — otherwise mounting a component reaches for
		// the server build, which has no `mount`.
		conditions: ['browser']
	},
	test: {
		environment: 'node',
		include: ['src/**/*.test.ts'],
	},
});