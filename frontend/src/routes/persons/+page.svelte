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
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import { afterNavigate, goto, replaceState } from '$app/navigation';
	import { getPersons, getCountries, getCategories } from '$lib/api';
	import { statusLabels } from '$lib/StatusBadge.svelte';
	import { debounce } from '$lib/debounce';
	import Banner from '$lib/Banner.svelte';
	import FilterToolbar from '$lib/FilterToolbar.svelte';
	import PersonCard from '$lib/PersonCard.svelte';
	import Icon from '$lib/Icon.svelte';
	import Skeleton from '$lib/Skeleton.svelte';
	import type { PageData } from './$types';
	import type { Paginated, Person, PersonCategory } from '$lib/types';

	let { data }: { data: PageData } = $props();

	const SEARCH_DEBOUNCE_MS = 300;
	const PAGE_SIZE = 12;
	const SKELETON_CARD_COUNT = 12;

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
	let persons: Person[] = $state(data.persons ?? []);
	let countries: { country: string; count: number }[] = $state(data.countries ?? []);
	let categories: PersonCategory[] = $state(data.categories ?? []);
	let loading = $state(false);
	let error: string | null = $state(data.error);
	let totalCount = $state(data.personsCount ?? 0);
	let currentPage = $state(1);

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
		sort = sp.get('ordering') ?? '-created_at';
		stale = sp.get('stale') ?? '';
	}

	// Filters
	let search = $state('');
	let filterCountry = $state('');
	let filterStatus = $state('');
	let filterCategory = $state('');
	let sort = $state('-created_at');
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

	// Sync the URL to the current filter state. replaceState keeps
	// Back/Forward history clean (each filter change doesn't add a
	// new entry); noScroll + keepFocus preserve scroll position and
	// which control the user was interacting with. Called by every
	// state change that affects applyFilters.
	async function syncUrl() {
		const sp = new URLSearchParams();
		if (search) sp.set('search', search);
		if (filterCountry) sp.set('country', filterCountry);
		if (filterStatus) sp.set('current_status', filterStatus);
		if (filterCategory) sp.set('category', filterCategory);
		if (stale) sp.set('stale', stale);
		if (sort && sort !== '-created_at') sp.set('ordering', sort);
		const qs = sp.toString();
		const target = qs ? `?${qs}` : page.url.pathname;
		// Only navigate if the URL would actually change — avoids
		// unnecessary history churn when re-renders fire.
		if (target !== page.url.pathname + page.url.search) {
			await goto(target, { replaceState: true, noScroll: true, keepFocus: true });
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
		Boolean(search || filterCountry || filterStatus || filterCategory || stale || sort !== '-created_at'),
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
		loading = true;
		error = null;
		try {
			const pageParams = { ...params, page: String(page) };
			const data: Paginated<Person> = await getPersons(pageParams);
			persons = data.results;
			totalCount = data.count;
			currentPage = page;
			if (typeof window !== 'undefined') window.scrollTo({ top: 0, behavior: 'smooth' });
		} catch (e: unknown) {
			console.error(e);
			error =
				e instanceof Error
					? `Could not load cases: ${e.message}`
					: 'Could not load cases. Please try again.';
		} finally {
			loading = false;
		}
	}

	function currentFilterParams(): Record<string, string> {
		const params: Record<string, string> = {};
		if (search) params.search = search;
		if (filterCountry) params.country = filterCountry;
		if (filterStatus) params.current_status = filterStatus;
		if (filterCategory) params.category = filterCategory;
		if (stale) params.stale = stale;
		if (sort) params.ordering = sort;
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
		await loadPersons(currentFilterParams(), 1);
		const newKey = JSON.stringify(
			Object.entries(currentCountryParams()).sort(([a], [b]) => a.localeCompare(b)),
		);
		if (newKey !== lastCountryParamKey) {
			lastCountryParamKey = newKey;
			loadCountries(currentCountryParams());
		}
		// Mirror filter state → URL so users can share/bookmark.
		// replaceState + noScroll + keepFocus avoids scroll jumps
		// and keeps focus on the control the user just clicked.
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
		sort = '-created_at';
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
</svelte:head>

<div class="page-surface">
	<header class="catalog-header">
		<h1>Cases</h1>
		<p class="muted">
			{#if loading && persons.length === 0}
				<Skeleton variant="text" width="8rem" />
			{:else}
				{totalCount} case{totalCount !== 1 ? 's' : ''} recorded
			{/if}
		</p>
	</header>

	{#if bannerMsg}
		<Banner
			kind={bannerKind}
			message={bannerMsg}
			onDismiss={() => (bannerMsg = '')}
		/>
	{/if}

	{#if error}
		<div class="error-banner-inline" role="alert">
			<Icon name="help" size={18} />
			<span>{error}</span>
			<button type="button" class="toolbar-clear" onclick={applyFilters}>Retry</button>
		</div>
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

	{#if loading && persons.length === 0}
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
		<div class="empty-state">
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
							<td><strong><a href="{base}/persons/{person.id}">{person.name}</a></strong></td>
							<td>{person.country || '—'}</td>
							<td>{person.rough_location || '—'}</td>
							<td>
								{#if person.current_status}
									<span class="badge badge-{person.current_status}">
										{statusLabels[person.current_status] ?? person.current_status}
									</span>
								{/if}
							</td>
							<td>{person.last_known_date || '—'}</td>
							<td>{person.report_count ?? 0}</td>
							<td><a href="{base}/persons/{person.id}">View »</a></td>
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
		margin-bottom: 1.5rem;
		border-bottom: 1px solid var(--color-border-light);
	}
	.catalog-header h1 {
		margin: 0;
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
		transition: background 0.15s ease, color 0.15s ease;
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
