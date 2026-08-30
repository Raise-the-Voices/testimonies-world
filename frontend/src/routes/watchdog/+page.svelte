<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { getWatchdog } from '$lib/api';
	import StatusBadge from '$lib/StatusBadge.svelte';
	import Skeleton from '$lib/Skeleton.svelte';
	import type { Person } from '$lib/types';

	let persons: Person[] = $state([]);
	let loading = $state(true);
	let error: string | null = $state(null);

	async function loadWatchdog() {
		loading = true;
		error = null;
		try {
			persons = await getWatchdog();
		} catch (e: unknown) {
			console.error(e);
			error = e instanceof Error ? e.message : 'Failed to load watchdog.';
		} finally {
			loading = false;
		}
	}

	onMount(loadWatchdog);

	// Returns a relative-time string. Older entries read as more urgent
	// so the watchdog column has natural visual weight — newer entries
	// are quieter, older ones louder.
	function daysSince(dateStr: string | null | undefined): string {
		if (!dateStr) return 'never';
		const days = Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000);
		if (days === 0) return 'today';
		if (days === 1) return '1 day ago';
		return `${days} days ago`;
	}

	// 0–29 days = fresh (muted text), 30–89 = stale (warning),
	// 90+ = urgent (danger). Returns a CSS class so the cell can
	// pick up the visual weight without the script leaking
	// inline styles.
	function recencyClass(dateStr: string | null | undefined): 'fresh' | 'stale' | 'urgent' | 'never' {
		if (!dateStr) return 'never';
		const days = Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000);
		if (days >= 90) return 'urgent';
		if (days >= 30) return 'stale';
		return 'fresh';
	}
</script>

<svelte:head>
	<title>Watchdog — Testimonies.world</title>
</svelte:head>

<div class="watchdog-page">
	<header class="watchdog-header">
		<h1>Watchdog</h1>
		<p class="watchdog-intro">
			Cases most urgently needing an update — sorted by time since the last
			report. Older entries are louder so volunteers can spot them first.
		</p>
	</header>

	{#if loading}
		<section class="watchdog-card" aria-busy="true" aria-label="Loading watchdog cases">
			<div class="watchdog-skeleton">
				{#each Array.from({ length: 6 }, (_, i) => i) as i (i)}
					<Skeleton variant="table-row" cols={6} />
				{/each}
			</div>
		</section>
	{:else if error}
		<section class="watchdog-card watchdog-card-error" role="alert">
			<header class="error-header">
				<span class="error-icon" aria-hidden="true">⚠</span>
				<h2>Could not load the watchdog</h2>
			</header>
			<p class="error-message">{error}</p>
			<button type="button" class="btn btn-secondary" onclick={loadWatchdog}>Retry</button>
		</section>
	{:else if persons.length === 0}
		<section class="watchdog-card watchdog-card-empty">
			<header class="empty-header">
				<span class="empty-icon" aria-hidden="true">✓</span>
				<h2>Nothing needs attention right now</h2>
			</header>
			<p class="empty-message">
				Every case on the platform has had a report within the last 30 days.
				Check back later, or visit <a href="{base}/persons">all cases</a> to browse the full record.
			</p>
		</section>
	{:else}
		<section class="watchdog-card" aria-label="Watchdog cases">
			<header class="watchdog-card-header">
				<span class="card-count" aria-label="{persons.length} cases">
					<strong>{persons.length}</strong> case{persons.length === 1 ? '' : 's'} waiting
				</span>
				<span class="card-legend">
					<span class="legend-dot legend-dot-fresh" aria-hidden="true"></span> Fresh (&lt;30 days)
					<span class="legend-dot legend-dot-stale" aria-hidden="true"></span> Stale (30–89 days)
					<span class="legend-dot legend-dot-urgent" aria-hidden="true"></span> Urgent (90+ days)
				</span>
			</header>
			<div class="watchdog-table-wrap">
				<table class="watchdog-table">
					<thead>
						<tr>
							<th scope="col">Name</th>
							<th scope="col">Country</th>
							<th scope="col">Status</th>
							<th scope="col">Medical</th>
							<th scope="col">Last Report</th>
							<th scope="col" class="num">Reports</th>
						</tr>
					</thead>
					<tbody>
						{#each persons as person (person.id)}
							{@const recency = recencyClass(person.last_known_date)}
							<tr class="row-{recency}">
								<td>
									<a class="person-link" href="{base}/persons/{person.id}">{person.name}</a>
								</td>
								<td class="cell-country">{person.country || '—'}</td>
								<td>
									{#if person.current_status}
										<StatusBadge status={person.current_status} />
									{:else}
										<span class="muted">—</span>
									{/if}
								</td>
								<td class="cell-medical">{person.medical_status || '—'}</td>
								<td class="cell-recency cell-{recency}">
									<span class="recency-dot" aria-hidden="true"></span>
									<span class="recency-text">{daysSince(person.last_known_date)}</span>
								</td>
								<td class="num">{person.report_count ?? 0}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</section>
	{/if}
</div>

<style>
	/* === Page header === */
	.watchdog-page {
		width: 100%;
		max-width: var(--max-w-page);
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}
	.watchdog-header h1 {
		margin: 0 0 0.4rem 0;
		color: var(--color-primary);
		font-size: 1.85rem;
		font-weight: 700;
		letter-spacing: -0.01em;
	}
	.watchdog-intro {
		margin: 0;
		max-width: var(--max-w-prose);
		color: var(--color-text);
		font-size: 1rem;
		line-height: 1.6;
	}

	/* === Shared card surface === */
	.watchdog-card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-subtle);
		border-left: 3px solid var(--color-primary);
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-card);
		padding: 1.5rem 1.75rem;
	}

	/* Card header — count + legend */
	.watchdog-card-header {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		flex-wrap: wrap;
		gap: 0.75rem 1.25rem;
		padding-bottom: 0.85rem;
		margin-bottom: 1rem;
		border-bottom: 1px solid var(--color-border-subtle);
	}
	.card-count {
		font-size: 0.92rem;
		color: var(--color-text);
	}
	.card-count strong {
		color: var(--color-primary);
		font-weight: 700;
	}
	.card-legend {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem 1rem;
		flex-wrap: wrap;
		font-size: 0.78rem;
		color: var(--color-text-muted);
		line-height: 1.4;
	}
	.legend-dot {
		display: inline-block;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		margin-right: 0.3rem;
		vertical-align: middle;
	}
	.legend-dot-fresh {
		background: var(--color-success);
	}
	.legend-dot-stale {
		background: #d97706;
	}
	.legend-dot-urgent {
		background: var(--color-danger);
	}

	/* === Table === */
	.watchdog-table-wrap {
		overflow-x: auto;
		-webkit-overflow-scrolling: touch;
	}
	.watchdog-table {
		width: 100%;
		min-width: 540px;
		border-collapse: collapse;
	}

	th,
	td {
		padding: 0.7rem 0.85rem;
		text-align: left;
		border-bottom: 1px solid var(--color-border-subtle);
		vertical-align: middle;
	}
	th {
		font-size: 0.72rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		color: var(--color-text-muted);
		background: transparent;
		border-bottom: 1px solid var(--color-border-light);
		white-space: nowrap;
	}
	th.num,
	td.num {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	tbody tr {
		transition: background 0.15s ease;
	}
	tbody tr:hover {
		background: var(--color-surface);
	}
	tbody tr:last-child td {
		border-bottom: none;
	}

	/* Cell content */
	.person-link {
		color: var(--color-text);
		font-weight: 600;
		text-decoration: none;
	}
	.person-link:hover {
		color: var(--color-primary);
		text-decoration: underline;
		text-decoration-color: var(--color-primary-tint);
		text-underline-offset: 3px;
	}
	.cell-country {
		color: var(--color-text-muted);
	}
	.cell-medical {
		color: var(--color-text-muted);
		font-size: 0.88rem;
		text-transform: capitalize;
	}

	/* Recency — fresh / stale / urgent. The colored dot draws the
	   eye to the oldest cases first. */
	.cell-recency {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.88rem;
	}
	.recency-dot {
		display: inline-block;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex: 0 0 8px;
	}
	.cell-fresh .recency-dot {
		background: var(--color-success);
	}
	.cell-fresh .recency-text {
		color: var(--color-text-muted);
	}
	.cell-stale .recency-dot {
		background: #d97706;
	}
	.cell-stale .recency-text {
		color: var(--color-text);
		font-weight: 600;
	}
	.cell-urgent .recency-dot {
		background: var(--color-danger);
		box-shadow: 0 0 0 3px rgba(217, 22, 22, 0.2);
	}
	.cell-urgent .recency-text {
		color: var(--color-danger);
		font-weight: 700;
	}
	.cell-never .recency-dot {
		background: var(--color-border-light);
	}
	.cell-never .recency-text {
		color: var(--color-text-muted);
		font-style: italic;
	}

	/* Empty state — same card surface, no left border */
	.watchdog-card-empty {
		text-align: center;
		border-left-color: var(--color-success);
	}
	.empty-header {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.6rem;
		margin-bottom: 0.6rem;
		color: var(--color-success);
	}
	.empty-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		border-radius: 50%;
		background: rgba(47, 133, 90, 0.15);
		color: var(--color-success);
		font-weight: 700;
		font-size: 1rem;
	}
	.empty-header h2 {
		margin: 0;
		font-size: 1.05rem;
		font-weight: 700;
		color: var(--color-text);
	}
	.empty-message {
		margin: 0 auto;
		max-width: var(--max-w-prose);
		color: var(--color-text-muted);
		font-size: 0.92rem;
		line-height: 1.55;
	}

	/* Error state — danger left border, prominent icon */
	.watchdog-card-error {
		border-left-color: var(--color-danger);
	}
	.error-header {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		margin-bottom: 0.6rem;
		color: var(--color-danger);
	}
	.error-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		border-radius: 50%;
		background: rgba(217, 22, 22, 0.12);
		color: var(--color-danger);
		font-weight: 700;
		font-size: 1rem;
	}
	.error-header h2 {
		margin: 0;
		font-size: 1.05rem;
		font-weight: 700;
		color: var(--color-text);
	}
	.error-message {
		margin: 0 0 1rem 0;
		color: var(--color-text-muted);
		font-size: 0.92rem;
	}

	/* === Responsive === */
	@media (max-width: 720px) {
		.watchdog-card {
			padding: 1.25rem 1.25rem;
		}
		.watchdog-card-header {
			flex-direction: column;
			align-items: flex-start;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		tbody tr {
			transition: none;
		}
	}
</style>
