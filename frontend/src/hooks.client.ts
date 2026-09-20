/**
 * Client-side Sentry init.
 *
 * Loaded once on hydration. Captures uncaught browser errors,
 * unhandled promise rejections, and (when `PUBLIC_SENTRY_TRACES_SAMPLE_RATE`
 * is non-zero) performance spans for navigation + fetch.
 *
 * SECURITY: `sendDefaultPii` is OFF by default to match the backend
 * (testimonies-world handles sensitive human-rights PII — never ship
 * it to a third-party service unless an operator explicitly opts in).
 *
 * We use `$env/dynamic/public` (not `$env/static/public`) so the
 * build doesn't fail when an operator hasn't set the vars yet.
 * The trade-off: the Sentry SDK is always bundled. Acceptable —
 * Sentry's init({ dsn: '' }) is a runtime no-op when the DSN is
 * absent, so there's no outbound traffic in unconfigured envs.
 */
import {
	browserTracingIntegration,
	handleErrorWithSentry,
	init,
} from '@sentry/sveltekit';
import { env as publicEnv } from '$env/dynamic/public';

const dsn = publicEnv.PUBLIC_SENTRY_DSN ?? '';

init({
	dsn,
	environment: publicEnv.PUBLIC_SENTRY_ENV ?? 'development',
	release: publicEnv.PUBLIC_SENTRY_RELEASE ?? undefined,
	// 0.0 disables tracing entirely; non-zero enables it for the
	// percentage of sessions sampled.
	tracesSampleRate: Number(publicEnv.PUBLIC_SENTRY_TRACES_SAMPLE_RATE ?? 0),
	sendDefaultPii: false,
	integrations: [browserTracingIntegration()],
	// Skip static-asset URLs entirely — a 1×1 favicon fetch shouldn't
	// burn a trace quota slot.
	tracePropagationTargets: [/^\/(?!_app\/).*/, /^\/api\//],
});

/**
 * SvelteKit's client-side error boundary. handleErrorWithSentry
 * reports the error to Sentry AND returns it so SvelteKit's own
 * UI fallback can still render.
 */
export const handleError = handleErrorWithSentry();
