<!--
  /dashboard/audit-logs — staff-only audit log page.

  Layout (desktop):
    ┌─────────────────────────────────────────────────┐
    │ Header: title + subtitle                         │
    ├─────────────────────────────────────────────────┤
    │ Filters card (DashboardCard)                     │
    ├─────────────────────────────────────────────────┤
    │ Results card (DashboardCard)                     │
    │   - "Showing N entries"                          │
    │   - <ul.activity-feed> via ActivityItem          │
    │   - pagination controls                          │
    └─────────────────────────────────────────────────┘

  Visual alignment with the dashboard
  -----------------------------------
  The activity list reuses ActivityItem — the same component the
  dashboard's "Recent activity" widget uses — so the two surfaces
  read as one product. The audit log adds two fields the widget
  doesn't have room for (target link, secondary details/IP line)
  via ActivityItem's optional props.

  Filter syncs to the URL via SvelteKit `goto(...)`. Each input's
  oncommit (blur / change / Enter) rebuilds the URLSearchParams,
  strips empty values, and navigates — +page.ts re-runs and the
  list re-renders. Pagination preserves the current filter params
  (otherwise going to page 2 would clear filters).

  PAGE_SIZE matches the backend default (settings.py REST_FRAMEWORK).
  Bump both together if the global default ever changes.
-->
<script lang="ts" module>
	/** Default page size — matches AuditLogPagination.page_size in the
	 *  backend. The dropdown options below are the values the user
	 *  can pick; bump both together if the backend default ever moves. */
	export const PAGE_SIZE = 25;
	/** Page-size choices offered in the dropdown. Capped at 200 to keep
	 *  the table scannable; the backend caps at 500 so any value here
	 *  is honored. */
	const PAGE_SIZE_OPTIONS = [10, 25, 50, 100, 200] as const;
</script>

<script lang="ts">
	import { untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { base } from '$app/paths';
	import { user as userStore } from '$lib/session';
	import type { PageData } from './$types';
	import DashboardCard from '$lib/DashboardCard.svelte';
	import ActivityItem from '$lib/ActivityItem.svelte';
	import AuditLogsFilters from '$lib/AuditLogsFilters.svelte';
	import ErrorCard from '$lib/ErrorCard.svelte';

	let { data }: { data: PageData } = $props();

	// SSR-hydrated auth (see +layout.svelte for the full rationale).
	const currentUser = $derived(data.user ?? $userStore);

	function convertIsoToLocal(iso: string): string {
		// Backend returns ISO 8601 (often with Z or +00:00).
		// <input type="datetime-local"> expects `YYYY-MM-DDTHH:mm`.
		if (!iso) return '';
		return iso.slice(0, 16);
	}

	function parsePageSize(raw: string | undefined): number {
		const n = raw ? Number(raw) : NaN;
		if (Number.isFinite(n) && (PAGE_SIZE_OPTIONS as readonly number[]).includes(n)) return n;
		return PAGE_SIZE;
	}

	let username = $state(untrack(() => data.requestParams.user__username ?? ''));
	let action = $state(untrack(() => data.requestParams.action ?? ''));
	let targetType = $state(untrack(() => data.requestParams.target_type ?? ''));
	let search = $state(untrack(() => data.requestParams.search ?? ''));
	let timestampAfter = $state(untrack(() => convertIsoToLocal(data.requestParams.timestamp_after ?? '')));
	let timestampBefore = $state(untrack(() => convertIsoToLocal(data.requestParams.timestamp_before ?? '')));
	// pageSize mirrors ?page_size= in the URL so deep-links survive a
	// reload. Falls back to PAGE_SIZE when the param is absent or invalid.
	let pageSize = $state(untrack(() => parsePageSize(data.requestParams.page_size)));
	let jumpTo = $state<number>(untrack(() => currentPageFromUrl()));

	function currentPageFromUrl(): number {
		const p = $page.url.searchParams.get('page');
		const n = p ? Number(p) : 1;
		return Number.isFinite(n) && n >= 1 ? n : 1;
	}

	function buildParams(nextPage: number | null = null): URLSearchParams {
		const params = new URLSearchParams();
		if (username.trim()) params.set('user__username', username.trim());
		if (action) params.set('action', action);
		if (targetType) params.set('target_type', targetType);
		if (search.trim()) params.set('search', search.trim());
		if (timestampAfter) params.set('timestamp_after', timestampAfter);
		if (timestampBefore) params.set('timestamp_before', timestampBefore);
		// Omit page_size when it's the default — keeps the URL clean
		// and matches the case where the backend itself omits it.
		if (pageSize !== PAGE_SIZE) params.set('page_size', String(pageSize));
		if (nextPage && nextPage > 1) {
			params.set('page', String(nextPage));
		} else if (nextPage === null) {
			// Preserve the current page when applying filters — let the
			// user stay on page 2 even if they tweak a filter.
			const cur = currentPageFromUrl();
			if (cur > 1) params.set('page', String(cur));
		}
		return params;
	}

	function applyFilters() {
		const params = buildParams(null); // changing filters keeps current page
		const qs = params.toString();
		goto(qs ? `?${qs}` : $page.url.pathname, { replaceState: true, noScroll: true });
	}

	function goToPage(pageNum: number) {
		const params = buildParams(pageNum);
		const qs = params.toString();
		goto(qs ? `?${qs}` : $page.url.pathname, { replaceState: true, noScroll: true });
	}

	/** Changing page size resets to page 1 — keeping the old page
	 *  number is meaningless once the slice size shifts. */
	function changePageSize() {
		const params = buildParams(1);
		const qs = params.toString();
		goto(qs ? `?${qs}` : $page.url.pathname, { replaceState: true, noScroll: true });
	}

	/** Clamp the jump-to input to [1, totalPages] and navigate. No-op
	 *  when the target equals the current page. */
	function jumpToPage() {
		const total = pagesTotal();
		const target = Math.max(1, Math.min(total, Math.floor(jumpTo) || 1));
		if (target !== currentPageFromUrl()) goToPage(target);
	}

	function clearFilters() {
		username = '';
		action = '';
		targetType = '';
		search = '';
		timestampAfter = '';
		timestampBefore = '';
		goto($page.url.pathname, { replaceState: true, noScroll: true });
	}

	function formatWhen(iso: string): string {
		const then = new Date(iso).getTime();
		if (Number.isNaN(then)) return iso;
		const diffMs = Date.now() - then;
		const mins = Math.floor(diffMs / 60000);
		if (mins < 1) return 'just now';
		if (mins < 60) return `${mins}m ago`;
		const hours = Math.floor(mins / 60);
		if (hours < 24) return `${hours}h ago`;
		const days = Math.floor(hours / 24);
		if (days < 30) return `${days}d ago`;
		return new Date(iso).toLocaleString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit',
		});
	}

	/** Only `person` has a known URL pattern today. Other target_types
	 *  (report, media, contact, casework, ...) don't have a dedicated
	 *  detail page yet, so the cell stays a static span instead of a
	 *  dead link. */
	function targetHref(targetType: string, targetId: number): string | null {
		if (targetType === 'person') return `${base}/persons/${targetId}`;
		return null;
	}

	/** Build the secondary line that ActivityItem renders under the
	 *  primary meta. Combines details + IP, with a `—` fallback for
	 *  empty fields so the line collapses cleanly when both are blank. */
	function buildSecondary(details: string, ip: string | null | undefined): string {
		const d = details?.trim() ?? '';
		const i = ip?.trim() ?? '';
		if (d && i) return `${d}  ·  IP ${i}`;
		if (d) return d;
		if (i) return `IP ${i}`;
		return '';
	}

	// Derived: page count + window for the numeric pagination strip.
	function pagesTotal(): number {
		const count = data.logs?.count ?? 0;
		return Math.max(1, Math.ceil(count / pageSize));
	}

	/** Build the page-number strip shown inside the pagination nav.
	 *  Always shows first and last, current ± 1, and an ellipsis on
	 *  each gap when the window doesn't bridge them. */
	function buildPageList(current: number, total: number): (number | 'ellipsis')[] {
		if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
		const pages: (number | 'ellipsis')[] = [1];
		const start = Math.max(2, current - 1);
		const end = Math.min(total - 1, current + 1);
		if (start > 2) pages.push('ellipsis');
		for (let i = start; i <= end; i++) pages.push(i);
		if (end < total - 1) pages.push('ellipsis');
		pages.push(total);
		return pages;
	}
</script>

<svelte:head>
	<title>Audit log — Testimonies.world</title>
	<meta name="description" content="Staff-only record of every CRUD action on sensitive viewsets. Filter by user, action, target type, or time range." />
	<meta property="og:description" content="Staff-only record of every CRUD action on sensitive viewsets. Filter by user, action, target type, or time range." />
	<meta property="og:type" content="website" />
	<meta name="twitter:description" content="Staff-only record of every CRUD action on sensitive viewsets. Filter by user, action, target type, or time range." />
</svelte:head>

<div class="audit-page">
	<header class="page-header">
		<div>
			<h1>Audit log</h1>
			<p class="page-subtitle">
				Staff-only record of every CRUD action on sensitive viewsets. Filter by user,
				action, target type, or time range.
			</p>
		</div>
	</header>

	{#if data.error}
		<ErrorCard
			title="Couldn't load the audit log"
			message={data.error}
			kind="network"
		/>
	{:else if data.logs}
		<DashboardCard
			title="Filters"
			subtitle="URL syncs as you change filters — shareable, refresh-safe."
		>
			<AuditLogsFilters
				bind:username
				bind:action
				bind:targetType
				bind:search
				bind:timestampAfter
				bind:timestampBefore
				oncommit={applyFilters}
				onclear={clearFilters}
			/>
		</DashboardCard>

		<DashboardCard
			title="Results"
			subtitle="{data.logs.count} {data.logs.count === 1 ? 'entry' : 'entries'}"
		>
			{#if data.logs.results.length === 0}
				<p class="empty">No audit log entries match your filters. <span class="empty-total">({data.logs.count} total entries)</span></p>
			{:else}
				<!-- activity-feed + ActivityItem — same shape as the
				     dashboard's Recent activity widget, so this page
				     reads as part of the same product. -->
				<ul class="activity-feed" aria-label="Audit log entries">
					{#each data.logs.results as row (row.id)}
						<ActivityItem
							user={row.user}
							action={row.action}
							targetType={row.target_type}
							targetId={row.target_id}
							targetHref={targetHref(row.target_type, row.target_id)}
							when={formatWhen(row.timestamp)}
							secondary={buildSecondary(row.details, row.ip_address)}
						/>
					{/each}
				</ul>

				{#if data.logs.next || data.logs.previous || data.logs.count > pageSize}
					{@const totalPages = pagesTotal()}
					{@const currentPage = currentPageFromUrl()}
					{@const pageList = buildPageList(currentPage, totalPages)}
					{@const showingFrom = (currentPage - 1) * pageSize + 1}
					{@const showingTo = Math.min(currentPage * pageSize, data.logs.count)}
					<nav class="pagination" aria-label="Pagination">
						<div class="pagination-summary">
							Showing <strong>{showingFrom}–{showingTo}</strong> of <strong>{data.logs.count}</strong> entries
						</div>

						<div class="pagination-controls">
							<button
								type="button"
								class="btn btn-secondary"
								onclick={() => goToPage(1)}
								disabled={currentPage <= 1}
								aria-label="First page"
							>
								« First
							</button>
							<button
								type="button"
								class="btn btn-secondary"
								onclick={() => goToPage(currentPage - 1)}
								disabled={!data.logs.previous}
								aria-label="Previous page"
							>
								‹ Prev
							</button>
							{#each pageList as p, i (i + '-' + p)}
								{#if p === 'ellipsis'}
									<span class="pagination-ellipsis" aria-hidden="true">…</span>
								{:else if p === currentPage}
									<span class="pagination-current" aria-current="page">{p}</span>
								{:else}
									<button
										type="button"
										class="btn btn-secondary"
										onclick={() => goToPage(p)}
										aria-label={`Page ${p}`}
									>
										{p}
									</button>
								{/if}
							{/each}
							<button
								type="button"
								class="btn btn-secondary"
								onclick={() => goToPage(currentPage + 1)}
								disabled={!data.logs.next}
								aria-label="Next page"
							>
								Next ›
							</button>
							<button
								type="button"
								class="btn btn-secondary"
								onclick={() => goToPage(totalPages)}
								disabled={currentPage >= totalPages}
								aria-label="Last page"
							>
								Last »
							</button>
						</div>

						<div class="pagination-extras">
							<label class="pagination-extras-field">
								<span class="pagination-extras-label">Page size</span>
								<select
									class="select"
									bind:value={pageSize}
									onchange={changePageSize}
									aria-label="Results per page"
								>
									{#each PAGE_SIZE_OPTIONS as opt (opt)}
										<option value={opt}>{opt}</option>
									{/each}
								</select>
							</label>
							<label class="pagination-extras-field">
								<span class="pagination-extras-label">Go to page</span>
								<input
									type="number"
									class="input"
									min="1"
									max={totalPages}
									bind:value={jumpTo}
									onkeydown={(e) => e.key === 'Enter' && jumpToPage()}
									aria-label={`Go to page (1–${totalPages})`}
								/>
							</label>
						</div>
					</nav>
				{/if}
			{/if}
		</DashboardCard>
	{/if}
</div>

<style>
	.audit-page {
		width: 100%;
		max-width: var(--max-w-page);
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-end;
		gap: 1rem;
		flex-wrap: wrap;
		padding-bottom: 0.75rem;
		border-bottom: 1px solid var(--color-border-light);
	}
	.page-header h1 {
		margin: 0 0 0.25rem 0;
		font-size: 1.5rem;
		color: var(--color-primary);
	}
	.page-subtitle {
		margin: 0;
		font-size: 0.95rem;
		color: var(--color-text-muted);
		max-width: var(--max-w-prose);
	}

	/* activity-feed owns the list layout; .activity-item owns each row.
	   Both are re-extracted from ActivityItem to keep the same render
	   shape on this page even if a future refactor moves the component. */
	.activity-feed {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.empty {
		margin: 0;
		padding: 1.5rem 0;
		text-align: center;
		color: var(--color-text-muted);
		font-size: 0.95rem;
	}
	.empty-total {
		color: var(--color-text-muted);
		font-size: 0.85rem;
		font-variant-numeric: tabular-nums;
	}

	/* Pagination nav: summary row, control row (page numbers + first/
	   prev/next/last), extras row (page size + jump). Stacks on
	   narrow viewports via flex-wrap so the table reads cleanly on
	   mobile. */
	.pagination {
		display: flex;
		flex-direction: column;
		gap: 0.65rem;
		margin-top: 0.85rem;
		padding-top: 0.85rem;
		border-top: 1px solid var(--color-border-light);
	}
	.pagination-summary {
		font-size: 0.85rem;
		color: var(--color-text-muted);
	}
	.pagination-summary strong {
		color: var(--color-text);
		font-variant-numeric: tabular-nums;
	}
	.pagination-controls {
		display: flex;
		align-items: center;
		gap: 0.3rem;
		flex-wrap: wrap;
	}
	.pagination-current {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 2rem;
		height: 2rem;
		padding: 0 0.6rem;
		font-size: 0.85rem;
		font-variant-numeric: tabular-nums;
		font-weight: 600;
		color: var(--color-primary);
		background: var(--color-primary-tint);
		border: 1px solid var(--color-primary);
		border-radius: var(--radius-input);
	}
	.pagination-ellipsis {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 1.5rem;
		height: 2rem;
		color: var(--color-text-muted);
		font-size: 0.85rem;
	}
	.pagination-extras {
		display: flex;
		gap: 1rem;
		flex-wrap: wrap;
		align-items: flex-end;
	}
	.pagination-extras-field {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}
	.pagination-extras-label {
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		color: var(--color-text-muted);
	}
	.pagination-extras .input,
	.pagination-extras .select {
		font: inherit;
		padding: 0.35rem 0.5rem;
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-input);
		background: var(--color-bg-white);
		color: var(--color-text);
		min-width: 4.5rem;
	}
	.pagination-extras .input {
		max-width: 6rem;
	}
	.pagination-extras .input:focus-visible,
	.pagination-extras .select:focus-visible {
		outline: none;
		box-shadow: 0 0 0 3px var(--color-primary-tint);
		border-color: var(--color-primary);
	}
	.btn[disabled] {
		opacity: 0.5;
		cursor: not-allowed;
	}

	</style>
