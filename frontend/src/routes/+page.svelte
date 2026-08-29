<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { getStatistics } from '$lib/api';
	import Icon from '$lib/Icon.svelte';
	import StatCounter from '$lib/StatCounter.svelte';
	import HelpCard from '$lib/HelpCard.svelte';
	import SkeletonStatItem from '$lib/SkeletonStatItem.svelte';
	import type { Statistics } from '$lib/types';

	let stats: Statistics | null = $state(null);
	let statsLoading = $state(true);

	// Stat counters, defined as data so the markup is one {#each} loop.
	// `value` is a thunk so we evaluate stats.* lazily (the page must
	// still render when stats is null).
	type Counter = {
		icon: 'cases' | 'globe' | 'lock' | 'help';
		label: string;
		value: () => number;
	};
	const counters: Counter[] = [
		{ icon: 'cases', label: 'Cases', value: () => stats?.total ?? 0 },
		{
			icon: 'globe',
			label: 'Countries',
			value: () => Object.keys(stats?.by_country ?? {}).length,
		},
		{
			icon: 'lock',
			label: 'Detained',
			value: () => stats?.by_status?.detained ?? 0,
		},
		{
			icon: 'help',
			label: 'Disappeared',
			value: () => stats?.by_status?.disappeared ?? 0,
		},
	];

	// Help cards, same pattern.
	type Help = {
		icon: 'pencil' | 'refresh' | 'megaphone' | 'newspaper';
		title: string;
		description: string;
	};
	const helpItems: Help[] = [
		{
			icon: 'pencil',
			title: 'Submit a case',
			description:
				'If you know of someone facing oppression, log in and submit their story.',
		},
		{
			icon: 'refresh',
			title: 'Update existing cases',
			description: 'Add new reports with updated information as situations evolve.',
		},
		{
			icon: 'megaphone',
			title: 'Advocate',
			description:
				'Contact us to join as a casework volunteer and amplify documented cases.',
		},
		{
			icon: 'newspaper',
			title: 'Journalists and NGOs',
			description: 'Data exports available upon request for reporting and analysis.',
		},
	];

	onMount(async () => {
		try {
			stats = await getStatistics();
		} catch {
			/* empty db is fine */
		} finally {
			statsLoading = false;
		}
	});
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
	{:else if stats && stats.total > 0}
		<section class="stats-bar" aria-label="Platform statistics">
			{#each counters as c (c.label)}
				<StatCounter icon={c.icon} value={c.value()} label={c.label} />
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
				<Icon name="cases" size={18} />
				Browse Cases
				<Icon name="arrow-right" size={18} />
			</a>
			<a href="{base}/statistics" class="btn btn-secondary btn-lg">
				<Icon name="chart-bar" size={18} />
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
		<div class="help-grid">
			{#each helpItems as item, i (item.title)}
				<HelpCard
					icon={item.icon}
					title={item.title}
					description={item.description}
					delayMs={100 + i * 50}
				/>
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

	/* === 1. Stats counters — unified floating bar === */
	.stats-bar {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		box-shadow: var(--shadow-card);
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: var(--gap-card);
		padding: 1.25rem 1.5rem;
		animation: fadeSlideUp 0.4s ease both;
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

	/* === 3. How to help grid === */
	.section-header {
		text-align: center;
		margin-bottom: 1.25rem;
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
	.help-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: var(--gap-card);
	}

	/* Responsive */
	@media (max-width: 900px) {
		.stats-bar {
			grid-template-columns: repeat(2, 1fr);
		}
		.help-grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}
	@media (max-width: 560px) {
		.stats-bar {
			grid-template-columns: 1fr;
		}
		.help-grid {
			grid-template-columns: 1fr;
		}
		.hero-card {
			padding: 1.5rem 1.25rem;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.stats-bar,
		.hero-card {
			animation: none;
		}
		.btn-lg:hover {
			transform: none;
		}
	}
</style>
