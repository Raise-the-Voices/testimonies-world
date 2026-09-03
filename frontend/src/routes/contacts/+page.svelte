<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { user, isAdvocate } from '$lib/session';
	import { getContacts } from '$lib/api';
	import Skeleton from '$lib/Skeleton.svelte';
	import type { Contact, ContactRole } from '$lib/types';

	let currentUser = $derived($user);
	let contacts: Contact[] = $state([]);
	let loading = $state(true);
	let error: string | null = $state(null);
	let filterRole = $state('');

	// Human-readable labels per role — kept here (not in app.css) so the
	// source of truth for "what we call each role" stays in one place.
	const roleLabels: Record<ContactRole, string> = {
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
		error = null;
		try {
			const params: Record<string, string> = {};
			if (filterRole) params.role = filterRole;
			const data = await getContacts(params);
			contacts = Array.isArray(data) ? data : data.results ?? [];
		} catch (e: unknown) {
			console.error(e);
			error = e instanceof Error ? e.message : 'Failed to load contacts.';
		} finally {
			loading = false;
		}
	}

	onMount(() => loadContacts());
</script>

<svelte:head>
	<title>Contacts — Testimonies.world</title>
</svelte:head>

<div class="contacts-page">
	{#if !isAdvocate(currentUser)}
		<p class="muted">
			You must be logged in as an advocate to view contacts.
			<a href="{base}/api/auth/login/?next={base}/contacts">Login</a>
		</p>
	{:else}
		<header class="contacts-header">
			<h1>Contacts</h1>
			<p class="contacts-intro">
				People involved in cases — advocates, lawyers, journalists, family
				members, and officials. Always private; visible only to advocates.
			</p>
		</header>

		<section class="contacts-card" aria-label="Contacts list">
			<div class="contacts-toolbar">
				<label class="toolbar-field" for="role-filter">
					<span class="toolbar-label">Filter by role</span>
					<select
						id="role-filter"
						class="select--filter"
						bind:value={filterRole}
						onchange={loadContacts}
					>
						<option value="">All roles</option>
						{#each Object.entries(roleLabels) as [value, label] (value)}
							<option {value}>{label}</option>
						{/each}
					</select>
				</label>
				{#if !loading && contacts.length > 0}
					<span class="contacts-count" aria-label="{contacts.length} contacts">
						<strong>{contacts.length}</strong>
						contact{contacts.length === 1 ? '' : 's'}
					</span>
				{/if}
			</div>

			{#if loading}
				<div class="contacts-skeleton" aria-busy="true" aria-label="Loading contacts">
					{#each Array.from({ length: 6 }, (_, i) => i) as i (i)}
						<Skeleton variant="table-row" cols={5} />
					{/each}
				</div>
			{:else if error}
				<div class="contacts-error" role="alert">
					<header class="error-header">
						<span class="error-icon" aria-hidden="true">⚠</span>
						<h2>Could not load contacts</h2>
					</header>
					<p class="error-message">{error}</p>
					<button type="button" class="btn btn-secondary" onclick={loadContacts}>Retry</button>
				</div>
			{:else if contacts.length === 0}
				<div class="contacts-empty">
					<header class="empty-header">
						<span class="empty-icon" aria-hidden="true">○</span>
						<h2>No contacts yet</h2>
					</header>
					<p class="empty-message">
						Contacts are added through the Django admin. Once they're in,
						they'll appear here — filterable by role.
					</p>
				</div>
			{:else}
				<div class="contacts-table-wrap">
					<table class="contacts-table">
						<thead>
							<tr>
								<th scope="col">Name</th>
								<th scope="col">Role</th>
								<th scope="col">Email</th>
								<th scope="col">Phone</th>
								<th scope="col">Signal</th>
							</tr>
						</thead>
						<tbody>
							{#each contacts as contact (contact.id)}
								<tr>
									<td class="cell-name">{contact.name}</td>
									<td>
										<span class="role-pill role-pill-{contact.role}">
											{roleLabels[contact.role] || contact.role}
										</span>
									</td>
									<td class="cell-contact" class:is-empty={!contact.email}>{contact.email || '—'}</td>
									<td class="cell-contact" class:is-empty={!contact.phone}>{contact.phone || '—'}</td>
									<td class="cell-contact" class:is-empty={!contact.signal}>{contact.signal || '—'}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		</section>
	{/if}
</div>

<style>
	/* === Page layout — matches /watchdog === */
	.contacts-page {
		width: 100%;
		max-width: var(--max-w-page);
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	/* === Page header === */
	.contacts-header h1 {
		margin: 0 0 0.4rem 0;
		color: var(--color-primary);
		font-size: 1.85rem;
		font-weight: 700;
		letter-spacing: -0.01em;
	}
	.contacts-intro {
		margin: 0;
		max-width: var(--max-w-prose);
		color: var(--color-text);
		font-size: 1rem;
		line-height: 1.6;
	}

	/* === Card surface — same recipe as /watchdog === */
	.contacts-card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-subtle);
		border-left: 3px solid var(--color-primary);
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-card);
		padding: 1.5rem 1.75rem;
	}

	/* === Toolbar: filter + count, baseline-aligned === */
	.contacts-toolbar {
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
		flex-wrap: wrap;
		gap: 0.75rem 1.25rem;
		padding-bottom: 1rem;
		margin-bottom: 1.25rem;
		border-bottom: 1px solid var(--color-border-subtle);
	}
	.toolbar-field {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
		min-width: 220px;
	}
	.toolbar-label {
		font-size: 0.72rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		color: var(--color-text-muted);
	}
	/* .select--filter is defined globally in app.css (line ~400) — it
	   brings the clean border, padding, and focus-ring. We only override
	   width here so the dropdown reads as a toolbar control, not a
	   full-width form field. */
	.toolbar-field .select--filter {
		width: auto;
		min-width: 200px;
	}
	.contacts-count {
		font-size: 0.92rem;
		color: var(--color-text);
	}
	.contacts-count strong {
		color: var(--color-primary);
		font-weight: 700;
	}

	/* === Loading skeleton === */
	.contacts-skeleton {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	/* === Table — minimalist thead, generous cell padding, row hover === */
	.contacts-table-wrap {
		overflow-x: auto;
		-webkit-overflow-scrolling: touch;
	}
	.contacts-table {
		width: 100%;
		min-width: 560px;
		border-collapse: collapse;
	}
	.contacts-table th,
	.contacts-table td {
		padding: 0.85rem 1rem;
		text-align: left;
		border-bottom: 1px solid var(--color-border-subtle);
		vertical-align: middle;
	}
	.contacts-table th {
		font-size: 0.72rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		color: var(--color-text-muted);
		background: transparent;
		border-bottom: 1px solid var(--color-border-light);
		white-space: nowrap;
	}
	.contacts-table tbody tr {
		transition: background 0.15s ease;
	}
	.contacts-table tbody tr:hover {
		background: var(--color-surface);
	}
	.contacts-table tbody tr:last-child td {
		border-bottom: none;
	}

	/* === Cell content === */
	.cell-name {
		font-weight: 600;
		color: var(--color-text);
	}
	.cell-contact {
		font-size: 0.92rem;
		color: var(--color-text);
		font-variant-numeric: tabular-nums;
	}
	/* Empty cells render as a muted em-dash — quieter than real text so
	   missing data doesn't read as a typo or a broken render. */
	.cell-contact.is-empty {
		color: var(--color-text-muted);
		font-weight: 400;
	}

	/* === Role pills — soft tints, matching text colors, modern dashboard feel === */
	.role-pill {
		display: inline-flex;
		align-items: center;
		padding: 0.28rem 0.7rem;
		border-radius: 999px;
		font-size: 0.78rem;
		font-weight: 600;
		letter-spacing: 0.01rem;
		line-height: 1.2;
		white-space: nowrap;
	}
	.role-pill-family     { background: #f3e8ff; color: #6b46c1; }
	.role-pill-advocate   { background: #d1fae5; color: #276749; }
	.role-pill-lawyer     { background: #dbeafe; color: #2b6cb0; }
	.role-pill-official   { background: #e0e7ff; color: #4338ca; }
	.role-pill-journalist { background: #fef3c7; color: #92400e; }
	.role-pill-reporter   { background: #fde68a; color: #854d0e; }
	.role-pill-other      { background: #f1f5f9; color: #475569; }

	/* === Empty state — friendly icon, same card surface === */
	.contacts-empty {
		text-align: center;
		padding: 1rem 0 0.5rem 0;
	}
	.empty-header {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.6rem;
		margin-bottom: 0.6rem;
		color: var(--color-text-muted);
	}
	.empty-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		border-radius: 50%;
		background: var(--color-primary-tint);
		color: var(--color-primary);
		font-weight: 700;
		font-size: 1.05rem;
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

	/* === Error state === */
	.contacts-error {
		border-left: 3px solid var(--color-danger);
	}
	.contacts-error .error-header {
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
	.contacts-error h2 {
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
		.contacts-card {
			padding: 1.25rem 1.25rem;
		}
		.contacts-toolbar {
			flex-direction: column;
			align-items: stretch;
		}
		.toolbar-field {
			min-width: 0;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.contacts-table tbody tr {
			transition: none;
		}
	}
</style>