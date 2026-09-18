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
	import { onMount, untrack } from 'svelte';
	import { base } from '$app/paths';
	import { getReports, createReport, ApiError, request } from '$lib/api';
	import { user, isVolunteer } from '$lib/session';
	import Skeleton from '$lib/Skeleton.svelte';
	import StatusBadge from '$lib/StatusBadge.svelte';
	import ErrorCard from '$lib/ErrorCard.svelte';
	import Modal from '$lib/Modal.svelte';
	import PersonPicker from '$lib/PersonPicker.svelte';
	import type { PageData } from './$types';
	import type { Media, MediaType, Paginated, Report, Visibility } from '$lib/types';

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

	// "Add Report" comprehensive form modal. Mirrors the field set of
	// the per-case form at /persons/[id]/report so the two entry points
	// accept the same data. Backend requires a non-nullable person FK
	// (models.py:524-526), so the PersonPicker is the first section and
	// is mandatory before submit.
	const MAX_NARRATIVE = 5000;
	const MAX_SHORT = 500;

	let formOpen = $state(false);
	let formSaving = $state(false);
	let formErrorMsg = $state('');
	let formErrorKind = $state<'generic' | 'network' | 'auth' | 'server' | 'validation'>('generic');
	let fieldErrors = $state<Record<string, string>>({});

	// Person (required)
	let formPersonId = $state<number | null>(null);

	// Source information
	let sourceType = $state<Report['source_type']>('firsthand');
	let sourceAttribution = $state('');
	let reporterName = $state('');
	let reporterContact = $state('');

	// Event timeline & location
	let dateStart = $state('');
	let dateEnd = $state('');

	// Report details
	let narrative = $state('');
	let suspectedReason = $state('');
	let officialReason = $state('');

	// Privacy
	let isPrivate = $state(false);

	// --- Additional Sources (witnesses / news / docs) -------------------
	// ReportSerializer.sources is writable nested on POST /reports/.
	// We track N entries client-side; on submit they're sent inside the
	// Report payload. Empty entries (no attribution, no narrative) are
	// dropped so a user who clicked "Add another" by mistake doesn't
	// create a blank source row.
	interface SourceEntry {
		uid: number; // local-only, for keyed {#each}
		source_type: Report['source_type'];
		source_attribution: string;
		date_start: string;
		narrative: string;
		is_private: boolean;
	}
	let sourceEntries = $state<SourceEntry[]>([]);

	// --- Media (photos / docs / videos / links) -------------------------
	// MediaViewSet has `report` as a writable FK, so we POST each media
	// row separately with `report=<newId>` after the Report creates.
	// Multi-step because ReportSerializer.media_files is read-only nested.
	interface MediaEntry {
		uid: number;
		media_type: MediaType;
		visibility: Visibility;
		description: string;
		url: string;
	}
	let mediaEntries = $state<MediaEntry[]>([]);

	// Monotonic local id for keyed each. Not the backend id.
	let nextEntryUid = 1;
	function makeSourceEntry(): SourceEntry {
		return {
			uid: nextEntryUid++,
			source_type: 'firsthand',
			source_attribution: '',
			date_start: '',
			narrative: '',
			is_private: false,
		};
	}
	function makeMediaEntry(): MediaEntry {
		return {
			uid: nextEntryUid++,
			media_type: 'photo',
			visibility: 'public',
			description: '',
			url: '',
		};
	}
	function addSource() {
		sourceEntries = [...sourceEntries, makeSourceEntry()];
	}
	function removeSource(idx: number) {
		sourceEntries = sourceEntries.filter((_, i) => i !== idx);
	}
	function addMedia() {
		mediaEntries = [...mediaEntries, makeMediaEntry()];
	}
	function removeMedia(idx: number) {
		mediaEntries = mediaEntries.filter((_, i) => i !== idx);
	}

	// Tracks media that failed to save after a successful Report POST.
	// The report itself is created — these are warnings, not blockers.
	let mediaFailures = $state<string[]>([]);
	function dismissMediaFailures() {
		mediaFailures = [];
	}

	// Source type labels — used in both the table pills and the form
	// dropdown, kept next to the column that renders them.
	const sourceTypeFormLabels: Record<Report['source_type'], string> = {
		firsthand: 'Firsthand',
		secondhand: 'Secondhand',
		news: 'News report',
		document: 'Document',
	};
	const sourceTypeFormHelp: Record<Report['source_type'], string> = {
		firsthand: 'From someone who directly witnessed or experienced the event.',
		secondhand: 'From someone close to the event (family, neighbor, colleague).',
		news: 'From a media report — link the source in the attribution field.',
		document: 'From an official document, court filing, or organizational report.',
	};

	function resetForm() {
		formPersonId = null;
		sourceType = 'firsthand';
		sourceAttribution = '';
		reporterName = '';
		reporterContact = '';
		dateStart = '';
		dateEnd = '';
		narrative = '';
		suspectedReason = '';
		officialReason = '';
		isPrivate = false;
		sourceEntries = [];
		mediaEntries = [];
		fieldErrors = {};
		formErrorMsg = '';
		formErrorKind = 'generic';
	}
	function openAddForm() {
		resetForm();
		formOpen = true;
	}
	function closeAddForm() {
		if (formSaving) return; // don't allow dismissing mid-submit
		formOpen = false;
		// Reset on close so a subsequent open starts clean.
		resetForm();
	}
	function onPersonPicked(id: number | null) {
		formPersonId = id;
		if (fieldErrors.person) {
			const { person: _drop, ...rest } = fieldErrors;
			fieldErrors = rest;
		}
	}

	function validate(): boolean {
		const e: Record<string, string> = {};
		if (formPersonId === null) {
			e.person = 'Pick the case this report belongs to.';
		}
		if (!narrative.trim()) {
			e.narrative = 'Narrative is required.';
		} else if (narrative.length > MAX_NARRATIVE) {
			e.narrative = `Narrative is too long (max ${MAX_NARRATIVE} characters).`;
		}
		if (dateStart && dateEnd && dateEnd < dateStart) {
			e.date_end = 'End date must be on or after the start date.';
		}
		if (sourceAttribution.length > MAX_SHORT) {
			e.source_attribution = `Source attribution is too long (max ${MAX_SHORT} characters).`;
		}
		if (reporterContact.length > MAX_SHORT) {
			e.reporter_contact = `Reporter contact is too long (max ${MAX_SHORT} characters).`;
		}
		fieldErrors = e;
		return Object.keys(e).length === 0;
	}

	async function submitForm() {
		if (formSaving) return; // re-entrancy guard
		if (!validate()) return;
		if (formPersonId === null) return; // narrowed by validate()
		formSaving = true;
		formErrorMsg = '';
		formErrorKind = 'generic';
		mediaFailures = [];

		// Drop empty source entries — a user who clicked "Add another"
		// by mistake shouldn't create a blank row.
		const sources = sourceEntries
			.filter((s) => s.source_attribution.trim() || s.narrative.trim())
			.map((s) => ({
				source_type: s.source_type,
				source_attribution: s.source_attribution,
				date_start: s.date_start || null,
				narrative: s.narrative,
				is_private: s.is_private,
			}));

		const payload = {
			person: formPersonId,
			source_type: sourceType,
			source_attribution: sourceAttribution,
			reporter_name: reporterName,
			reporter_contact: reporterContact,
			date_start: dateStart || null,
			date_end: dateEnd || null,
			rough_location: '', // rough_location intentionally not in the modal — see per-case form for full location flow
			narrative,
			suspected_reason: suspectedReason,
			official_reason: officialReason,
			is_private: isPrivate,
			sources,
		};
		try {
			// Step 1: create the report (with nested sources).
			const created = await createReport(payload);

			// Step 2: attach each media item separately. ReportSerializer
			// has media_files as read-only nested, so a second POST per
			// item is required. Track failures but don't fail the whole
			// flow — the report itself is saved.
			const failures: string[] = [];
			for (let i = 0; i < mediaEntries.length; i++) {
				const m = mediaEntries[i];
				// Skip empty media entries (same "Add another" mistake).
				if (!m.url.trim() && !m.description.trim()) continue;
				try {
					await request<Media>('/media/', {
						method: 'POST',
						body: JSON.stringify({
							report: created.id,
							media_type: m.media_type,
							visibility: m.visibility,
							description: m.description,
							url: m.url,
						}),
					});
				} catch (mErr: unknown) {
					const msg = mErr instanceof Error ? mErr.message : 'unknown error';
					failures.push(`Media #${i + 1}: ${msg}`);
				}
			}

			// Success (regardless of media partial-failures) — close
			// modal, refresh list so the new report + its media show up.
			formOpen = false;
			resetForm();
			currentPage = 1;
			await loadReports();

			// Surface partial-failure warning as a page-level banner
			// (not in the closed modal).
			if (failures.length > 0) {
				mediaFailures = failures;
			}
		} catch (err: unknown) {
			if (err instanceof ApiError) {
				if (err.isValidation && err.fieldErrors && Object.keys(err.fieldErrors).length) {
					fieldErrors = Object.fromEntries(
						Object.entries(err.fieldErrors).map(([k, v]) => [k, v[0] ?? '']),
					);
					formErrorMsg = err.message;
					formErrorKind = 'validation';
				} else if (err.isUnauthorized) {
					formErrorMsg = 'Your session has expired. Please log in again to continue.';
					formErrorKind = 'auth';
				} else if (err.isServer || err.status === 0) {
					formErrorMsg = err.status === 0
						? err.message
						: "The server hit a snag. Please try again in a moment.";
					formErrorKind = err.status === 0 ? 'network' : 'server';
				} else {
					formErrorMsg = err.message;
					formErrorKind = 'generic';
				}
			} else {
				formErrorMsg = err instanceof Error ? err.message : 'Failed to save the report.';
			}
		} finally {
			formSaving = false;
		}
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
									<td data-label="Date" class="cell-date">
										{#if r.date_start}
											{formatDate(r.date_start)}
											{#if r.date_end && r.date_end !== r.date_start}
												<span class="muted">— {formatDate(r.date_end)}</span>
											{/if}
										{:else}
											<span class="muted small">{new Date(r.created_at).toLocaleDateString()}</span>
										{/if}
									</td>
									<td data-label="Case" class="cell-case">
										<a href="{base}/persons/{r.person}" class="case-link">
											{r.person}
										</a>
									</td>
									<td data-label="Source">
										<span class="source-pill source-pill-{r.source_type}">
											{sourceTypeLabels[r.source_type] ?? r.source_type}
										</span>
									</td>
									<td data-label="Title" class="cell-title">
										<a href="{base}/persons/{r.person}" class="title-link" title={title}>
											{title}
										</a>
									</td>
									<td data-label="Status">
										{#if r.person}
											<!-- Person current_status isn't included in the
											     reports serializer — keep the status cell muted
											     for now; could be added by extending the
											     serializer to nest a Person field. -->
											<span class="muted small">—</span>
										{/if}
									</td>
									<td data-label="Visibility" class="cell-private">
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

	<!-- "Add Report" comprehensive form modal — gated to volunteers+
	     (matches the case-page button). Mirrors the field set of the
	     per-case form at /persons/[id]/report so the two entry points
	     accept the same data. The modal's own onClose handles
	     Escape/backdrop; re-entrancy guard in closeAddForm() blocks
	     dismissal mid-submit. -->
	<Modal
		open={formOpen}
		title="Add a report"
		onClose={closeAddForm}
		dismissable={!formSaving}
	>
		<form
			class="report-form report-form--modal"
			onsubmit={(e) => {
				e.preventDefault();
				void submitForm();
			}}
			novalidate
		>
			{#if formErrorMsg}
				<div class="form-error form-error-{formErrorKind}" role="alert">
					<span class="form-error-icon" aria-hidden="true">!</span>
					<span>{formErrorMsg}</span>
					{#if formErrorKind === 'auth'}
						<div class="form-error-actions">
							<button type="button" onclick={() => location.reload()}>
								Refresh session
							</button>
							<a href="{base}/api/auth/login/?next={base}/reports">Log in again</a>
						</div>
					{/if}
				</div>
			{/if}

			<!-- Person (required) -->
			<fieldset class="form-section">
				<legend class="section-legend">
					<span class="section-icon" aria-hidden="true">◉</span>
					Case
				</legend>
				<p class="section-hint">
					Reports belong to a case (a Person). Pick one before
					filling in the rest.
				</p>
				<div class="field field-full">
					<PersonPicker
						inputId="reports-form-person"
						value={formPersonId}
						onChange={onPersonPicked}
						disabled={formSaving}
					/>
					{#if fieldErrors.person}
						<p class="field-error">{fieldErrors.person}</p>
					{/if}
				</div>
			</fieldset>

			<!-- Source information -->
			<fieldset class="form-section">
				<legend class="section-legend">
					<span class="section-icon" aria-hidden="true">⚲</span>
					Source information
				</legend>
				<p class="section-hint">Who reported this, and how reliable is the source?</p>

				<div class="grid-2">
					<div class="field">
						<label for="rf-source-type">Source type</label>
						<select
							id="rf-source-type"
							class="input--search"
							bind:value={sourceType}
							disabled={formSaving}
						>
							{#each Object.entries(sourceTypeFormLabels) as [value, label] (value)}
								<option {value}>{label}</option>
							{/each}
						</select>
						<p class="field-hint">{sourceTypeFormHelp[sourceType]}</p>
					</div>

					<div class="field">
						<label for="rf-source-attr">
							Source attribution
							<span class="badge-public" title="Shown publicly">public</span>
						</label>
						<input
							id="rf-source-attr"
							type="text"
							class="input--search"
							class:has-error={!!fieldErrors.source_attribution}
							bind:value={sourceAttribution}
							placeholder='e.g. "family member", "BBC article"'
							maxlength={MAX_SHORT}
							autocomplete="off"
							disabled={formSaving}
						/>
						{#if fieldErrors.source_attribution}
							<p class="field-error">{fieldErrors.source_attribution}</p>
						{/if}
					</div>

					<div class="field">
						<label for="rf-reporter-name">
							Reporter name
							<span class="badge-private" title="Hidden from public view">
								<svg viewBox="0 0 16 16" width="11" height="11" aria-hidden="true">
									<path
										fill="currentColor"
										d="M4 7V5a4 4 0 1 1 8 0v2h1a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1h1zm2 0h4V5a2 2 0 1 0-4 0v2z"
									/>
								</svg>
								private
							</span>
						</label>
						<input
							id="rf-reporter-name"
							type="text"
							class="input--search"
							bind:value={reporterName}
							placeholder="Not shown publicly"
							maxlength={255}
							autocomplete="off"
							disabled={formSaving}
						/>
					</div>

					<div class="field">
						<label for="rf-reporter-contact">
							Reporter contact
							<span class="badge-private" title="Hidden from public view">
								<svg viewBox="0 0 16 16" width="11" height="11" aria-hidden="true">
									<path
										fill="currentColor"
										d="M4 7V5a4 4 0 1 1 8 0v2h1a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1h1zm2 0h4V5a2 2 0 1 0-4 0v2z"
									/>
								</svg>
								private
							</span>
						</label>
						<input
							id="rf-reporter-contact"
							type="text"
							class="input--search"
							class:has-error={!!fieldErrors.reporter_contact}
							bind:value={reporterContact}
							placeholder="Email, phone, Signal — how we follow up"
							maxlength={MAX_SHORT}
							autocomplete="off"
							disabled={formSaving}
						/>
						{#if fieldErrors.reporter_contact}
							<p class="field-error">{fieldErrors.reporter_contact}</p>
						{/if}
					</div>
				</div>
			</fieldset>

			<!-- Event timeline & location -->
			<fieldset class="form-section">
				<legend class="section-legend">
					<span class="section-icon" aria-hidden="true">⌚</span>
					Event timeline
				</legend>
				<p class="section-hint">
					When did it happen? Leave the end date blank for a single-day event.
				</p>

				<div class="grid-2">
					<div class="field">
						<label for="rf-date-start">Start date</label>
						<input
							id="rf-date-start"
							type="date"
							class="input--search"
							class:has-error={!!fieldErrors.date_start}
							bind:value={dateStart}
							disabled={formSaving}
						/>
					</div>

					<div class="field">
						<label for="rf-date-end">End date <span class="optional-mark">(optional)</span></label>
						<input
							id="rf-date-end"
							type="date"
							class="input--search"
							class:has-error={!!fieldErrors.date_end}
							bind:value={dateEnd}
							disabled={formSaving}
						/>
						{#if fieldErrors.date_end}
							<p class="field-error">{fieldErrors.date_end}</p>
						{/if}
					</div>
				</div>
			</fieldset>

			<!-- Report details -->
			<fieldset class="form-section">
				<legend class="section-legend">
					<span class="section-icon" aria-hidden="true">≡</span>
					Report details
				</legend>
				<p class="section-hint">What happened, in your own words. Be specific.</p>

				<div class="field field-full">
					<label for="rf-narrative">
						Narrative <span class="required-mark" aria-hidden="true">*</span>
						<span class="sr-only">required</span>
					</label>
					<textarea
						id="rf-narrative"
						class="input--search narrative-textarea"
						class:has-error={!!fieldErrors.narrative}
						bind:value={narrative}
						maxlength={MAX_NARRATIVE}
						placeholder="What happened? What is known? Include dates, places, people, and any context that helps."
						disabled={formSaving}
					></textarea>
					{#if fieldErrors.narrative}
						<p class="field-error">{fieldErrors.narrative}</p>
					{/if}
					<div class="field-counter" aria-live="polite">
						{narrative.length} / {MAX_NARRATIVE}
					</div>
				</div>

				<div class="grid-2">
					<div class="field">
						<label for="rf-suspected">
							Suspected reason <span class="optional-mark">(optional)</span>
						</label>
						<textarea
							id="rf-suspected"
							class="input--search"
							bind:value={suspectedReason}
							maxlength={MAX_NARRATIVE}
							placeholder="What do sources believe is the reason? Stay close to what they actually say."
							disabled={formSaving}
						></textarea>
					</div>

					<div class="field">
						<label for="rf-official">
							Official reason <span class="optional-mark">(optional)</span>
						</label>
						<textarea
							id="rf-official"
							class="input--search"
							bind:value={officialReason}
							maxlength={MAX_NARRATIVE}
							placeholder="What did the state officially charge, if anything?"
							disabled={formSaving}
						></textarea>
					</div>
				</div>
			</fieldset>

			<!-- Privacy -->
			<fieldset class="form-section">
				<legend class="section-legend">
					<span class="section-icon" aria-hidden="true">
						<svg viewBox="0 0 16 16" width="14" height="14">
							<path
								fill="currentColor"
								d="M4 7V5a4 4 0 1 1 8 0v2h1a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1h1zm2 0h4V5a2 2 0 1 0-4 0v2z"
							/>
						</svg>
					</span>
					Privacy
				</legend>
				<p class="section-hint">
					Private reports are hidden from the public case page.
					Volunteers and advocates can still see them when logged in.
				</p>
				<div class="field">
					<label class="field-checkbox">
						<input
							type="checkbox"
							bind:checked={isPrivate}
							disabled={formSaving}
						/>
						<span>Mark this report as private</span>
					</label>
				</div>
			</fieldset>

			<!-- Additional Sources (witnesses / news / documents) -->
			<fieldset class="form-section">
				<legend class="section-legend">
					<span class="section-icon" aria-hidden="true">⚲</span>
					Sources
					<span class="legend-count">{sourceEntries.length}</span>
				</legend>
				<p class="section-hint">
					Add additional sources backing this report — each witness,
					news article, or supporting document gets its own entry
					with its own attribution, narrative, and privacy flag.
				</p>

				{#each sourceEntries as entry, i (entry.uid)}
					<div class="repeatable-entry" data-index={i}>
						<div class="repeatable-entry-header">
							<h4 class="repeatable-entry-title">Source #{i + 1}</h4>
							<button
								type="button"
								class="repeatable-entry-remove"
								aria-label="Remove source {i + 1}"
								onclick={() => removeSource(i)}
								disabled={formSaving}
							>✕ Remove</button>
						</div>

						<div class="grid-2">
							<div class="field">
								<label for="src-{entry.uid}-type">Source type</label>
								<select
									id="src-{entry.uid}-type"
									class="input--search"
									bind:value={entry.source_type}
									disabled={formSaving}
								>
									{#each Object.entries(sourceTypeFormLabels) as [value, label] (value)}
										<option {value}>{label}</option>
									{/each}
								</select>
								<p class="field-hint">{sourceTypeFormHelp[entry.source_type]}</p>
							</div>

							<div class="field">
								<label for="src-{entry.uid}-attr">
									Source attribution
									<span class="badge-public" title="Shown publicly">public</span>
								</label>
								<input
									id="src-{entry.uid}-attr"
									type="text"
									class="input--search"
									bind:value={entry.source_attribution}
									placeholder='e.g. "family member", "BBC article"'
									maxlength={MAX_SHORT}
									autocomplete="off"
									disabled={formSaving}
								/>
							</div>

							<div class="field">
								<label for="src-{entry.uid}-date">Date start</label>
								<input
									id="src-{entry.uid}-date"
									type="date"
									class="input--search"
									bind:value={entry.date_start}
									disabled={formSaving}
								/>
							</div>

							<div class="field">
								<label class="field-checkbox">
									<input
										type="checkbox"
										bind:checked={entry.is_private}
										disabled={formSaving}
									/>
									<span>Mark this source as private</span>
								</label>
								<p class="field-hint">
									Private sources are hidden from public reads,
									even on a public report.
								</p>
							</div>
						</div>

						<div class="field field-full">
							<label for="src-{entry.uid}-narrative">Narrative</label>
							<textarea
								id="src-{entry.uid}-narrative"
								class="input--search"
								bind:value={entry.narrative}
								maxlength={MAX_NARRATIVE}
								placeholder="What does this source say happened? Dates, places, context."
								disabled={formSaving}
							></textarea>
							<div class="field-counter" aria-live="polite">
								{entry.narrative.length} / {MAX_NARRATIVE}
							</div>
						</div>
					</div>
				{/each}

				<button
					type="button"
					class="repeatable-add"
					onclick={addSource}
					disabled={formSaving}
				>+ Add another</button>
			</fieldset>

			<!-- Media (photos / documents / videos / links) -->
			<fieldset class="form-section">
				<legend class="section-legend">
					<span class="section-icon" aria-hidden="true">▣</span>
					Media
					<span class="legend-count">{mediaEntries.length}</span>
				</legend>
				<p class="section-hint">
					Attach supporting evidence — photos, documents, videos,
					or external links. Each item gets its own visibility
					tier; "Sensitive" requires Advocate/Admin role.
				</p>

				{#each mediaEntries as entry, i (entry.uid)}
					<div class="repeatable-entry" data-index={i}>
						<div class="repeatable-entry-header">
							<h4 class="repeatable-entry-title">Media #{i + 1}</h4>
							<button
								type="button"
								class="repeatable-entry-remove"
								aria-label="Remove media {i + 1}"
								onclick={() => removeMedia(i)}
								disabled={formSaving}
							>✕ Remove</button>
						</div>

						<div class="grid-2">
							<div class="field">
								<label for="med-{entry.uid}-type">Media type</label>
								<select
									id="med-{entry.uid}-type"
									class="input--search"
									bind:value={entry.media_type}
									disabled={formSaving}
								>
									<option value="photo">Photo</option>
									<option value="document">Document</option>
									<option value="video">Video</option>
									<option value="link">External link</option>
								</select>
							</div>

							<div class="field">
								<label for="med-{entry.uid}-vis">Visibility</label>
								<select
									id="med-{entry.uid}-vis"
									class="input--search"
									bind:value={entry.visibility}
									disabled={formSaving}
								>
									<option value="public">Public — anyone can view</option>
									<option value="restricted">Restricted — authenticated users only</option>
									<option value="sensitive">Sensitive — advocates/admin only</option>
								</select>
							</div>

							<div class="field field-full">
								<label for="med-{entry.uid}-desc">
									Description <span class="optional-mark">(optional)</span>
								</label>
								<input
									id="med-{entry.uid}-desc"
									type="text"
									class="input--search"
									bind:value={entry.description}
									placeholder="What's in this media? Alt text for images."
									maxlength={500}
									autocomplete="off"
									disabled={formSaving}
								/>
							</div>

							<div class="field field-full">
								<label for="med-{entry.uid}-url">
									File URL <span class="optional-mark">(URL or upload via Media gallery)</span>
								</label>
								<input
									id="med-{entry.uid}-url"
									type="url"
									class="input--search"
									bind:value={entry.url}
									placeholder="https://… (paste a link, or upload via the case page)"
									maxlength={1000}
									autocomplete="off"
									disabled={formSaving}
								/>
								<p class="field-hint">
									File uploads (multipart) happen on the case page
									media gallery — this form accepts external links.
								</p>
							</div>
						</div>
					</div>
				{/each}

				<button
					type="button"
					class="repeatable-add"
					onclick={addMedia}
					disabled={formSaving}
				>+ Add another Media</button>
			</fieldset>

			<!-- Action footer -->
			<footer class="form-footer form-footer--modal">
				<p class="form-footer-hint">
					By submitting, you confirm the information is accurate
					to the best of your knowledge.
				</p>
				<div class="form-footer-actions">
					<button
						type="button"
						class="btn btn-secondary"
						onclick={closeAddForm}
						disabled={formSaving}
					>Cancel</button>
					<button
						type="submit"
						class="btn btn-primary"
						disabled={formSaving}
					>
						{#if formSaving}
							<span class="spinner" aria-hidden="true"></span>
							Saving…
						{:else}
							Submit report
						{/if}
					</button>
				</div>
			</footer>
		</form>
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
	.reports-header-action {
		flex: 0 0 auto;
		align-self: flex-start;
		padding: 0.55rem 1rem;
		font-size: 0.82rem;
		min-height: 0;
	}
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

	/* Mobile card reflow — same pattern as /watchdog + /contacts.
	   At <768px the table re-flows into stacked cards using
	   data-label pseudo-elements; horizontal scroll remains the
	   fallback at very narrow widths. */
	@media (max-width: 768px) {
		.reports-table,
		.reports-table thead,
		.reports-table tbody,
		.reports-table tr,
		.reports-table td {
			display: block;
			width: 100%;
		}
		.reports-table thead {
			display: none;
		}
		.reports-table tbody tr {
			background: var(--color-bg-white);
			border: 1px solid var(--color-border-light);
			border-left: 3px solid var(--color-primary-light);
			border-radius: var(--radius-card);
			margin-bottom: 0.75rem;
			padding: 0.65rem 0.85rem;
		}
		.reports-table td {
			display: flex;
			justify-content: space-between;
			align-items: center;
			gap: 0.75rem;
			padding: 0.4rem 0;
			border-bottom: 1px solid var(--color-border-subtle);
		}
		.reports-table td:last-child {
			border-bottom: none;
		}
		.reports-table td::before {
			content: attr(data-label);
			flex: 0 0 auto;
			font-size: 0.72rem;
			text-transform: uppercase;
			letter-spacing: 0.06rem;
			color: var(--color-text-muted);
			font-weight: 700;
		}
		/* Title is the card "headline" — full width, larger, no label. */
		.reports-table td.cell-title {
			flex-direction: column;
			align-items: flex-start;
			gap: 0.15rem;
			padding-bottom: 0.55rem;
			margin-bottom: 0.25rem;
			border-bottom: 1px solid var(--color-border-light);
		}
		.reports-table td.cell-title::before {
			content: none;
		}
	}

	/* "Add Report" comprehensive form modal — body chrome. The modal
	   itself (chrome / backdrop / focus trap) lives in Modal.svelte;
	   this file owns the form layout that fills it. */
	.report-form--modal {
		padding: 1.25rem 1.5rem 1.5rem 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
		max-width: none;
		margin: 0;
		width: 100%;
		box-sizing: border-box;
	}

	/* Modal is wider than the default — accommodate the form sections
	   without forcing horizontal scroll on common widths. */
	:global(.modal:has(.report-form--modal)) {
		max-width: 760px;
	}

	/* Form-level error banner — same family as /persons/[id]/report */
	.report-form--modal .form-error {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem 0.85rem;
		padding: 0.7rem 0.95rem;
		background: #fed7d7;
		color: #c53030;
		border: 1px solid #feb2b2;
		border-radius: var(--radius-card);
		font-size: 0.9rem;
	}
	.report-form--modal .form-error-network {
		background: #fffaf0;
		color: #5a3b00;
		border-color: #fbd38d;
	}
	.report-form--modal .form-error-server {
		background: #fed7d7;
		color: #c53030;
		border-color: #feb2b2;
	}
	.report-form--modal .form-error-validation {
		background: #fef5e7;
		color: #744210;
		border-color: #f6ad55;
	}
	.report-form--modal .form-error-auth {
		background: var(--color-surface);
		color: var(--color-text);
		border-color: var(--color-border-light);
	}
	.report-form--modal .form-error-actions {
		display: flex;
		gap: 0.5rem;
		align-items: center;
		margin-left: auto;
	}
	.report-form--modal .form-error-actions a,
	.report-form--modal .form-error-actions button {
		font-size: 0.85rem;
		font-weight: 500;
		text-decoration: none;
		padding: 0.3rem 0.7rem;
		border-radius: var(--radius-control);
		border: 1px solid currentColor;
		background: transparent;
		color: inherit;
		cursor: pointer;
	}
	.report-form--modal .form-error-actions a:hover,
	.report-form--modal .form-error-actions button:hover {
		background: rgba(0, 0, 0, 0.06);
	}
	.report-form--modal .form-error-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 22px;
		height: 22px;
		border-radius: 50%;
		background: rgba(197, 48, 48, 0.2);
		font-weight: 700;
		font-size: 0.85rem;
	}

	/* Section cards */
	.report-form--modal .form-section {
		border: 1px solid var(--color-border-subtle);
		border-left: 3px solid var(--color-primary);
		border-radius: var(--radius-card-lg);
		background: var(--color-bg-white);
		padding: 1.25rem 1.25rem 1.4rem 1.25rem;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: 0.85rem;
	}
	.report-form--modal .section-legend {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0 0.5rem;
		font-size: 0.95rem;
		font-weight: 700;
		color: var(--color-text);
	}
	.report-form--modal .section-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 26px;
		height: 26px;
		border-radius: 50%;
		background: var(--color-primary-tint, #e6efff);
		color: var(--color-primary);
		font-size: 0.9rem;
	}
	.report-form--modal .section-hint {
		margin: -0.3rem 0 0.1rem 0;
		font-size: 0.85rem;
		color: var(--color-text-muted);
		line-height: 1.5;
	}

	/* Two-column grid for paired fields; full-width fields opt out */
	.report-form--modal .grid-2 {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 0.85rem 1rem;
	}
	.report-form--modal .field-full {
		grid-column: 1 / -1;
	}
	@media (max-width: 640px) {
		.report-form--modal .grid-2 {
			grid-template-columns: 1fr;
		}
	}

	/* Field chrome */
	.report-form--modal .field {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
		min-width: 0;
	}
	.report-form--modal .field label {
		display: inline-flex;
		align-items: center;
		gap: 0.45rem;
		font-size: 0.82rem;
		font-weight: 600;
		color: var(--color-text);
		margin: 0;
		flex-wrap: wrap;
	}
	.report-form--modal .field-hint {
		margin: 0;
		font-size: 0.75rem;
		color: var(--color-text-muted);
		line-height: 1.45;
	}
	.report-form--modal .field-counter {
		font-size: 0.75rem;
		color: var(--color-text-muted);
		text-align: right;
	}
	.report-form--modal .field-error {
		margin: 0;
		font-size: 0.8rem;
		color: var(--color-danger);
	}

	/* Privacy-style checkbox row */
	.report-form--modal .field-checkbox {
		display: inline-flex;
		align-items: center;
		gap: 0.55rem;
		font-size: 0.92rem;
		color: var(--color-text);
		cursor: pointer;
		user-select: none;
	}
	.report-form--modal .field-checkbox input[type='checkbox'] {
		width: 18px;
		height: 18px;
		accent-color: var(--color-primary);
		cursor: pointer;
	}

	/* Inputs (reuses .input--search from app.css) */
	.report-form--modal .input--search,
	.report-form--modal textarea.input--search {
		font-size: 0.92rem;
		padding: 0.5rem 0.75rem;
		width: 100%;
		box-sizing: border-box;
	}
	.report-form--modal textarea.input--search {
		min-height: 90px;
		resize: vertical;
		font-family: inherit;
		line-height: 1.5;
	}
	.report-form--modal .narrative-textarea {
		min-height: 160px;
	}
	.report-form--modal .input--search.has-error {
		border-color: var(--color-danger);
	}
	.report-form--modal .input--search.has-error:focus {
		box-shadow: 0 0 0 3px rgba(217, 22, 22, 0.15);
	}
	.report-form--modal input:disabled,
	.report-form--modal select:disabled,
	.report-form--modal textarea:disabled {
		opacity: 0.65;
		cursor: not-allowed;
	}

	/* Public / private badges on labels */
	.report-form--modal .badge-public,
	.report-form--modal .badge-private {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.1rem 0.5rem;
		border-radius: 999px;
		font-size: 0.66rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.04rem;
		line-height: 1.2;
	}
	.report-form--modal .badge-public {
		background: #c6f6d5;
		color: #22543d;
	}
	.report-form--modal .badge-private {
		background: #fefcbf;
		color: #744210;
	}
	.report-form--modal .badge-private svg {
		display: inline-block;
	}

	/* Required / optional markers */
	.report-form--modal .required-mark {
		color: var(--color-danger);
		font-weight: 700;
	}
	.report-form--modal .optional-mark {
		color: var(--color-text-muted);
		font-size: 0.75rem;
		font-weight: 400;
	}
	.report-form--modal .sr-only {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
		border: 0;
	}

	/* Action footer */
	.report-form--modal .form-footer--modal {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		padding: 0.85rem 1.1rem;
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-subtle);
		border-left: 3px solid var(--color-primary);
		border-radius: var(--radius-card-lg);
		box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.04);
	}
	.report-form--modal .form-footer-hint {
		margin: 0;
		font-size: 0.8rem;
		color: var(--color-text-muted);
		max-width: 460px;
		line-height: 1.45;
	}
	.report-form--modal .form-footer-actions {
		display: flex;
		gap: 0.65rem;
		flex: 0 0 auto;
	}
	.report-form--modal .form-footer-actions .btn {
		min-width: 110px;
	}
	.report-form--modal .form-footer-actions .btn:disabled {
		opacity: 0.65;
		cursor: not-allowed;
	}

	/* Submit spinner */
	.report-form--modal .spinner {
		display: inline-block;
		width: 14px;
		height: 14px;
		border: 2px solid currentColor;
		border-right-color: transparent;
		border-radius: 50%;
		animation: form-spin 0.7s linear infinite;
		margin-right: 0.4rem;
		vertical-align: -2px;
	}
	@keyframes form-spin {
		to {
			transform: rotate(360deg);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.report-form--modal .spinner {
			animation: none;
		}
	}

	@media (max-width: 600px) {
		.report-form--modal .form-footer--modal {
			flex-direction: column;
			align-items: stretch;
			text-align: center;
		}
		.report-form--modal .form-footer-actions {
			justify-content: stretch;
		}
		.report-form--modal .form-footer-actions .btn {
			flex: 1 1 auto;
			min-width: 0;
		}
	}

	/* === Repeatable entry (Sources / Media) ============================
	   Each entry lives in its own bordered block with a header row
	   (title + remove button) and a field grid. Visual separation
	   prevents the volunteer from accidentally typing into the wrong
	   source's narrative. */
	.report-form--modal .repeatable-entry {
		display: flex;
		flex-direction: column;
		gap: 0.85rem;
		padding: 1rem 1.1rem;
		border: 1px solid var(--color-border-light);
		border-left: 3px solid var(--color-primary-light, #aac0ff);
		border-radius: var(--radius-card);
		background: var(--color-surface, #f7f7f9);
	}
	.report-form--modal .repeatable-entry + .repeatable-entry {
		margin-top: 0.75rem;
	}
	.report-form--modal .repeatable-entry-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		margin-bottom: 0.1rem;
	}
	.report-form--modal .repeatable-entry-title {
		margin: 0;
		font-size: 0.92rem;
		font-weight: 700;
		color: var(--color-text);
	}
	.report-form--modal .repeatable-entry-remove {
		background: transparent;
		border: 1px solid var(--color-border-light);
		color: var(--color-danger, #c53030);
		font-size: 0.78rem;
		padding: 0.25rem 0.65rem;
		border-radius: var(--radius-card);
		cursor: pointer;
		font-weight: 600;
		min-height: 0;
	}
	.report-form--modal .repeatable-entry-remove:hover:not(:disabled) {
		background: #fed7d7;
		border-color: #feb2b2;
	}
	.report-form--modal .repeatable-entry-remove:disabled {
		opacity: 0.55;
		cursor: not-allowed;
	}

	/* Add-another button — full-width below the entries list */
	.report-form--modal .repeatable-add {
		width: 100%;
		margin-top: 0.85rem;
		padding: 0.6rem 0.85rem;
		background: var(--color-bg-white);
		border: 1px dashed var(--color-border-light);
		color: var(--color-primary);
		font-size: 0.9rem;
		font-weight: 600;
		border-radius: var(--radius-card);
		cursor: pointer;
		min-height: 0;
	}
	.report-form--modal .repeatable-add:hover:not(:disabled) {
		background: var(--color-surface, #f7f7f9);
		border-style: solid;
		border-color: var(--color-primary-light);
	}
	.report-form--modal .repeatable-add:disabled {
		opacity: 0.55;
		cursor: not-allowed;
	}

	/* Count badge next to section legend (Sources: 3, Media: 1, etc.) */
	.report-form--modal .legend-count {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 24px;
		padding: 0.05rem 0.55rem;
		margin-left: 0.5rem;
		background: var(--color-primary-tint, #e6efff);
		color: var(--color-primary);
		font-size: 0.75rem;
		font-weight: 700;
		border-radius: 999px;
		vertical-align: middle;
	}

	/* === Media partial-failure banner (page-level) ==================== */
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
</style>