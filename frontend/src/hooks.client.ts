/**
 * Client hooks.
 *
 * Sentry was previously wired here but is now intentionally not used.
 * The `testimonies.world` site handles sensitive human-rights PII; we
 * don't ship telemetry to a third-party service unless an operator
 * makes a deliberate, documented decision to opt in. When that
 * decision is made, restore the wiring here with the same
 * dynamic-import + DSN-presence gate documented in `docs/sentry.md`
 * (so a SDK module-load side effects can't hang the browser event
 * loop).
 */
import type { HandleClientError } from '@sveltejs/kit';

export const handleError: HandleClientError = ({ error }) => {
	console.error(error);
};
