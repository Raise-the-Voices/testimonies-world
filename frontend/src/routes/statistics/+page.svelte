<script lang="ts">
	import { onMount } from 'svelte';
	import { getStatistics } from '$lib/api';
	import StatCard from '$lib/StatCard.svelte';
	import StatRow from '$lib/StatRow.svelte';

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
			return byCountry.map((row: any) => [
				row.country ?? row.name ?? '',
				Number(row.count),
			]);
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
			<StatCard title="By Status" meta="{sortedByStatus.length} categories" delayMs={0}>
				{#if sortedByStatus.length > 0}
					<ul class="stat-list">
						{#each sortedByStatus as [key, count] (key)}
							<StatRow label={statusLabels[key] || key} count={count as number} {total} />
						{/each}
					</ul>
				{:else}
					<p class="stat-empty">No data yet</p>
				{/if}
			</StatCard>

			<StatCard title="By Country" meta="{countries.length} countries" delayMs={50}>
				{#if countries.length > 0}
					<ul class="stat-list">
						{#each countries as [country, count] (country)}
							<StatRow label={country} {count} {total} />
						{/each}
					</ul>
				{:else}
					<p class="stat-empty">No data yet</p>
				{/if}
			</StatCard>

			<StatCard
				title="By Category"
				meta="{sortedCategories.length} categories"
				delayMs={100}
			>
				{#if sortedCategories.length > 0}
					<ul class="stat-list">
						{#each sortedCategories as cat (cat.name)}
							<StatRow label={cat.name} count={cat.count} {total} />
						{/each}
					</ul>
				{:else}
					<p class="stat-empty">No data yet</p>
				{/if}
			</StatCard>

			<StatCard
				title="By Medical Status"
				meta="{sortedByMedical.length} statuses"
				delayMs={150}
			>
				{#if sortedByMedical.length > 0}
					<ul class="stat-list">
						{#each sortedByMedical as [key, count] (key)}
							<StatRow label={medicalLabels[key] || key} count={count as number} {total} />
						{/each}
					</ul>
				{:else}
					<p class="stat-empty">No data yet</p>
				{/if}
			</StatCard>
		</div>
	{/if}
</div>

<style>
	.statistics-page {
		width: 100%;
		max-width: var(--max-w-page);
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
		max-width: var(--max-w-prose);
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
		gap: var(--gap-card);
	}

	.stat-list {
		list-style: none;
		margin: 0;
		padding: 0.4rem 0;
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
</style>