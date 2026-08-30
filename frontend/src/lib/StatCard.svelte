<script lang="ts">
	/**
	 * StatCard — used on the Statistics dashboard to hold a labelled
	 * list of metrics.
	 *
	 * Layout (humanized):
	 *   ┌─────────────────────────────────────┐
	 *   │  Title                  {meta}      │   <- plain uppercase title
	 *   │  ─────────                         │   <- hairline divider
	 *   │  <slot>                             │   <- StatRow items go here
	 *   └─────────────────────────────────────┘
	 *
	 * Previously had a primary-color header band — replaced with a
	 * plain uppercase title + hairline rule so the dashboard reads as
	 * a list of sections, not a grid of badges.
	 */

	let {
		title,
		meta = '',
		delayMs = 0,
		children,
	}: {
		title: string;
		meta?: string;
		delayMs?: number;
		children: import('svelte').Snippet;
	} = $props();
</script>

<article class="stat-card" style="animation-delay: {delayMs}ms">
	<header class="stat-card-header">
		<h2>{title}</h2>
		{#if meta}
			<span class="stat-card-meta">{meta}</span>
		{/if}
	</header>
	{@render children()}
</article>

<style>
	.stat-card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		box-shadow: var(--shadow-card);
		overflow: hidden;
		display: flex;
		flex-direction: column;
		animation: fadeSlideUp 0.4s ease both;
	}

	.stat-card-header {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 0.75rem;
		padding: 1rem 1.25rem 0.6rem 1.25rem;
		border-bottom: 1px solid var(--color-border-light);
	}
	.stat-card-header h2 {
		font-size: 0.78rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		margin: 0;
		color: var(--color-text-muted);
	}
	.stat-card-meta {
		font-size: 0.72rem;
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05rem;
		white-space: nowrap;
	}

	@media (prefers-reduced-motion: reduce) {
		.stat-card {
			animation: none;
		}
	}
</style>