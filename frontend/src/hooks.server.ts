/**
 * Server-side Sentry init (runs in the SvelteKit Node process).
 *
 * `sentryHandle` MUST be the FIRST handler in the chain so it
 * wraps every downstream handle(), load(), and server route — that
 * wrapping is how Sentry captures errors thrown by +page.server.ts
 * load functions, +server.ts API routes, and `hooks.server.ts`
 * downstream handlers.
 *
 * `$env/dynamic/public` (not `$env/static/public`) so the build
 * doesn't fail when an operator hasn't set the vars yet. Sentry's
 * init({ dsn: '' }) is a runtime no-op when DSN is absent — no
 * outbound traffic in unconfigured envs. Same trade-off as the
 * client hook.
 *
 * SECURITY: `sendDefaultPii` is OFF by default to match the backend
 * (testimonies-world handles sensitive human-rights PII — never ship
 * it to a third-party service unless an operator explicitly opts in).
 */
import {
	handleErrorWithSentry,
	init,
	sentryHandle,
} from '@sentry/sveltekit';
import { sequence } from '@sveltejs/kit/hooks';
import { env as publicEnv } from '$env/dynamic/public';

init({
	dsn: publicEnv.PUBLIC_SENTRY_DSN ?? '',
	environment: publicEnv.PUBLIC_SENTRY_ENV ?? 'development',
	release: publicEnv.PUBLIC_SENTRY_RELEASE ?? undefined,
	tracesSampleRate: Number(publicEnv.PUBLIC_SENTRY_TRACES_SAMPLE_RATE ?? 0),
	sendDefaultPii: false,
	tracePropagationTargets: [/^\/api\//],
});

export const handle = sequence(sentryHandle());

/**
 * SSR error boundary. handleErrorWithSentry reports the error to
 * Sentry and returns it so SvelteKit's error page can still render.
 */
export const handleError = handleErrorWithSentry();
