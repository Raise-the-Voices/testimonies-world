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
	export const PAGE_SIZE = 10;
</script>

<script lang="ts">
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

	let username = $state(data.requestParams.user__username ?? '');
	let action = $state(data.requestParams.action ?? '');
	let targetType = $state(data.requestParams.target_type ?? '');
	let search = $state(data.requestParams.search ?? '');
	let timestampAfter = $state(convertIsoToLocal(data.requestParams.timestamp_after ?? ''));
	let timestampBefore = $state(convertIsoToLocal(data.requestParams.timestamp_before ?? ''));

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
				<p class="empty">No audit log entries match your filters.</p>
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

				{#if data.logs.next || data.logs.previous}
					{@const totalPages = Math.ceil(data.logs.count / PAGE_SIZE)}
					{@const currentPage = currentPageFromUrl()}
					<nav class="pagination" aria-label="Pagination">
						<div class="pagination-summary">
							Page <strong>{currentPage}</strong> of <strong>{totalPages}</strong>
						</div>
						<div class="pagination-controls">
							<button
								type="button"
								class="btn btn-secondary"
								onclick={() => goToPage(currentPage - 1)}
								disabled={!data.logs.previous}
								aria-label="Previous page"
							>
								‹ Previous
							</button>
							<button
								type="button"
								class="btn btn-secondary"
								onclick={() => goToPage(currentPage + 1)}
								disabled={!data.logs.next}
								aria-label="Next page"
							>
								Next ›
							</button>
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

	.pagination {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 1rem;
		flex-wrap: wrap;
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
		gap: 0.5rem;
	}
	.btn[disabled] {
		opacity: 0.5;
		cursor: not-allowed;
	}

	@media (prefers-reduced-motion: reduce) {
		.activity-feed *,
		.activity-feed *::before,
		.activity-feed *::after {
			transition: none;
		}
	}
</style>
