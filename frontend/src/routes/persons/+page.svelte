<script lang="ts">
	/**
	 * /persons — the cases catalog page.
	 *
	 * Composes the floating FilterToolbar + the PersonCard grid + a
	 * legacy list-view table for users who prefer tabular browsing.
	 * Owns all filter / sort / pagination state; view-mode persistence
	 * is delegated to <ViewToggle>.
	 *
	 * Initial paint: +page.ts universal load reads `?search=...&country=...`
	 * from the URL and fetches the first page server-side, so deep
	 * links render with results instead of a skeleton. Client-side
	 * filter changes still call applyFilters() (no re-run of load()).
	 */
	import { onMount, untrack } from 'svelte';
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import { afterNavigate, replaceState } from '$app/navigation';
	import { getPersons, getCountries, getCategories } from '$lib/api';
	import { statusLabels } from '$lib/StatusBadge.svelte';
	import { debounce } from '$lib/debounce';
	import Banner from '$lib/Banner.svelte';
	import FilterToolbar from '$lib/FilterToolbar.svelte';
	import PersonCard from '$lib/PersonCard.svelte';
	import Icon from '$lib/Icon.svelte';
	import Skeleton from '$lib/Skeleton.svelte';
	import ErrorCard from '$lib/ErrorCard.svelte';
	import type { PageData } from './$types';
	import type { Paginated, Person, PersonCategory } from '$lib/types';

	let { data }: { data: PageData } = $props();

	const SEARCH_DEBOUNCE_MS = 300;
	// Mirror of PersonSearchFilter.MIN_LENGTH on the backend. Below this,
	// `?search=` would return 0 results regardless — so we suppress the
	// fetch entirely and surface a "keep typing" hint instead, keeping
	// the previous results + URL on screen until the user crosses the
	// threshold or clears the input.
	const MIN_SEARCH_LENGTH = 3;
	const PAGE_SIZE = 12;
	const SKELETON_CARD_COUNT = 12;

	// The API's default ordering, which the catalog sends as "no
	// ?ordering= at all" rather than spelling it out — see
	// currentFilterParams().
	const DEFAULT_SORT = '-created_at';

	const sorts = [
		{ value: '-created_at', label: 'Newest submitted' },
		{ value: 'created_at', label: 'Oldest submitted' },
		{ value: '-updated_at', label: 'Recently updated' },
		{ value: 'name', label: 'Name (A–Z)' },
		{ value: 'country', label: 'Country' },
		{ value: 'current_status', label: 'Status' },
	];

	// Seed local state from the SSR load. data.persons / data.countries /
	// data.categories / data.personsCount come back filled if the load
	// succeeded; on failure they're empty and the client refetches via
	// applyFilters() on mount.
	let persons: Person[] = $state(untrack(() => data.persons ?? []));
	let countries: { country: string; count: number }[] = $state(untrack(() => data.countries ?? []));
	let categories: PersonCategory[] = $state(untrack(() => data.categories ?? []));
	let loading = $state(false);
	let error: string | null = $state(untrack(() => data.error));
	let totalCount = $state(untrack(() => data.personsCount ?? 0));
	let currentPage = $state(1);
	// Becomes true after the first loadPersons() settles. The skeleton
	// only renders on the very first load (when we have nothing to show);
	// every subsequent search goes straight from "loading" to either
	// results or the empty state. This stops the "search gibberish →
	// skeleton forever" loop, and also prevents the skeleton from
	// flickering over already-loaded results when the user keeps typing.
	let initialLoadComplete = $state(false);

	// Single counter for loadPersons; bumped on every load() and on
	// unmount. Any async path that captured the previous value sees
	// `myToken !== loadToken` and bails. Together with the
	// AbortController below this stops an older in-flight request from
	// clobbering a newer one when the user types fast (the source of
	// "results flicker" between consecutive searches).
	let loadToken = 0;
	let loadController: AbortController | null = null;

	// Initialize filter state from URL so the controls reflect the deep
	// link. Without this, a user landing on /persons?country=USA would
	// see the right results but the toolbar dropdown would still say
	// "All countries".
	function readFiltersFromUrl() {
		const sp = page.url.searchParams;
		search = sp.get('search') ?? '';
		filterCountry = sp.get('country') ?? '';
		filterStatus = sp.get('current_status') ?? '';
		filterCategory = sp.get('category') ?? '';
		sort = sp.get('ordering') ?? DEFAULT_SORT;
		stale = sp.get('stale') ?? '';
	}

	// Filters
	let search = $state('');
	let filterCountry = $state('');
	let filterStatus = $state('');
	let filterCategory = $state('');
	let sort = $state(DEFAULT_SORT);
	// Recency / staleness quick-filter. `''` means "All"; a positive
	// integer is the "inactive N+ days" threshold. Empty string is
	// the URL-default and is what makes the segmented control
	// "All" the default selection.
	let stale = $state('');

	// Stale quick-filter options — empty string ("All") plus four
	// commonly-used thresholds. Living as a constant (not a fetch)
	// because these are UI-side buckets, not API enum values.
	const staleOptions: Array<{ value: string; label: string }> = [
		{ value: '', label: 'All' },
		{ value: '30', label: 'Inactive 30+ d' },
		{ value: '90', label: 'Inactive 90+ d' },
		{ value: '180', label: 'Inactive 180+ d' },
		{ value: '365', label: 'Inactive 1y+' },
	];

	// Sync the URL to the current filter state. replaceState updates the
	// address bar WITHOUT re-running load() — every keystroke used to
	// call goto(), which re-fetched /api/persons on the server,
	// re-rendered the page, and stole focus from the search input
	// (the "double-Enter / focus loss" bug). replaceState keeps the
	// SearchInput DOM node alive and skips the redundant server
	// round-trip on every keystroke.
	async function syncUrl() {
		const sp = new URLSearchParams();
		if (search) sp.set('search', search);
		if (filterCountry) sp.set('country', filterCountry);
		if (filterStatus) sp.set('current_status', filterStatus);
		if (filterCategory) sp.set('category', filterCategory);
		if (stale) sp.set('stale', stale);
		if (sort && sort !== DEFAULT_SORT) sp.set('ordering', sort);
		const qs = sp.toString();
		const target = qs ? `?${qs}` : page.url.pathname;
		// Only update if the URL would actually change — avoids
		// unnecessary history churn when re-renders fire.
		if (target !== page.url.pathname + page.url.search) {
			await replaceState(target, {});
		}
	}

	// View mode is owned by <ViewToggle>; we read it for the conditional
	// markup but never write to localStorage directly here.
	let viewMode: 'cards' | 'list' = $state('cards');

	// --- Top-of-page banner (deleted=1 from /persons/[id] redirect) -------
	// The detail page redirects here after a successful delete. We surface a
	// transient banner mirroring /contacts/+page.svelte's pattern, then
	// strip the query string so a refresh doesn't replay it.
	type BannerKind = 'success' | 'error';
	let bannerMsg = $state('');
	let bannerKind = $state<BannerKind>('success');

	async function consumeUrlBanner() {
		const url = page.url;
		const deleted = url.searchParams.get('deleted');
		const err = url.searchParams.get('error');
		if (deleted === '1') {
			bannerKind = 'success';
			bannerMsg = 'Case deleted.';
		} else if (err) {
			bannerKind = 'error';
			bannerMsg = err;
		}
		if (deleted || err) {
			const clean = new URL(url);
			clean.searchParams.delete('deleted');
			clean.searchParams.delete('error');
			// Use $app/navigation's replaceState so SvelteKit's internal
			// history.state is preserved by API contract — direct
			// history.replaceState could lose it on a future refactor.
			await replaceState(clean.pathname + clean.search, {});
		}
	}

	// Derived pagination + filter flag
	let totalPages = $derived(Math.max(1, Math.ceil(totalCount / PAGE_SIZE)));
	let pageStart = $derived(((currentPage - 1) * PAGE_SIZE) + 1);
	let pageEnd = $derived(Math.min(currentPage * PAGE_SIZE, totalCount));
	let canPrev = $derived(currentPage > 1);
	let canNext = $derived(currentPage < totalPages);
	let hasActiveFilters = $derived(
		Boolean(search || filterCountry || filterStatus || filterCategory || stale || sort !== DEFAULT_SORT),
	);

	// Memoized signature for the countries-dropdown query — refetches only
	// when the *other* filters change, not when `filterCountry` itself does.
	let lastCountryParamKey = '';

	async function loadCountries(countryParams: Record<string, string> = {}) {
		try {
			countries = await getCountries(countryParams);
		} catch (e) {
			console.error(e);
		}
	}

	async function loadPersons(
		params: Record<string, string> = {},
		page: number = currentPage,
	) {
		const myToken = ++loadToken;
		loadController?.abort();
		loadController = new AbortController();
		const { signal } = loadController;

		loading = true;
		error = null;
		try {
			const pageParams = { ...params, page: String(page) };
			const data: Paginated<Person> = await getPersons(pageParams, { signal });
			// If a newer load() (or unmount) has happened, drop the result.
			if (myToken !== loadToken) return;
			persons = data.results;
			totalCount = data.count;
			currentPage = page;
			if (typeof window !== 'undefined') window.scrollTo({ top: 0, behavior: 'smooth' });
		} catch (e: unknown) {
			// AbortError is the expected outcome of cancellation; the caller
			// (and the user) treat it the same as a dropped result so we
			// don't render an error banner for a request they've moved past.
			if (e instanceof DOMException && e.name === 'AbortError') return;
			console.error(e);
			error =
				e instanceof Error
					? `Could not load cases: ${e.message}`
					: 'Could not load cases. Please try again.';
		} finally {
			// Only flip loading=false if we're still the latest request; an
			// in-flight newer one owns the spinner.
			if (myToken === loadToken) loading = false;
			initialLoadComplete = true;
		}
	}

	function currentFilterParams(): Record<string, string> {
		const params: Record<string, string> = {};
		// Below MIN_SEARCH_LENGTH the backend returns nothing regardless,
		// so suppress the key entirely (defensive — applyFilters also
		// early-returns for short queries, but a direct filter-select
		// change could still land here).
		if (search && search.length >= MIN_SEARCH_LENGTH) params.search = search;
		if (filterCountry) params.country = filterCountry;
		if (filterStatus) params.current_status = filterStatus;
		if (filterCategory) params.category = filterCategory;
		if (stale) params.stale = stale;
		// Omit the default so the API applies its own default ordering
		// (deceased cases last, then newest first). Sending
		// `ordering=-created_at` explicitly would replace both keys and
		// pull deceased cases back onto the first page. Mirrors the same
		// omission in syncUrl().
		if (sort && sort !== DEFAULT_SORT) params.ordering = sort;
		return params;
	}

	// Same as currentFilterParams() but omits `country` so the dropdown
	// still shows every option alongside the per-country match counts.
	function currentCountryParams(): Record<string, string> {
		const params = currentFilterParams();
		delete params.country;
		return params;
	}

	async function applyFilters() {
		// Drop any pending debounced search so a synchronous submit
		// (Enter / Search button / filter select) doesn't fire again 300ms
		// later with stale args. No-op when called from the debounce
		// itself (timer is already null by then).
		debouncedSearch.cancel();
		// Mid-type guard: while the query is below MIN_SEARCH_LENGTH the
		// backend would return nothing, so don't fire a fetch, don't
		// touch the URL, and don't re-run the countries dropdown — just
		// keep the previous list + URL on screen until the user crosses
		// the threshold (or clears the input). The "Keep typing — search
		// needs at least 3 characters" hint in the template makes the
		// state visible.
		if (search.length > 0 && search.length < MIN_SEARCH_LENGTH) return;
		await loadPersons(currentFilterParams(), 1);
		const newKey = JSON.stringify(
			Object.entries(currentCountryParams()).sort(([a], [b]) => a.localeCompare(b)),
		);
		if (newKey !== lastCountryParamKey) {
			lastCountryParamKey = newKey;
			loadCountries(currentCountryParams());
		}
		// Mirror filter state → URL so users can share/bookmark.
		// replaceState avoids re-running load() and re-rendering the page,
		// which was the source of the focus-loss bug.
		await syncUrl();
	}

	async function goToPage(page: number) {
		if (page < 1 || page > totalPages || page === currentPage) return;
		await loadPersons(currentFilterParams(), page);
	}

	function clearFilters() {
		search = '';
		filterCountry = '';
		filterStatus = '';
		filterCategory = '';
		stale = '';
		sort = DEFAULT_SORT;
		applyFilters();
	}

	const debouncedSearch = debounce(() => applyFilters(), SEARCH_DEBOUNCE_MS);

	// Stale-filter change handler. Setting `stale` directly is enough
	// to drive applyFilters via the existing change flow; we wrap it
	// in a named function so the inline onclick stays readable.
	function onStaleChange(value: string) {
		stale = value;
		void applyFilters();
	}

	// Re-sync filter state on same-route Back/Forward (e.g. /persons?country=USA
	// → /persons?country=FR → Back). SvelteKit re-runs `+page.ts` load() but
	// keeps this component mounted, so without this block the bound <select>
	// values would stay on the old filter and the rendered list would not
	// reflect the URL. Cross-route navigation unmounts the component and
	// onMount handles initial state, so we filter on from.url.pathname.
	afterNavigate(({ from, to }) => {
		if (!from || !to) return;
		if (from.url.pathname !== to.url.pathname) return;
		readFiltersFromUrl();
		void applyFilters();
		void loadCountries(currentCountryParams());
	});

	onMount(async () => {
		// Pull any `?deleted=1` / `?error=...` banner param first so the
		// banner appears as soon as the catalog renders.
		await consumeUrlBanner();
		// Sync filter controls from URL (the load() already used these to
		// fetch, but the bound <select>/<input> values still reflect
		// their initial $state defaults unless we copy them across).
		readFiltersFromUrl();
		// If the SSR load returned an error (data.persons is empty AND
		// data.error is set), fall back to a client-side fetch so the
		// Retry button still works. Otherwise trust the SSR data.
		if (data.error) {
			const initial = currentFilterParams();
			await Promise.all([
				loadPersons(initial, 1),
				loadCountries(currentCountryParams()),
				getCategories()
					.then((d) => {
						categories = Array.isArray(d) ? d : d.results ?? [];
					})
					.catch((e: unknown) => console.error(e)),
			]);
		}
		lastCountryParamKey = JSON.stringify(
			Object.entries(currentCountryParams()).sort(([a], [b]) => a.localeCompare(b)),
		);
	});
</script>

<svelte:head>
	<title>Cases — Testimonies.world</title>
	<meta name="description" content="Browse and search the full catalog of persons documented by volunteers. Filter by country, status, category." />
	<meta property="og:description" content="Browse and search the full catalog of persons documented by volunteers. Filter by country, status, category." />
	<meta property="og:type" content="website" />
	<meta name="twitter:description" content="Browse and search the full catalog of persons documented by volunteers. Filter by country, status, category." />
</svelte:head>

<div class="page-surface">
	<header class="catalog-header">
		<h1>Cases</h1>
		<p class="muted">
			{#if !initialLoadComplete && loading}
				<Skeleton variant="text" width="8rem" />
			{:else}
				{totalCount} case{totalCount !== 1 ? 's' : ''} recorded
			{/if}
		</p>
		{#if search.length > 0 && search.length < MIN_SEARCH_LENGTH}
			<!--
				Mid-type guard hint. Tells the user the search isn't
				firing yet, which matches what they're seeing (the list
				stays on the previous results). role="status" + polite
				live region so screen readers announce the transition.
			-->
			<p class="muted small search-hint" role="status" aria-live="polite">
				Keep typing — search needs at least {MIN_SEARCH_LENGTH} characters.
			</p>
		{/if}
	</header>

	{#if bannerMsg}
		<Banner
			kind={bannerKind}
			message={bannerMsg}
			onDismiss={() => (bannerMsg = '')}
		/>
	{/if}

	{#if error}
		<ErrorCard
			title="Couldn't load the case list"
			message={error}
			kind="network"
			retry={applyFilters}
		/>
	{/if}

	<FilterToolbar
		bind:search
		bind:filterCountry
		bind:filterStatus
		bind:filterCategory
		bind:sort
		bind:viewMode
		{countries}
		{categories}
		{sorts}
		{hasActiveFilters}
		onApply={applyFilters}
		onClear={clearFilters}
		onSearchInput={debouncedSearch}
	/>

	<!-- Stale / inactivity quick filter. Inlined here (not in the
	     shared FilterToolbar) because contacts/cases don't have an
	     "activity" axis — this control is /persons-specific. Segmented
	     buttons rather than a select because the buckets are short and
	     a click-target that fits a thumb is faster to scan on mobile. -->
	<div class="stale-filter" role="group" aria-label="Inactivity quick filter">
		<span class="stale-filter-label">Activity</span>
		<div class="stale-filter-buttons">
			{#each staleOptions as opt (opt.value)}
				<button
					type="button"
					class="stale-btn"
					class:active={stale === opt.value}
					aria-pressed={stale === opt.value}
					onclick={() => onStaleChange(opt.value)}
				>
					{opt.label}
				</button>
			{/each}
		</div>
	</div>

	{#if !initialLoadComplete && loading}
		{#if viewMode === 'list'}
			<div class="cases-table-wrap" aria-busy="true" aria-label="Loading cases">
				<div class="cases-table-skeleton">
					{#each Array.from({ length: PAGE_SIZE }, (_, i) => i) as i (i)}
						<Skeleton variant="table-row" cols={7} />
					{/each}
				</div>
			</div>
		{:else}
			<div class="cases-grid" aria-busy="true" aria-label="Loading cases">
				{#each Array.from({ length: SKELETON_CARD_COUNT }, (_, i) => i) as i (i)}
					<Skeleton variant="card" />
				{/each}
			</div>
		{/if}
	{:else if persons.length === 0}
		<!--
			Empty state — covers both "no cases exist yet" and
			"search returned nothing". The Clear-filters CTA only shows
			when the user has applied filters; otherwise it would be a
			dead button. role="status" + aria-live="polite" so screen
			readers announce the transition once the search settles.
		-->
		<div class="empty-state" role="status" aria-live="polite">
			<Icon name="cases" size={48} />
			<p>No cases found matching your criteria.</p>
			{#if hasActiveFilters}
				<button type="button" class="btn btn-secondary" onclick={clearFilters}>
					Clear filters
				</button>
			{/if}
		</div>
	{:else if viewMode === 'list'}
		<div class="cases-table-wrap">
			<table class="cases-table">
				<thead>
					<tr>
						<th>Name</th>
						<th>Country</th>
						<th>Location</th>
						<th>Status</th>
						<th>Last known</th>
						<th>Reports</th>
						<th></th>
					</tr>
				</thead>
				<tbody>
					{#each persons as person (person.id)}
						<tr>
							<td data-label="Name"><strong><a href="{base}/persons/{person.id}">{person.name}</a></strong></td>
							<td data-label="Country">{person.country || '—'}</td>
							<td data-label="Location">{person.rough_location || '—'}</td>
							<td data-label="Status">
								{#if person.current_status}
									<span class="badge badge-{person.current_status}">
										{statusLabels[person.current_status] ?? person.current_status}
									</span>
								{/if}
							</td>
							<td data-label="Last known">{person.last_known_date || '—'}</td>
							<td data-label="Reports">{person.report_count ?? 0}</td>
							<td data-label="" class="cell-actions"><a href="{base}/persons/{person.id}" class="view-link">View »</a></td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{:else}
		<div class="cases-grid">
			{#each persons as person, i (person.id)}
				<PersonCard {person} delayMs={(i % 8) * 40} />
			{/each}
		</div>
	{/if}

	{#if totalCount > 0 && totalPages > 1}
		<nav class="pagination" aria-label="Pagination">
			<button
				type="button"
				class="page-btn"
				disabled={!canPrev || loading}
				onclick={() => goToPage(currentPage - 1)}
			>
				‹ Prev
			</button>
			<div class="page-indicator">
				Page <strong>{currentPage}</strong> of {totalPages}
				<span class="muted small">— showing {pageStart}–{pageEnd} of {totalCount}</span>
			</div>
			<button
				type="button"
				class="page-btn"
				disabled={!canNext || loading}
				onclick={() => goToPage(currentPage + 1)}
			>
				Next ›
			</button>
		</nav>
	{/if}
</div>

<style>
	.catalog-header {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: 1rem;
		flex-wrap: wrap;
		padding-bottom: 1rem;
		margin-bottom: var(--space-section);
		border-bottom: 1px solid var(--color-border-light);
	}
	.catalog-header h1 {
		margin: 0;
		color: var(--color-primary);
	}

	/* Page outer wrapper — standardized rhythm (matches dashboard/casework).
	   Replaces the legacy .page-surface (which inherited the global
	   85%-width .container). */
	.page-surface {
		width: 100%;
		max-width: var(--max-w-page);
		padding: 0 var(--page-px);
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: var(--space-section);
	}

	.cases-table-wrap {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card-lg);
		/* overflow-x: auto lets wide tables scroll horizontally on
		   phones instead of clipping. The previous `overflow: hidden`
		   silently dropped columns off the right edge — a real
		   accessibility bug for mobile advocates. vertical overflow
		   stays clipped (round corners + sticky shadows still work).
		   -webkit-overflow-scrolling: touch enables momentum
		   scrolling on iOS Safari where it's otherwise janky. */
		overflow-x: auto;
		overflow-y: hidden;
		-webkit-overflow-scrolling: touch;
		box-shadow: var(--shadow-card);
	}
	.cases-table-skeleton {
		display: flex;
		flex-direction: column;
	}
	.cases-table {
		width: 100%;
		border-collapse: collapse;
	}
	.cases-table th,
	.cases-table td {
		padding: 0.75rem 1rem;
		text-align: left;
		border-bottom: 1px solid var(--color-border-light);
	}
	.cases-table th {
		background: var(--color-surface);
		font-size: 0.78rem;
		text-transform: uppercase;
		letter-spacing: 0.05rem;
		color: var(--color-text-muted);
	}
	.cases-table tbody tr:hover {
		background: var(--color-surface);
	}
	.cases-table tbody tr:last-child td {
		border-bottom: none;
	}

	/* Mobile card reflow — same pattern as /watchdog + /contacts +
	   /reports. At <768px the table re-flows into stacked cards
	   using data-label pseudo-elements; horizontal scroll remains
	   the fallback at very narrow widths. */
	@media (max-width: 768px) {
		.cases-table,
		.cases-table thead,
		.cases-table tbody,
		.cases-table tr,
		.cases-table td {
			display: block;
			width: 100%;
		}
		.cases-table thead {
			display: none;
		}
		.cases-table tbody tr {
			background: var(--color-bg-white);
			border: 1px solid var(--color-border-light);
			border-left: 3px solid var(--color-primary-light);
			border-radius: var(--radius-card);
			margin-bottom: 0.75rem;
			padding: 0.65rem 0.85rem;
			box-shadow: var(--shadow-card);
			/* Containment on table rows is partially supported —
			   `layout`/`paint` work but `content-visibility: auto`
			   interferes with the table's intrinsic sizing on
			   some engines, so we scope only the layout+paint
			   containment here. */
			contain: layout paint;
		}
		.cases-table tbody tr:hover {
			background: var(--color-bg-white);
		}
		.cases-table td {
			display: flex;
			justify-content: space-between;
			align-items: center;
			gap: 0.75rem;
			padding: 0.4rem 0;
			border-bottom: 1px solid var(--color-border-subtle);
		}
		.cases-table td:last-child {
			border-bottom: none;
		}
		.cases-table td::before {
			content: attr(data-label);
			flex: 0 0 auto;
			font-size: 0.72rem;
			text-transform: uppercase;
			letter-spacing: 0.06rem;
			color: var(--color-text-muted);
			font-weight: 700;
		}
		/* Name is the card "title" — full width, larger, no label. */
		.cases-table td[data-label='Name'] {
			flex-direction: column;
			align-items: flex-start;
			gap: 0.15rem;
			padding-bottom: 0.55rem;
			margin-bottom: 0.25rem;
			border-bottom: 1px solid var(--color-border-light);
		}
		.cases-table td[data-label='Name']::before {
			content: none;
		}
		.cases-table td.cell-actions {
			justify-content: flex-end;
			padding-top: 0.55rem;
		}
		.cases-table td.cell-actions::before {
			content: none;
		}
		.view-link {
			min-width: 44px;
			min-height: 44px;
			display: inline-flex;
			align-items: center;
			justify-content: center;
		}
	}

	.pagination {
		display: flex;
		justify-content: center;
		align-items: center;
		gap: 1.5rem;
		margin-top: 2rem;
	}
	.page-btn {
		padding: 0.55rem 1.1rem;
		border: 1px solid var(--color-primary);
		background: var(--color-bg-white);
		color: var(--color-primary);
		border-radius: var(--radius-input);
		font-weight: 600;
		font-size: 0.85rem;
		cursor: pointer;
		/* Perf: no transition here. The previous `background` /
		   `color` transition was paint-only and added 0.15s of
		   paint work per hover with no perceptible UX benefit
		   over a snap. The mobile trace showed hover state
		   paints contending with card-list paints. */
	}
	.page-btn:hover:not(:disabled) {
		background: var(--color-primary);
		color: var(--color-text-light);
	}
	.page-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
	.page-indicator {
		text-align: center;
	}

	.text-center {
		text-align: center;
	}

	@media (prefers-reduced-motion: reduce) {
		.page-btn {
			transition: none;
		}
	}

	/* === Stale / inactivity quick filter ============================
	   Segmented control rendered just below the FilterToolbar so the
	   user can scan "All / Inactive 30+ d / 90+ d / 180+ d / 1y+"
	   as a single visual row. Keyboard-accessible via tab + space/enter
	   (native <button>); aria-pressed reflects the toggle state.
	   ============================================================ */

	.stale-filter {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex-wrap: wrap;
		padding: 0.5rem 0.85rem;
		background: var(--color-surface);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
	}
	.stale-filter-label {
		font-size: 0.72rem;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		color: var(--color-text-muted);
		font-weight: 700;
	}
	.stale-filter-buttons {
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
	}
	.stale-btn {
		font: inherit;
		font-size: 0.78rem;
		font-weight: 600;
		padding: 0.35rem 0.7rem;
		border-radius: 999px;
		border: 1px solid var(--color-border-light);
		background: var(--color-bg-white);
		color: var(--color-text-muted);
		cursor: pointer;
		transition:
			background var(--transition-card),
			color var(--transition-card),
			border-color var(--transition-card);
	}
	.stale-btn:hover {
		border-color: var(--color-primary-light);
		color: var(--color-text);
	}
	.stale-btn:focus-visible {
		outline: none;
		box-shadow: 0 0 0 3px var(--color-primary-tint);
	}
	.stale-btn.active {
		background: var(--color-primary);
		border-color: var(--color-primary);
		color: var(--color-bg-white);
	}
	.stale-btn.active:hover {
		background: var(--color-primary-light);
		border-color: var(--color-primary-light);
		color: var(--color-bg-white);
	}
	@media (max-width: 600px) {
		.stale-filter {
			flex-direction: column;
			align-items: flex-start;
		}
	}
</style>
