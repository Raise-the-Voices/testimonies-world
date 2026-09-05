<script lang="ts">
	/**
	 * /reports — Global Reports List Page.
	 *
	 * Cross-case investigation surface for the Advocacy team. Lists every
	 * report in the system chronologically (newest first), with filters
	 * for source type, date range, and free-text search.
	 *
	 * Role gate: page-level, like `/contacts` — only Volunteers / Advocates /
	 * staff see the table; everyone else gets a muted message + Login link.
	 *
	 * Filters are kept in component state (NOT URL state) — matches the
	 * existing pattern at `/contacts` and `/casework`. Bookmarkability of
	 * "report lists" isn't a stated need for an authenticated advocacy
	 * dashboard.
	 */
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { getReports } from '$lib/api';
	import { user, isVolunteer } from '$lib/session';
	import Skeleton from '$lib/Skeleton.svelte';
	import StatusBadge from '$lib/StatusBadge.svelte';
	import type { Paginated, Report } from '$lib/types';

	const PAGE_SIZE = 10;
	const SEARCH_DEBOUNCE_MS = 300;

	let currentUser = $derived($user);

	// Filter state — all local, never written to the URL.
	let searchText = $state('');
	let filterSource = $state<'' | Report['source_type']>('');
	let dateFrom = $state(''); // YYYY-MM-DD
	let dateTo = $state('');   // YYYY-MM-DD
	let currentPage = $state(1);

	// Data state.
	let reports = $state<Report[]>([]);
	let totalCount = $state(0);
	let loading = $state(true);
	let error: string | null = $state(null);

	// Source type labels — mirror backend `Report.SourceType.choices`.
	// Kept here (not in api.ts) so the source-of-truth for display stays
	// next to the column that renders them.
	const sourceTypeLabels: Record<Report['source_type'], string> = {
		firsthand: 'Firsthand',
		secondhand: 'Secondhand',
		news: 'News',
		document: 'Document',
	};

	const hasActiveFilters = $derived(
		Boolean(searchText || filterSource || dateFrom || dateTo),
	);

	// Derived pagination.
	const totalPages = $derived(Math.max(1, Math.ceil(totalCount / PAGE_SIZE)));
	const pageStart = $derived(((currentPage - 1) * PAGE_SIZE) + 1);
	const pageEnd = $derived(Math.min(currentPage * PAGE_SIZE, totalCount));
	const canPrev = $derived(currentPage > 1);
	const canNext = $derived(currentPage < totalPages);

	// --- Data loading ----------------------------------------------------
	async function loadReports() {
		loading = true;
		error = null;
		try {
			const params: Record<string, string> = { page: String(currentPage) };
			if (searchText.trim()) params.search = searchText.trim();
			if (filterSource) params.source_type = filterSource;
			if (dateFrom) params.date_from = dateFrom;
			if (dateTo) params.date_to = dateTo;
			const data = (await getReports(params)) as Paginated<Report>;
			reports = data.results ?? [];
			totalCount = data.count ?? 0;
		} catch (e: unknown) {
			console.error(e);
			error = e instanceof Error ? e.message : 'Failed to load reports.';
			reports = [];
			totalCount = 0;
		} finally {
			loading = false;
		}
	}

	// Debounced search — applies the textbox value after 300ms of idle
	// typing, then resets to page 1. Falls back to "Enter key" so
	// keyboard users can submit immediately.
	let searchTimer: ReturnType<typeof setTimeout> | null = null;
	function onSearchInput() {
		if (searchTimer) clearTimeout(searchTimer);
		searchTimer = setTimeout(() => {
			currentPage = 1;
			void loadReports();
		}, SEARCH_DEBOUNCE_MS);
	}
	function onSearchSubmit(e: Event) {
		e.preventDefault();
		if (searchTimer) clearTimeout(searchTimer);
		currentPage = 1;
		void loadReports();
	}

	// Dropdown / date filter changes apply immediately and reset to page 1.
	function onSourceChange() {
		currentPage = 1;
		void loadReports();
	}
	function onDateFromChange() {
		currentPage = 1;
		void loadReports();
	}
	function onDateToChange() {
		currentPage = 1;
		void loadReports();
	}

	function clearFilters() {
		searchText = '';
		filterSource = '';
		dateFrom = '';
		dateTo = '';
		currentPage = 1;
		void loadReports();
	}

	async function goToPage(page: number) {
		if (page < 1 || page > totalPages || page === currentPage) return;
		currentPage = page;
		await loadReports();
	}

	// Row title: prefer the public `source_attribution` (e.g. "BBC
	// report", "family member") since it's the most specific text the
	// report carries. Fall back to the source_type label, then the
	// narrative's first line.
	function titleFor(r: Report): string {
		if (r.source_attribution && r.source_attribution.trim()) return r.source_attribution;
		return sourceTypeLabels[r.source_type] ?? r.source_type;
	}

	function formatDate(iso: string | null | undefined): string {
		if (!iso) return '—';
		// YYYY-MM-DD → render as-is (no timezone shift). Matches the
		// date inputs used by the filter row, so visual diffs read
		// consistently.
		return iso;
	}

	onMount(loadReports);
</script>

<svelte:head>
	<title>Reports — Testimonies.world</title>
</svelte:head>

<div class="reports-page">
	{#if !isVolunteer(currentUser)}
		<p class="muted">
			You must be logged in as a volunteer to view the global reports feed.
			<a href="{base}/accounts/google/login/?next={base}/reports">Login</a>
		</p>
	{:else}
		<header class="reports-header">
			<div class="reports-header-text">
				<h1>Reports</h1>
				<p class="reports-intro">
					Every report across every case, newest first. Use the filters
					to narrow by source, date, or free-text search.
				</p>
			</div>
		</header>

		<!-- Filter row: search + source dropdown + date range + clear -->
		<section class="reports-toolbar" aria-label="Filters">
			<form class="toolbar-search" onsubmit={onSearchSubmit}>
				<label for="reports-search" class="toolbar-label">Search</label>
				<input
					id="reports-search"
					type="search"
					class="toolbar-input"
					placeholder="Search narrative or attribution…"
					bind:value={searchText}
					oninput={onSearchInput}
				/>
			</form>
			<label class="toolbar-field" for="reports-source">
				<span class="toolbar-label">Source</span>
				<select
					id="reports-source"
					class="toolbar-select"
					bind:value={filterSource}
					onchange={onSourceChange}
				>
					<option value="">All sources</option>
					<option value="firsthand">{sourceTypeLabels.firsthand}</option>
					<option value="secondhand">{sourceTypeLabels.secondhand}</option>
					<option value="news">{sourceTypeLabels.news}</option>
					<option value="document">{sourceTypeLabels.document}</option>
				</select>
			</label>
			<label class="toolbar-field" for="reports-date-from">
				<span class="toolbar-label">From</span>
				<input
					id="reports-date-from"
					type="date"
					class="toolbar-input"
					bind:value={dateFrom}
					onchange={onDateFromChange}
				/>
			</label>
			<label class="toolbar-field" for="reports-date-to">
				<span class="toolbar-label">To</span>
				<input
					id="reports-date-to"
					type="date"
					class="toolbar-input"
					bind:value={dateTo}
					onchange={onDateToChange}
				/>
			</label>
			{#if hasActiveFilters}
				<button
					type="button"
					class="toolbar-clear"
					onclick={clearFilters}
				>Clear filters</button>
			{/if}
		</section>

		<section class="reports-card" aria-label="Reports list">
			{#if loading}
				<div class="reports-skeleton" aria-busy="true" aria-label="Loading reports">
					{#each Array.from({ length: 8 }, (_, i) => i) as i (i)}
						<Skeleton variant="table-row" cols={6} />
					{/each}
				</div>
			{:else if error}
				<div class="reports-error" role="alert">
					<header class="error-header">
						<span class="error-icon" aria-hidden="true">⚠</span>
						<h2>Could not load reports</h2>
					</header>
					<p class="error-message">{error}</p>
					<button type="button" class="btn btn-secondary" onclick={loadReports}>Retry</button>
				</div>
			{:else if reports.length === 0}
				<div class="reports-empty">
					<header class="empty-header">
						<span class="empty-icon" aria-hidden="true">○</span>
						<h2>
							{#if hasActiveFilters}
								No reports match these filters
							{:else}
								No reports yet
							{/if}
						</h2>
					</header>
					<p class="empty-message">
						{#if hasActiveFilters}
							Try widening the date range or
							<button type="button" class="link-button" onclick={clearFilters}>
								clear the filters
							</button>.
						{:else}
							Once volunteers start logging reports on cases, they'll
							appear here in chronological order.
						{/if}
					</p>
				</div>
			{:else}
				<div class="reports-table-wrap">
					<table class="reports-table">
						<thead>
							<tr>
								<th scope="col">Date</th>
								<th scope="col">Case</th>
								<th scope="col">Source</th>
								<th scope="col">Title</th>
								<th scope="col" class="th-status">Status</th>
								<th scope="col" class="th-private">Visibility</th>
							</tr>
						</thead>
						<tbody>
							{#each reports as r (r.id)}
								{@const title = titleFor(r)}
								<tr>
									<td class="cell-date">
										{#if r.date_start}
											{formatDate(r.date_start)}
											{#if r.date_end && r.date_end !== r.date_start}
												<span class="muted">— {formatDate(r.date_end)}</span>
											{/if}
										{:else}
											<span class="muted small">{new Date(r.created_at).toLocaleDateString()}</span>
										{/if}
									</td>
									<td class="cell-case">
										<a href="{base}/persons/{r.person}" class="case-link">
											{r.person}
										</a>
									</td>
									<td>
										<span class="source-pill source-pill-{r.source_type}">
											{sourceTypeLabels[r.source_type] ?? r.source_type}
										</span>
									</td>
									<td class="cell-title">
										<a href="{base}/persons/{r.person}" class="title-link" title={title}>
											{title}
										</a>
									</td>
									<td>
										{#if r.person}
											<!-- Person current_status isn't included in the
											     reports serializer — keep the status cell muted
											     for now; could be added by extending the
											     serializer to nest a Person field. -->
											<span class="muted small">—</span>
										{/if}
									</td>
									<td class="cell-private">
										{#if r.is_private}
											<span class="visibility-pill visibility-private" title="Private — only volunteers+">
												🔒 Private
											</span>
										{:else}
											<span class="visibility-pill visibility-public">Public</span>
										{/if}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>

				{#if totalPages > 1}
					<nav class="reports-pagination" aria-label="Pagination">
						<button
							type="button"
							class="btn btn-secondary btn-sm"
							disabled={!canPrev}
							onclick={() => goToPage(currentPage - 1)}
						>‹ Prev</button>
						<span class="page-indicator">
							Page <strong>{currentPage}</strong> of {totalPages}
							<span class="muted">— {pageStart}–{pageEnd} of {totalCount}</span>
						</span>
						<button
							type="button"
							class="btn btn-secondary btn-sm"
							disabled={!canNext}
							onclick={() => goToPage(currentPage + 1)}
						>Next ›</button>
					</nav>
				{:else}
					<div class="reports-pagination">
						<span class="muted small">
							{totalCount} report{totalCount === 1 ? '' : 's'}
						</span>
					</div>
				{/if}
			{/if}
		</section>
	{/if}
</div>

<style>
	/* Page layout — matches /watchdog + /contacts */
	.reports-page {
		width: 100%;
		max-width: var(--max-w-page);
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.reports-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 1rem;
	}
	.reports-header-text { flex: 1 1 auto; min-width: 0; }
	.reports-header h1 {
		margin: 0 0 0.4rem 0;
		color: var(--color-primary);
		font-size: 1.85rem;
		font-weight: 700;
		letter-spacing: -0.01em;
	}
	.reports-intro {
		margin: 0;
		max-width: var(--max-w-prose);
		color: var(--color-text);
		font-size: 1rem;
		line-height: 1.6;
	}

	/* Toolbar — search + source + date range + clear */
	.reports-toolbar {
		display: flex;
		align-items: flex-end;
		gap: 0.85rem 1.25rem;
		padding: 1rem 1.25rem;
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-subtle);
		border-left: 3px solid var(--color-primary);
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-card);
		flex-wrap: wrap;
	}
	.toolbar-search {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
		flex: 1 1 220px;
		min-width: 220px;
	}
	.toolbar-field {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
		flex: 0 0 auto;
	}
	.toolbar-label {
		font-size: 0.72rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		color: var(--color-text-muted);
	}
	.toolbar-input,
	.toolbar-select {
		font: inherit;
		padding: 0.5rem 0.65rem;
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		background: var(--color-bg-white);
		color: var(--color-text);
		min-width: 160px;
	}
	.toolbar-input:focus-visible,
	.toolbar-select:focus-visible {
		outline: 2px solid var(--color-primary);
		outline-offset: 1px;
		border-color: var(--color-primary);
	}
	.toolbar-clear {
		background: transparent;
		border: 1px solid var(--color-border-light);
		color: var(--color-text);
		padding: 0.5rem 0.85rem;
		border-radius: var(--radius-card);
		cursor: pointer;
		font: inherit;
		font-size: 0.88rem;
		transition: background 0.15s ease, border-color 0.15s ease;
	}
	.toolbar-clear:hover {
		background: var(--color-surface);
		border-color: var(--color-primary-light);
	}

	/* Card surface — matches the contacts page */
	.reports-card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-subtle);
		border-left: 3px solid var(--color-primary);
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-card);
		padding: 1.5rem 1.75rem;
	}

	/* Loading skeleton */
	.reports-skeleton {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	/* Error state */
	.reports-error {
		padding: 1rem;
		background: #fed7d7;
		color: #742a2a;
		border: 1px solid #feb2b2;
		border-radius: var(--radius-card);
	}
	.error-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin: 0 0 0.5rem 0;
	}
	.error-header h2 {
		margin: 0;
		font-size: 1rem;
		font-weight: 700;
	}
	.error-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		border-radius: 50%;
		background: rgba(116, 42, 42, 0.2);
		font-weight: 700;
	}
	.error-message {
		margin: 0 0 0.75rem 0;
	}

	/* Empty state */
	.reports-empty {
		text-align: center;
		padding: 2.5rem 1rem;
	}
	.empty-header {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		margin: 0 0 0.75rem 0;
	}
	.empty-header h2 {
		margin: 0;
		font-size: 1.15rem;
		font-weight: 700;
		color: var(--color-text);
	}
	.empty-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		border-radius: 50%;
		background: var(--color-surface);
		color: var(--color-text-muted);
		font-size: 1rem;
	}
	.empty-message {
		margin: 0;
		color: var(--color-text-muted);
		max-width: 32rem;
		margin-left: auto;
		margin-right: auto;
		line-height: 1.6;
	}

	/* Table */
	.reports-table-wrap {
		overflow-x: auto;
		-webkit-overflow-scrolling: touch;
	}
	.reports-table {
		width: 100%;
		min-width: 760px;
		border-collapse: collapse;
	}
	.reports-table th,
	.reports-table td {
		padding: 0.75rem 0.85rem;
		text-align: left;
		border-bottom: 1px solid var(--color-border-subtle);
		vertical-align: middle;
	}
	.reports-table th {
		font-size: 0.72rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		color: var(--color-text-muted);
		background: transparent;
		border-bottom: 1px solid var(--color-border-light);
		white-space: nowrap;
	}
	.th-status { width: 1%; }
	.th-private { width: 1%; }

	.reports-table tbody tr {
		transition: background 0.15s ease;
	}
	.reports-table tbody tr:hover {
		background: var(--color-surface);
	}
	.reports-table tbody tr:last-child td {
		border-bottom: none;
	}

	.cell-date {
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
		color: var(--color-text);
		font-size: 0.92rem;
	}
	.cell-case {
		font-weight: 600;
	}
	.case-link,
	.title-link {
		color: var(--color-primary);
		text-decoration: none;
	}
	.case-link:hover,
	.title-link:hover {
		text-decoration: underline;
	}
	.cell-title {
		max-width: 28rem;
	}
	.title-link {
		display: inline-block;
		max-width: 100%;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		vertical-align: bottom;
	}
	.cell-private {
		white-space: nowrap;
	}

	/* Source pill — colored by source type for the "🟢/🟡" feel.
	   Matches the badge-source-* family used on /persons/[id]. */
	.source-pill {
		display: inline-flex;
		align-items: center;
		padding: 0.18rem 0.6rem;
		border-radius: 999px;
		font-size: 0.72rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		line-height: 1.2;
	}
	.source-pill-firsthand { background: #c6f6d5; color: #22543d; }
	.source-pill-secondhand { background: #fefcbf; color: #744210; }
	.source-pill-news { background: #bee3f8; color: #2a4365; }
	.source-pill-document { background: #e9d8fd; color: #44337a; }

	/* Visibility pill */
	.visibility-pill {
		display: inline-flex;
		align-items: center;
		padding: 0.2rem 0.6rem;
		border-radius: 999px;
		font-size: 0.7rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		line-height: 1.2;
	}
	.visibility-public {
		background: var(--color-surface);
		color: var(--color-text-muted);
	}
	.visibility-private {
		background: #fed7d7;
		color: #742a2a;
	}

	/* Pagination */
	.reports-pagination {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.85rem;
		padding-top: 1rem;
		margin-top: 1rem;
		border-top: 1px solid var(--color-border-subtle);
		font-size: 0.92rem;
	}
	.btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	.page-indicator strong {
		color: var(--color-primary);
		font-weight: 700;
	}

	/* Inline link button inside empty state */
	.link-button {
		background: transparent;
		border: none;
		color: var(--color-primary);
		text-decoration: underline;
		cursor: pointer;
		padding: 0;
		font: inherit;
	}
	.link-button:hover {
		color: var(--color-primary-light);
	}

	@media (max-width: 720px) {
		.reports-header {
			flex-direction: column;
			align-items: stretch;
		}
		.reports-toolbar {
			flex-direction: column;
			align-items: stretch;
		}
		.toolbar-search,
		.toolbar-field,
		.toolbar-input,
		.toolbar-select {
			min-width: 0;
			width: 100%;
		}
	}
</style>