<script lang="ts">
	/**
	 * SkeletonStatItem — loading placeholder for <StatCounter>, matching
	 * the exact grid geometry (icon well + number + label) so swapping in
	 * the real component does not reflow.
	 */
	import Skeleton from './Skeleton.svelte';
</script>

<div class="stat-item" aria-hidden="true">
	<span class="stat-icon">
		<Skeleton variant="circle" width="40px" />
	</span>
	<span class="stat-text">
		<span class="stat-number">
			<Skeleton variant="text" width="3rem" />
		</span>
		<span class="stat-label">
			<Skeleton variant="text" width="4rem" />
		</span>
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
	}
	.stat-icon {
		grid-row: 1 / span 2;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 40px;
		height: 40px;
		flex: 0 0 auto;
	}
	.stat-text {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}
	.stat-number {
		font-size: 1.35rem;
		line-height: 1.1;
		height: 1.35rem;
	}
	.stat-label {
		font-size: 0.78rem;
		margin-top: 0.1rem;
		height: 0.78rem;
	}
</style>
