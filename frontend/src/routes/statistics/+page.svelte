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

<div class="container">
	<h1>Statistics</h1>

	{#if loading}
		<p class="muted">Loading...</p>
	{:else if stats}
		<p class="mb-2">{stats.total} total cases recorded.</p>

		<div class="stats-grid">
			<div class="card">
				<h3>By Status</h3>
				{#if Object.keys(stats.by_status).length > 0}
					<table>
						<tbody>
							{#each Object.entries(stats.by_status).sort((a, b) => (b[1] as number) - (a[1] as number)) as [key, count]}
								<tr>
									<td>{statusLabels[key] || key}</td>
									<td class="count">{count}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{:else}
					<p class="muted small">No data yet</p>
				{/if}
			</div>

			<div class="card">
				<h3>By Country</h3>
				{#if Object.keys(stats.by_country).length > 0}
					<table>
						<tbody>
							{#each Object.entries(stats.by_country).sort((a, b) => (b[1] as number) - (a[1] as number)) as [country, count]}
								<tr>
									<td>{country}</td>
									<td class="count">{count}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{:else}
					<p class="muted small">No data yet</p>
				{/if}
			</div>

			<div class="card">
				<h3>By Category</h3>
				{#if stats.by_category.length > 0}
					<table>
						<tbody>
							{#each stats.by_category.filter((c: any) => c.count > 0) as cat}
								<tr>
									<td>{cat.name}</td>
									<td class="count">{cat.count}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{:else}
					<p class="muted small">No data yet</p>
				{/if}
			</div>

			<div class="card">
				<h3>By Medical Status</h3>
				{#if Object.keys(stats.by_medical).length > 0}
					<table>
						<tbody>
							{#each Object.entries(stats.by_medical).sort((a, b) => (b[1] as number) - (a[1] as number)) as [key, count]}
								<tr>
									<td>{medicalLabels[key] || key}</td>
									<td class="count">{count}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				{:else}
					<p class="muted small">No data yet</p>
				{/if}
			</div>
		</div>
	{/if}
</div>

<style>
	.stats-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
		gap: 1rem;
	}
	.stats-grid .card h3 {
		background: #25646a;
		color: #fafafa;
		padding: 5px 10px;
		margin: -10px -10px 10px -10px;
		border-radius: 4px 4px 0 0;
	}
	table {
		width: 100%;
		border-collapse: collapse;
	}
	td {
		padding: 0.35rem 0;
		border-bottom: 1px solid var(--color-border-light);
		font-size: 0.9rem;
	}
	.count {
		text-align: right;
		font-weight: 600;
	}
</style>
