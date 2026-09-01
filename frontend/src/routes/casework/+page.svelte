<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { user, isAdvocate } from '$lib/session';
	import { getCasework, deleteCasework } from '$lib/api';
	import Skeleton from '$lib/Skeleton.svelte';

	let currentUser = $derived($user);
	let records: any[] = $state([]);
	let loading = $state(true);
	let loadError = $state('');
	let filterStatus = $state('');
	let filterAction = $state('');

	// Inline delete-confirmation state — record id currently in "are you sure?" mode
	let confirmingDelete: number | null = $state(null);
	let deleting = $state(false);

	// Banner state — sourced from URL on mount, can be set directly too
	let bannerMsg = $state('');
	let bannerKind = $state<'success' | 'error'>('success');

	const actionLabels: Record<string, string> = {
		outreach: 'Outreach',
		legal_filing: 'Legal Filing',
		media: 'Media',
		advocacy: 'Advocacy',
		investigation: 'Investigation',
		other: 'Other',
	};

	const statusLabels: Record<string, string> = {
		open: 'Open',
		in_progress: 'In Progress',
		done: 'Done',
	};

	const statusKind: Record<string, 'detained' | 'unknown' | 'released'> = {
		open: 'detained',
		in_progress: 'unknown',
		done: 'released',
	};

	function consumeUrlBanner() {
		const url = $page.url;
		const saved = url.searchParams.get('saved');
		const deleted = url.searchParams.get('deleted');
		const err = url.searchParams.get('error');
		if (saved === '1') {
			bannerKind = 'success';
			bannerMsg = 'Record saved.';
		} else if (deleted === '1') {
			bannerKind = 'success';
			bannerMsg = 'Record deleted.';
		} else if (err) {
			bannerKind = 'error';
			bannerMsg = err;
		}
		if (saved || deleted || err) {
			const clean = new URL(url);
			clean.searchParams.delete('saved');
			clean.searchParams.delete('deleted');
			clean.searchParams.delete('error');
			history.replaceState(history.state, '', clean.toString());
		}
	}

	onMount(() => {
		consumeUrlBanner();
		loadRecords();
	});

	async function loadRecords() {
		loading = true;
		loadError = '';
		try {
			const params: Record<string, string> = {};
			if (filterStatus) params.status = filterStatus;
			if (filterAction) params.action_type = filterAction;
			const data = await getCasework(params);
			records = Array.isArray(data) ? data : data.results ?? [];
		} catch (e: any) {
			loadError =
				e?.message ||
				"Couldn't load casework records. Check your connection and try again.";
			records = [];
		} finally {
			loading = false;
		}
	}

	function recencyClass(dateStr: string): 'fresh' | 'stale' | 'urgent' {
		const d = new Date(dateStr);
		if (Number.isNaN(d.getTime())) return 'stale';
		const days = Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24));
		if (days < 30) return 'fresh';
		if (days < 90) return 'stale';
		return 'urgent';
	}

	function formatDate(d: string): string {
		try {
			return new Date(d).toLocaleDateString(undefined, {
				year: 'numeric',
				month: 'short',
				day: 'numeric',
			});
		} catch {
			return d;
		}
	}

	function startDelete(id: number) {
		confirmingDelete = id;
		bannerMsg = '';
	}

	function cancelDelete() {
		confirmingDelete = null;
	}

	async function performDelete(id: number) {
		deleting = true;
		try {
			await deleteCasework(id);
			records = records.filter((r) => r.id !== id);
			confirmingDelete = null;
			bannerKind = 'success';
			bannerMsg = 'Record deleted.';
		} catch (e: any) {
			bannerKind = 'error';
			bannerMsg = e?.message || "Couldn't delete that record. Please try again.";
			confirmingDelete = null;
		} finally {
			deleting = false;
		}
	}

	function clearFilters() {
		filterStatus = '';
		filterAction = '';
		loadRecords();
	}

	const hasActiveFilters = $derived(!!filterStatus || !!filterAction);
</script>

<svelte:head>
	<title>Casework — Testimonies.world</title>
</svelte:head>

<div class="container">
	{#if !isAdvocate(currentUser)}
		<p class="muted">
			You must be logged in as an advocate to view casework.
			<a href="{base}/api/auth/login/?next={base}/casework">Login</a>
		</p>
	{:else}
		<header class="page-header">
			<div>
				<h1>Casework</h1>
				<p class="page-intro">
					Every advocacy action logged against a case. Click <strong>Edit</strong> on a
					record to update it, or <strong>Delete</strong> to remove it.
				</p>
			</div>
			<a href="{base}/casework/new" class="btn btn-primary header-cta">+ New Record</a>
		</header>

		{#if bannerMsg}
			<div class="banner banner-{bannerKind}" role="status">
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

		<div class="filters">
			<div class="filter-group">
				<label for="filter-status">Status</label>
				<select id="filter-status" bind:value={filterStatus} onchange={loadRecords}>
					<option value="">All</option>
					<option value="open">Open</option>
					<option value="in_progress">In progress</option>
					<option value="done">Done</option>
				</select>
			</div>
			<div class="filter-group">
				<label for="filter-action">Action type</label>
				<select id="filter-action" bind:value={filterAction} onchange={loadRecords}>
					<option value="">All</option>
					{#each Object.entries(actionLabels) as [value, label]}
						<option {value}>{label}</option>
					{/each}
				</select>
			</div>
			{#if hasActiveFilters}
				<button type="button" class="filter-clear" onclick={clearFilters}>
					Clear filters
				</button>
			{/if}
		</div>

		{#if loading}
			<div class="casework-skeleton" aria-busy="true" aria-label="Loading casework records">
				<Skeleton variant="rect" height="6rem" />
				<Skeleton variant="rect" height="6rem" />
				<Skeleton variant="rect" height="6rem" />
			</div>
		{:else if loadError}
			<div class="state-card state-error" role="alert">
				<div class="state-icon state-icon-error" aria-hidden="true">!</div>
				<h2 class="state-title">Couldn't load casework</h2>
				<p class="state-body">{loadError}</p>
				<button type="button" class="btn btn-primary" onclick={loadRecords}>Try again</button>
			</div>
		{:else if records.length === 0}
			<div class="state-card state-empty">
				<div class="state-icon state-icon-empty" aria-hidden="true">✓</div>
				{#if hasActiveFilters}
					<h2 class="state-title">No records match these filters</h2>
					<p class="state-body">Try clearing the filters, or log a new advocacy action.</p>
					<div class="state-actions">
						<button type="button" class="btn btn-secondary" onclick={clearFilters}>Clear filters</button>
						<a href="{base}/casework/new" class="btn btn-primary">+ New Record</a>
					</div>
				{:else}
					<h2 class="state-title">No casework yet</h2>
					<p class="state-body">
						Nothing logged yet. When you take an advocacy action — a call, a filing,
						a meeting — log it here so the next advocate can pick up where you left off.
					</p>
					<div class="state-actions">
						<a href="{base}/casework/new" class="btn btn-primary">+ Log first record</a>
					</div>
				{/if}
			</div>
		{:else}
			<section class="records-list" aria-label="Casework records">
				{#each records as record (record.id)}
					{@const rc = recencyClass(record.date)}
					{@const isConfirming = confirmingDelete === record.id}
					<article class="record-card record-{rc}" class:is-confirming={isConfirming}>
						<div class="record-main">
							<div class="record-head">
								<div class="record-badges">
									<span class="badge badge-action">
										{actionLabels[record.action_type] || record.action_type}
									</span>
									<span class="badge badge-status badge-{statusKind[record.status] || 'unknown'}">
										{statusLabels[record.status] || record.status}
									</span>
									<span class="recency recency-{rc}">
										<span class="recency-dot" aria-hidden="true"></span>
										{formatDate(record.date)}
									</span>
								</div>
								<div class="record-actions">
									<a href="{base}/casework/new?id={record.id}" class="btn btn-secondary btn-sm">
										Edit
									</a>
									{#if isConfirming}
										<button
											type="button"
											class="btn btn-secondary btn-sm"
											onclick={cancelDelete}
											disabled={deleting}
										>Cancel</button>
										<button
											type="button"
											class="btn btn-danger btn-sm"
											onclick={() => performDelete(record.id)}
											disabled={deleting}
											aria-label="Confirm delete this record"
										>
											{#if deleting}
												<span class="spinner-inline" aria-hidden="true"></span>
												Deleting…
											{:else}
												Confirm delete
											{/if}
										</button>
									{:else}
										<button
											type="button"
											class="btn btn-danger-soft btn-sm"
											onclick={() => startDelete(record.id)}
										>Delete</button>
									{/if}
								</div>
							</div>

							<p class="record-description">{record.description}</p>

							{#if record.next_steps}
								<p class="record-meta">
									<strong>Next steps:</strong> {record.next_steps}
								</p>
							{/if}

							{#if record.notes}
								<details class="record-notes">
									<summary>Internal notes</summary>
									<p>{record.notes}</p>
								</details>
							{/if}

							{#if record.performed_by_name}
								<footer class="record-footer">
									<span class="record-author">By {record.performed_by_name}</span>
								</footer>
							{/if}
						</div>

						{#if isConfirming}
							<div class="confirm-panel" role="alertdialog" aria-label="Confirm deletion">
								<div class="confirm-icon" aria-hidden="true">!</div>
								<div class="confirm-body">
									<p class="confirm-title">Delete this record?</p>
									<p class="confirm-text">
										This will permanently remove the
										<strong>{actionLabels[record.action_type] || record.action_type}</strong>
										record from {formatDate(record.date)}. This can't be undone.
									</p>
								</div>
							</div>
						{/if}
					</article>
				{/each}
			</section>
		{/if}
	{/if}
</div>

<style>
	.page-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 1rem;
		margin-bottom: 1.5rem;
		flex-wrap: wrap;
	}
	.page-header h1 {
		margin: 0 0 0.35rem 0;
		color: var(--color-primary);
		font-size: 1.85rem;
		font-weight: 700;
		letter-spacing: -0.01em;
	}
	.page-intro {
		margin: 0;
		max-width: var(--max-w-prose);
		color: var(--color-text);
		font-size: 0.98rem;
		line-height: 1.55;
	}
	.page-intro strong {
		color: var(--color-primary);
		font-weight: 600;
	}
	.header-cta {
		flex: 0 0 auto;
		white-space: nowrap;
	}

	.banner {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		padding: 0.7rem 0.9rem;
		margin-bottom: 1.25rem;
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-subtle);
		border-left: 4px solid var(--color-primary);
		border-radius: var(--radius-input);
		box-shadow: var(--shadow-card);
	}
	.banner-success { border-left-color: var(--color-success); }
	.banner-error { border-left-color: var(--color-danger); }
	.banner-icon {
		flex: 0 0 auto;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 22px;
		height: 22px;
		border-radius: 50%;
		font-size: 0.85rem;
		font-weight: 700;
		font-family: 'Georgia', serif;
		color: white;
	}
	.banner-success .banner-icon { background: var(--color-success); }
	.banner-error .banner-icon { background: var(--color-danger); }
	.banner-text {
		flex: 1 1 auto;
		color: var(--color-text);
		font-size: 0.92rem;
	}
	.banner-dismiss {
		flex: 0 0 auto;
		background: transparent;
		border: 0;
		color: var(--color-text-muted);
		font-size: 1.3rem;
		cursor: pointer;
		padding: 0 0.2rem;
	}
	.banner-dismiss:hover { color: var(--color-text); }

	.filters {
		display: flex;
		gap: 1rem;
		align-items: flex-end;
		flex-wrap: wrap;
		margin-bottom: 1.25rem;
		padding: 0.9rem 1.1rem;
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-subtle);
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-card);
	}
	.filter-group {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
		min-width: 180px;
		flex: 0 1 auto;
	}
	.filter-group label {
		font-size: 0.78rem;
		font-weight: 600;
		color: var(--color-primary);
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}
	.filter-group select {
		appearance: none;
		-webkit-appearance: none;
		padding: 0.5rem 2rem 0.5rem 0.75rem;
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-input);
		background: var(--color-bg-white);
		color: var(--color-text);
		font-family: inherit;
		font-size: 0.92rem;
		background-image: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2325646a' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
		background-repeat: no-repeat;
		background-position: right 0.7rem center;
		background-size: 11px 11px;
		transition: border-color 0.15s ease, box-shadow 0.15s ease;
	}
	.filter-group select:focus {
		outline: none;
		border-color: var(--color-primary);
		box-shadow: 0 0 0 3px var(--color-primary-tint);
	}
	.filter-clear {
		background: transparent;
		border: 0;
		color: var(--color-primary-light);
		font-size: 0.88rem;
		font-weight: 500;
		cursor: pointer;
		padding: 0.55rem 0.4rem;
		text-decoration: underline;
		text-underline-offset: 2px;
		margin-bottom: 2px;
	}
	.filter-clear:hover { color: var(--color-primary); }

	.records-list {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
	.record-card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-subtle);
		border-left: 3px solid var(--color-primary);
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-card);
		padding: 1rem 1.25rem 1.1rem;
		transition: box-shadow 0.15s ease, border-color 0.15s ease;
	}
	.record-card:hover { box-shadow: var(--shadow-card-hover); }
	.record-card.is-confirming { border-left-color: var(--color-danger); }
	.record-fresh { border-left-color: var(--color-success); }
	.record-stale { border-left-color: #c97a0d; }
	.record-urgent { border-left-color: var(--color-danger); }

	.record-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		margin-bottom: 0.55rem;
		flex-wrap: wrap;
	}
	.record-badges {
		display: flex;
		align-items: center;
		gap: 0.45rem;
		flex-wrap: wrap;
	}
	.badge {
		display: inline-flex;
		align-items: center;
		padding: 0.18rem 0.5rem;
		font-size: 0.74rem;
		font-weight: 600;
		border-radius: 4px;
		letter-spacing: 0.02em;
	}
	.badge-action {
		background: var(--color-primary-tint);
		color: var(--color-primary);
	}
	.badge-status { color: white; }
	.badge-detained { background: var(--color-danger); }
	.badge-released { background: var(--color-success); }
	.badge-unknown { background: #c97a0d; }

	.recency {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		font-size: 0.82rem;
		color: var(--color-text-muted);
		font-weight: 500;
	}
	.recency-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex: 0 0 8px;
	}
	.recency-fresh .recency-dot {
		background: var(--color-success);
		box-shadow: 0 0 0 3px rgba(47, 133, 90, 0.18);
	}
	.recency-stale .recency-dot { background: #c97a0d; }
	.recency-urgent .recency-dot {
		background: var(--color-danger);
		box-shadow: 0 0 0 3px rgba(217, 22, 22, 0.18);
	}

	.record-actions {
		display: flex;
		gap: 0.4rem;
		flex: 0 0 auto;
	}
	.btn-sm {
		padding: 0.35rem 0.8rem;
		font-size: 0.82rem;
		min-width: 0;
	}
	:global(.btn.btn-danger-soft) {
		background: transparent;
		color: var(--color-danger);
		border: 1px solid var(--color-border-light);
	}
	:global(.btn.btn-danger-soft:hover) {
		background: rgba(217, 22, 22, 0.08);
		border-color: var(--color-danger);
	}
	:global(.btn.btn-danger) {
		background: var(--color-danger);
		color: var(--color-text-light);
		border: 1px solid var(--color-danger);
	}
	:global(.btn.btn-danger:hover:not(:disabled)) {
		background: #b51313;
		border-color: #b51313;
	}
	:global(.btn.btn-danger:disabled) {
		opacity: 0.7;
		cursor: not-allowed;
	}
	.spinner-inline {
		display: inline-block;
		width: 11px;
		height: 11px;
		border: 2px solid currentColor;
		border-right-color: transparent;
		border-radius: 50%;
		animation: spin 0.7s linear infinite;
		vertical-align: middle;
		margin-right: 0.2rem;
	}
	@keyframes spin { to { transform: rotate(360deg); } }

	.record-description {
		margin: 0 0 0.45rem 0;
		color: var(--color-text);
		font-size: 0.95rem;
		line-height: 1.55;
	}
	.record-meta {
		margin: 0.3rem 0 0;
		color: var(--color-text);
		font-size: 0.88rem;
		line-height: 1.5;
	}
	.record-notes {
		margin-top: 0.4rem;
		font-size: 0.85rem;
	}
	.record-notes summary {
		cursor: pointer;
		color: var(--color-text-muted);
		font-weight: 500;
		padding: 0.25rem 0;
	}
	.record-notes summary:hover { color: var(--color-primary); }
	.record-notes p {
		margin: 0.4rem 0 0;
		padding: 0.6rem 0.8rem;
		background: var(--color-surface);
		border-radius: var(--radius-input);
		color: var(--color-text);
		line-height: 1.5;
		white-space: pre-wrap;
	}
	.record-footer {
		display: flex;
		justify-content: flex-end;
		margin-top: 0.6rem;
	}
	.record-author {
		font-size: 0.78rem;
		color: var(--color-text-muted);
	}

	/* Inline confirm panel */
	.confirm-panel {
		display: flex;
		gap: 0.75rem;
		align-items: flex-start;
		margin-top: 0.85rem;
		padding: 0.75rem 0.9rem;
		background: rgba(217, 22, 22, 0.04);
		border: 1px solid var(--color-danger);
		border-radius: var(--radius-input);
	}
	.confirm-icon {
		flex: 0 0 auto;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 26px;
		height: 26px;
		border-radius: 50%;
		background: var(--color-danger);
		color: white;
		font-family: 'Georgia', serif;
		font-style: italic;
		font-weight: 700;
		font-size: 0.95rem;
		line-height: 1;
	}
	.confirm-body { flex: 1 1 auto; min-width: 0; }
	.confirm-title {
		margin: 0 0 0.15rem 0;
		color: var(--color-text);
		font-size: 0.92rem;
		font-weight: 700;
	}
	.confirm-text {
		margin: 0;
		color: var(--color-text-muted);
		font-size: 0.85rem;
		line-height: 1.45;
	}

	.casework-skeleton {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
	.state-card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-subtle);
		border-radius: var(--radius-card-lg);
		padding: 2.5rem 2rem;
		text-align: center;
		box-shadow: var(--shadow-card);
		max-width: 540px;
		margin: 1.5rem auto;
	}
	.state-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 48px;
		height: 48px;
		border-radius: 50%;
		font-family: 'Georgia', serif;
		font-style: italic;
		font-weight: 700;
		font-size: 1.4rem;
		color: white;
		margin-bottom: 1rem;
	}
	.state-icon-empty { background: var(--color-success); }
	.state-icon-error { background: var(--color-danger); }
	.state-title {
		margin: 0 0 0.5rem 0;
		color: var(--color-text);
		font-size: 1.15rem;
		font-weight: 700;
	}
	.state-body {
		margin: 0 0 1.25rem 0;
		color: var(--color-text-muted);
		font-size: 0.95rem;
		line-height: 1.55;
	}
	.state-actions {
		display: flex;
		justify-content: center;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	@media (max-width: 720px) {
		.page-header {
			flex-direction: column;
			align-items: stretch;
		}
		.header-cta { width: 100%; }
		.filter-group { min-width: 100%; }
		.record-head {
			flex-direction: column;
			align-items: stretch;
		}
		.record-actions { justify-content: flex-end; flex-wrap: wrap; }
	}

	@media (prefers-reduced-motion: reduce) {
		.record-card,
		.recency-dot,
		.spinner-inline {
			transition: none;
			animation: none;
		}
	}
</style>
