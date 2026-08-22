<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { getPersons, getCountries, getCategories } from '$lib/api';
	import StatusBadge from '$lib/StatusBadge.svelte';

	// Debounce helper — calls `fn` only after `delay` ms of silence.
	// Without this, every keystroke in the search box fires a full API
	// round-trip; with it, we wait until the user stops typing.
	const SEARCH_DEBOUNCE_MS = 300;

	function debounce<T extends (...args: any[]) => void>(fn: T, delay: number) {
		let timer: ReturnType<typeof setTimeout> | null = null;
		const wrapped = (...args: Parameters<T>) => {
			if (timer) clearTimeout(timer);
			timer = setTimeout(() => {
				timer = null;
				fn(...args);
			}, delay);
		};
		wrapped.flush = () => {
			if (timer) {
				clearTimeout(timer);
				timer = null;
				fn();
			}
		};
		return wrapped;
	}

	let persons: any[] = $state([]);
	let countries: any[] = $state([]);
	let categories: any[] = $state([]);
	let loading = $state(true);
	let totalCount = $state(0);

	// Pagination — backend returns PAGE_SIZE per page; we track our
	// current page so we can render Prev/Next and a "Page N of M"
	// indicator. Resets to 1 on any filter change.
	const PAGE_SIZE = 10;
	let currentPage = $state(1);
	let totalPages = $derived(Math.max(1, Math.ceil(totalCount / PAGE_SIZE)));
	let pageStart = $derived(((currentPage - 1) * PAGE_SIZE) + 1);
	let pageEnd = $derived(Math.min(currentPage * PAGE_SIZE, totalCount));
	let canPrev = $derived(currentPage > 1);
	let canNext = $derived(currentPage < totalPages);

	// Filters
	let search = $state('');
	let filterCountry = $state('');
	let filterStatus = $state('');
	let filterCategory = $state('');
	let sort = $state('-created_at');

	// View mode: 'cards' or 'list'. Remembered per browser.
	let viewMode = $state<'cards' | 'list'>('cards');

	const sorts = [
		{ value: '-created_at', label: 'Newest submitted' },
		{ value: 'created_at', label: 'Oldest submitted' },
		{ value: '-updated_at', label: 'Recently updated' },
		{ value: 'name', label: 'Name (A–Z)' },
		{ value: 'country', label: 'Country' },
		{ value: 'current_status', label: 'Status' },
	];

	const statuses = [
		{ value: 'detained', label: 'Detained' },
		{ value: 'disappeared', label: 'Disappeared' },
		{ value: 'restricted_movement', label: 'Restricted Movement' },
		{ value: 'released', label: 'Released' },
		{ value: 'deceased', label: 'Deceased' },
		{ value: 'unknown', label: 'Unknown' },
		{ value: 'stateless', label: 'Stateless' },
		{ value: 'rights_restricted', label: 'Rights Restricted' },
	];

	async function loadCountries(countryParams: Record<string, string> = {}) {
		try {
			countries = await getCountries(countryParams);
		} catch (e) {
			console.error(e);
		}
	}

	async function loadPersons(
		params: Record<string, string> = {},
		page: number = currentPage
	) {
		loading = true;
		try {
			const pageParams = { ...params, page: String(page) };
			const data = await getPersons(pageParams);
			persons = data.results;
			totalCount = data.count;
			currentPage = page;
			// Scroll the list back to the top so users don't lose context
			// when paging through results.
			if (typeof window !== 'undefined') window.scrollTo({ top: 0, behavior: 'smooth' });
		} catch (e) {
			console.error(e);
		}
		loading = false;
	}

	function goToPage(page: number) {
		if (page < 1 || page > totalPages || page === currentPage) return;
		loadPersons(currentFilterParams(), page);
	}

	function currentFilterParams(): Record<string, string> {
		const params: Record<string, string> = {};
		if (search) params.search = search;
		if (filterCountry) params.country = filterCountry;
		if (filterStatus) params.current_status = filterStatus;
		if (filterCategory) params.category = filterCategory;
		if (sort) params.ordering = sort;
		return params;
	}

	function currentCountryParams(): Record<string, string> {
		// Build separate params for the countries dropdown so its counts
		// are dynamic: when status/category/search change, the count next
		// to each country updates to reflect the filtered subset.
		// `country` itself is excluded so the dropdown always shows all
		// options regardless of which one is selected.
		const countryParams: Record<string, string> = {};
		if (filterStatus) countryParams.current_status = filterStatus;
		if (filterCategory) countryParams.category = filterCategory;
		if (search) countryParams.search = search;
		return countryParams;
	}

	function applyFilters() {
		// Filters always reset to page 1 so users don't land on an empty
		// or out-of-range page that no longer matches their criteria.
		loadPersons(currentFilterParams(), 1);
		// Countries dropdown doesn't depend on the `country` filter itself,
		// so we don't need to refetch it when only country changes — but
		// we do when status/category/search change because those affect
		// the per-country counts.
		const cp = currentCountryParams();
		const keys = Object.keys(cp).sort().join(',');
		if (keys !== lastCountryParamKey) {
			lastCountryParamKey = keys;
			loadCountries(cp);
		}
	}

	// Tracks the last country-dropdown query signature so we only refetch
	// the dropdown when its inputs actually change.
	let lastCountryParamKey = '';

	// Debounced wrapper around applyFilters for the search input. Without
	// this, every keystroke fires a full API round-trip; with it, we
	// wait until the user pauses for SEARCH_DEBOUNCE_MS before firing.
	const debouncedSearch = debounce(() => applyFilters(), SEARCH_DEBOUNCE_MS);

	function setView(mode: 'cards' | 'list') {
		viewMode = mode;
		try { localStorage.setItem('rtv-cases-view', mode); } catch {}
	}

	function clearFilters() {
		search = '';
		filterCountry = '';
		filterStatus = '';
		filterCategory = '';
		sort = '-created_at';
		applyFilters();
	}

	onMount(async () => {
		try {
			const saved = localStorage.getItem('rtv-cases-view');
			if (saved === 'cards' || saved === 'list') viewMode = saved;
		} catch {}
		const [, countriesData, catsData] = await Promise.all([
			applyFilters(),
			getCountries(),
			getCategories(),
		]);
		countries = countriesData;
		categories = catsData.results || catsData;
	});
</script>

<svelte:head>
	<title>Cases — Testimonies.world</title>
</svelte:head>

<div class="victims">
	<h1>Cases</h1>
	<p class="muted mb-2">{totalCount} case{totalCount !== 1 ? 's' : ''} recorded</p>

	<div class="search-select">
		<form onsubmit={(e) => { e.preventDefault(); applyFilters(); }}>
			<input
				type="text"
				class="search"
				placeholder="Search by name..."
				bind:value={search}
				oninput={debouncedSearch}
			/>
		</form>
		<div class="select-submit">
			<select bind:value={filterStatus} onchange={applyFilters}>
				<option value="">All statuses</option>
				{#each statuses as s}
					<option value={s.value}>{s.label}</option>
				{/each}
			</select>
			<select
				value={filterCountry}
				onchange={(e) => {
					filterCountry = (e.currentTarget as HTMLSelectElement).value;
					applyFilters();
				}}
			>
				<option value="">All countries</option>
				{#each countries as c}
					<option value={c.country}>{c.country} ({c.count})</option>
				{/each}
			</select>
			<select bind:value={filterCategory} onchange={applyFilters}>
				<option value="">All categories</option>
				{#each categories as cat}
					<option value={cat.id}>{cat.name}</option>
				{/each}
			</select>
			<button class="btn" onclick={applyFilters}>Search</button>
		</div>
	</div>

	<div class="toolbar">
		<label class="sort">
			Sort:
			<select bind:value={sort} onchange={applyFilters}>
				{#each sorts as s}
					<option value={s.value}>{s.label}</option>
				{/each}
			</select>
		</label>
		<div class="view-toggle">
			<button class:active={viewMode === 'cards'} onclick={() => setView('cards')}>Cards</button>
			<button class:active={viewMode === 'list'} onclick={() => setView('list')}>List</button>
		</div>
		{#if search || filterCountry || filterStatus || filterCategory}
			<button class="link-btn" onclick={clearFilters}>Clear filters</button>
		{/if}
	</div>

	{#if loading}
		<p class="muted">Loading...</p>
	{:else if persons.length === 0}
		<p class="muted">No cases found matching your criteria.</p>
	{:else if viewMode === 'list'}
		<table class="cases-table">
			<thead>
				<tr>
					<th>Name</th>
					<th>Country</th>
					<th>Location</th>
					<th>Status</th>
					<th>Last known</th>
					<th class="num">Reports</th>
					<th></th>
				</tr>
			</thead>
			<tbody>
				{#each persons as person}
					<tr>
						<td><a href="{base}/persons/{person.id}">{person.name}</a></td>
						<td>{person.country || '—'}</td>
						<td class="muted">{person.rough_location || '—'}</td>
						<td><StatusBadge status={person.current_status} /></td>
						<td class="muted">{person.last_known_date || '—'}</td>
						<td class="num">{person.report_count || 0}</td>
						<td><a href="{base}/persons/{person.id}">View &raquo;</a></td>
					</tr>
				{/each}
			</tbody>
		</table>
	{:else}
		<ul class="list">
			{#each persons as person}
				<li>
					<div class="col">
						{#if person.profile_image_url}
							<img src={person.profile_image_url} alt={person.name} class="photo" />
						{:else}
							<div class="photo-placeholder"></div>
						{/if}
					</div>
					<div class="col">
						<span>{person.name}</span>
						<p class="small muted">{person.country}</p>
						{#if person.rough_location}
							<p class="small muted">{person.rough_location}</p>
						{/if}
						<div class="mt-1">
							<StatusBadge status={person.current_status} />
						</div>
						{#if person.last_known_date}
							<p class="small muted mt-1">Last known: {person.last_known_date}</p>
						{/if}
						{#if person.report_count > 0}
							<p class="small muted">{person.report_count} report{person.report_count !== 1 ? 's' : ''}</p>
						{/if}
						<div class="more-btn">
							<a href="{base}/persons/{person.id}">View details &raquo;</a>
						</div>
					</div>
				</li>
			{/each}
		</ul>
	{/if}

	{#if totalCount > 0 && totalPages > 1}
		<nav class="pagination" aria-label="Pagination">
			<button
				class="page-btn"
				disabled={!canPrev || loading}
				onclick={() => goToPage(currentPage - 1)}
				aria-label="Previous page"
			>
				‹ Prev
			</button>
			<span class="page-indicator">
				Page <strong>{currentPage}</strong> of {totalPages}
				<span class="muted">— showing {pageStart}–{pageEnd} of {totalCount}</span>
			</span>
			<button
				class="page-btn"
				disabled={!canNext || loading}
				onclick={() => goToPage(currentPage + 1)}
				aria-label="Next page"
			>
				Next ›
			</button>
		</nav>
	{/if}
</div>

<style>
	.victims {
		width: 90%;
		margin: 0 auto;
	}
	.search-select {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: center;
		margin: 0 0 10px;
	}
	.search-select form {
		width: 24%;
		margin: 0 2px;
	}
	.search-select .search {
		border: 1px solid darkgray;
		width: 100%;
	}
	.select-submit {
		display: flex;
		align-items: center;
		gap: 4px;
	}
	.select-submit select {
		padding: 8px 15px;
		width: auto;
	}
	.toolbar {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 12px;
		margin: 4px 0 8px;
	}
	.toolbar .sort {
		font-size: 0.9rem;
		color: #444;
	}
	.toolbar .sort select {
		padding: 6px 10px;
		margin-left: 4px;
	}
	.view-toggle {
		display: inline-flex;
		border: 1px solid darkgray;
		border-radius: 4px;
		overflow: hidden;
	}
	.view-toggle button {
		border: none;
		background: white;
		padding: 6px 14px;
		cursor: pointer;
		font-size: 0.9rem;
	}
	.view-toggle button.active {
		background: #2b3a55;
		color: white;
	}
	.link-btn {
		border: none;
		background: none;
		color: #2b3a55;
		text-decoration: underline;
		cursor: pointer;
		font-size: 0.9rem;
		padding: 0;
	}
	.pagination {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		margin-top: 1.5rem;
		padding: 1rem 0;
	}
	.page-btn {
		border: 1px solid #2b3a55;
		background: white;
		color: #2b3a55;
		padding: 6px 14px;
		border-radius: 4px;
		cursor: pointer;
		font-size: 0.9rem;
	}
	.page-btn:hover:not(:disabled) {
		background: #2b3a55;
		color: white;
	}
	.page-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
	.page-indicator {
		font-size: 0.9rem;
		color: #2b3a55;
	}
	.page-indicator .muted {
		color: #666;
		font-size: 0.85rem;
		margin-left: 4px;
	}
	.cases-table {
		width: 100%;
		border-collapse: collapse;
		background: white;
		margin-top: 12px;
		font-size: 0.92rem;
	}
	.cases-table th,
	.cases-table td {
		text-align: left;
		padding: 8px 10px;
		border-bottom: 1px solid #e0e0e0;
		vertical-align: middle;
	}
	.cases-table thead th {
		border-bottom: 2px solid #ccc;
		font-weight: 600;
		white-space: nowrap;
	}
	.cases-table tbody tr:hover {
		background: #f6f8fb;
	}
	.cases-table .num {
		text-align: right;
	}
	.list {
		display: flex;
		flex-wrap: wrap;
		align-items: stretch;
		justify-content: space-between;
		margin-top: 20px;
	}
	.list li {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: flex-start;
		overflow-wrap: break-word;
		word-break: break-all;
		width: 48%;
		background: white;
		border-radius: 4px;
		border: 1px solid darkgray;
		box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.2);
		margin-bottom: 20px;
		padding: 10px;
	}
	.col:first-child {
		margin-right: 20px;
		width: 130px;
		height: 160px;
		overflow: hidden;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}
	.col:nth-child(2) {
		flex: 1;
	}
	.photo {
		height: 100%;
		width: 100%;
		object-fit: contain;
	}
	.photo-placeholder {
		width: 100%;
		height: 100%;
		background: var(--color-bg);
		border-radius: 4px;
	}
	.list span {
		font-weight: bold;
	}
	.more-btn {
		margin-top: 10px;
	}
	.more-btn a {
		color: #25646a;
		text-transform: uppercase;
	}
	.more-btn a:visited {
		color: #25646a;
	}
	.more-btn a:hover, .more-btn a:focus, .more-btn a:active {
		color: black;
	}

	@media (max-width: 800px) {
		.victims {
			width: 100%;
		}
		.search-select {
			flex-direction: column;
		}
		.search-select form {
			width: 100%;
			margin: 0 0 10px;
		}
		.select-submit {
			flex-direction: row;
			flex-wrap: wrap;
			width: 100%;
		}
		.select-submit select {
			width: 100%;
		}
		.list li {
			width: 100%;
		}
	}
	@media (max-width: 480px) {
		.list li {
			flex-direction: column;
		}
		.col:first-child {
			margin-right: 0;
			margin-bottom: 10px;
		}
		.more-btn {
			text-align: right;
		}
	}
</style>
