<script lang="ts">
	import { base } from '$app/paths';
	import { user } from '$lib/session';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	let currentUser = $derived(data.user ?? $user);

	const t = $derived(data.testimonial);

	function formatDate(iso: string | null | undefined): string {
		if (!iso) return '';
		return new Date(iso).toLocaleDateString(undefined, {
			year: 'numeric',
			month: 'long',
			day: 'numeric',
		});
	}
</script>

<svelte:head>
	{#if t}
		<title>{t.title || 'Testimonial'} — Testimonies.world</title>
		<meta name="description" content={t.summary || 'A documented testimonial.'} />
	{:else}
		<title>Testimonial — Testimonies.world</title>
	{/if}
</svelte:head>

<div class="testimonial-detail">
	<a href="{base}/testimonials" class="back-link">← Back to testimonials</a>

	{#if data.error || !t}
		<div class="error-state" role="alert">
			<h1>Testimonial not available</h1>
			<p>{data.error ?? 'This testimonial could not be loaded.'}</p>
			<a class="btn btn-secondary" href="{base}/testimonials">Return to list</a>
		</div>
	{:else}
		<article class="testimonial-card-detail">
			<header class="testimonial-card-header">
				{#if t.country || t.public_location_display}
					<p class="testimonial-card-location">
						{t.public_location_display || t.country}{#if t.country && t.region && t.region !== t.public_location_display}, {t.region}{/if}
					</p>
				{/if}
				<h1>{t.title || 'Untitled testimonial'}</h1>
				{#if t.incident_date}
					<p class="testimonial-card-date">
						Incident on
						<time datetime={t.incident_date}>{formatDate(t.incident_date)}</time>
					</p>
				{/if}
			</header>

			{#if t.summary}
				<section class="testimonial-section">
					<h2>Summary</h2>
					<p class="testimonial-summary">{t.summary}</p>
				</section>
			{/if}

			{#if t.narrative}
				<section class="testimonial-section">
					<h2>Narrative</h2>
					<p class="testimonial-narrative">{t.narrative}</p>
				</section>
			{/if}

			{#if t.outcome}
				<section class="testimonial-section">
					<h2>Outcome</h2>
					<p class="testimonial-outcome">{t.outcome}</p>
				</section>
			{/if}

			<dl class="testimonial-meta">
				{#if t.source_visible && t.public_source_label}
					<dt>Source</dt>
					<dd>{t.public_source_label}</dd>
				{/if}
				{#if t.verification_level}
					<dt>Verification</dt>
					<dd class="capitalize">{t.verification_level.replace(/level_/g, '').replace(/_/g, ' ')}</dd>
				{/if}
				{#if t.published_at}
					<dt>Published</dt>
					<dd>{formatDate(t.published_at)}</dd>
				{/if}
				{#if t.language && t.language !== 'en'}
					<dt>Language</dt>
					<dd class="uppercase">{t.language}</dd>
				{/if}
				{#if t.tags && t.tags.length > 0}
					<dt>Tags</dt>
					<dd>
						<ul class="testimonial-tags-list">
							{#each t.tags as tag (tag.id)}
								<li class="testimonial-tag">{tag.name}</li>
							{/each}
						</ul>
					</dd>
				{/if}
			</dl>

			{#if t.family_protected || t.contact_protected}
				<aside class="testimonial-privacy" aria-label="Privacy protections in effect">
					<h3>Privacy protections</h3>
					<ul>
						{#if t.family_protected}
							<li>Family member identities are replaced with role labels throughout.</li>
						{/if}
						{#if t.contact_protected}
							<li>Contact details are withheld.</li>
						{/if}
					</ul>
				</aside>
			{/if}
		</article>
	{/if}
</div>

<style>
	.testimonial-detail {
		max-width: var(--max-w-prose);
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.back-link {
		color: var(--color-primary);
		text-decoration: none;
		font-size: 0.9rem;
	}
	.back-link:hover {
		text-decoration: underline;
	}

	.testimonial-card-detail {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-card-lg);
		padding: clamp(1.5rem, 4vw, 2.75rem);
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.testimonial-card-header h1 {
		margin: 0.25rem 0 0.5rem 0;
		color: var(--color-primary);
		font-size: clamp(1.75rem, 4vw, 2.5rem);
		line-height: 1.2;
	}
	.testimonial-card-location {
		margin: 0;
		text-transform: uppercase;
		letter-spacing: 0.08rem;
		font-size: 0.78rem;
		color: var(--color-text-muted);
	}
	.testimonial-card-date {
		margin: 0;
		font-size: 0.92rem;
		color: var(--color-text-muted);
	}

	.testimonial-section h2 {
		margin: 0 0 0.5rem 0;
		font-size: 0.78rem;
		text-transform: uppercase;
		letter-spacing: 0.08rem;
		color: var(--color-text-muted);
	}
	.testimonial-summary {
		font-size: 1.1rem;
		color: var(--color-text);
		line-height: 1.55;
	}
	.testimonial-narrative,
	.testimonial-outcome {
		font-size: 1rem;
		color: var(--color-text);
		line-height: 1.7;
		white-space: pre-line;
	}

	.testimonial-meta {
		display: grid;
		grid-template-columns: max-content 1fr;
		gap: 0.5rem 1rem;
		padding-top: 1rem;
		border-top: 1px solid var(--color-border-subtle);
	}
	.testimonial-meta dt {
		font-size: 0.72rem;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		color: var(--color-text-muted);
		font-weight: 700;
		align-self: center;
	}
	.testimonial-meta dd {
		margin: 0;
		color: var(--color-text);
		font-size: 0.95rem;
	}
	.capitalize {
		text-transform: capitalize;
	}
	.uppercase {
		text-transform: uppercase;
	}
	.testimonial-tags-list {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.testimonial-tag {
		padding: 0.2rem 0.6rem;
		background: var(--color-section-bg);
		color: var(--color-primary);
		border-radius: 999px;
		font-size: 0.78rem;
		font-weight: 700;
	}

	.testimonial-privacy {
		background: var(--color-section-bg);
		border-left: 3px solid var(--color-primary-light);
		border-radius: var(--radius-card);
		padding: 1rem 1.25rem;
	}
	.testimonial-privacy h3 {
		margin: 0 0 0.5rem 0;
		font-size: 0.78rem;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		color: var(--color-primary);
	}
	.testimonial-privacy ul {
		margin: 0;
		padding-left: 1.25rem;
		color: var(--color-text);
		font-size: 0.9rem;
	}

	.error-state {
		padding: 2rem 1.5rem;
		text-align: center;
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-left: 3px solid var(--color-danger);
		border-radius: var(--radius-card);
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		align-items: center;
	}
</style>
