<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { getStatistics } from '$lib/api';

	let stats: any = $state(null);

	onMount(async () => {
		try {
			stats = await getStatistics();
		} catch { /* empty db is fine */ }
	});
</script>

<svelte:head>
	<title>Cases — RaisetheVoices.org</title>
</svelte:head>

<div class="home">
	{#if stats && stats.total > 0}
		<div class="stats-row">
			<div class="stat-item">
				<span class="stat-number">{stats.total}</span>
				<span class="stat-label">Cases</span>
			</div>
			<div class="stat-item">
				<span class="stat-number">{Object.keys(stats.by_country).length}</span>
				<span class="stat-label">Countries</span>
			</div>
			<div class="stat-item">
				<span class="stat-number">{stats.by_status?.detained || 0}</span>
				<span class="stat-label">Detained</span>
			</div>
			<div class="stat-item">
				<span class="stat-number">{stats.by_status?.disappeared || 0}</span>
				<span class="stat-label">Disappeared</span>
			</div>
		</div>
	{/if}

	<p>
		Documenting cases of people facing oppression — enforced disappearances,
		arbitrary detention, restricted rights, statelessness, and other situations where
		people cannot turn to their own government for protection.
	</p>
	<p>
		We anchor reports, track cases, and coordinate advocacy so that no one is forgotten.
		Reports can be entered even in uncertain or incomplete form — the goal is to create
		a record that can grow over time as more information becomes available.
	</p>
	<p>
		Based on the principle that freedom and due process are universal human rights,
		regardless of birthplace, race, religion, gender, or language.
	</p>

	<div class="actions">
		<a href="{base}/persons" class="btn">Browse Cases</a>
		<a href="{base}/statistics" class="btn btn-secondary">View Statistics</a>
	</div>

	<div class="how-to-help">
		<h2>How to help</h2>
		<ul>
			<li><strong>Submit a case</strong> — if you know of someone facing oppression, log in and submit their story</li>
			<li><strong>Update existing cases</strong> — add new reports with updated information</li>
			<li><strong>Advocate</strong> — contact us to join as a casework volunteer</li>
			<li><strong>Journalists and NGOs</strong> — data exports available upon request</li>
		</ul>
	</div>
</div>

<style>
	.home {
		width: 60%;
		margin: 0 auto;
	}
	.home p {
		font-size: 1.1rem;
		letter-spacing: 0.01rem;
		text-align: justify;
		margin-bottom: 1rem;
	}
	.stats-row {
		display: flex;
		gap: 0.5rem;
		justify-content: center;
		flex-wrap: wrap;
		margin-bottom: 1.5rem;
	}
	.stat-item {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border);
		border-radius: 3px;
		padding: 0.4rem 0.8rem;
		text-align: center;
	}
	.stat-number {
		font-size: 1.1rem;
		font-weight: 700;
		color: var(--color-primary);
	}
	.stat-label {
		font-size: 0.75rem;
		color: var(--color-text-muted);
		margin-left: 0.3rem;
	}
	.actions {
		text-align: center;
		display: flex;
		gap: 1rem;
		justify-content: center;
		margin: 1.5rem 0;
	}
	.how-to-help {
		margin-top: 1.5rem;
	}
	.how-to-help ul {
		list-style: disc;
		padding-left: 1.5rem;
	}
	.how-to-help li {
		margin-bottom: 0.5rem;
	}

	@media (max-width: 800px) {
		.home {
			width: 100%;
		}
	}
</style>
