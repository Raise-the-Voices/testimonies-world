<script lang="ts">
	import { base } from '$app/paths';
	import { user } from '$lib/session';
	import TestimonialForm from '$lib/TestimonialForm.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	let currentUser = $derived(data.user ?? $user);
</script>

<svelte:head>
	<title>New testimonial — Testimonies.world</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="new-testimonial-page">
	<header class="page-header">
		<a href="{base}/testimonials" class="back-link">← Back to testimonials</a>
		<h1>New testimonial</h1>
		<p class="page-subtitle">
			{#if !currentUser.authenticated}
				You need to be signed in to submit a testimonial.
				<a href={data.anonHref}>Sign in with Google</a> to continue.
			{:else if currentUser.is_staff || (currentUser.groups ?? []).includes('Advocate')}
				You can publish directly. The default status is
				<strong>draft</strong>; the buttons below let you submit it for
				review (recommended for transparency) or publish immediately.
			{:else}
				Your draft is private to you until a reviewer approves it. Choose
				<em>Submit for review</em> when you're done — you'll see it
				under "My drafts" with its current status.
			{/if}
		</p>
	</header>

	<TestimonialForm
		mode="create"
		pageUser={currentUser}
		anonHref={data.anonHref}
	/>
</div>

<style>
	.new-testimonial-page {
		max-width: var(--max-w-prose);
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}
	.page-header h1 {
		margin: 0.25rem 0 0.5rem 0;
		color: var(--color-primary);
	}
	.page-subtitle {
		margin: 0;
		color: var(--color-text-muted);
		max-width: var(--max-w-prose);
		line-height: 1.55;
	}
	.back-link {
		color: var(--color-primary);
		text-decoration: none;
		font-size: 0.9rem;
	}
	.back-link:hover { text-decoration: underline; }
</style>