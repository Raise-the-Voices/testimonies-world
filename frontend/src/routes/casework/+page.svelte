<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { fly } from 'svelte/transition';
	import { user, isAdvocate } from '$lib/session';
	import { getCasework, deleteCasework } from '$lib/api';
	import Skeleton from '$lib/Skeleton.svelte';

	let currentUser = $derived($user);
	let records: any[] = $state([]);
	let loading = $state(true);
	let loadError = $state('');
	let filterStatus = $state('');
	let filterAction = $state('');

	// Top-of-page delete toast state.
	// Stages: 'confirming' (Cancel + Confirm), 'deleting' (request in flight,
	// button shows spinner), 'success' (auto-dismiss after 2s), 'error' (sticky
	// until user closes). Carries enough of the record to render the toast text.
	type DeleteStage = 'confirming' | 'deleting' | 'success' | 'error';
	interface DeleteToast {
		id: number;
		actionType: string;
		date: string;
		stage: DeleteStage;
		errorMessage?: string;
	}
	let deleteToast = $state<DeleteToast | null>(null);
	let toastTimer: ReturnType<typeof setTimeout> | null = null;

	// Esc closes the toast (confirming + error stages). Modal-like behavior
	// only when the toast is open — Cancel already handles clicks.
	function onToastKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' && deleteToast) {
			e.preventDefault();
			cancelDelete();
		}
	}

	// Banner state — sourced from URL on mount, can be set directly too.
	// Auto-dismisses after BANNER_TTL_MS unless the X button clears it
	// sooner. Re-showing the banner (e.g. after a second save) resets the
	// timer via the $effect cleanup.
	let bannerMsg = $state('');
	let bannerKind = $state<'success' | 'error'>('success');
	const BANNER_TTL_MS = 3500;

	$effect(() => {
		if (!bannerMsg) return;
		const id = setTimeout(() => {
			bannerMsg = '';
		}, BANNER_TTL_MS);
		return () => clearTimeout(id);
	});

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

	function clearToastTimer() {
		if (toastTimer) {
			clearTimeout(toastTimer);
			toastTimer = null;
		}
	}

	// Svelte action: focus an element when it's mounted. Used on the toast's
	// Cancel button so a stray Enter is a no-op rather than a destructive
	// confirm. Svelte's `autofocus` attribute warns under a11y rules; doing
	// it imperatively via an action keeps the focus management explicit and
	// reviewable, and avoids the warning.
	function autofocus(node: HTMLElement) {
		node.focus();
	}

	// Global Esc handler while the toast is open. Mounted/unmounted with the
	// toast so we don't leak listeners when the page goes away mid-flow.
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

	function startDelete(id: number, actionType: string, date: string) {
		clearToastTimer();
		deleteToast = { id, actionType, date, stage: 'confirming' };
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
			await deleteCasework(target.id);
			records = records.filter((r) => r.id !== target.id);
			deleteToast = { ...target, stage: 'success' };
			// Auto-dismiss the success toast after 2s.
			clearToastTimer();
			toastTimer = setTimeout(() => {
				if (deleteToast?.id === target.id) deleteToast = null;
			}, 2000);
		} catch (e: any) {
			deleteToast = {
				...target,
				stage: 'error',
				errorMessage: e?.message || "Couldn't delete that record. Please try again.",
			};
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
			<h1 class="page-title">
				Casework
				{#if !loading && records.length > 0 && !loadError}
					<span class="page-title-count" aria-label="{records.length} records">· {records.length}</span>
				{/if}
			</h1>
			<a href="{base}/casework/new" class="btn btn-primary header-cta">+ New record</a>
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
			<!--
				Backdrop: dimmed, blurred. Clicks dismiss the toast (safe default —
				destructive confirmations require a deliberate Confirm click).
				`role="presentation"` because the dialog itself is the focusable surface.
			-->
			<div
				class="delete-toast-overlay"
				onclick={cancelDelete}
				role="presentation"
			></div>

			<!--
				Fixed top-of-page toast. Lives here in DOM order (just under the
				banner) for logical reading order; CSS positions it at the viewport
				top with backdrop blur over the rest of the page. Cancel button is
				auto-focused so a stray Enter is a no-op rather than a delete.
			-->
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
							Delete this record?
						{:else if deleteToast.stage === 'deleting'}
							Deleting record…
						{:else if deleteToast.stage === 'success'}
							Record deleted
						{:else}
							Couldn’t delete this record
						{/if}
					</h2>
					<p id="delete-toast-text" class="delete-toast-text">
						{#if deleteToast.stage === 'confirming'}
							This <strong>{actionLabels[deleteToast.actionType] || deleteToast.actionType}</strong>
							from {formatDate(deleteToast.date)} will be permanently removed. This action cannot be undone.
						{:else if deleteToast.stage === 'deleting'}
							Please wait while the record is removed.
						{:else if deleteToast.stage === 'success'}
							The record has been removed from your list.
						{:else}
							{deleteToast.errorMessage}
						{/if}
					</p>
				</div>
				<div class="delete-toast-actions">
					{#if deleteToast.stage === 'confirming'}
						<button
							type="button"
							class="btn btn-secondary btn-sm"
							onclick={cancelDelete}
							use:autofocus
						>Cancel</button>
						<button
							type="button"
							class="btn btn-danger btn-sm"
							onclick={performDelete}
						>Delete</button>
					{:else if deleteToast.stage === 'deleting'}
						<button
							type="button"
							class="btn btn-secondary btn-sm"
							disabled
						>Deleting…</button>
					{:else}
						<button
							type="button"
							class="btn btn-secondary btn-sm"
							onclick={cancelDelete}
						>Close</button>
					{/if}
				</div>
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
					<article class="record-card">
						<div class="record-main">
							<div class="record-head">
								<div class="record-badges">
									<span class="badge badge-action">
										{actionLabels[record.action_type] || record.action_type}
									</span>
									<span class="badge badge-status badge-{statusKind[record.status] || 'unknown'}">
										{statusLabels[record.status] || record.status}
									</span>
									<span class="record-date">— {formatDate(record.date)}</span>
								</div>
								<div class="record-actions">
									<a href="{base}/casework/new?id={record.id}" class="btn btn-secondary btn-sm">
										Edit
									</a>
									<button
										type="button"
										class="btn btn-danger-soft btn-sm"
										onclick={() => startDelete(record.id, record.action_type, record.date)}
										aria-label="Delete this record"
									>Delete</button>
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
									<span class="record-author"><span class="record-author-mark" aria-hidden="true">·</span> By {record.performed_by_name}</span>
									{#if record.seen_by && record.seen_by.length > 0}
										<span class="record-seen" aria-label="Seen by {record.seen_by.length} advocate{record.seen_by.length === 1 ? '' : 's'}">
											· Seen by {record.seen_by.slice(0, 3).map((s: { name: string }) => s.name).join(', ')}{record.seen_by.length > 3 ? ` +${record.seen_by.length - 3}` : ''}
										</span>
									{/if}
								</footer>
							{/if}
						</div>
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
		margin-bottom: 1.75rem;
		flex-wrap: wrap;
	}
	.page-title {
		margin: 0;
		color: var(--color-primary);
		font-size: 1.85rem;
		font-weight: 700;
		letter-spacing: -0.01em;
		line-height: 1.2;
	}
	.page-title-count {
		color: var(--color-text-muted);
		font-weight: 500;
		font-size: 1.05rem;
		margin-left: 0.4rem;
		font-variant-numeric: tabular-nums;
	}
	.header-cta {
		flex: 0 0 auto;
		white-space: nowrap;
		align-self: center;
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
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-card);
		padding: 1rem 1.25rem 1.1rem;
		/* Smooth hover lift — shadow + border tint together so the card
		   feels responsive without being noisy. */
		transition:
			box-shadow 0.18s ease,
			border-color 0.18s ease,
			transform 0.18s ease;
	}
	.record-card:hover {
		box-shadow: var(--shadow-card-hover);
		border-color: var(--color-primary-light, var(--color-border-subtle));
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
	.badge-status { color: white; }
	.badge-detained { background: var(--color-danger); }
	.badge-released { background: var(--color-success); }
	.badge-unknown { background: #c97a0d; }

	/* Date inside the badge row — plain, muted, prefixed with an em-dash so
	   it reads as metadata, not as a separate status pill. */
	.record-date {
		font-size: 0.82rem;
		color: var(--color-text-muted);
		font-weight: 500;
		letter-spacing: 0.01em;
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
	/* Byline at the bottom of the card — far right, plenty of breathing room
	   above so it sits clearly as metadata, not part of the description. */
	.record-footer {
		display: flex;
		justify-content: flex-end;
		flex-wrap: wrap;
		gap: 0.25rem 0.6rem;
		margin-top: 1rem;
		padding-top: 0.6rem;
		border-top: 1px solid var(--color-border-subtle);
	}
	.record-author {
		font-size: 0.78rem;
		color: var(--color-text-muted);
		font-weight: 500;
		letter-spacing: 0.01em;
	}
	.record-author-mark {
		margin-right: 0.35rem;
		opacity: 0.6;
	}
	.record-seen {
		font-size: 0.78rem;
		color: var(--color-text-muted);
		font-weight: 500;
		letter-spacing: 0.01em;
	}

	/* ============================================================
	   Delete toast (fixed top-of-page)
	   - Backdrop dims + blurs the page so the user's eye lands here
	   - Card sits at the viewport top, not nested inside any card
	   - Top border color encodes stage: danger / success / danger
	   ============================================================ */
	.delete-toast-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.28);
		backdrop-filter: blur(4px);
		-webkit-backdrop-filter: blur(4px);
		z-index: 90;
		animation: deleteToastFadeIn 0.18s ease both;
	}
	.delete-toast {
		position: fixed;
		top: 1.25rem;
		left: 50%;
		transform: translateX(-50%);
		z-index: 100;
		width: min(560px, calc(100vw - 2rem));
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-subtle);
		border-left: 4px solid var(--color-danger);
		border-radius: var(--radius-card-lg);
		box-shadow: 0 14px 36px rgba(0, 0, 0, 0.22);
		padding: 1.1rem 1.25rem;
		display: flex;
		gap: 0.9rem;
		align-items: flex-start;
		animation: deleteToastSlideDown 0.22s ease both;
	}
	.delete-toast-success { border-left-color: var(--color-success); }
	.delete-toast-error { border-left-color: var(--color-danger); }
	/* Stage indicator — a small left accent bar instead of the old circular
	   icon well. Reads as part of the card, not as a cartoon badge. */
	.delete-toast-body { flex: 1 1 auto; min-width: 0; }
	.delete-toast-title {
		margin: 0 0 0.2rem 0;
		color: var(--color-text);
		font-size: 1rem;
		font-weight: 700;
		line-height: 1.3;
	}
	.delete-toast-text {
		margin: 0;
		color: var(--color-text-muted);
		font-size: 0.9rem;
		line-height: 1.5;
	}
	.delete-toast-text strong {
		color: var(--color-text);
		font-weight: 600;
	}
	.delete-toast-actions {
		flex: 0 0 auto;
		display: flex;
		gap: 0.4rem;
		align-items: center;
	}
	@keyframes deleteToastFadeIn {
		from { opacity: 0; }
		to   { opacity: 1; }
	}
	@keyframes deleteToastSlideDown {
		from { opacity: 0; transform: translate(-50%, -10px); }
		to   { opacity: 1; transform: translate(-50%, 0); }
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
		.delete-toast {
			top: 0.75rem;
			padding: 0.95rem 1rem;
			gap: 0.7rem;
		}
		.delete-toast-actions { width: 100%; }
		.delete-toast-actions :global(.btn) { flex: 1 1 0; }
	}

	@media (prefers-reduced-motion: reduce) {
		.record-card,
		.spinner-inline,
		.delete-toast,
		.delete-toast-overlay {
			transition: none;
			animation: none;
		}
	}
</style>
