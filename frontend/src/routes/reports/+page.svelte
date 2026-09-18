<!--
  /reports — Global Reports List Page.

  Cross-case investigation surface for the Advocacy team. Lists every
  report in the system chronologically (newest first), with filters
  for source type, date range, and free-text search.

  Role gate: page-level, like `/contacts` — only Volunteers / Advocates /
  staff see the table; everyone else gets a muted message + Login link.

  Filters are kept in component state (NOT URL state) — matches the
  existing pattern at `/contacts` and `/casework`. Bookmarkability of
  "report lists" isn't a stated need for an authenticated advocacy
  dashboard.

  The "Add Report" entry point opens a Modal containing the shared
  ReportForm component (same component used by the per-case page at
  /persons/{id}/report). Both entry points produce identical report
  payloads — single source of truth, zero drift risk.
-->
<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { base } from '$app/paths';
	import { getReports } from '$lib/api';
	import { user, isVolunteer } from '$lib/session';
	import Skeleton from '$lib/Skeleton.svelte';
	import StatusBadge from '$lib/StatusBadge.svelte';
	import ErrorCard from '$lib/ErrorCard.svelte';
	import Modal from '$lib/Modal.svelte';
	import ReportForm from '$lib/ReportForm.svelte';
	import { showToast } from '$lib/toast';
	import type { PageData } from './$types';
	import type { Paginated, Report } from '$lib/types';

	const PAGE_SIZE = 10;
	const SEARCH_DEBOUNCE_MS = 300;

	let { data }: { data: PageData } = $props();

	// SSR-hydrated auth (see +layout.svelte for the full rationale).
	let currentUser = $derived(data.user ?? $user);

	// Filter state — all local, never written to the URL.
	let searchText = $state('');
	let filterSource = $state<'' | Report['source_type']>('');
	let dateFrom = $state(''); // YYYY-MM-DD
	let dateTo = $state('');   // YYYY-MM-DD
	let currentPage = $state(1);

	// Data state — seeded from the +page.ts universal load. SSR has
	// populated this before first paint, so `loading` defaults to
	// false (no skeleton flash). If the SSR load returned an error
	// (e.g. anonymous user hitting the endpoint before the layout's
	// session is hydrated), `onMount` retries once via loadReports().
	let reports = $state<Report[]>(untrack(() => data.reports ?? []));
	let totalCount = $state(untrack(() => data.reportCount ?? 0));
	let loading = $state(false);
	let error: string | null = $state<string | null>(untrack(() => data.error ?? null));

	// Modal open/close — the form's state lives inside ReportForm.
	let formOpen = $state(false);
	function openAddForm() {
		formOpen = true;
	}
	function closeAddForm() {
		formOpen = false;
	}

	// Partial-failure banner: the report itself saves, but if any media
	// item failed to attach, surface which ones so the volunteer can
	// retry on the case page.
	let mediaFailures = $state<string[]>([]);
	function dismissMediaFailures() {
		mediaFailures = [];
	}

	// After a successful save, close the modal, reset to page 1, and
	// re-fetch so the new report shows up at the top (newest-first).
	// Also fires a success toast carrying the full server response so
	// the operator sees the new id, FK to the case, and created_at
	// timestamp — visual confirmation that the row landed.
	function onFormSuccess(detail: { report: Report; mediaFailures: string[] }) {
		formOpen = false;
		mediaFailures = detail.mediaFailures;
		currentPage = 1;
		showToast('Report saved.', {
			variant: 'success',
			details: detail.report as unknown as Record<string, unknown>,
		});
		void loadReports();
	}

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

	// Narrative snippet: first ~200 chars of the narrative, collapsed
	// on whitespace so we don't cut mid-word. Returns a structured
	// { snippet, hasMore } so the template can render a "Show more"
	// affordance when the full text would overflow.
	const SNIPPET_MAX = 200;
	function narrativeSnippet(r: Report): { text: string; hasMore: boolean } {
		const full = (r.narrative ?? '').trim().replace(/\s+/g, ' ');
		if (full.length <= SNIPPET_MAX) return { text: full, hasMore: false };
		// Find a word boundary at or before SNIPPET_MAX.
		const cut = full.lastIndexOf(' ', SNIPPET_MAX);
		const idx = cut > 80 ? cut : SNIPPET_MAX;
		return { text: full.slice(0, idx) + '…', hasMore: true };
	}

	// Media count: media_files is included on the list response via
	// ReportSerializer.media_files (prefetched on the queryset).
	function mediaCount(r: Report): number {
		return r.media_files?.length ?? 0;
	}
	// Source count: sources is included on the list response via
	// ReportSerializer.sources (prefetched on the queryset).
	function sourceCount(r: Report): number {
		return r.sources?.length ?? 0;
	}

	onMount(() => {
		// The SSR load has already populated `reports` / `totalCount`
		// (or set `error`). Only retry if the SSR fetch failed —
		// otherwise this would duplicate the on-paint request.
		if (data.error) void loadReports();
	});
</script>

<svelte:head>
	<title>Reports — Testimonies.world</title>
	<meta name="description" content="Every report across every case, newest first. Use the filters to narrow by source, date, or free-text search." />
	<meta property="og:description" content="Every report across every case, newest first. Use the filters to narrow by source, date, or free-text search." />
	<meta property="og:type" content="website" />
	<meta name="twitter:description" content="Every report across every case, newest first. Use the filters to narrow by source, date, or free-text search." />
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
			{#if isVolunteer(currentUser)}
				<button
					type="button"
					class="btn btn-primary reports-header-action"
					onclick={openAddForm}
				>Add Report</button>
			{/if}
		</header>

		<!-- Partial-failure banner: shown when the report itself saved
		     but one or more media items failed. -->
		{#if mediaFailures.length > 0}
			<div class="media-failures" role="alert">
				<div class="media-failures-header">
					<span class="media-failures-icon" aria-hidden="true">!</span>
					<strong>Report saved, but {mediaFailures.length} media item(s) failed to attach:</strong>
				</div>
				<ul class="media-failures-list">
					{#each mediaFailures as msg (msg)}
						<li>{msg}</li>
					{/each}
				</ul>
				<div class="media-failures-actions">
					<button type="button" onclick={dismissMediaFailures}>
						Dismiss
					</button>
				</div>
			</div>
		{/if}

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
				<ErrorCard
					title="Could not load reports"
					message={error}
					kind="network"
					retry={loadReports}
				/>
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
				<ul class="reports-list" aria-label="Reports">
					{#each reports as r (r.id)}
						{@const title = titleFor(r)}
						{@const snippet = narrativeSnippet(r)}
						{@const mc = mediaCount(r)}
						{@const sc = sourceCount(r)}
						<li class="report-row" class:report-row--private={r.is_private}>
							<a
								class="report-row-link"
								href="{base}/persons/{r.person}"
								aria-label="Open case {r.person} — {title}"
							>
								<!-- Date column — fixed width, aligns across rows -->
								<div class="report-row-date">
									{#if r.date_start}
										<time class="report-row-date-primary" datetime={r.date_start}>
											{formatDate(r.date_start)}
										</time>
										{#if r.date_end && r.date_end !== r.date_start}
											<time class="report-row-date-secondary" datetime={r.date_end}>
												— {formatDate(r.date_end)}
											</time>
										{/if}
									{:else}
										<time class="report-row-date-primary report-row-date-primary--fallback" datetime={r.created_at}>
											{new Date(r.created_at).toLocaleDateString()}
										</time>
									{/if}
								</div>

								<!-- Pills column — source type + privacy, vertical stack -->
								<div class="report-row-pills">
									<span class="source-pill source-pill-{r.source_type}">
										{sourceTypeLabels[r.source_type] ?? r.source_type}
									</span>
									{#if r.is_private}
										<span class="visibility-pill visibility-private">🔒 Private</span>
									{:else}
										<span class="visibility-pill visibility-public">Public</span>
									{/if}
								</div>

								<!-- Content column — title + snippet + stats -->
								<div class="report-row-content">
									<h3 class="report-row-title">{title}</h3>
									{#if snippet.text}
										<p class="report-row-snippet">{snippet.text}</p>
									{/if}
									{#if mc > 0 || sc > 0 || r.rough_location}
										<div class="report-row-stats">
											{#if mc > 0}
												<span class="report-stat">
													<span class="report-stat-icon" aria-hidden="true">📎</span>
													{mc} media{mc === 1 ? '' : 's'}
												</span>
											{/if}
											{#if sc > 0}
												<span class="report-stat">
													<span class="report-stat-icon" aria-hidden="true">⚲</span>
													{sc} {sc === 1 ? 'source' : 'sources'}
												</span>
											{/if}
											{#if r.rough_location}
												<span class="report-stat">
													<span class="report-stat-icon" aria-hidden="true">📍</span>
													{r.rough_location}
												</span>
											{/if}
										</div>
									{/if}
								</div>

								<!-- Arrow column — visual affordance for "click me" -->
								<div class="report-row-arrow" aria-hidden="true">→</div>
							</a>
						</li>
					{/each}
				</ul>

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

	<!-- "Add Report" modal — wraps the shared ReportForm so /reports
	     and /persons/{id}/report use the EXACT same form. The form's
	     own state lives inside ReportForm; we only own the modal chrome. -->
	<Modal
		open={formOpen}
		title="Add a report"
		onClose={closeAddForm}
	>
		<div class="report-form-modal-wrapper">
			<ReportForm
				onSuccess={onFormSuccess}
				onCancel={closeAddForm}
			/>
		</div>
	</Modal>
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
	.reports-header-action {
		flex: 0 0 auto;
		align-self: flex-start;
		padding: 0.55rem 1rem;
		font-size: 0.82rem;
		min-height: 0;
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

	/* === Report rows ===
	   A clean, table-like list using CSS Grid for column alignment.
	   Four columns: date | pills | content | arrow. The content column
	   flexes to fill; the others are auto-sized so dates align across
	   rows. The whole row is one clickable <a>. */
	.reports-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 0.65rem;
	}
	.report-row {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-subtle);
		border-left: 3px solid var(--color-primary);
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-card);
		transition:
			transform 0.15s ease,
			box-shadow 0.15s ease,
			border-color 0.15s ease;
	}
	.report-row:hover {
		transform: translateY(-1px);
		box-shadow: var(--shadow-card-lg);
		border-left-color: var(--color-primary-light);
	}
	.report-row:focus-within {
		outline: 2px solid var(--color-primary);
		outline-offset: 2px;
	}
	.report-row--private {
		border-left-color: var(--color-danger, #c53030);
	}
	.report-row-link {
		display: grid;
		grid-template-columns: 9rem auto 1fr 1.5rem;
		gap: 1.25rem;
		align-items: start;
		padding: 1.05rem 1.4rem;
		color: inherit;
		text-decoration: none;
	}

	/* Date column — fixed-width, dates align across rows */
	.report-row-date {
		display: flex;
		flex-direction: column;
		gap: 0.1rem;
		padding-top: 0.15rem;
		font-variant-numeric: tabular-nums;
	}
	.report-row-date-primary {
		font-size: 0.88rem;
		font-weight: 700;
		color: var(--color-text);
		letter-spacing: -0.01em;
	}
	.report-row-date-primary--fallback {
		color: var(--color-text-muted);
		font-weight: 500;
	}
	.report-row-date-secondary {
		font-size: 0.78rem;
		color: var(--color-text-muted);
		font-weight: 500;
	}

	/* Pills column — source type + privacy, vertical stack */
	.report-row-pills {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
		align-items: flex-start;
		padding-top: 0.05rem;
	}

	/* Content column — title + snippet + stats, takes remaining width */
	.report-row-content {
		min-width: 0; /* allow text wrap inside grid item */
		display: flex;
		flex-direction: column;
		gap: 0.45rem;
	}
	.report-row-title {
		margin: 0;
		font-size: 1.02rem;
		font-weight: 700;
		color: var(--color-text);
		line-height: 1.35;
		letter-spacing: -0.005em;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.report-row-snippet {
		margin: 0;
		font-size: 0.9rem;
		color: var(--color-text-muted);
		line-height: 1.5;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.report-row-stats {
		display: flex;
		gap: 1rem;
		flex-wrap: wrap;
		margin-top: 0.15rem;
	}
	.report-stat {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		font-size: 0.82rem;
		color: var(--color-text-muted);
		font-weight: 500;
	}
	.report-stat-icon {
		font-size: 0.95rem;
		opacity: 0.85;
	}

	/* Arrow column — visual affordance for "click me" */
	.report-row-arrow {
		font-size: 1.15rem;
		color: var(--color-text-muted);
		align-self: center;
		line-height: 1;
		transition: transform 0.15s ease, color 0.15s ease;
	}
	.report-row:hover .report-row-arrow {
		color: var(--color-primary);
		transform: translateX(3px);
	}

	/* Mobile — collapse the date column inline with title; pills sit
	   above the snippet. Three-column layout (pills / content / arrow)
	   with date as a meta line above the content. */
	@media (max-width: 720px) {
		.report-row-link {
			grid-template-columns: auto 1fr 1.5rem;
			grid-template-areas:
				"pills  content  arrow"
				"date   content  arrow";
			gap: 0.6rem 1rem;
			padding: 1rem 1.15rem;
		}
		.report-row-date {
			grid-area: date;
			flex-direction: row;
			gap: 0.4rem;
		}
		.report-row-date-secondary { font-size: 0.82rem; }
		.report-row-pills {
			grid-area: pills;
			flex-direction: row;
			gap: 0.4rem;
		}
		.report-row-content {
			grid-area: content;
		}
		.report-row-arrow {
			grid-area: arrow;
		}
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

	/* === Media partial-failure banner (page-level) === */
	.media-failures {
		padding: 0.85rem 1.1rem;
		background: #fef5e7;
		color: #744210;
		border: 1px solid #f6ad55;
		border-left: 3px solid #dd6b20;
		border-radius: var(--radius-card);
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	.media-failures-header {
		display: flex;
		align-items: center;
		gap: 0.55rem;
	}
	.media-failures-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 22px;
		height: 22px;
		border-radius: 50%;
		background: rgba(221, 107, 32, 0.2);
		color: #dd6b20;
		font-weight: 700;
		font-size: 0.85rem;
		flex: 0 0 auto;
	}
	.media-failures-list {
		margin: 0;
		padding-left: 1.5rem;
		font-size: 0.88rem;
		color: #5a3b00;
		line-height: 1.5;
	}
	.media-failures-list li {
		margin: 0.15rem 0;
	}
	.media-failures-actions {
		display: flex;
		justify-content: flex-end;
		margin-top: 0.25rem;
	}
	.media-failures-actions button {
		background: transparent;
		border: 1px solid currentColor;
		color: inherit;
		font-size: 0.82rem;
		padding: 0.3rem 0.75rem;
		border-radius: var(--radius-control);
		cursor: pointer;
		font-weight: 600;
		min-height: 0;
	}
	.media-failures-actions button:hover {
		background: rgba(0, 0, 0, 0.05);
	}

	/* === Report form inside the modal ===
	   The Modal component caps itself at 540px wide by default; the
	   ReportForm is wider (880px-ish). Widen the modal when it
	   contains a ReportForm so the form breathes. */
	:global(.modal:has(.report-form-modal-wrapper)) {
		max-width: 760px;
	}
	.report-form-modal-wrapper {
		padding: 1.25rem 1.5rem 1.5rem 1.5rem;
	}
	/* Re-scope the form chrome to fit the modal canvas without
	   inheriting the page-mode width cap. */
	.report-form-modal-wrapper :global(.report-form) {
		max-width: none;
		margin: 0;
	}
	.report-form-modal-wrapper :global(.form-section) {
		padding: 1.25rem 1.25rem 1.4rem 1.25rem;
	}
	.report-form-modal-wrapper :global(.section-icon) {
		width: 26px;
		height: 26px;
		font-size: 0.9rem;
	}
	.report-form-modal-wrapper :global(.section-legend) {
		font-size: 0.95rem;
	}
	.report-form-modal-wrapper :global(.grid-2) {
		gap: 0.85rem 1rem;
	}
	.report-form-modal-wrapper :global(.form-footer) {
		position: static;
		box-shadow: none;
		padding: 0.85rem 1.1rem;
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
