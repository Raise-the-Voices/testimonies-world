<script lang="ts">
	/**
	 * SearchInput — search box with a leading icon and a token-driven
	 * focus ring. Pairs visually with FilterSelect so the floating
	 * toolbar reads as one row.
	 *
	 * Usage:
	 *   <SearchInput bind:value={search} placeholder="Search by name…" />
	 *   <SearchInput value={search} oninput={onSearchChange} />
	 */
	import Icon from './Icon.svelte';

	let {
		value = $bindable(''),
		placeholder = 'Search…',
		ariaLabel = 'Search',
		oninput,
		name,
	}: {
		value?: string;
		placeholder?: string;
		ariaLabel?: string;
		oninput?: (e: Event) => void;
		name?: string;
	} = $props();
</script>

<label class="search-input">
	<span class="search-input-icon" aria-hidden="true">
		<Icon name="search" size={18} />
	</span>
	<input
		class="input--search"
		type="search"
		{name}
		{placeholder}
		aria-label={ariaLabel}
		bind:value
		{oninput}
	/>
</label>

<style>
	.search-input {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		position: relative;
		flex: 1 1 280px;
		min-width: 220px;
	}
	.search-input-icon {
		position: absolute;
		left: 0.85rem;
		top: 50%;
		transform: translateY(-50%);
		color: var(--color-text-muted);
		pointer-events: none;
		display: inline-flex;
	}
	.search-input :global(.input--search) {
		padding-left: 2.5rem;
		width: 100%;
	}
	/* Hide the native ✕ clear button on type=search — we don't use it,
	   and it makes the input look misaligned against FilterSelect. */
	.search-input :global(input[type='search']::-webkit-search-cancel-button) {
		appearance: none;
	}
</style>
