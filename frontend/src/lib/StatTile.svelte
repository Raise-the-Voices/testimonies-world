<!--
  StatTile - one number + label tile for the dashboard summary row.

  Optional `href` makes the whole tile a link. If `href` is set, the
  tile is keyboard-focusable as a single unit; if not, the tile renders
  as a static block (e.g., for tiles that aren't actionable yet).
-->
<script lang="ts">
	interface Props {
		label: string;
		value: number | null;
		href?: string;
		/** Optional muted sub-label rendered below the number. */
		hint?: string;
		/** When true, renders a small SkeletonStatItem placeholder
		 *  instead of the number - used during initial paint. */
		loading?: boolean;
	}

	let { label, value, href, hint, loading = false }: Props = $props();

	const displayValue = $derived(
		value === null || value === undefined ? '-' : value.toLocaleString('en-US'),
	);
</script>

{#if href}
	<a class="stat-tile stat-tile-link" {href} aria-label="{label}: {displayValue}">
		<span class="stat-tile-value">{displayValue}</span>
		<span class="stat-tile-label">{label}</span>
		{#if hint}
			<span class="stat-tile-hint">{hint}</span>
		{/if}
	</a>
{:else}
	<div class="stat-tile" aria-label="{label}: {displayValue}">
		{#if loading}
			<span class="stat-tile-skeleton" aria-hidden="true"></span>
		{:else}
			<span class="stat-tile-value">{displayValue}</span>
		{/if}
		<span class="stat-tile-label">{label}</span>
		{#if hint}
			<span class="stat-tile-hint">{hint}</span>
		{/if}
	</div>
{/if}

<style>
	.stat-tile {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		box-shadow: var(--shadow-card);
		padding: 1.1rem 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		min-width: 0;
		transition: box-shadow var(--transition-card), border-color var(--transition-card);
	}
	.stat-tile-link {
		text-decoration: none;
		color: inherit;
	}
	.stat-tile-link:hover {
		box-shadow: var(--shadow-card-hover);
		border-color: var(--color-primary-light);
	}
	.stat-tile-link:focus-visible {
		outline: none;
		box-shadow: 0 0 0 3px var(--color-primary-tint);
	}
	.stat-tile-value {
		font-size: 1.75rem;
		font-weight: 700;
		color: var(--color-primary);
		line-height: 1.1;
		font-variant-numeric: tabular-nums;
	}
	.stat-tile-label {
		font-size: 0.78rem;
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.06rem;
	}
	.stat-tile-hint {
		font-size: 0.78rem;
		color: var(--color-text-muted);
		line-height: 1.3;
		margin-top: 0.15rem;
	}
	.stat-tile-skeleton {
		display: block;
		width: 60%;
		height: 1.75rem;
		background: var(--skeleton-bg);
		border-radius: 4px;
		animation: skeleton-shimmer 1.4s ease-in-out infinite;
	}
	@media (prefers-reduced-motion: reduce) {
		.stat-tile,
		.stat-tile-link:hover {
			transition: none;
		}
		.stat-tile-skeleton {
			animation: none;
			background: var(--skeleton-bg-static);
		}
	}
</style>
