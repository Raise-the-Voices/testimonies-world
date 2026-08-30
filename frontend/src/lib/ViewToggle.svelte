<script lang="ts">
	/**
	 * ViewToggle — segmented pill control for switching between cards
	 * and list views. Persists the choice to localStorage so the user's
	 * preference survives a reload.
	 *
	 * Usage:
	 *   <ViewToggle bind:value={viewMode} />
	 *
	 * The component owns the localStorage key ('rtv-cases-view') so the
	 * /persons page doesn't have to think about it.
	 */
	const STORAGE_KEY = 'rtv-cases-view';

	type Mode = 'cards' | 'list';

	let {
		value = $bindable<Mode>('cards'),
		onchange,
	}: {
		value?: Mode;
		onchange?: (mode: Mode) => void;
	} = $props();

	// Read persisted preference once on mount — guarded so SSR + private-
	// mode browsers don't blow up. Invalid stored values fall back to
	// 'cards'.
	import { onMount } from 'svelte';
	onMount(() => {
		try {
			const stored = localStorage.getItem(STORAGE_KEY);
			if (stored === 'cards' || stored === 'list') value = stored;
		} catch {
			/* ignore — private mode / SSR */
		}
	});

	function set(mode: Mode) {
		if (mode === value) return;
		value = mode;
		try {
			localStorage.setItem(STORAGE_KEY, mode);
		} catch {
			/* ignore */
		}
		onchange?.(mode);
	}
</script>

<div class="view-toggle" role="tablist" aria-label="View mode">
	<button
		type="button"
		role="tab"
		aria-selected={value === 'cards'}
		class="view-toggle-btn"
		class:active={value === 'cards'}
		onclick={() => set('cards')}
	>
		<span>Cards</span>
	</button>
	<button
		type="button"
		role="tab"
		aria-selected={value === 'list'}
		class="view-toggle-btn"
		class:active={value === 'list'}
		onclick={() => set('list')}
	>
		<span>List</span>
	</button>
</div>

<style>
	.view-toggle {
		display: inline-flex;
		padding: 0.25rem;
		background: var(--color-section-bg);
		border-radius: 999px;
		gap: 0.25rem;
	}
	.view-toggle-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.45rem 0.9rem;
		border: none;
		background: transparent;
		color: var(--color-text-muted);
		font-size: 0.85rem;
		font-weight: 600;
		border-radius: 999px;
		cursor: pointer;
		transition: background 0.18s ease, color 0.18s ease, box-shadow 0.18s ease;
	}
	.view-toggle-btn:hover:not(.active) {
		color: var(--color-text);
	}
	.view-toggle-btn.active {
		background: var(--color-primary);
		color: var(--color-text-light);
		box-shadow: var(--shadow-card);
	}
	.view-toggle-btn:focus-visible {
		outline: 2px solid var(--color-primary);
		outline-offset: 2px;
	}
	@media (prefers-reduced-motion: reduce) {
		.view-toggle-btn { transition: none; }
	}
</style>
