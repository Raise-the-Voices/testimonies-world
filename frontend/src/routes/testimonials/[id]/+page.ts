// Universal load for a single testimonial. Backend already enforces
// the role-based queryset filter (anonymous → PUBLISHED only), so the
// SSR fetch via orval's `testimonialsRetrieve(id)` is safe to share
// across public + authenticated users. `id` is the canonical detail
// lookup field on the ViewSet; slug-based URLs can be added later
// (would require a `lookup_field = 'slug'` change on the backend).
import { base } from '$app/paths';
import type { TestimonialPublic } from '$lib/api/generated/endpoints.schemas';

export async function load({ fetch, params }) {
	const id = Number(params.id);
	if (!Number.isInteger(id) || id <= 0) {
		return { testimonial: null, error: 'Invalid testimonial id.' };
	}
	try {
		const res = await fetch(`${base}/api/testimonials/${id}/`);
		if (res.status === 404) {
			return { testimonial: null, error: 'Not found.' };
		}
		if (!res.ok) {
			return { testimonial: null, error: `HTTP ${res.status}` };
		}
		const data = (await res.json()) as { data?: TestimonialPublic };
		return { testimonial: data.data ?? null, error: null };
	} catch (e) {
		return {
			testimonial: null,
			error: e instanceof Error ? e.message : 'Could not load testimonial.',
		};
	}
}
