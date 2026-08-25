<script lang="ts">
	import { onMount } from 'svelte';
	import { getStatistics } from '$lib/api';

	let stats: any = $state(null);
	let loading = $state(true);

	const statusLabels: Record<string, string> = {
		detained: 'Detained',
		disappeared: 'Disappeared',
		restricted_movement: 'Restricted Movement',
		released: 'Released',
		deceased: 'Deceased',
		unknown: 'Unknown',
		stateless: 'Stateless',
		rights_restricted: 'Rights Restricted',
	};

	const medicalLabels: Record<string, string> = {
		unknown: 'Unknown',
		healthy: 'Healthy',
		health_concerns: 'Health Concerns',
		critical: 'Critical',
		deceased: 'Deceased',
	};

	const total = $derived(stats?.total ?? 0);

	/**
	 * The backend can return stats.by_country in one of two shapes:
	 *   1) Array of tuples from `_aggregate_countries()` —
	 *      [['Pakistan', 60], ['India', 47], ...]
	 *   2) Array of objects from `PersonViewSet.countries()` —
	 *      [{country: 'Pakistan', count: 60}, ...]
	 * The previous version called Object.entries() on shape #1, which
	 * produced [[0, ['Pakistan', 60]], ...] and rendered "0 / Pakistan,60".
	 * Normalize both into a single [label, count] tuple shape.
	 */
	function normalizeCountries(byCountry: any): [string, number][] {
		if (!byCountry) return [];
		if (!Array.isArray(byCountry)) {
			return Object.entries(byCountry) as [string, number][];
		}
		const first = byCountry[0];
		if (first && typeof first === 'object' && !Array.isArray(first)) {
			return byCountry.map((row: any) => [row.country ?? row.name ?? '', Number(row.count)]);
		}
		return byCountry.map((row: [string, number]) => [row[0], Number(row[1])]);
	}

	const countries = $derived(
		normalizeCountries(stats?.by_country).sort((a, b) => b[1] - a[1])
	);

	const sortedByStatus = $derived(
		Object.entries(stats?.by_status ?? {}).sort(
			(a, b) => (b[1] as number) - (a[1] as number)
		)
	);

	const sortedByMedical = $derived(
		Object.entries(stats?.by_medical ?? {}).sort(
			(a, b) => (b[1] as number) - (a[1] as number)
		)
	);

	const sortedCategories = $derived(
		((stats?.by_category ?? []) as any[])
			.filter((c) => c.count > 0)
			.sort((a, b) => b.count - a.count)
	);

	function pct(n: number): number {
		if (total <= 0) return 0;
		return Math.min(100, Math.round((n / total) * 100));
	}

	onMount(async () => {
		try {
			stats = await getStatistics();
		} catch (e) {
			console.error(e);
		}
		loading = false;
	});
</script>

<svelte:head>
	<title>Statistics — Testimonies.world</title>
</svelte:head>

<div class="statistics-page">
	<header class="page-header">
		<div class="page-header-text">
			<h1>Statistics</h1>
			<p class="page-subtitle">
				Aggregate breakdown of documented cases across status, geography, category, and
				medical condition.
			</p>
		</div>
		{#if !loading && stats}
			<div class="total-badge" aria-label="{stats.total} total cases">
				<span class="total-number">{stats.total}</span>
				<span class="total-label">Total cases</span>
			</div>
		{/if}
	</header>

	{#if loading}
		<p class="muted">Loading…</p>
	{:else if stats}
		<div class="stats-grid">
			<!-- By Status -->
			<article class="stat-card">
				<header class="stat-card-header">
					<h2>By Status</h2>
					<span class="stat-card-meta">{sortedByStatus.length} categories</span>
				</header>
				{#if sortedByStatus.length > 0}
					<ul class="stat-list">
						{#each sortedByStatus as [key, count] (key)}
							<li class="stat-row">
								<span class="stat-row-label">{statusLabels[key] || key}</span>
								<span class="stat-row-count" aria-label="{count} cases">{count}</span>
								<span class="stat-row-bar" aria-hidden="true">
									<span class="stat-row-bar-fill" style="width: {pct(count as number)}%"></span>
								</span>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="stat-empty">No data yet</p>
				{/if}
			</article>

			<!-- By Country -->
			<article class="stat-card">
				<header class="stat-card-header">
					<h2>By Country</h2>
					<span class="stat-card-meta">{countries.length} countries</span>
				</header>
				{#if countries.length > 0}
					<ul class="stat-list">
						{#each countries as [country, count] (country)}
							<li class="stat-row">
								<span class="stat-row-label">{country}</span>
								<span class="stat-row-count" aria-label="{count} cases">{count}</span>
								<span class="stat-row-bar" aria-hidden="true">
									<span class="stat-row-bar-fill" style="width: {pct(count)}%"></span>
								</span>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="stat-empty">No data yet</p>
				{/if}
			</article>

			<!-- By Category -->
			<article class="stat-card">
				<header class="stat-card-header">
					<h2>By Category</h2>
					<span class="stat-card-meta">{sortedCategories.length} categories</span>
				</header>
				{#if sortedCategories.length > 0}
					<ul class="stat-list">
						{#each sortedCategories as cat (cat.name)}
							<li class="stat-row">
								<span class="stat-row-label">{cat.name}</span>
								<span class="stat-row-count" aria-label="{cat.count} cases">{cat.count}</span>
								<span class="stat-row-bar" aria-hidden="true">
									<span class="stat-row-bar-fill" style="width: {pct(cat.count)}%"></span>
								</span>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="stat-empty">No data yet</p>
				{/if}
			</article>

			<!-- By Medical Status -->
			<article class="stat-card">
				<header class="stat-card-header">
					<h2>By Medical Status</h2>
					<span class="stat-card-meta">{sortedByMedical.length} statuses</span>
				</header>
				{#if sortedByMedical.length > 0}
					<ul class="stat-list">
						{#each sortedByMedical as [key, count] (key)}
							<li class="stat-row">
								<span class="stat-row-label">{medicalLabels[key] || key}</span>
								<span class="stat-row-count" aria-label="{count} cases">{count}</span>
								<span class="stat-row-bar" aria-hidden="true">
									<span class="stat-row-bar-fill" style="width: {pct(count as number)}%"></span>
								</span>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="stat-empty">No data yet</p>
				{/if}
			</article>
		</div>
	{/if}
</div>

<style>
	.statistics-page {
		width: 100%;
		max-width: 1100px;
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-end;
		gap: 1rem;
		flex-wrap: wrap;
		padding-bottom: 0.75rem;
		border-bottom: 1px solid var(--color-border-light);
	}
	.page-header-text {
		flex: 1 1 300px;
		min-width: 0;
	}
	.page-header h1 {
		margin: 0 0 0.25rem 0;
		color: var(--color-text);
	}
	.page-subtitle {
		margin: 0;
		color: var(--color-text-muted);
		font-size: 0.95rem;
		max-width: 640px;
		line-height: 1.55;
	}

	.total-badge {
		display: inline-flex;
		align-items: baseline;
		gap: 0.6rem;
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		box-shadow: var(--shadow-card);
		padding: 0.75rem 1.1rem;
	}
	.total-number {
		font-size: 1.85rem;
		font-weight: 700;
		color: var(--color-primary);
		line-height: 1;
	}
	.total-label {
		font-size: 0.78rem;
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.06rem;
	}

	.stats-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 1rem;
	}

	.stat-card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		box-shadow: var(--shadow-card);
		overflow: hidden;
		display: flex;
		flex-direction: column;
		transition:
			box-shadow var(--transition-card),
			transform var(--transition-card);
		animation: fadeSlideUp 0.4s ease both;
	}
	.stat-card:hover {
		box-shadow: var(--shadow-card-hover);
	}
	.stat-card:nth-child(1) {
		animation-delay: 0s;
	}
	.stat-card:nth-child(2) {
		animation-delay: 0.05s;
	}
	.stat-card:nth-child(3) {
		animation-delay: 0.1s;
	}
	.stat-card:nth-child(4) {
		animation-delay: 0.15s;
	}

	.stat-card-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		background: var(--color-primary);
		color: var(--color-text-light);
		padding: 0.7rem 1rem;
	}
	.stat-card-header h2 {
		font-size: 0.95rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		margin: 0;
		color: var(--color-text-light);
	}
	.stat-card-meta {
		font-size: 0.72rem;
		color: rgba(250, 250, 250, 0.85);
		text-transform: uppercase;
		letter-spacing: 0.05rem;
		white-space: nowrap;
	}

	.stat-list {
		list-style: none;
		margin: 0;
		padding: 0.4rem 0;
	}

	.stat-row {
		display: grid;
		grid-template-columns: 1fr auto;
		grid-template-rows: auto auto;
		column-gap: 0.85rem;
		row-gap: 0.3rem;
		align-items: center;
		padding: 0.6rem 1rem;
		border-bottom: 1px solid var(--color-border-light);
		transition: background var(--transition-card);
	}
	.stat-row:last-child {
		border-bottom: none;
	}
	.stat-row:hover {
		background: var(--color-bg);
	}

	.stat-row-label {
		grid-column: 1;
		grid-row: 1;
		font-size: 0.92rem;
		color: var(--color-text);
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.stat-row-count {
		grid-column: 2;
		grid-row: 1;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 2.4rem;
		height: 1.7rem;
		padding: 0 0.55rem;
		border-radius: 999px;
		background: rgba(37, 100, 106, 0.1);
		color: var(--color-primary);
		font-size: 0.85rem;
		font-weight: 700;
		line-height: 1;
		flex: 0 0 auto;
	}
	.stat-row-bar {
		grid-column: 1 / -1;
		grid-row: 2;
		display: block;
		height: 4px;
		border-radius: 999px;
		background: var(--color-bg);
		overflow: hidden;
	}
	.stat-row-bar-fill {
		display: block;
		height: 100%;
		background: linear-gradient(90deg, var(--color-primary), var(--color-primary-light));
		border-radius: 999px;
		transition: width 0.4s ease;
	}

	.stat-empty {
		margin: 0;
		padding: 1rem;
		color: var(--color-text-muted);
		font-size: 0.85rem;
		text-align: center;
	}

	@media (max-width: 700px) {
		.stats-grid {
			grid-template-columns: 1fr;
		}
		.page-header {
			flex-direction: column;
			align-items: stretch;
		}
		.total-badge {
			align-self: flex-start;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.stat-card {
			animation: none;
		}
		.stat-row-bar-fill {
			transition: none;
		}
	}
</style>