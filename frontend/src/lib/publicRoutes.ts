/**
 * The public pages.
 *
 * An allowlist, not a denylist: a route that nobody has thought about is
 * treated as internal, so the ambient wash can never leak onto a new staff
 * tool. The editorial register (scroll reveals, count-ups) is scoped to the
 * same list.
 *
 * Paths are compared without the deployment base path (`/testimonies`).
 */

const PUBLIC_ROOTS = new Set(['persons', 'testimonials', 'statistics', 'watchdog']);

/**
 * Removes the deployment base path (`/testimonies`) so routes can be
 * compared against the allowlist.
 */
export function stripBasePath(pathname: string, base: string): string {
	if (!base || base === '/') return pathname;
	const trimmed = base.endsWith('/') ? base.slice(0, -1) : base;
	if (pathname === trimmed) return '/';
	if (pathname.startsWith(`${trimmed}/`)) return pathname.slice(trimmed.length);
	return pathname;
}

function isRecordId(segment: string): boolean {
	return /^\d+$/.test(segment);
}

/**
 * True for the pages a visitor reads without an account:
 * `/`, `/persons`, `/persons/<id>`, `/testimonials`, `/testimonials/<id>`,
 * `/statistics`, `/watchdog`.
 *
 * Everything else — the edit and report sub-pages, `/dashboard`,
 * `/casework`, `/contacts`, `/reports`, `/submit`, `/settings`,
 * `/notifications` — is internal.
 */
export function isPublicRoute(pathname: string): boolean {
	const path = pathname.replace(/\/+$/, '') || '/';
	if (path === '/') return true;

	const segments = path.split('/').filter(Boolean);
	const root = segments[0];
	if (!root || !PUBLIC_ROOTS.has(root)) return false;

	if (root === 'statistics' || root === 'watchdog') {
		return segments.length === 1;
	}

	// /persons and /persons/<id>
	if (root === 'persons') {
		return segments.length === 1 || (segments.length === 2 && isRecordId(segments[1]));
	}

	// /testimonials and /testimonials/<id> — /testimonials/new is a staff form.
	return segments.length === 1 || (segments.length === 2 && isRecordId(segments[1]));
}
