<script lang="ts">
	/**
	 * FilterSelect — custom-chevron select matching the SearchInput
	 * height. Used in the floating toolbar for status / country / category
	 * / sort filters.
	 *
	 * Usage:
	 *   <FilterSelect
	 *     bind:value={filterStatus}
	 *     options={STATUS_VALUES.map(v => ({ value: v, label: statusLabels[v] }))}
	 *     placeholder="All statuses"
	 *     ariaLabel="Filter by status"
	 *   />
	 */
	import Icon from './Icon.svelte';

	type Option = { value: string; label: string };

	let {
		value = $bindable(''),
		options,
		placeholder,
		ariaLabel,
		onchange,
	}: {
		value?: string;
		options: Option[];
		placeholder?: string;
		ariaLabel: string;
		onchange?: (e: Event) => void;
	} = $props();
</script>

<label class="filter-select">
	<select
		class="select--filter"
		bind:value
		{onchange}
		aria-label={ariaLabel}
	>
		{#if placeholder}
			<option value="">{placeholder}</option>
		{/if}
		{#each options as opt (opt.value)}
			<option value={opt.value}>{opt.label}</option>
		{/each}
	</select>
	<span class="filter-select-chevron" aria-hidden="true">
		<Icon name="chevron-down" size={16} />
	</span>
</label>

<style>
	.filter-select {
		display: inline-flex;
		align-items: center;
		position: relative;
		min-width: 160px;
		flex: 0 1 220px;
	}
	.filter-select :global(.select--filter) {
		width: 100%;
		appearance: none;
		-webkit-appearance: none;
		padding-right: 2.25rem;
		cursor: pointer;
	}
	.filter-select-chevron {
		position: absolute;
		right: 0.75rem;
		top: 50%;
		transform: translateY(-50%);
		color: var(--color-text-muted);
		pointer-events: none;
		display: inline-flex;
	}
</style>
