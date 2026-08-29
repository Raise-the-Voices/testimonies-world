<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { user, isAdvocate } from '$lib/session';
	import { getContacts } from '$lib/api';
	import Skeleton from '$lib/Skeleton.svelte';
	import type { Contact } from '$lib/types';

	let currentUser = $derived($user);
	let contacts: Contact[] = $state([]);
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
			contacts = Array.isArray(data) ? data : data.results ?? [];
		} catch (e) {
			console.error(e);
		} finally {
			loading = false;
		}
	}

	onMount(() => loadContacts());
</script>

<svelte:head>
	<title>Contacts — Testimonies.world</title>
</svelte:head>

<div class="container">
	{#if !isAdvocate(currentUser)}
		<p class="muted">
			You must be logged in as an advocate to view contacts.
			<a href="{base}/api/auth/login/?next={base}/contacts">Login</a>
		</p>
	{:else}
		<h1>Contacts</h1>

		<div class="flex gap-1 mb-2 mt-1">
			<select bind:value={filterRole} onchange={loadContacts} class="contacts-filter">
				<option value="">All roles</option>
				{#each Object.entries(roleLabels) as [value, label] (value)}
					<option {value}>{label}</option>
				{/each}
			</select>
		</div>

		{#if loading}
			<div class="contacts-table-wrap" aria-busy="true" aria-label="Loading contacts">
				<div class="contacts-skeleton">
					{#each Array.from({ length: 6 }, (_, i) => i) as i (i)}
						<Skeleton variant="table-row" cols={5} />
					{/each}
				</div>
			</div>
		{:else if contacts.length === 0}
			<p class="muted">No contacts found. Add contacts via the Django admin.</p>
		{:else}
			<div class="contacts-table-wrap">
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
						{#each contacts as contact (contact.id)}
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
			</div>
		{/if}
	{/if}
</div>

<style>
	.contacts-filter {
		width: auto;
		border-radius: var(--radius-input);
		border: 1px solid var(--color-border-light);
		padding: 0.65rem 1rem;
		background: var(--color-bg-white);
		color: var(--color-text);
		font-family: inherit;
		font-size: 0.95rem;
	}
	.contacts-table-wrap {
		/* Responsive: horizontal scroll on phones instead of breaking the viewport. */
		overflow-x: auto;
		-webkit-overflow-scrolling: touch;
		border-radius: var(--radius-card);
		background: var(--color-bg-white);
		box-shadow: var(--shadow-card);
		border: 1px solid var(--color-border-light);
	}
	.contacts-skeleton {
		display: flex;
		flex-direction: column;
		min-width: 480px;
	}
	.contacts-table {
		width: 100%;
		min-width: 480px;
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
