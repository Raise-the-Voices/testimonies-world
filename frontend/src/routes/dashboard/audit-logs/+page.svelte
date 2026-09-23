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
	import { afterNavigate, goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { base } from '$app/paths';
	import { user as userStore, isAdmin } from '$lib/session';
	import type { PageData } from './$types';
	import DashboardCard from '$lib/DashboardCard.svelte';
	import ActivityItem from '$lib/ActivityItem.svelte';
	import AuditLogsFilters from '$lib/AuditLogsFilters.svelte';
	import ErrorCard from '$lib/ErrorCard.svelte';

	let { data }: { data: PageData } = $props();

	// SSR-hydrated auth (see +layout.svelte for the full rationale).
	const currentUser = $derived(data.user ?? $userStore);
	// Defensive: `isAdmin` reads `u.authenticated`, so guard against a
	// null/undefined currentUser (initial SSR render before session
	// resolves).
	const showAdminLink = $derived(
		currentUser !== null && currentUser !== undefined && isAdmin(currentUser)
	);

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

	// Derived: total page count used by the pagination strip and the
	// "Go to page" input.
	function pagesTotal(): number {
		const count = data.logs?.count ?? 0;
		return Math.max(1, Math.ceil(count / pageSize));
	}

	/** Scroll the audit-log results card into view. Used after page
	 *  changes so the reader lands at the top of the new slice instead
	 *  of staying parked at the bottom of the previous one. Instant
	 *  (not smooth) because there's no positional context to preserve
	 *  — a smooth 400ms scroll feels laggy on every page click. */
	function scrollToResults() {
		if (typeof document === 'undefined') return;
		document.getElementById('audit-results-top')?.scrollIntoView({
			behavior: 'auto',
			block: 'start',
		});
	}

	/** After every SvelteKit navigation, scroll to the top of the
	 *  results card — but only when the ?page= param actually changed.
	 *  Filter changes keep the same page number, so scrolling there
	 *  would be a jarring surprise (the user is still reading the
	 *  same slice, just narrowed). */
	afterNavigate(({ to, from }) => {
		if (!to) return;
		const toPage = to.url.searchParams.get('page');
		const fromPage = from?.url.searchParams.get('page') ?? null;
		if (toPage !== fromPage) scrollToResults();
	});
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
		{#if showAdminLink}
			<!-- The old link targeted /admin/cases/auditlog/, which 404'd —
			     this app has no Django admin route. Point it at the only
			     valid audit-log target: the page the user is already on.
			     The "Django admin →" label is now misleading and should be
			     reworked in a follow-up if a real admin shortcut is wanted. -->
			<a
				href="{base}/dashboard/audit-logs"
				class="admin-link"
				rel="noopener"
				title="Open the audit log page"
			>
				Django admin →
			</a>
		{/if}
	</header>

	{#if data.error}
		<ErrorCard
			title="Couldn't load the audit log"
			message={data.error}
			kind={data.errorKind === 'auth' ? 'auth' : 'network'}
		/>
	{:else if data.logs && Array.isArray(data.logs.results)}
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
			subtitle="{data.logs.count ?? 0} {(data.logs.count ?? 0) === 1 ? 'entry' : 'entries'}"
		>
			<!-- `audit-results-top` is the scroll anchor used after page
			     changes. The afterNavigate hook in <script> lands here so
			     the reader starts at the top of the new slice instead of
			     staying parked at the bottom of the previous one. -->
			<div id="audit-results-top"></div>
			{#if data.logs.results.length === 0}
				<p class="empty">No audit log entries match your filters. <span class="empty-total">({data.logs.count ?? 0} total entries)</span></p>
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

				<!-- Pagination mirrors /persons and /reports: Prev +
				     page indicator + Next, plus Page size and Go-to-page
				     inputs. The earlier numbered-strip + First/Last +
				     ellipsis layout was overkill for a paginated audit
				     log and crowded the row. The Go-to-page input lets
				     readers jump anywhere they need without a long
				     button strip. -->
				{#if data.logs.next || data.logs.previous || data.logs.count > pageSize}
					{@const totalPages = pagesTotal()}
					{@const currentPage = currentPageFromUrl()}
					{@const showingFrom = (currentPage - 1) * pageSize + 1}
					{@const showingTo = Math.min(currentPage * pageSize, data.logs.count)}
					<nav class="pagination" aria-label="Pagination">
						<button
							type="button"
							class="btn btn-secondary"
							onclick={() => goToPage(currentPage - 1)}
							disabled={!data.logs.previous}
							aria-label="Previous page"
						>
							‹ Prev
						</button>
						<div class="pagination-indicator">
							Page <strong>{currentPage}</strong> of <strong>{totalPages}</strong>
							<span class="pagination-range">
								— showing <strong>{showingFrom}–{showingTo}</strong> of <strong>{data.logs.count}</strong>
							</span>
						</div>
						<button
							type="button"
							class="btn btn-secondary"
							onclick={() => goToPage(currentPage + 1)}
							disabled={!data.logs.next}
							aria-label="Next page"
						>
							Next ›
						</button>

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
	.admin-link {
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
		font-size: 0.85rem;
		color: var(--color-primary);
		text-decoration: none;
		padding: 0.35rem 0.7rem;
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-input);
	}
	.admin-link:hover {
		border-color: var(--color-primary);
		text-decoration: underline;
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

	/* Pagination nav: prev / indicator / next on the top row, page-size
	   + jump inputs on the second row. Same shape as /persons and
	   /reports so reviewers don't relearn the controls per page.
	   flex-wrap keeps it readable on narrow viewports. */
	.pagination {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex-wrap: wrap;
		margin-top: 0.85rem;
		padding-top: 0.85rem;
		border-top: 1px solid var(--color-border-light);
	}
	.pagination-indicator {
		font-size: 0.85rem;
		color: var(--color-text-muted);
		font-variant-numeric: tabular-nums;
		flex: 1 1 auto;
		text-align: center;
		min-width: 12rem;
	}
	.pagination-indicator strong {
		color: var(--color-text);
	}
	.pagination-range {
		color: var(--color-text-muted);
		margin-left: 0.35rem;
	}
	.pagination-extras {
		display: flex;
		gap: 1rem;
		flex-wrap: wrap;
		align-items: flex-end;
		flex-basis: 100%;
		justify-content: flex-end;
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
