<script lang="ts">
	import { base } from '$app/paths';
	import { user } from '$lib/session';
	import TestimonialForm from '$lib/TestimonialForm.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	let currentUser = $derived(data.user ?? $user);
	const t = $derived(data.testimonial);

	const locked = $derived(
		!!t && (t.status === 'published' || t.status === 'archived'),
	);
</script>

<svelte:head>
	<title>Edit testimonial — Testimonies.world</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="edit-testimonial-page">
	<header class="page-header">
		<a href="{base}/testimonials/{t?.id}" class="back-link">← Back to testimonial</a>
		<h1>Edit testimonial</h1>
		{#if locked}
			<p class="page-warning" role="alert">
				This testimonial is {t?.status} and cannot be edited. The
				state machine is the only way forward — contact an Advocate if
				a correction is required.
			</p>
		{:else if data.error}
			<p class="page-warning" role="alert">{data.error}</p>
		{/if}
	</header>

	{#if !locked && t}
		<TestimonialForm
			mode="edit"
			testimonial={t}
			pageUser={currentUser}
			anonHref={data.anonHref}
		/>
	{/if}
</div>

<style>
	.edit-testimonial-page {
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
	.back-link {
		color: var(--color-primary);
		text-decoration: none;
		font-size: 0.9rem;
	}
	.back-link:hover { text-decoration: underline; }
	.page-warning {
		padding: 0.85rem 1rem;
		border: 1px solid var(--color-danger);
		border-left: 3px solid var(--color-danger);
		border-radius: var(--radius-card);
		color: var(--color-danger);
		background: #fef2f2;
	}
</style>