<!--
  DashboardCard - chrome wrapper for each dashboard section.

  Reused by:
    - Stat tiles (one card per tile)
    - QuickActions card
    - RecentActivity card
    - StatusBreakdown card
    - any future section

  Variant props match the existing card-error / card-empty conventions
  from app.css (the same `border-left: 3px solid var(--color-...)`
  pattern used by /statistics and /watchdog error/empty states).
-->
<script lang="ts">
	interface Props {
		title?: string;
		subtitle?: string;
		/** Visual variant - overrides the left-border accent. */
		variant?: 'default' | 'error' | 'empty';
		/** Optional trailing slot rendered in the header right side
		 *  (typically a Refresh button or a "View all ->" link). */
		trailing?: import('svelte').Snippet;
		children: import('svelte').Snippet;
	}

	let {
		title,
		subtitle,
		variant = 'default',
		trailing,
		children,
	}: Props = $props();
</script>

<section class="dashboard-card card-{variant}">
	{#if title || trailing}
		<header class="card-header">
			<div class="card-titles">
				{#if title}
					<h2 class="card-title">{title}</h2>
				{/if}
				{#if subtitle}
					<p class="card-subtitle">{subtitle}</p>
				{/if}
			</div>
			{#if trailing}
				<div class="card-trailing">
					{@render trailing()}
				</div>
			{/if}
		</header>
	{/if}
	<div class="card-body">
		{@render children()}
	</div>
</section>

<style>
	.dashboard-card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-left: 3px solid var(--color-primary-light);
		border-radius: var(--radius-card);
		box-shadow: var(--shadow-card);
		padding: 1.25rem 1.5rem;
	}
	.card-error {
		border-left-color: var(--color-danger);
	}
	.card-empty {
		border-left-color: var(--color-success);
	}

	.card-header {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: 1rem;
		flex-wrap: wrap;
		margin-bottom: 1rem;
	}
	.card-titles {
		min-width: 0;
	}
	.card-title {
		margin: 0;
		font-size: 1.05rem;
		font-weight: 600;
		color: var(--color-text);
	}
	.card-subtitle {
		margin: 0.2rem 0 0 0;
		font-size: 0.88rem;
		color: var(--color-text-muted);
		max-width: var(--max-w-prose);
	}
	.card-trailing {
		flex-shrink: 0;
	}

	.card-body {
		/* Children get to define their own grid / spacing. */
	}
</style>
