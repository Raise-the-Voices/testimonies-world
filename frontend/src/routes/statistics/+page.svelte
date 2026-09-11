<script lang="ts">
	import { getStatistics } from '$lib/api';
	import { statusLabels } from '$lib/StatusBadge.svelte';
	import StatCard from '$lib/StatCard.svelte';
	import StatRow from '$lib/StatRow.svelte';
	import Skeleton from '$lib/Skeleton.svelte';
	import type { PageData } from './$types';
	import type { MedicalStatus, Statistics as StatisticsT } from '$lib/types';

	let { data }: { data: PageData } = $props();

	// Initialize from server-side data; if the load() returned null
	// (error or empty), the client may refetch via getStatistics() on
	// user-initiated actions (currently none — this page is read-only).
	let stats = $state<StatisticsT | null>(data.statistics);
	let loading = $state(false);
	let error: string | null = $state(data.error);

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
	function normalizeCountries(byCountry: StatisticsT['by_country']): [string, number][] {
		if (!byCountry) return [];
		if (!Array.isArray(byCountry)) {
			return Object.entries(byCountry) as [string, number][];
		}
		const first = byCountry[0];
		if (first && typeof first === 'object' && !Array.isArray(first)) {
			return (byCountry as Array<{ country?: string; name?: string; count: number }>).map(
				(row) => [row.country ?? row.name ?? '', Number(row.count)],
			);
		}
		return (byCountry as Array<[string, number]>).map((row) => [row[0], Number(row[1])]);
	}

	const countries = $derived(
		normalizeCountries(stats?.by_country ?? []).sort((a, b) => b[1] - a[1]),
	);

	const sortedByStatus = $derived(
		Object.entries(stats?.by_status ?? {}).sort(
			(a, b) => (b[1] as number) - (a[1] as number),
		),
	);

	const sortedByMedical = $derived(
		Object.entries(stats?.by_medical ?? {}).sort(
			(a, b) => (b[1] as number) - (a[1] as number),
		),
	);

	const sortedCategories = $derived(
		((stats?.by_category ?? []) as Array<{ name: string; count: number }>)
			.filter((c) => c.count > 0)
			.sort((a, b) => b.count - a.count),
	);

	async function loadStats() {
		loading = true;
		error = null;
		try {
			stats = await getStatistics();
		} catch (e: unknown) {
			console.error(e);
			error = e instanceof Error ? e.message : 'Failed to load statistics.';
		} finally {
			loading = false;
		}
	}

	// Initial paint is served by +page.ts universal load; no onMount
// refetch needed (this page is read-only — no user action triggers
// a new fetch). loadStats() is kept available for the Retry button.
</script>

<svelte:head>
	<title>Statistics — Testimonies.world</title>
	<meta name="description" content="Platform-wide statistics — total cases, country distribution, status breakdown. A snapshot of the work." />
	<meta property="og:description" content="Platform-wide statistics — total cases, country distribution, status breakdown. A snapshot of the work." />
	<meta property="og:type" content="website" />
	<meta name="twitter:description" content="Platform-wide statistics — total cases, country distribution, status breakdown. A snapshot of the work." />
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
		{#if loading}
			<div class="total-badge" aria-busy="true" aria-label="Loading total">
				<span class="total-number">
					<Skeleton variant="text" width="3rem" />
				</span>
				<span class="total-label">Total cases</span>
			</div>
		{:else if stats}
			<div class="total-badge" aria-label="{stats.total} total cases">
				<span class="total-number">{stats.total}</span>
				<span class="total-label">Total cases</span>
			</div>
		{/if}
	</header>

	{#if loading}
		<div class="stats-grid" aria-busy="true" aria-label="Loading statistics">
			<Skeleton variant="stat-card" lines={4} />
			<Skeleton variant="stat-card" lines={5} />
			<Skeleton variant="stat-card" lines={3} />
			<Skeleton variant="stat-card" lines={3} />
		</div>
	{:else if error}
		<div class="error-state" role="alert">
			<p class="error-state-message">Could not load statistics: {error}</p>
			<button type="button" class="btn btn-secondary" onclick={loadStats}>Retry</button>
		</div>
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
							<StatRow
								label={medicalLabels[key] || key}
								count={count as number}
								{total}
							/>
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
		color: var(--color-primary);
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

	.error-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
		padding: 3rem 1rem;
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-left: 3px solid var(--color-danger);
		border-radius: var(--radius-card);
		text-align: center;
	}
	.error-state-message {
		margin: 0;
		color: var(--color-text-muted);
		max-width: var(--max-w-prose);
	}

	@media (max-width: 700px) {
		.stats-grid {
			grid-template-columns: 1fr;
		}
		.page-header {
			flex-direction: column;
			/* justify-content default (flex-start) is the right
			   behavior on mobile. The desktop value above is
			   `space-between` which would push children apart in
			   the main axis — fine on a row, harmful on a column
			   because it inserts vertical air between the headline
			   and the metric. Override explicitly so the desktop
			   value never crosses over accidentally. */
			justify-content: flex-start;
			align-items: stretch;
			gap: 0.25rem;
			padding-bottom: 0;
			border-bottom: none;
		}
		/* ROOT CAUSE OF THE BREAKING BUG (find #3 from the user's
		   report, retried three times before this fix).

		   The desktop rule has `.page-header-text { flex: 1 1 300px }`
		   — a sensible desktop-row pattern where the basis (300px)
		   is the meaningful horizontal axis. On mobile the parent
		   flips to `flex-direction: column` so the *same* `300px`
		   basis now applies to the *vertical* axis. Net effect:
		   `.page-header-text` gets a 300px min-height even when its
		   content is one short subtitle paragraph — and the
		   `.total-badge` then sits 300px below the subtitle no
		   matter what gap / padding / border values we tried.

		   No margin tweak ever fixed it. Even removing the badge
		   chrome (which is what v2 did) couldn't shrink the
		   implicit 300px vertical hole.

		   The fix is to reset flex on mobile so the basis drops
		   out of the layout entirely. `flex: none` is shorthand
		   for `flex: 0 0 auto` — no growth, no shrink, basis from
		   content. `.page-header-text` then sizes by its content
		   height (a single h1 + p), and the badge sits immediately
		   under it with just the parent's 0.25rem gap between. */
		.page-header-text {
			flex: none;
		}
		/* On mobile the badge is not a separate card — it's the
		   next-line continuation of the headline. Inline-flex
		   keeps the number-and-label on the same baseline; the
		   bigger number (`--color-primary`) anchors the metric
		   visually without a chrome frame. The card view is
		   reserved for desktop where there's horizontal space to
		   separate the metric from the description. */
		.total-badge {
			align-self: stretch;
			background: transparent;
			border: 0;
			border-radius: 0;
			box-shadow: none;
			padding: 0;
			font-size: 1.2rem;
			color: var(--color-text);
		}
		/* Same idea on the page level — 0.5rem between the header
		   and the cards-grid keeps the visual rhythm tight on
		   narrow screens. */
		.statistics-page {
			gap: 0.5rem;
		}
	}
</style>
