<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { user, isAdvocate } from '$lib/session';
	import { getContacts } from '$lib/api';

	let currentUser = $derived($user);
	let contacts: any[] = $state([]);
	let loading = $state(true);
	let filterRole = $state('');

	const roleLabels: Record<string, string> = {
		family: 'Family',
		advocate: 'Advocate',
		lawyer: 'Lawyer',
		official: 'Official',
		journalist: 'Journalist',
		reporter: 'Reporter',
		other: 'Other',
	};

	async function loadContacts() {
		loading = true;
		try {
			const params: Record<string, string> = {};
			if (filterRole) params.role = filterRole;
			const data = await getContacts(params);
			contacts = data.results || data;
		} catch (e) {
			console.error(e);
		}
		loading = false;
	}

	onMount(() => loadContacts());
</script>

<svelte:head>
	<title>Contacts — Testimonies.world</title>
</svelte:head>

<div class="container">
	{#if !isAdvocate(currentUser)}
		<p class="muted">You must be logged in as an advocate to view contacts. <a href="{base}/api/auth/login/?next={base}/contacts">Login</a></p>
	{:else}
		<h1>Contacts</h1>

		<div class="flex gap-1 mb-2 mt-1">
			<select bind:value={filterRole} onchange={loadContacts} style="width:auto;">
				<option value="">All roles</option>
				{#each Object.entries(roleLabels) as [value, label]}
					<option {value}>{label}</option>
				{/each}
			</select>
		</div>

		{#if loading}
			<p class="muted">Loading...</p>
		{:else if contacts.length === 0}
			<p class="muted">No contacts found. Add contacts via the Django admin.</p>
		{:else}
			<table class="contacts-table">
				<thead>
					<tr>
						<th>Name</th>
						<th>Role</th>
						<th>Email</th>
						<th>Phone</th>
						<th>Signal</th>
					</tr>
				</thead>
				<tbody>
					{#each contacts as contact}
						<tr>
							<td><strong>{contact.name}</strong></td>
							<td class="small">{roleLabels[contact.role] || contact.role}</td>
							<td class="small">{contact.email || '—'}</td>
							<td class="small">{contact.phone || '—'}</td>
							<td class="small">{contact.signal || '—'}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	{/if}
</div>

<style>
	.contacts-table {
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
