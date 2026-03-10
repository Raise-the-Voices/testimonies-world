<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { user, isAdvocate } from '$lib/session';
	import { getCasework } from '$lib/api';

	let currentUser = $derived($user);
	let records: any[] = $state([]);
	let loading = $state(true);
	let filterStatus = $state('');

	const actionLabels: Record<string, string> = {
		outreach: 'Outreach',
		legal_filing: 'Legal Filing',
		media: 'Media',
		advocacy: 'Advocacy',
		investigation: 'Investigation',
		other: 'Other',
	};

	async function loadRecords() {
		loading = true;
		try {
			const params: Record<string, string> = {};
			if (filterStatus) params.status = filterStatus;
			const data = await getCasework(params);
			records = data.results || data;
		} catch (e) {
			console.error(e);
		}
		loading = false;
	}

	onMount(() => loadRecords());
</script>

<svelte:head>
	<title>Casework — Testimonies.world</title>
</svelte:head>

<div class="container">
	{#if !isAdvocate(currentUser)}
		<p class="muted">You must be logged in as an advocate to view casework. <a href="{base}/api/auth/login/?next={base}/casework">Login</a></p>
	{:else}
		<div class="flex justify-between items-center mb-2">
			<h1>Casework</h1>
			<a href="{base}/casework/new" class="btn btn-primary">New Record</a>
		</div>

		<div class="flex gap-1 mb-2">
			<select bind:value={filterStatus} onchange={loadRecords} style="width:auto;">
				<option value="">All statuses</option>
				<option value="open">Open</option>
				<option value="in_progress">In Progress</option>
				<option value="done">Done</option>
			</select>
		</div>

		{#if loading}
			<p class="muted">Loading...</p>
		{:else if records.length === 0}
			<p class="muted">No casework records found.</p>
		{:else}
			{#each records as record}
				<div class="card mb-1">
					<div class="flex justify-between items-center">
						<div>
							<span class="badge">{actionLabels[record.action_type] || record.action_type}</span>
							<span class="badge badge-{record.status === 'done' ? 'released' : record.status === 'open' ? 'detained' : 'unknown'}">
								{record.status}
							</span>
						</div>
						<span class="small muted">{record.date}</span>
					</div>
					<p class="mt-1">{record.description}</p>
					{#if record.next_steps}
						<p class="mt-1 small"><strong>Next steps:</strong> {record.next_steps}</p>
					{/if}
					{#if record.performed_by_name}
						<p class="small muted mt-1">By: {record.performed_by_name}</p>
					{/if}
				</div>
			{/each}
		{/if}
	{/if}
</div>
