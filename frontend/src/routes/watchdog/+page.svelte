<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { getWatchdog } from '$lib/api';
	import StatusBadge from '$lib/StatusBadge.svelte';
	import Skeleton from '$lib/Skeleton.svelte';
	import type { Person } from '$lib/types';

	let persons: Person[] = $state([]);
	let loading = $state(true);

	onMount(async () => {
		try {
			persons = await getWatchdog();
		} catch (e) {
			console.error(e);
		} finally {
			loading = false;
		}
	});

	function daysSince(dateStr: string | null | undefined): string {
		if (!dateStr) return 'never';
		const days = Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000);
		if (days === 0) return 'today';
		if (days === 1) return '1 day ago';
		return `${days} days ago`;
	}
</script>

<svelte:head>
	<title>Watchdog — Testimonies.world</title>
</svelte:head>

<div class="container">
	<h1>Watchdog</h1>
	<p class="muted mb-2">Cases most urgently needing updates, ordered by time since last report.</p>

	{#if loading}
		<div class="watchdog-table-wrap" aria-busy="true" aria-label="Loading watchdog cases">
			<div class="watchdog-skeleton">
				{#each Array.from({ length: 6 }, (_, i) => i) as i (i)}
					<Skeleton variant="table-row" cols={6} />
				{/each}
			</div>
		</div>
	{:else if persons.length === 0}
		<p class="muted">No active cases in the watchdog.</p>
	{:else}
		<div class="watchdog-table-wrap">
			<table class="watchdog-table">
				<thead>
					<tr>
						<th>Name</th>
						<th>Country</th>
						<th>Status</th>
						<th>Medical</th>
						<th>Last Report</th>
						<th>Reports</th>
					</tr>
				</thead>
				<tbody>
					{#each persons as person (person.id)}
						<tr>
							<td><a href="{base}/persons/{person.id}">{person.name}</a></td>
							<td>{person.country}</td>
							<td><StatusBadge status={person.current_status} /></td>
							<td class="small">{person.medical_status}</td>
							<td class="small muted">{daysSince(person.last_known_date)}</td>
							<td>{person.report_count || 0}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>

<style>
	.watchdog-table-wrap {
		/* Responsive: horizontal scroll on phones instead of breaking the viewport. */
		overflow-x: auto;
		-webkit-overflow-scrolling: touch;
		border-radius: var(--radius-card);
		background: var(--color-bg-white);
		box-shadow: var(--shadow-card);
		border: 1px solid var(--color-border-light);
	}
	.watchdog-skeleton {
		display: flex;
		flex-direction: column;
		min-width: 540px;
	}
	.watchdog-table {
		width: 100%;
		min-width: 540px;
		border-collapse: collapse;
	}
	th,
	td {
		padding: 0.5rem 0.75rem;
		text-align: left;
		border-bottom: 1px solid var(--color-border-light);
	}
	th {
		font-size: 0.85rem;
		font-weight: 600;
		background: var(--color-primary);
		color: var(--color-text-light);
	}
</style>
