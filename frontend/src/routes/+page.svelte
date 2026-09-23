<script lang="ts">
	import { untrack } from 'svelte';
	import { base } from '$app/paths';
	import { getStatistics } from '$lib/api';
	import { handleApiError } from '$lib/api/handleError';
	import Icon from '$lib/Icon.svelte';
	import StatsBar from '$lib/StatsBar.svelte';
	import type { PageData } from './$types';
	import type { Statistics } from '$lib/types';

	let { data }: { data: PageData } = $props();

	// Initial paint comes from +page.ts universal load.
	let stats: Statistics | null = $state(untrack(() => data.statistics));
	let statsLoading = $state(false);
	let statsError: string | null = $state(untrack(() => data.error));

	// Stat counters, defined as data so the markup is one {#each} loop.
	// `value` is a thunk so we evaluate stats.* lazily (the page must
	// still render when stats is null).
	type Counter = {
		label: string;
		value: () => number;
	};
	const counters: Counter[] = [
		{ label: 'Cases', value: () => stats?.total ?? 0 },
		{
			label: 'Countries',
			value: () => Object.keys(stats?.by_country ?? {}).length,
		},
		{
			label: 'Detained',
			value: () => stats?.by_status?.detained ?? 0,
		},
		{
			label: 'Disappeared',
			value: () => stats?.by_status?.disappeared ?? 0,
		},
	];

	// Help items — same data as before, just rendered as prose
	// paragraphs (no icon cards) for a less AI-grid look.
	type Help = {
		title: string;
		description: string;
	};
	const helpItems: Help[] = [
		{
			title: 'Submit a case',
			description:
				'If you know of someone facing oppression, log in and submit their story.',
		},
		{
			title: 'Update existing cases',
			description: 'Add new reports with updated information as situations evolve.',
		},
		{
			title: 'Advocate',
			description:
				'Contact us to join as a casework volunteer and amplify documented cases.',
		},
		{
			title: 'Journalists and NGOs',
			description: 'Data exports available upon request for reporting and analysis.',
		},
	];

	async function loadStats() {
		statsLoading = true;
		statsError = null;
		try {
			stats = await getStatistics();
		} catch (e) {
			// Inline UI keeps its short, friendly copy. The toast
			// surfaces the actual server/network reason for diagnosis
			// — visible even if the user has scrolled past the
			// stats-bar.
			statsError = 'Could not load platform statistics.';
			handleApiError(e);
		} finally {
			statsLoading = false;
		}
	}

	// Initial paint comes from +page.ts universal load; no onMount refetch
	// needed for the landing page (read-only). loadStats() is kept available
	// for the Retry button.
</script>

<svelte:head>
	<title>Cases — RaisetheVoices.org</title>
	<meta
		name="description"
		content="Document and amplify the stories of people facing enforced disappearances, arbitrary detention, and statelessness. Person-centered casework for human rights volunteers."
	/>
	<meta property="og:title" content="Cases — Testimonies.world" />
	<meta
		property="og:description"
		content="Document and amplify the stories of people facing enforced disappearances, arbitrary detention, and statelessness."
	/>
	<meta property="og:type" content="website" />
</svelte:head>

<div class="home">
	<h1 class="sr-only">Testimonies.world — person-centered casework for people facing oppression</h1>
	{#if statsLoading || statsError || (stats && stats.total > 0)}
		<StatsBar
			items={counters}
			loading={statsLoading}
			error={statsError}
			onRetry={loadStats}
		/>
	{/if}

	<section class="hero-card">
		<div class="hero-text">
			<p>
				Documenting cases of people facing oppression — enforced disappearances, arbitrary
				detention, restricted rights, statelessness, and other situations where people cannot
				turn to their own government for protection.
			</p>
			<p>
				We anchor reports, track cases, and coordinate advocacy so that no one is forgotten.
				Reports can be entered even in uncertain or incomplete form — the goal is to create a
				record that can grow over time as more information becomes available.
			</p>
			<p>
				Based on the principle that freedom and due process are universal human rights,
				regardless of birthplace, race, religion, gender, or language.
			</p>
		</div>
		<div class="actions">
			<a href="{base}/persons" class="btn btn-primary btn-lg">
				Browse Cases
				<Icon name="arrow-right" size={18} />
			</a>
			<a href="{base}/statistics" class="btn btn-secondary btn-lg">
				View Statistics
			</a>
		</div>
	</section>

	<section class="help-section">
		<header class="section-header">
			<h2 class="section-title">How to help</h2>
			<p class="section-subtitle">
				Four ways to contribute to the record of human rights documentation.
			</p>
		</header>
		<div class="help-list">
			{#each helpItems as item, i (item.title)}
				{#if i > 0}<hr class="help-rule" aria-hidden="true" />{/if}
				<div class="help-item">
					<h3>{item.title}</h3>
					<p>{item.description}</p>
				</div>
			{/each}
		</div>
	</section>
</div>

<style>
	.home {
		width: 100%;
		max-width: var(--max-w-page);
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 2rem;
	}

	/* === 1. Stats bar — see $lib/StatsBar.svelte === */

	/* === 2. Hero card === */
	.hero-card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		box-shadow: var(--shadow-card);
		padding: 2.25rem 2rem;
		text-align: center;
		animation: fadeSlideUp 0.4s ease both;
		animation-delay: 0.05s;
	}
	.hero-text {
		max-width: var(--max-w-prose);
		margin: 0 auto;
	}
	.hero-text p {
		font-size: 1.05rem;
		line-height: 1.7;
		margin: 0 0 1rem 0;
		color: var(--color-text);
	}
	.hero-text p:last-child {
		margin-bottom: 0;
	}

	.actions {
		display: flex;
		gap: 0.75rem;
		justify-content: center;
		flex-wrap: wrap;
		margin-top: 1.5rem;
	}
	.btn-lg {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.7rem 1.4rem;
		font-size: 0.95rem;
		font-weight: 600;
		border-radius: var(--radius-card);
		min-height: 44px;
		transition:
			background var(--transition-card),
			color var(--transition-card),
			border-color var(--transition-card),
			transform var(--transition-card),
			box-shadow var(--transition-card);
	}
	.btn-lg :global(svg) {
		width: 18px;
		height: 18px;
	}
	.btn-lg:hover {
		transform: translateY(-1px);
		box-shadow: var(--shadow-card-hover);
	}
	.btn-lg :global(svg:last-child) {
		transition: transform var(--transition-card);
	}
	.btn-lg:hover :global(svg:last-child) {
		transform: translateX(3px);
	}

	/* === 3. How to help — prose paragraphs separated by hairline rules === */
	.section-header {
		text-align: center;
		margin-bottom: var(--space-section);
	}
	.section-title {
		font-size: 1.4rem;
		font-weight: 700;
		margin: 0 0 0.35rem 0;
		color: var(--color-text);
	}
	.section-subtitle {
		color: var(--color-text-muted);
		margin: 0;
		font-size: 0.95rem;
	}
	.help-list {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		box-shadow: var(--shadow-card);
		padding: var(--card-padding-lg);
		max-width: var(--max-w-prose);
		margin: 0 auto;
	}
	.help-rule {
		border: 0;
		border-top: 1px solid var(--color-border-light);
		margin: 1.1rem 0;
	}
	.help-item {
		animation: fadeSlideUp 0.4s ease both;
	}
	.help-item h3 {
		font-size: 1.05rem;
		font-weight: 700;
		margin: 0 0 0.4rem 0;
		color: var(--color-text);
	}
	.help-item p {
		font-size: 0.95rem;
		line-height: 1.6;
		color: var(--color-text-muted);
		margin: 0;
	}

	/* Responsive */
	@media (max-width: 700px) {
		.hero-card {
			padding: 1.5rem 1.25rem;
		}
		.help-list {
			padding: 1rem 1.25rem;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.hero-card,
		.help-item {
			animation: none;
		}
		.btn-lg:hover {
			transform: none;
		}
	}
</style>
