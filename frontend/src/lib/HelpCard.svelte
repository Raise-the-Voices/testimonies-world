<script lang="ts">
	import Icon from './Icon.svelte';
	import type { IconName } from './Icon.svelte';

	/**
	 * HelpCard — a single feature card on the home page "How to help"
	 * section. Icon + title + description. `delayMs` cascades the entrance
	 * animation when several cards render in a grid.
	 */
	let {
		icon,
		title,
		description,
		delayMs = 0,
	}: {
		icon: IconName;
		title: string;
		description: string;
		delayMs?: number;
	} = $props();
</script>

<div class="help-card" style="animation-delay: {delayMs}ms">
	<span class="help-icon" aria-hidden="true">
		<Icon name={icon} size={22} />
	</span>
	<h3>{title}</h3>
	<p>{description}</p>
</div>

<style>
	.help-card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		box-shadow: var(--shadow-card);
		padding: 1.5rem;
		transition:
			box-shadow var(--transition-card),
			transform var(--transition-card),
			border-color var(--transition-card);
		animation: fadeSlideUp 0.4s ease both;
	}
	.help-card:hover {
		box-shadow: var(--shadow-card-hover);
		transform: translateY(-3px);
		border-color: var(--color-primary-light);
	}
	.help-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 44px;
		height: 44px;
		border-radius: 10px;
		background: var(--color-primary-tint);
		color: var(--color-primary);
		margin-bottom: 0.85rem;
	}
	.help-card h3 {
		font-size: 1.05rem;
		font-weight: 700;
		margin: 0 0 0.5rem 0;
		color: var(--color-text);
	}
	.help-card p {
		font-size: 0.9rem;
		line-height: 1.55;
		color: var(--color-text-muted);
		margin: 0;
	}

	@media (prefers-reduced-motion: reduce) {
		.help-card {
			animation: none;
		}
		.help-card:hover {
			transform: none;
		}
	}
</style>