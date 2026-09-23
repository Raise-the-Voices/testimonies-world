<!--
  StatsBar — inline platform-statistics row on the home page.

  Replaces the previous three-state block (loading / error / success)
  + ~70 lines of CSS that lived inline on +page.svelte. Owns the
  1.5rem/0.78rem stat-number/label geometry, the divider rules, the
  error state's danger left-border, the mobile breakpoint, and the
  reduced-motion fallback.

  Visual constraints (preserve byte-for-byte against the pre-refactor
  home page):
    - stat-number: 1.5rem (NOT StatisticsCard's 1.75rem kpi size)
    - stat-label: 0.78rem uppercase + 0.06rem letter-spacing
    - values render raw via item.value(); no toLocaleString
    - skeleton geometry matches StatisticsCard variant="skeleton"
      exactly, so the loading/success swap is invisible.
-->
<script lang="ts">
	import Icon from './Icon.svelte';
	import StatisticsCard from './StatisticsCard.svelte';

	export type StatItem = {
		label: string;
		value: () => number;
	};

	let {
		items,
		loading,
		error,
		onRetry,
	}: {
		items: StatItem[];
		loading: boolean;
		error: string | null;
		onRetry: () => void;
	} = $props();
</script>

{#if loading}
	<section class="stats-bar" aria-busy="true" aria-label="Loading platform statistics">
		{#each items as it (it.label)}
			<StatisticsCard variant="skeleton" />
		{/each}
	</section>
{:else if error}
	<section class="stats-bar stats-bar-error" role="alert" aria-label="Statistics unavailable">
		<div class="stats-error-content">
			<Icon name="help" size={18} />
			<span
				>Could not load platform statistics.
				<button type="button" class="stats-retry" onclick={onRetry}>Retry</button></span
			>
		</div>
	</section>
{:else}
	<section class="stats-bar" aria-label="Platform statistics">
		{#each items as it, i (it.label)}
			{#if i > 0}<span class="stat-divider" aria-hidden="true"></span>{/if}
			<div class="stat-item">
				<span class="stat-number">{it.value()}</span>
				<span class="stat-label">{it.label}</span>
			</div>
		{/each}
	</section>
{/if}

<style>
	.stats-bar {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		box-shadow: var(--shadow-card);
		padding: var(--card-padding);
		display: flex;
		align-items: baseline;
		justify-content: space-around;
		gap: 1rem;
		flex-wrap: wrap;
		animation: fadeSlideUp 0.4s ease both;
	}
	.stat-item {
		display: flex;
		flex-direction: column;
		align-items: center;
		min-width: 0;
		padding: 0.25rem 0.5rem;
	}
	.stat-number {
		font-size: 1.5rem;
		font-weight: 700;
		color: var(--color-primary);
		line-height: 1.1;
		font-variant-numeric: tabular-nums;
	}
	.stat-label {
		font-size: 0.78rem;
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		margin-top: 0.15rem;
	}
	.stat-divider {
		width: 1px;
		align-self: stretch;
		background: var(--color-border-light);
	}

	.stats-bar-error {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-left: 3px solid var(--color-danger);
	}
	.stats-error-content {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		color: var(--color-text-muted);
		font-size: 0.9rem;
		padding: 0.5rem 0;
	}
	.stats-error-content :global(svg) {
		color: var(--color-danger);
	}
	.stats-retry {
		background: transparent;
		border: none;
		color: var(--color-primary);
		font-weight: 600;
		text-decoration: underline;
		cursor: pointer;
		padding: 0;
		font: inherit;
	}
	.stats-retry:hover {
		color: var(--color-primary-light);
	}
	.stats-retry:focus-visible {
		outline: 2px solid var(--color-primary);
		outline-offset: 2px;
		border-radius: 3px;
	}

	@media (max-width: 700px) {
		.stats-bar {
			flex-direction: column;
			align-items: stretch;
			gap: 0.75rem;
		}
		.stat-divider {
			width: auto;
			height: 1px;
		}
		.stat-item {
			flex-direction: row;
			justify-content: space-between;
			padding: 0.15rem 0.25rem;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.stats-bar {
			animation: none;
		}
	}
</style>
