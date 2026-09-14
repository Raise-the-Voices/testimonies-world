/**
 * DRF-vs-orval response-shape compatibility shim.
 *
 * The backend's DRF ModelViewSet returns the serializer body
 * directly (e.g. `{ id: 1, title: '...' }`), but orval generates
 * TypeScript signatures that assume the response is wrapped in
 * `{ data, status, headers }` (the shape orval emits for fetchers).
 * On real responses, `res.data` is always undefined; reading it
 * silently returns nothing and surfaces as "broken cards" /
 * "missing id" bugs downstream.
 *
 * Earlier code worked around this with the same four-line shim in
 * four places. This module is the single source of truth — the
 * shape assumption lives here, not at every call site.
 */

import type { Paginated } from '$lib/types';

/**
 * Coerce an orval response into a paginated body. The fallback
 * chain:
 *   1. `res.data` if orval already wrapped it
 *   2. `res` itself (the actual DRF body) — the common case
 *   3. `{ results: [] }` if neither is usable
 */
export function asPaginated<T>(res: unknown): Paginated<T> {
	const candidate = (res ?? {}) as Record<string, unknown>;
	if (candidate.data && typeof candidate.data === 'object') {
		return candidate.data as unknown as Paginated<T>;
	}
	return candidate as unknown as Paginated<T>;
}

/**
 * Extract a created row's id from an orval response. Throws a
 * user-friendly error if no usable id is present so the caller can
 * surface it directly without wrapping in `instanceof Error`.
 */
export function extractCreatedId(res: unknown): number {
	const outer = (res ?? {}) as Record<string, unknown>;
	const candidate =
		outer.data && typeof outer.data === 'object'
			? (outer.data as Record<string, unknown>)
			: outer;
	const id = candidate.id;
	if (typeof id !== 'number' || !Number.isFinite(id)) {
		throw new Error(
			'The server accepted the testimonial but its response was missing a valid id. ' +
				'Please retry — if the problem persists, contact support via the audit log.',
		);
	}
	return id;
}

/**
 * Coerce an SSR `fetch().json()` response into a single object.
 * Anonymous and authenticated GETs use different serializers
 * (TestimonialPublic vs TestimonialInternal) — this helper is
 * shape-agnostic about that. Returns null on parse failure or
 * when the body is missing fields the caller will rely on.
 */
export function asTestimonialBody(res: unknown): Record<string, unknown> | null {
	if (!res || typeof res !== 'object') return null;
	return res as Record<string, unknown>;
}