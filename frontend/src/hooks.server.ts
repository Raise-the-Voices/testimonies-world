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

export const handle: Handle = ({ event, resolve }) => resolve(event);

export const handleError: HandleServerError = ({ error }) => {
	console.error(error);
};
