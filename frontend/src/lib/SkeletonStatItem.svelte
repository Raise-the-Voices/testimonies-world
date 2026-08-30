<script lang="ts">
	/**
	 * SkeletonStatItem — loading placeholder for the home-page stats bar.
	 * Mirrors the typographic row layout (number on top, uppercase label
	 * below) so swapping in the real value does not reflow.
	 */
	import Skeleton from './Skeleton.svelte';
</script>

<div class="stat-item" aria-hidden="true">
	<span class="stat-number">
		<Skeleton variant="text" width="3rem" />
	</span>
	<span class="stat-label">
		<Skeleton variant="text" width="4rem" />
	</span>
</div>

<style>
	.stat-item {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 0.25rem 0.5rem;
	}
	.stat-number {
		font-size: 1.5rem;
		line-height: 1.1;
	}
	.stat-label {
		font-size: 0.78rem;
		margin-top: 0.15rem;
	}
</style>
