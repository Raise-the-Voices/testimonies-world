<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { fly } from 'svelte/transition';
	import { page } from '$app/stores';
	import { user, isAdvocate } from '$lib/session';
	import { getContacts, deleteContact } from '$lib/api';
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

	// --- Top-of-page banner (saved/deleted/error from URL params) ----------
	type BannerKind = 'success' | 'error';
	let bannerMsg = $state('');
	let bannerKind = $state<BannerKind>('success');
	const BANNER_TTL_MS = 3500;

	$effect(() => {
		if (!bannerMsg) return;
		const id = setTimeout(() => (bannerMsg = ''), BANNER_TTL_MS);
		return () => clearTimeout(id);
	});

	function consumeUrlBanner() {
		const url = $page.url;
		const saved = url.searchParams.get('saved');
		const err = url.searchParams.get('error');
		if (saved === '1') {
			bannerKind = 'success';
			bannerMsg = 'Contact saved.';
		} else if (err) {
			bannerKind = 'error';
			bannerMsg = err;
		}
		if (saved || err) {
			const clean = new URL(url);
			clean.searchParams.delete('saved');
			clean.searchParams.delete('error');
			history.replaceState(history.state, '', clean.toString());
		}
	}

	// --- Delete toast (confirming → deleting → success | error) ------------
	type DeleteStage = 'confirming' | 'deleting' | 'success' | 'error';
	interface DeleteToast {
		id: number;
		name: string;
		stage: DeleteStage;
		errorMessage?: string;
	}
	let deleteToast = $state<DeleteToast | null>(null);
	let toastTimer: ReturnType<typeof setTimeout> | null = null;

	function clearToastTimer() {
		if (toastTimer) {
			clearTimeout(toastTimer);
			toastTimer = null;
		}
	}

	// Global Esc handler while the toast is open.
	$effect(() => {
		if (!deleteToast) return;
		const handler = (e: KeyboardEvent) => {
			if (e.key === 'Escape' && deleteToast) {
				e.preventDefault();
				cancelDelete();
			}
		};
		document.addEventListener('keydown', handler);
		return () => document.removeEventListener('keydown', handler);
	});

	// Svelte action: focus an element when it's mounted. Used on the toast's
	// Cancel button so a stray Enter is a no-op rather than a destructive
	// confirm. Same pattern /casework uses — svelte's `autofocus` warns
	// under a11y rules, so we do it imperatively.
	function autofocus(node: HTMLElement) {
		node.focus();
	}

	function startDelete(id: number, name: string) {
		clearToastTimer();
		deleteToast = { id, name, stage: 'confirming' };
		bannerMsg = '';
	}

	function cancelDelete() {
		clearToastTimer();
		deleteToast = null;
	}

	async function performDelete() {
		if (!deleteToast || deleteToast.stage !== 'confirming') return;
		const target = deleteToast;
		deleteToast = { ...target, stage: 'deleting' };
		try {
			await deleteContact(target.id);
			contacts = contacts.filter((c) => c.id !== target.id);
			deleteToast = { ...target, stage: 'success' };
			clearToastTimer();
			toastTimer = setTimeout(() => {
				if (deleteToast?.id === target.id) deleteToast = null;
			}, 2000);
		} catch (e: unknown) {
			deleteToast = {
				...target,
				stage: 'error',
				errorMessage: e instanceof Error ? e.message : "Couldn't delete that contact.",
			};
		}
	}

	// --- Data loading -------------------------------------------------------
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

	onMount(() => {
		consumeUrlBanner();
		loadContacts();
	});
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
			<div class="contacts-header-text">
				<h1>Contacts</h1>
				<p class="contacts-intro">
					People involved in cases — advocates, lawyers, journalists, family
					members, and officials. Always private; visible only to advocates.
				</p>
			</div>
			<a class="btn btn-primary header-cta" href="{base}/contacts/new">+ New contact</a>
		</header>

		{#if bannerMsg}
			<div
				class="banner banner-{bannerKind}"
				role="status"
				transition:fly={{ y: -8, duration: 220, opacity: 0 }}
			>
				<span class="banner-icon" aria-hidden="true">
					{bannerKind === 'success' ? '✓' : '!'}
				</span>
				<span class="banner-text">{bannerMsg}</span>
				<button
					type="button"
					class="banner-dismiss"
					aria-label="Dismiss"
					onclick={() => (bannerMsg = '')}
				>×</button>
			</div>
		{/if}

		{#if deleteToast}
			<!-- Backdrop: dimmed + blurred; clicks dismiss the toast (safe default
			     because the destructive Confirm needs a deliberate click). -->
			<div class="delete-toast-overlay" onclick={cancelDelete} role="presentation"></div>

			<!-- Toast: fixed top-of-page, dialog semantics, autofocus on Cancel. -->
			<div
				class="delete-toast"
				class:delete-toast-success={deleteToast.stage === 'success'}
				class:delete-toast-error={deleteToast.stage === 'error'}
				role="alertdialog"
				aria-modal="true"
				aria-labelledby="delete-toast-title"
				aria-describedby="delete-toast-text"
			>
				<div class="delete-toast-body">
					<h2 id="delete-toast-title" class="delete-toast-title">
						{#if deleteToast.stage === 'confirming'}
							Delete contact?
						{:else if deleteToast.stage === 'deleting'}
							Deleting…
						{:else if deleteToast.stage === 'success'}
							Contact deleted
						{:else}
							Couldn't delete
						{/if}
					</h2>
					<p id="delete-toast-text" class="delete-toast-text">
						{#if deleteToast.stage === 'confirming'}
							<strong>{deleteToast.name}</strong> will be removed from the list.
							The record is preserved internally for audit history.
						{:else if deleteToast.stage === 'deleting'}
							Removing <strong>{deleteToast.name}</strong>…
						{:else if deleteToast.stage === 'success'}
							<strong>{deleteToast.name}</strong> has been removed.
						{:else}
							{deleteToast.errorMessage || 'Something went wrong.'}
						{/if}
					</p>
				</div>
				<div class="delete-toast-actions">
					{#if deleteToast.stage === 'confirming'}
						<button
							type="button"
							class="btn btn-secondary"
							onclick={cancelDelete}
							use:autofocus
						>Cancel</button>
						<button
							type="button"
							class="btn btn-danger"
							onclick={performDelete}
						>Delete</button>
					{:else if deleteToast.stage === 'error'}
						<button
							type="button"
							class="btn btn-secondary"
							onclick={cancelDelete}
						>Close</button>
						<button
							type="button"
							class="btn btn-primary"
							onclick={performDelete}
						>Retry</button>
					{/if}
				</div>
			</div>
		{/if}

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
						<Skeleton variant="table-row" cols={6} />
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
						<h2>No contacts{filterRole ? ' match this filter' : ' yet'}</h2>
					</header>
					<p class="empty-message">
						{#if filterRole}
							Try a different role, or
							<button type="button" class="link-button" onclick={() => { filterRole = ''; loadContacts(); }}>
								clear the filter
							</button>.
						{:else}
							Add the first contact and they'll appear here.
						{/if}
					</p>
					<a class="btn btn-primary" href="{base}/contacts/new">+ New contact</a>
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
								<th scope="col" class="th-actions" aria-label="Actions"></th>
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
									<td class="cell-actions">
										<a
											class="row-action"
											href="{base}/contacts/new?id={contact.id}"
											aria-label="Edit {contact.name}"
											title="Edit"
										>
											<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
												<path
													fill="currentColor"
													d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"
												/>
											</svg>
										</a>
										<button
											type="button"
											class="row-action row-action-danger"
											aria-label="Delete {contact.name}"
											title="Delete"
											onclick={() => startDelete(contact.id, contact.name)}
										>
											<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
												<path
													fill="currentColor"
													d="M6 19a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"
												/>
											</svg>
										</button>
									</td>
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

	/* === Page header (matches /casework list pattern) === */
	.contacts-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 1rem;
	}
	.contacts-header-text { flex: 1 1 auto; min-width: 0; }
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
	.header-cta {
		flex: 0 0 auto;
		margin-top: 0.25rem;
		text-decoration: none;
	}

	/* === Banner (success / error, top-of-page) === */
	.banner {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.65rem 0.9rem;
		border-radius: var(--radius-card);
		font-size: 0.92rem;
	}
	.banner-success {
		background: #c6f6d5;
		color: #22543d;
		border: 1px solid #9ae6b4;
	}
	.banner-error {
		background: #fed7d7;
		color: #742a2a;
		border: 1px solid #feb2b2;
	}
	.banner-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 22px;
		height: 22px;
		border-radius: 50%;
		font-weight: 700;
		font-size: 0.85rem;
	}
	.banner-success .banner-icon { background: rgba(34, 84, 61, 0.18); color: #22543d; }
	.banner-error .banner-icon { background: rgba(116, 42, 42, 0.2); color: #742a2a; }
	.banner-text { flex: 1 1 auto; }
	.banner-dismiss {
		background: transparent;
		border: none;
		color: inherit;
		font-size: 1.1rem;
		padding: 0 0.25rem;
		line-height: 1;
		cursor: pointer;
	}

	/* === Delete toast (matches /casework pattern) === */
	.delete-toast-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.35);
		backdrop-filter: blur(2px);
		-webkit-backdrop-filter: blur(2px);
		z-index: 60;
	}
	.delete-toast {
		position: fixed;
		top: 1.25rem;
		left: 50%;
		transform: translateX(-50%);
		max-width: 460px;
		width: calc(100% - 2rem);
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-left: 3px solid var(--color-danger);
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-card-lg);
		padding: 1rem 1.25rem;
		z-index: 70;
		display: flex;
		flex-direction: column;
		gap: 0.85rem;
	}
	.delete-toast-success { border-left-color: var(--color-success); }
	.delete-toast-error { border-left-color: var(--color-danger); }
	.delete-toast-title {
		margin: 0;
		font-size: 1rem;
		font-weight: 700;
		color: var(--color-text);
	}
	.delete-toast-text {
		margin: 0;
		font-size: 0.88rem;
		color: var(--color-text-muted);
		line-height: 1.5;
	}
	.delete-toast-text strong { color: var(--color-text); }
	.delete-toast-actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.5rem;
	}
	.btn-danger {
		background: var(--color-danger);
		color: var(--color-text-light);
	}
	.btn-danger:hover { background: #b71212; color: var(--color-text-light); }

	/* === Card surface === */
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
		min-width: 640px;
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
	.th-actions {
		width: 1%;
		text-align: right;
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
	.cell-contact.is-empty {
		color: var(--color-text-muted);
		font-weight: 400;
	}

	/* === Row actions (edit / delete) === */
	.cell-actions {
		text-align: right;
		white-space: nowrap;
	}
	.row-action {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 30px;
		height: 30px;
		border-radius: var(--radius-card);
		background: transparent;
		border: 1px solid transparent;
		color: var(--color-text-muted);
		cursor: pointer;
		text-decoration: none;
		transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
		padding: 0;
	}
	.row-action:hover {
		background: var(--color-primary-tint);
		color: var(--color-primary);
		border-color: var(--color-primary-tint);
	}
	.row-action-danger:hover {
		background: rgba(217, 22, 22, 0.1);
		color: var(--color-danger);
		border-color: rgba(217, 22, 22, 0.15);
	}

	/* === Role pills === */
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

	/* === Empty state === */
	.contacts-empty {
		text-align: center;
		padding: 1rem 0 0.5rem 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.85rem;
	}
	.empty-header {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.6rem;
		margin-bottom: 0.4rem;
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
	.link-button {
		background: transparent;
		border: none;
		color: var(--color-primary);
		cursor: pointer;
		padding: 0;
		font: inherit;
		text-decoration: underline;
		text-decoration-color: var(--color-primary-tint);
		text-underline-offset: 2px;
	}
	.link-button:hover {
		text-decoration-color: var(--color-primary);
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
		.contacts-header {
			flex-direction: column;
			align-items: stretch;
		}
		.header-cta { width: 100%; text-align: center; }
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
		.contacts-table tbody tr,
		.row-action,
		.banner {
			transition: none;
		}
	}
</style>