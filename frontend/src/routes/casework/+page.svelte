<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { user, isAdvocate } from '$lib/session';
	import {
		getCasework,
		deleteCasework,
		type CaseworkRecord as ApiCaseworkRecord,
	} from '$lib/api';
	import Toast from '$lib/Toast.svelte';
	import ConfirmDialog from '$lib/ConfirmDialog.svelte';
	import Skeleton from '$lib/Skeleton.svelte';
	import { toastSuccess, toastError } from '$lib/toast';

	let currentUser = $derived($user);
	let records: ApiCaseworkRecord[] = $state([]);
	let loading = $state(true);
	let loadError = $state('');
	let filterStatus = $state('');
	let filterAction = $state('');

	// Delete confirmation state
	let deleteTarget: ApiCaseworkRecord | null = $state(null);
	let deleting = $state(false);

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

	onMount(() => loadRecords());

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

	function startDelete(record: ApiCaseworkRecord) {
		deleteTarget = record;
	}

	function cancelDelete() {
		deleteTarget = null;
	}

	async function confirmDelete() {
		if (!deleteTarget) return;
		deleting = true;
		const target = deleteTarget;
		try {
			await deleteCasework(target.id);
			records = records.filter((r) => r.id !== target.id);
			toastSuccess('Record deleted', `The ${actionLabels[target.action_type] ?? target.action_type} record was removed.`);
		} catch (e: any) {
			toastError(
				"Couldn't delete that record",
				e?.message || 'Please try again in a moment.',
			);
		} finally {
			deleting = false;
			deleteTarget = null;
		}
	}

	function clearFilters() {
		filterStatus = '';
		filterAction = '';
		loadRecords();
	}

	const hasActiveFilters = $derived(!!filterStatus || !!filterAction);
	const activeCount = $derived(records.length);
	const openCount = $derived(records.filter((r) => r.status === 'open').length);
	const inProgressCount = $derived(records.filter((r) => r.status === 'in_progress').length);
	const doneCount = $derived(records.filter((r) => r.status === 'done').length);
</script>

<svelte:head>
	<title>Casework — Testimonies.world</title>
</svelte:head>

<Toast />

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
					Every advocacy action logged against a case — outreach, legal filings,
					media, follow-ups. Filter, edit, or remove any record below.
				</p>
			</div>
			<a href="{base}/casework/new" class="btn btn-primary header-cta">+ New Record</a>
		</header>

		<!-- ============== Stats strip ============== -->
		{#if !loading && !loadError && activeCount > 0}
			<div class="stats-strip" aria-label="Casework counts">
				<div class="stat-cell">
					<span class="stat-num">{activeCount}</span>
					<span class="stat-lbl">Total</span>
				</div>
				<div class="stat-cell stat-open">
					<span class="stat-num">{openCount}</span>
					<span class="stat-lbl">Open</span>
				</div>
				<div class="stat-cell stat-progress">
					<span class="stat-num">{inProgressCount}</span>
					<span class="stat-lbl">In progress</span>
				</div>
				<div class="stat-cell stat-done">
					<span class="stat-num">{doneCount}</span>
					<span class="stat-lbl">Done</span>
				</div>
			</div>
		{/if}

		<!-- ============== Filters ============== -->
		<section class="filters-card" aria-label="Filter records">
			<div class="filters-row">
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
		</section>

		<!-- ============== Loading state ============== -->
		{#if loading}
			<div class="casework-skeleton" aria-busy="true" aria-label="Loading casework records">
				<Skeleton variant="rect" height="6rem" />
				<Skeleton variant="rect" height="6rem" />
				<Skeleton variant="rect" height="6rem" />
			</div>

		<!-- ============== Error state ============== -->
		{:else if loadError}
			<div class="state-card state-error" role="alert">
				<div class="state-icon state-icon-error" aria-hidden="true">!</div>
				<h2 class="state-title">Couldn't load casework</h2>
				<p class="state-body">{loadError}</p>
				<button type="button" class="btn btn-primary" onclick={loadRecords}>Try again</button>
			</div>

		<!-- ============== Empty state ============== -->
		{:else if activeCount === 0}
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

		<!-- ============== Records ============== -->
		{:else}
			<section class="records-list" aria-label="Casework records">
				{#each records as record (record.id)}
					{@const rc = recencyClass(record.date)}
					<article class="record-card record-{rc}">
						<div class="record-main">
							<div class="record-head">
								<div class="record-badges">
									<span class="badge badge-action">
										{actionLabels[record.action_type] || record.action_type}
									</span>
									<span class="badge badge-status badge-{statusKind[record.status] || 'unknown'}">
										{statusLabels[record.status] || record.status}
									</span>
									<span class="recency recency-{rc}" title="Date of action">
										<span class="recency-dot" aria-hidden="true"></span>
										{formatDate(record.date)}
									</span>
								</div>
								<div class="record-actions">
									<a href="{base}/casework/{record.id}" class="btn btn-secondary btn-sm">
										Edit
									</a>
									<button
										type="button"
										class="btn btn-danger-soft btn-sm"
										onclick={() => startDelete(record)}
									>
										Delete
									</button>
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

							<footer class="record-footer">
								{#if record.performed_by_name}
									<span class="record-author">By {record.performed_by_name}</span>
								{/if}
							</footer>
						</div>
					</article>
				{/each}
			</section>
		{/if}
	{/if}
</div>

<ConfirmDialog
	open={deleteTarget !== null}
	title="Delete this record?"
	body={deleteTarget
		? `This will permanently remove the ${actionLabels[deleteTarget.action_type] ?? deleteTarget.action_type} record from ${formatDate(deleteTarget.date)}. This can't be undone.`
		: ''}
	confirmLabel="Delete record"
	cancelLabel="Keep it"
	kind="danger"
	confirming={deleting}
	onConfirm={confirmDelete}
	onCancel={cancelDelete}
/>

<style>
	/* === Page header === */
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
	.header-cta {
		flex: 0 0 auto;
		white-space: nowrap;
	}

	/* === Stats strip === */
	.stats-strip {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 0.75rem;
		margin-bottom: 1.5rem;
	}
	.stat-cell {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-subtle);
		border-radius: var(--radius-input);
		padding: 0.75rem 0.9rem;
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
		box-shadow: var(--shadow-card);
	}
	.stat-num {
		font-size: 1.6rem;
		font-weight: 700;
		color: var(--color-primary);
		font-variant-numeric: tabular-nums;
		line-height: 1.1;
	}
	.stat-lbl {
		font-size: 0.78rem;
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.04em;
		font-weight: 600;
	}
	.stat-open .stat-num { color: var(--color-danger); }
	.stat-progress .stat-num { color: #c97a0d; }
	.stat-done .stat-num { color: var(--color-success); }

	/* === Filters === */
	.filters-card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-subtle);
		border-radius: var(--radius-card-lg);
		padding: 1rem 1.25rem;
		margin-bottom: 1.25rem;
		box-shadow: var(--shadow-card);
	}
	.filters-row {
		display: flex;
		gap: 1rem;
		align-items: flex-end;
		flex-wrap: wrap;
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
	.filter-clear:hover {
		color: var(--color-primary);
	}

	/* === Records === */
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
		transition: box-shadow 0.15s ease, transform 0.15s ease;
	}
	.record-card:hover {
		box-shadow: var(--shadow-card-hover);
		transform: translateY(-1px);
	}
	.record-fresh {
		border-left-color: var(--color-success);
	}
	.record-stale {
		border-left-color: #c97a0d;
	}
	.record-urgent {
		border-left-color: var(--color-danger);
	}

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
	.badge-status {
		color: white;
	}
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
	.recency-stale .recency-dot {
		background: #c97a0d;
	}
	.recency-urgent .recency-dot {
		background: var(--color-danger);
		box-shadow: 0 0 0 3px rgba(217, 22, 22, 0.18);
		animation: pulse 2.5s ease-in-out infinite;
	}
	@keyframes pulse {
		0%, 100% { box-shadow: 0 0 0 3px rgba(217, 22, 22, 0.18); }
		50% { box-shadow: 0 0 0 6px rgba(217, 22, 22, 0.06); }
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
	.record-notes summary:hover {
		color: var(--color-primary);
	}
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

	/* === States (loading / error / empty) === */
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
	.state-icon-empty {
		background: var(--color-success);
	}
	.state-icon-error {
		background: var(--color-danger);
	}
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

	/* === Responsive === */
	@media (max-width: 720px) {
		.stats-strip {
			grid-template-columns: repeat(2, 1fr);
		}
		.page-header {
			flex-direction: column;
			align-items: stretch;
		}
		.header-cta {
			width: 100%;
		}
		.filter-group {
			min-width: 100%;
		}
		.record-head {
			flex-direction: column;
			align-items: stretch;
		}
		.record-actions {
			justify-content: flex-end;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.record-card,
		.recency-dot {
			transition: none;
			animation: none;
		}
	}
</style>
