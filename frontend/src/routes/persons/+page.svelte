<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { getPersons, getCountries, getCategories } from '$lib/api';
	import StatusBadge from '$lib/StatusBadge.svelte';

	let persons: any[] = $state([]);
	let countries: any[] = $state([]);
	let categories: any[] = $state([]);
	let loading = $state(true);
	let totalCount = $state(0);
	let nextPage = $state<string | null>(null);
	let prevPage = $state<string | null>(null);

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

	async function loadPersons(params: Record<string, string> = {}) {
		loading = true;
		try {
			const data = await getPersons(params);
			persons = data.results;
			totalCount = data.count;
			nextPage = data.next;
			prevPage = data.previous;
		} catch (e) {
			console.error(e);
		}
		loading = false;
	}

	function applyFilters() {
		const params: Record<string, string> = {};
		if (search) params.search = search;
		if (filterCountry) params.country = filterCountry;
		if (filterStatus) params.current_status = filterStatus;
		if (filterCategory) params.category = filterCategory;
		if (sort) params.ordering = sort;
		loadPersons(params);
	}

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
			<input type="text" class="search" placeholder="Search by name..." bind:value={search} />
		</form>
		<div class="select-submit">
			<select bind:value={filterStatus} onchange={applyFilters}>
				<option value="">All statuses</option>
				{#each statuses as s}
					<option value={s.value}>{s.label}</option>
				{/each}
			</select>
			<select bind:value={filterCountry} onchange={applyFilters}>
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
