// Universal load for the public testimonials list. SSR-renders with
// published testimonials so the first paint has content (no skeleton
// flash on hard refresh). Authenticated users get the same payload
// here; the page itself shows role-aware "My drafts" and "Review
// queue" tabs that fetch through authenticated APIs on the client
// (those tabs' content isn't in the public surface anyway, so SSR
// can't pre-fill them — they fetch on mount + on tab activation).
import { base } from '$app/paths';
import type { Paginated } from '$lib/types';
import type { TestimonialPublic } from '$lib/api/generated/endpoints.schemas';

export async function load({ fetch, url }) {
	const searchParams = url.searchParams;
	const params: Record<string, string> = {};
	// Sort newest published first as a sane default; the page UI lets
	// users change ordering, but those changes are client-side only
	// (no need to round-trip through SSR).
	const ordering = searchParams.get('ordering');
	if (ordering) params.ordering = ordering;
	const page = searchParams.get('page');
	if (page) params.page = page;

	try {
		const qs = new URLSearchParams(params).toString();
		const res = await fetch(`${base}/api/testimonials/${qs ? '?' + qs : ''}`);
		const data = res.ok
			? ((await res.json()) as Paginated<TestimonialPublic>)
			: ({ results: [], count: 0, next: null, previous: null } as unknown as Paginated<TestimonialPublic>);
		return {
			testimonials: data.results ?? [],
			count: data.count ?? 0,
			error: res.ok ? null : `HTTP ${res.status}`,
		};
	} catch (e) {
		return {
			testimonials: [],
			count: 0,
			error: e instanceof Error ? e.message : 'Could not load testimonials.',
		};
	}
}
