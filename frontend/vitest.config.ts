/// <reference types="vitest" />
import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// Vitest config — see "Frontend test infrastructure" commit. Scope
// is intentionally narrow (lib/testimonial-sanitize.ts + the pure
// statusPresentation module) so the suite stays fast enough to run
// on every PR. Playwright E2E is a separate epic (per the audit's
// E2E gap; this commit only adds the runner + a smoke).
export default defineConfig({
	plugins: [svelte({ hot: false })],
	test: {
		environment: 'node',
		include: ['src/**/*.test.ts'],
	},
});