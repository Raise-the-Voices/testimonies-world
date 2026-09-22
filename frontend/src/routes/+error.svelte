<!--
  Top-level SvelteKit error boundary. Catches anything a child
  load() / +layout.ts / server route throws and renders an
  ErrorCard with retry + back actions instead of SvelteKit's
  bare default page.

  Why this exists:
    - SSR failures (e.g. backend 502 / 5xx cascading into the
      layout session load) previously surfaced as a plain
      "500 Internal Error" page with no recovery path.
    - On the demo VM we saw the SvelteKit Node upstream
      intermittently 502; nginx shows a hard error and the
      user's only recourse was a hard refresh.
    - With this page, SSR failures render a styled card with
      "Try again" (re-runs the load chain) and "Back to home"
      (escape hatch). Even when the server is down the page
      never presents an unwinnable error state.
-->
<script lang="ts">
	import { page } from '$app/stores';
	import { base } from '$app/paths';
	import { invalidateAll } from '$app/navigation';
	import ErrorCard from '$lib/ErrorCard.svelte';

	let { error }: { error: { message?: string } } = $props();

	// SvelteKit attaches a `status` to the page store on error.
	// 5xx → likely transient (retry makes sense). 4xx → unlikely to
	// resolve on retry; show back-link + skip retry button so the
	// user doesn't bang their head against a permanent failure.
	const status = $derived(($page.status as number) ?? 500);
	const isTransient = $derived(status >= 500);

	const title = $derived(
		status === 404
			? "We couldn't find that page"
			: status === 403
				? "You don't have access to this page"
				: status === 401
					? 'Please sign in to continue'
					: 'Something went wrong loading this page'
	);

	const kind = $derived(
		status === 401 || status === 403
			? 'auth'
			: status >= 500
				? 'server'
				: 'generic'
	);

	const message = $derived(
		error?.message
			? `The page hit an unexpected error: ${error.message}.`
			: 'The page hit an unexpected error.'
	);

	function retry() {
		// Re-run the chain. invalidateAll re-runs every load function
		// for the current page — the closest we can get to a "retry
		// the request" button on a server-rendered page.
		void invalidateAll();
	}
</script>

<svelte:head>
	<title>{title} — Testimonies.world</title>
</svelte:head>

<div class="error-page">
	<ErrorCard
		{title}
		{message}
		{kind}
		retry={isTransient ? retry : undefined}
		back={{ href: `${base}/`, label: 'Back to home' }}
	/>
</div>

<style>
	.error-page {
		max-width: 560px;
		margin: 4rem auto;
		padding: 0 var(--page-px);
	}
</style>