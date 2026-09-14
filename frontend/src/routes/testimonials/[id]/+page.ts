// Universal load for a single testimonial. Backend already enforces
// the role-based queryset filter (anonymous → PUBLISHED only), so the
// SSR fetch via orval's `testimonialsRetrieve(id)` is safe to share
// across public + authenticated users. `id` is the canonical detail
// lookup field on the ViewSet; slug-based URLs can be added later
// (would require a `lookup_field = 'slug'` change on the backend).
import { base } from '$app/paths';
import { asTestimonialBody } from '$lib/api/drfCompat';

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
		// DRF returns the serializer data DIRECTLY (not wrapped in
		// {data, status} the way the orval-generated TS type assumes).
		// asTestimonialBody() in $lib/api/drfCompat.ts handles the
		// shape assumption in one place — see that module for the
		// full rationale.
		const data = asTestimonialBody(await res.json());
		return { testimonial: data, error: null };
	} catch (e) {
		return {
			testimonial: null,
			error: e instanceof Error ? e.message : 'Could not load testimonial.',
		};
	}
}
