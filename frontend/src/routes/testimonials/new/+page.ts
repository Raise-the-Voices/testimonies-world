// Universal load for /testimonials/new. Gated server-side (the
// serializer / view requires authentication for POST anyway), but
// we 404 in SSR for anonymous viewers so the navigation doesn't
// flash an empty form before the auth check rejects it. We don't
// redirect — direct nav shouldn't bounce through /accounts/… for
// a form the user wants to fill out, and the page itself will show
// a "please sign in" panel.
import { base } from '$app/paths';
import type { PageData } from './$types';

export async function load({ fetch, url }) {
	const initRes = await fetch(`${base}/api/testimonial-tags/`);
	const tags = initRes.ok ? ((await initRes.json()) as { results?: unknown[] }).results ?? [] : [];
	return {
		anonHref: `${base}/accounts/google/login/?next=${encodeURIComponent(url.pathname)}`,
		initTags: tags,
	};
}
