<script lang="ts">
	import Icon from './Icon.svelte';
	import type { IconName } from './Icon.svelte';

	/**
	 * StatCounter — a single icon + value + label item used in the
	 * home page stats bar (or any summary strip).
	 *
	 *   ┌──────┐
	 *   │ icon │  1,234
	 *   └──────┘  CASES
	 *
	 * The whole row is hoverable: it lifts slightly and gains the
	 * standard card-hover shadow.
	 */
	let {
		icon,
		value,
		label,
	}: {
		icon: IconName;
		value: number | string;
		label: string;
	} = $props();
</script>

<div class="stat-item">
	<span class="stat-icon" aria-hidden="true">
		<Icon name={icon} size={20} />
	</span>
	<span class="stat-text">
		<span class="stat-number">{value}</span>
		<span class="stat-label">{label}</span>
	</span>
</div>

<style>
	.stat-item {
		display: grid;
		grid-template-columns: auto 1fr;
		grid-template-rows: auto auto;
		column-gap: 0.85rem;
		row-gap: 0.15rem;
		align-items: center;
		padding: 0.6rem 0.7rem;
		border-radius: var(--radius-card);
		transition:
			box-shadow var(--transition-card),
			transform var(--transition-card),
			background var(--transition-card);
	}
	.stat-item:hover {
		box-shadow: var(--shadow-card-hover);
		transform: translateY(-2px);
		background: var(--color-bg);
	}
	.stat-icon {
		grid-row: 1 / span 2;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 40px;
		height: 40px;
		border-radius: 50%;
		background: var(--color-primary-tint);
		color: var(--color-primary);
		flex: 0 0 auto;
	}
	.stat-text {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}
	.stat-number {
		font-size: 1.35rem;
		font-weight: 700;
		color: var(--color-primary);
		line-height: 1.1;
	}
	.stat-label {
		font-size: 0.78rem;
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		margin-top: 0.1rem;
	}

	@media (prefers-reduced-motion: reduce) {
		.stat-item:hover {
			transform: none;
		}
	}
</style>