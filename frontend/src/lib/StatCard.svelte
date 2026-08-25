<script lang="ts">
	/**
	 * StatCard — a unified card surface used on the Statistics dashboard
	 * (and reusable anywhere a labelled list of metrics lives).
	 *
	 * Layout:
	 *   ┌─ header band (primary color) ────────┐
	 *   │  Title                  {meta}       │
	 *   ├──────────────────────────────────────┤
	 *   │  <slot>                              │
	 *   │  (StatRow items go here)             │
	 *   └──────────────────────────────────────┘
	 *
	 * The card animates in with fadeSlideUp and lifts on hover via the
	 * design-system shadow tokens. Stagger delay is exposed as `delayMs`
	 * so a parent grid can cascade the entrance.
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
		transition:
			box-shadow var(--transition-card),
			transform var(--transition-card);
		animation: fadeSlideUp 0.4s ease both;
	}
	.stat-card:hover {
		box-shadow: var(--shadow-card-hover);
	}

	.stat-card-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		background: var(--color-primary);
		color: var(--color-text-light);
		padding: 0.7rem 1rem;
	}
	.stat-card-header h2 {
		font-size: 0.95rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		margin: 0;
		color: var(--color-text-light);
	}
	.stat-card-meta {
		font-size: 0.72rem;
		color: rgba(250, 250, 250, 0.85);
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