<script lang="ts">
	/**
	 * StatRow — a single labelled metric row inside a <StatCard>.
	 *
	 *   ┌──────────────────────────────────────────────────┐
	 *   │  Label                       (60)  ← count pill  │
	 *   │  ▰▰▰▰▰▰▰▱▱▱▱▱▱▱▱  ← progress bar                │
	 *   └──────────────────────────────────────────────────┘
	 *
	 * The bar fill is `count / total * 100%` rounded, with a horizontal
	 * gradient. Pass `total={0}` to suppress the bar.
	 */
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
	<span class="stat-row-count" aria-label="{count} cases">{count}</span>
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
	.stat-row-bar {
		grid-column: 1 / -1;
		grid-row: 2;
		display: block;
		height: 3px;
		border-radius: 999px;
		background: var(--color-bg);
		overflow: hidden;
	}
	.stat-row-bar-fill {
		display: block;
		height: 100%;
		background: var(--color-primary);
		border-radius: 999px;
	}

	@media (prefers-reduced-motion: reduce) {
		.stat-row-bar-fill {
			transition: none;
		}
	}
</style>