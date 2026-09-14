// Universal load for /testimonials/[id]/edit. Mirrors [id]/+page.ts
// — fetches the testimonial via the public API, surfaces the same
// 404 / HTTP-error states, and lets the SSR-authenticated user edit
// the row via PATCH /api/testimonials/{id}/. The backend's
// CanEditOwnOrReview gate enforces ownership; the page itself does
// no client-side authorization (DRF is the boundary).
import { base } from '$app/paths';
import type { TestimonialPublic } from '$lib/api/generated/endpoints.schemas';

export async function load({ fetch, params, url }) {
	const id = Number(params.id);
	if (!Number.isInteger(id) || id <= 0) {
		return { testimonial: null, error: 'Invalid testimonial id.', anonHref: null };
	}
	try {
		const res = await fetch(`${base}/api/testimonials/${id}/`);
		if (res.status === 404) {
			return { testimonial: null, error: 'Not found.', anonHref: null };
		}
		if (!res.ok) {
			return { testimonial: null, error: `HTTP ${res.status}`, anonHref: null };
		}
		const data = (await res.json()) as TestimonialPublic;
		return {
			testimonial: data,
			error: null,
			anonHref: `${base}/accounts/google/login/?next=${encodeURIComponent(url.pathname)}`,
		};
	} catch (e) {
		return {
			testimonial: null,
			error: e instanceof Error ? e.message : 'Could not load testimonial.',
			anonHref: null,
		};
	}
}