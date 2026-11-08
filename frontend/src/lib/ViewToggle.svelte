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

<div class="view-toggle" role="tablist" aria-label="View mode" data-mode={value}>
	<!-- The pill: one segment's worth of background, slid to the
	     selected segment. Decorative — the buttons carry the state. -->
	<span class="view-toggle-pill" aria-hidden="true"></span>
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
		position: relative;
		display: inline-flex;
		padding: 0.25rem;
		background: var(--color-section-bg);
		border-radius: 999px;
	}
	/* The pill slides; it never changes size. The two segments are the
	   same width, so the pill is exactly one of them and a transform
	   moves it from one to the other — no measurement, no re-layout,
	   and it is in place from the first paint. */
	.view-toggle-pill {
		position: absolute;
		top: 0.25rem;
		bottom: 0.25rem;
		left: 0.25rem;
		width: calc(50% - 0.25rem);
		background: var(--color-primary);
		border-radius: 999px;
		box-shadow: var(--shadow-card);
		pointer-events: none;
		transition: transform var(--motion-duration-overlay) var(--motion-ease-overlay);
	}
	.view-toggle[data-mode='list'] .view-toggle-pill {
		transform: translateX(100%);
	}
	.view-toggle-btn {
		/* Positioned so the pill — which comes first in the DOM —
		   paints underneath the labels. */
		position: relative;
		flex: 1 1 0;
		min-width: 92px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.4rem;
		padding: 0.45rem 0.9rem;
		border: none;
		background: transparent;
		color: var(--color-text-muted);
		font-size: 0.85rem;
		font-weight: 600;
		border-radius: 999px;
		cursor: pointer;
		transition: color var(--motion-duration-fast) var(--motion-ease-overlay);
	}
	.view-toggle-btn:hover:not(.active) {
		color: var(--color-text);
	}
	.view-toggle-btn.active {
		color: var(--color-text-light);
	}
	.view-toggle-btn:focus-visible {
		outline: 2px solid var(--color-primary);
		outline-offset: 2px;
	}
	@media (prefers-reduced-motion: reduce) {
		.view-toggle-pill,
		.view-toggle-btn { transition: none; }
	}
</style>
