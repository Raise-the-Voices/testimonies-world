<script lang="ts">
	import { base } from '$app/paths';
	import { getStatistics } from '$lib/api';
	import Icon from '$lib/Icon.svelte';
	import SkeletonStatItem from '$lib/SkeletonStatItem.svelte';
	import type { PageData } from './$types';
	import type { Statistics } from '$lib/types';

	let { data }: { data: PageData } = $props();

	// Initial paint comes from +page.ts universal load.
	let stats: Statistics | null = $state(data.statistics);
	let statsLoading = $state(false);
	let statsError: string | null = $state(data.error);

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
			statsError = e instanceof Error ? e.message : 'Could not load statistics.';
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
</svelte:head>

<div class="home">
	{#if statsLoading}
		<section class="stats-bar" aria-busy="true" aria-label="Loading platform statistics">
			{#each counters as c (c.label)}
				<SkeletonStatItem />
			{/each}
		</section>
	{:else if statsError}
		<section class="stats-bar stats-bar-error" role="alert" aria-label="Statistics unavailable">
			<div class="stats-error-content">
				<Icon name="help" size={18} />
				<span>Could not load platform statistics. <button type="button" class="stats-retry" onclick={loadStats}>Retry</button></span>
			</div>
		</section>
	{:else if stats && stats.total > 0}
		<section class="stats-bar" aria-label="Platform statistics">
			{#each counters as c, i (c.label)}
				{#if i > 0}<span class="stat-divider" aria-hidden="true"></span>{/if}
				<div class="stat-item">
					<span class="stat-number">{c.value()}</span>
					<span class="stat-label">{c.label}</span>
				</div>
			{/each}
		</section>
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

	/* === 1. Stats bar — inline typographic row (no icons, no card grid) === */
	.stats-bar {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		box-shadow: var(--shadow-card);
		padding: 1.1rem 1.5rem;
		display: flex;
		align-items: baseline;
		justify-content: space-around;
		gap: 1rem;
		flex-wrap: wrap;
		animation: fadeSlideUp 0.4s ease both;
	}
	.stat-item {
		display: flex;
		flex-direction: column;
		align-items: center;
		min-width: 0;
		padding: 0.25rem 0.5rem;
	}
	.stat-number {
		font-size: 1.5rem;
		font-weight: 700;
		color: var(--color-primary);
		line-height: 1.1;
		font-variant-numeric: tabular-nums;
	}
	.stat-label {
		font-size: 0.78rem;
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		margin-top: 0.15rem;
	}
	.stat-divider {
		width: 1px;
		align-self: stretch;
		background: var(--color-border-light);
	}

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
		margin-bottom: 1.5rem;
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
		padding: 1.25rem 1.75rem;
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
		.stats-bar {
			flex-direction: column;
			align-items: stretch;
			gap: 0.75rem;
		}
		.stat-divider {
			width: auto;
			height: 1px;
		}
		.stat-item {
			flex-direction: row;
			justify-content: space-between;
			padding: 0.15rem 0.25rem;
		}
		.hero-card {
			padding: 1.5rem 1.25rem;
		}
		.help-list {
			padding: 1rem 1.25rem;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.stats-bar,
		.hero-card,
		.help-item {
			animation: none;
		}
		.btn-lg:hover {
			transform: none;
		}
	}

	.stats-bar-error {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-left: 3px solid var(--color-danger);
	}
	.stats-error-content {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		color: var(--color-text-muted);
		font-size: 0.9rem;
		padding: 0.5rem 0;
	}
	.stats-error-content :global(svg) {
		color: var(--color-danger);
	}
	.stats-retry {
		background: transparent;
		border: none;
		color: var(--color-primary);
		font-weight: 600;
		text-decoration: underline;
		cursor: pointer;
		padding: 0;
		font: inherit;
	}
	.stats-retry:hover {
		color: var(--color-primary-light);
	}
	.stats-retry:focus-visible {
		outline: 2px solid var(--color-primary);
		outline-offset: 2px;
		border-radius: 3px;
	}
</style>
