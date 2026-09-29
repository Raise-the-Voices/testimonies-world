/**
 * Server hooks.
 *
 * Sentry was previously wired here but is now intentionally not used.
 * The `testimonies.world` site handles sensitive human-rights PII; we
 * don't ship telemetry to a third-party service unless an operator
 * makes a deliberate, documented decision to opt in. When that
 * decision is made, restore the wiring here with the same
 * dynamic-import + DSN-presence gate documented in `docs/sentry.md`
 * (so a missing DSN can't hang Node 22's top-level await — the
 * `@sentry/sveltekit` SDK's module-load side effects register an
 * OpenTelemetry task that keeps the event loop unsettled).
 */
import type { Handle, HandleServerError } from '@sveltejs/kit';

// adapter-node emits `sveltekit:shutdown` after the HTTP server fully
// closes during SIGTERM/SIGINT/SHUTDOWN_TIMEOUT-driven shutdown
// (see node_modules/@sveltejs/adapter-node/files/index.js:272, emitted
// at build/index.js:280). Listening here gives operators a single,
// grep-able journald line that says "we shut down cleanly and why".
// When Sentry is re-wired per docs/sentry.md, Sentry.flush(2000) slots
// into this same listener with no further plumbing.
process.on('sveltekit:shutdown', (reason) => {
    console.info(`sveltekit:shutdown reason=${reason ?? 'unknown'}`);
});

export const handle: Handle = ({ event, resolve }) => resolve(event);

export const handleError: HandleServerError = ({ error }) => {
	console.error(error);
};
