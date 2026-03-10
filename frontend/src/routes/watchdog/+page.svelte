<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { getWatchdog } from '$lib/api';
	import StatusBadge from '$lib/StatusBadge.svelte';

	let persons: any[] = $state([]);
	let loading = $state(true);

	onMount(async () => {
		try {
			persons = await getWatchdog();
		} catch (e) {
			console.error(e);
		}
		loading = false;
	});

	function daysSince(dateStr: string | null): string {
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
		<p class="muted">Loading...</p>
	{:else if persons.length === 0}
		<p class="muted">No active cases in the watchdog.</p>
	{:else}
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
				{#each persons as person}
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
	{/if}
</div>

<style>
	.watchdog-table {
		width: 100%;
		border-collapse: collapse;
		background: white;
		border: 1px solid darkgray;
		border-radius: 4px;
		box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.2);
	}
	th, td {
		padding: 0.5rem 0.75rem;
		text-align: left;
		border-bottom: 1px solid var(--color-border-light);
	}
	th {
		font-size: 0.85rem;
		font-weight: 600;
		background: #25646a;
		color: #fafafa;
	}
</style>
