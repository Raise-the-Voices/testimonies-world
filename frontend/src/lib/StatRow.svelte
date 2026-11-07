<script lang="ts">
	/**
	 * StatRow — a single labelled metric row inside a <StatisticsCard variant="section">.
	 *
	 *   ┌──────────────────────────────────────────────────┐
	 *   │  Label                       (60)  ← count pill  │
	 *   │  ▰▰▰▰▰▰▰▱▱▱▱▱▱▱▱  ← progress bar                │
	 *   └──────────────────────────────────────────────────┘
	 *
	 * The bar fill is `count / total * 100%` rounded, with a horizontal
	 * gradient. Pass `total={0}` to suppress the bar.
	 *
	 * Motion: the count rises into place and the bar grows from the
	 * left as the card reveals. Both are driven by the card's
	 * `data-reveal` state, so a card that opts out of the reveal
	 * (the dashboard) shows the final values immediately.
	 */
	import { countUp } from './motion';

	let {
		label,
		count,
		total = 0,
	}: {
		label: string;
		count: number;
		total?: number;
	} = $props();

	const pct = $derived(
		total <= 0 ? 0 : Math.min(100, Math.round((count / total) * 100))
	);
</script>

<li class="stat-row">
	<span class="stat-row-label" title={label}>{label}</span>
	<span class="stat-row-count" aria-label="{count} cases">
		<!-- The count-up writes into .stat-row-count-digits. The static
		     fallback carries the number for readers without scripting;
		     .sr-only carries it for screen readers, so the value is
		     announced once either way. -->
		<span
			class="stat-row-count-digits"
			aria-hidden="true"
			style="min-width: {String(count).length}ch"
			use:countUp={{ value: count, when: 'visible' }}
		></span>
		<span class="stat-row-count-fallback" aria-hidden="true">{count}</span>
		<span class="sr-only">{count} cases</span>
	</span>
	<span class="stat-row-bar" aria-hidden="true">
		<span class="stat-row-bar-fill" style="width: {pct}%"></span>
	</span>
</li>

<style>
	.stat-row {
		display: grid;
		grid-template-columns: 1fr auto;
		grid-template-rows: auto auto;
		column-gap: 0.85rem;
		row-gap: 0.3rem;
		align-items: baseline;
		padding: 0.6rem 1rem;
		border-bottom: 1px solid var(--color-border-light);
	}
	.stat-row:last-child {
		border-bottom: none;
	}

	.stat-row-label {
		grid-column: 1;
		grid-row: 1;
		font-size: 0.92rem;
		color: var(--color-text);
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.stat-row-count {
		grid-column: 2;
		grid-row: 1;
		font-size: 0.92rem;
		font-weight: 700;
		color: var(--color-primary);
		font-variant-numeric: tabular-nums;
		line-height: 1;
		flex: 0 0 auto;
	}
	/* The count-up writes into .stat-row-count-digits. Until scripting
	   runs, the static fallback shows the number; with scripting the
	   fallback is hidden and the animated slot takes over. The slot
	   reserves the final width (min-width, set inline from the value) so
	   the count causes no layout shift. */
	.stat-row-count-fallback {
		display: inline;
	}
	.stat-row-count-digits {
		display: none;
	}
	@media (scripting: enabled) {
		.stat-row-count-fallback {
			display: none;
		}
		.stat-row-count-digits {
			display: inline-block;
		}
	}
	.stat-row-bar {
		grid-column: 1 / -1;
		grid-row: 2;
		display: block;
		height: 3px;
		border-radius: 999px;
		background: var(--color-bg);
		overflow: hidden;
	}
	/* The bar grows from the left as its card reveals. The fill keeps its
	   final width throughout — only the paint scales — so nothing reflows.
	   A card with no `data-reveal` attribute (the dashboard) has no
	   pending state and the bar simply sits at full width. */
	.stat-row-bar-fill {
		display: block;
		height: 100%;
		background: var(--color-primary);
		border-radius: 999px;
		transform-origin: left center;
		transform: scaleX(1);
		transition: transform var(--motion-duration-grow) var(--motion-ease-editorial);
	}
	:global([data-reveal='pending']) .stat-row-bar-fill {
		transform: scaleX(0);
		transition: none;
	}
	:global([data-reveal='in']) .stat-row-bar-fill {
		transform: scaleX(1);
	}

	@media (prefers-reduced-motion: reduce) {
		.stat-row-bar-fill {
			transition: none;
			transform: scaleX(1);
		}
		:global([data-reveal='pending']) .stat-row-bar-fill {
			transform: scaleX(1);
		}
	}
</style>
