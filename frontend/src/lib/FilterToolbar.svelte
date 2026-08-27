<script lang="ts">
	/**
	 * FilterToolbar — the floating elevated card on /persons holding the
	 * search box, three filter selects, the sort select, the view toggle,
	 * and a Clear-filters button. Hosts no state of its own — every prop
	 * is bindable so the parent page can keep its existing reactive
	 * filter logic intact.
	 *
	 * Usage:
	 *   <FilterToolbar
	 *     bind:search bind:filterCountry bind:filterStatus bind:filterCategory
	 *     bind:sort bind:viewMode
	 *     {countries} {categories} {hasActiveFilters}
	 *     onApply={applyFilters} onClear={clearFilters}
	 *     onSearchInput={debouncedSearch}
	 *   />
	 */
	import { STATUS_VALUES, statusLabels } from './StatusBadge.svelte';
	import SearchInput from './SearchInput.svelte';
	import FilterSelect from './FilterSelect.svelte';
	import ViewToggle from './ViewToggle.svelte';

	type Mode = 'cards' | 'list';

	let {
		search = $bindable(''),
		filterCountry = $bindable(''),
		filterStatus = $bindable(''),
		filterCategory = $bindable(''),
		sort = $bindable('-created_at'),
		viewMode = $bindable<Mode>('cards'),
		countries,
		categories,
		sorts,
		hasActiveFilters,
		onApply,
		onClear,
		onSearchInput,
	}: {
		search?: string;
		filterCountry?: string;
		filterStatus?: string;
		filterCategory?: string;
		sort?: string;
		viewMode?: Mode;
		countries: { country: string; count: number }[];
		categories: { id: number; name: string }[];
		sorts: { value: string; label: string }[];
		hasActiveFilters: boolean;
		onApply: () => void;
		onClear: () => void;
		onSearchInput?: (e: Event) => void;
	} = $props();

	// Build option lists — countries dropdown shows "{country} ({count})"
	// so users see how many matches each filter would produce.
	let statusOptions = $derived(
		STATUS_VALUES.map((v) => ({ value: v, label: statusLabels[v] ?? v }))
	);
	let countryOptions = $derived(
		countries.map((c) => ({ value: c.country, label: `${c.country} (${c.count})` }))
	);
	let categoryOptions = $derived(categories.map((c) => ({ value: String(c.id), label: c.name })));
</script>

<section class="toolbar-card" aria-label="Filter and search cases">
	<form
		class="toolbar-row toolbar-row-primary"
		onsubmit={(e) => {
			e.preventDefault();
			onApply();
		}}
	>
		<SearchInput
			bind:value={search}
			oninput={onSearchInput}
			placeholder="Search by name…"
			ariaLabel="Search cases by name"
		/>
		<FilterSelect
			bind:value={filterStatus}
			options={statusOptions}
			placeholder="All statuses"
			ariaLabel="Filter by status"
			onchange={onApply}
		/>
		<FilterSelect
			bind:value={filterCountry}
			options={countryOptions}
			placeholder="All countries"
			ariaLabel="Filter by country"
			onchange={onApply}
		/>
		<FilterSelect
			bind:value={filterCategory}
			options={categoryOptions}
			placeholder="All categories"
			ariaLabel="Filter by category"
			onchange={onApply}
		/>
		<button class="toolbar-submit" type="submit">Search</button>
	</form>

	<div class="toolbar-row toolbar-row-secondary">
		<div class="toolbar-row-secondary-left">
			<label class="toolbar-sort">
				<span class="toolbar-sort-label">Sort by</span>
				<FilterSelect
					bind:value={sort}
					options={sorts}
					ariaLabel="Sort cases"
					onchange={onApply}
				/>
			</label>
			{#if hasActiveFilters}
				<button type="button" class="toolbar-clear" onclick={onClear}>
					Clear filters
				</button>
			{/if}
		</div>
		<ViewToggle bind:value={viewMode} />
	</div>
</section>

<style>
	.toolbar-card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-toolbar);
		padding: 1.25rem 1.5rem;
		margin-bottom: 2rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
		animation: fadeSlideUp 0.4s ease both;
	}
	.toolbar-row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.75rem;
	}
	.toolbar-row-primary {
		align-items: stretch;
	}
	.toolbar-row-secondary {
		justify-content: space-between;
		gap: 1rem;
	}
	.toolbar-row-secondary-left {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex-wrap: wrap;
	}
	.toolbar-sort {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
	}
	.toolbar-sort-label {
		font-size: 0.78rem;
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		font-weight: 600;
	}
	.toolbar-submit {
		padding: 0.65rem 1.1rem;
		border: none;
		background: var(--color-primary);
		color: var(--color-text-light);
		border-radius: var(--radius-input);
		font-weight: 700;
		font-size: 0.85rem;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		cursor: pointer;
		transition: background 0.15s ease, box-shadow 0.15s ease;
	}
	.toolbar-submit:hover {
		background: var(--color-primary-light);
		box-shadow: var(--shadow-card);
	}
	.toolbar-submit:focus-visible {
		outline: 2px solid var(--color-primary);
		outline-offset: 2px;
	}
	.toolbar-clear {
		padding: 0.5rem 0.9rem;
		border: 1px solid var(--color-border-light);
		background: transparent;
		color: var(--color-primary);
		border-radius: var(--radius-input);
		font-weight: 600;
		font-size: 0.8rem;
		cursor: pointer;
		transition: background 0.15s ease, border-color 0.15s ease;
	}
	.toolbar-clear:hover {
		background: var(--color-primary-tint);
		border-color: var(--color-primary);
	}
	.toolbar-clear:focus-visible {
		outline: 2px solid var(--color-primary);
		outline-offset: 2px;
	}

	/* Tablet — wrap toolbar rows onto two visual lines. */
	@media (max-width: 900px) {
		.toolbar-row-primary :global(.search-input) {
			flex: 1 1 100%;
		}
	}

	/* Phone — stack everything full-width. */
	@media (max-width: 600px) {
		.toolbar-row-secondary {
			flex-direction: column;
			align-items: stretch;
		}
		.toolbar-row-secondary-left {
			flex-direction: column;
			align-items: stretch;
		}
		.toolbar-sort {
			flex-direction: column;
			align-items: stretch;
			gap: 0.25rem;
		}
		:global(.toolbar-card .view-toggle) {
			align-self: stretch;
			justify-content: center;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.toolbar-card { animation: none; }
		.toolbar-submit,
		.toolbar-clear { transition: none; }
	}
</style>
