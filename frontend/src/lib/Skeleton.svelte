<script lang="ts">
	/**
	 * Skeleton — animated placeholder matching the geometry of the loaded
	 * content. Designed for zero CLS: every variant pins width/height (or
	 * uses aspect-ratio) so swapping in real content does not reflow.
	 *
	 * Variants:
	 *   - text         Single line of text. Height ≈ body line.
	 *   - text-block   N stacked text lines with a shorter last line.
	 *   - circle       Round (avatars, status wells).
	 *   - rect         Free rectangle (width × height).
	 *   - card         PersonCard geometry: image + name + 3 meta + CTA.
	 *   - stat-card    StatCard geometry: header band + N rows.
	 *   - stat-row     One labelled row with progress bar.
	 *   - table-row    Single tabular row with N columns.
	 *   - badge        Small pill (badges).
	 *   - button       Button-shaped block.
	 *
	 * Animation: a left-to-right shimmer via a CSS gradient on a
	 * pseudo-element. Honors `prefers-reduced-motion: reduce` by
	 * switching to a static, lower-contrast surface.
	 */
	import type { Snippet } from 'svelte';

	type Variant =
		| 'text'
		| 'text-block'
		| 'circle'
		| 'rect'
		| 'card'
		| 'stat-card'
		| 'stat-row'
		| 'table-row'
		| 'badge'
		| 'button';

	type SkeletonProps = {
		variant?: Variant;
		width?: string;
		height?: string;
		lines?: number;
		cols?: number;
		rounded?: boolean;
		class?: string;
		/** Optional snippet rendered instead of the default geometry. */
		children?: Snippet;
	};

	let {
		variant = 'rect',
		width,
		height,
		lines = 3,
		cols = 5,
		rounded = false,
		class: klass = '',
		children,
	}: SkeletonProps = $props();
</script>

{#if variant === 'text'}
	<span
		class="skeleton skeleton-text {klass}"
		style:width
		style:height
		aria-hidden="true"
	></span>
{:else if variant === 'text-block'}
	<div class="skeleton-text-block {klass}" aria-hidden="true">
		{#each Array.from({ length: lines }, (_, i) => i) as i (i)}
			<span
				class="skeleton skeleton-text"
				style:width={i === lines - 1 ? '70%' : '100%'}
			></span>
		{/each}
	</div>
{:else if variant === 'circle'}
	<span
		class="skeleton skeleton-circle {klass}"
		style:width={width ?? '40px'}
		style:height={height ?? width ?? '40px'}
		aria-hidden="true"
	></span>
{:else if variant === 'card'}
	<!-- PersonCard geometry: 4:3 image + 3 meta rows + CTA. -->
	<div class="skeleton-card {klass}" aria-hidden="true">
		<div class="skeleton skeleton-card-media"></div>
		<div class="skeleton-card-body">
			<div class="skeleton skeleton-card-name"></div>
			<div class="skeleton skeleton-card-meta"></div>
			<div class="skeleton skeleton-card-meta" style="width: 70%"></div>
			<div class="skeleton skeleton-card-meta" style="width: 85%"></div>
			<div class="skeleton skeleton-card-cta"></div>
		</div>
	</div>
{:else if variant === 'stat-card'}
	<!-- StatCard geometry: colored header band + N rows with a bar each. -->
	<div class="skeleton-stat-card {klass}" aria-hidden="true">
		<div class="skeleton-stat-card-header">
			<div class="skeleton skeleton-stat-card-title"></div>
		</div>
		<div class="skeleton-stat-card-body">
			{#each Array.from({ length: lines }, (_, i) => i) as i (i)}
				<div class="skeleton-stat-card-row">
					<div class="skeleton skeleton-stat-card-label"></div>
					<div class="skeleton skeleton-stat-card-pill"></div>
					<div class="skeleton skeleton-stat-card-bar"></div>
				</div>
			{/each}
		</div>
	</div>
{:else if variant === 'stat-row'}
	<div class="skeleton-stat-row {klass}" aria-hidden="true">
		<div class="skeleton skeleton-stat-row-label"></div>
		<div class="skeleton skeleton-stat-row-pill"></div>
		<div class="skeleton skeleton-stat-row-bar"></div>
	</div>
{:else if variant === 'table-row'}
	<div class="skeleton-table-row {klass}" aria-hidden="true">
		{#each Array.from({ length: cols }, (_, i) => i) as i (i)}
			<div class="skeleton skeleton-table-cell" style:width></div>
		{/each}
	</div>
{:else if variant === 'badge'}
	<span
		class="skeleton skeleton-badge {klass}"
		style:width={width ?? '5rem'}
		style:height={height ?? '1.25rem'}
		aria-hidden="true"
	></span>
{:else if variant === 'button'}
	<span
		class="skeleton skeleton-button {klass}"
		style:width={width ?? '8rem'}
		style:height={height ?? '2.5rem'}
		aria-hidden="true"
	></span>
{:else}
	<span
		class="skeleton skeleton-rect {klass}"
		class:rounded
		style:width
		style:height
		aria-hidden="true"
	></span>
{/if}

{#if children}
	<div class="skeleton-slot {klass}">
		{@render children()}
	</div>
{/if}

<style>
	/* All variants share the shimmer animation. The skeleton base class
	   only sets the gradient; geometry lives on each variant. */
	.skeleton {
		display: block;
		background: var(--skeleton-bg);
		background-image: linear-gradient(
			90deg,
			transparent 0%,
			var(--skeleton-shine) 50%,
			transparent 100%
		);
		background-size: 200% 100%;
		background-repeat: no-repeat;
		animation: skeleton-shimmer 1.4s ease-in-out infinite;
		border-radius: 4px;
	}

	@keyframes skeleton-shimmer {
		0% {
			background-position: 200% 0;
		}
		100% {
			background-position: -200% 0;
		}
	}

	/* === text === */
	.skeleton-text {
		height: 0.9em;
		width: 100%;
	}
	.text-block,
	.skeleton-text-block {
		display: flex;
		flex-direction: column;
		gap: 0.5em;
	}

	/* === circle === */
	.skeleton-circle {
		border-radius: 50%;
	}

	/* === rect === */
	.skeleton-rect {
		min-height: 1rem;
	}
	.skeleton-rect.rounded {
		border-radius: 999px;
	}

	/* === card (PersonCard) === */
	.skeleton-card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-card);
		overflow: hidden;
		display: flex;
		flex-direction: column;
	}
	.skeleton-card-media {
		width: 100%;
		aspect-ratio: 4 / 3;
		border-radius: 0;
	}
	.skeleton-card-body {
		padding: 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 0.55rem;
		flex-grow: 1;
	}
	.skeleton-card-name {
		height: 1.05rem;
		width: 75%;
	}
	.skeleton-card-meta {
		height: 0.7rem;
		width: 100%;
	}
	.skeleton-card-cta {
		height: 0.75rem;
		width: 40%;
		margin-top: auto;
		padding-top: 0.85rem;
		border-top: 1px solid var(--color-border-light);
	}

	/* === stat-card (StatCard) === */
	.skeleton-stat-card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		box-shadow: var(--shadow-card);
		overflow: hidden;
		display: flex;
		flex-direction: column;
	}
	.skeleton-stat-card-header {
		background: var(--color-primary);
		padding: 0.7rem 1rem;
		display: flex;
		align-items: center;
	}
	.skeleton-stat-card-title {
		height: 0.95rem;
		width: 7rem;
		/* Override base skeleton bg to a light variant readable on the
		   dark primary header. */
		background: rgba(255, 255, 255, 0.18);
		background-image: linear-gradient(
			90deg,
			transparent 0%,
			rgba(255, 255, 255, 0.32) 50%,
			transparent 100%
		);
		background-size: 200% 100%;
		background-repeat: no-repeat;
		animation: skeleton-shimmer 1.4s ease-in-out infinite;
	}
	.skeleton-stat-card-body {
		padding: 0.6rem 0;
	}
	.skeleton-stat-card-row {
		display: grid;
		grid-template-columns: 1fr auto;
		grid-template-rows: auto auto;
		column-gap: 0.85rem;
		row-gap: 0.3rem;
		align-items: center;
		padding: 0.6rem 1rem;
		border-bottom: 1px solid var(--color-border-light);
	}
	.skeleton-stat-card-row:last-child {
		border-bottom: none;
	}
	.skeleton-stat-card-label {
		height: 0.92rem;
	}
	.skeleton-stat-card-pill {
		height: 1.7rem;
		width: 2.4rem;
		border-radius: 999px;
	}
	.skeleton-stat-card-bar {
		grid-column: 1 / -1;
		grid-row: 2;
		height: 4px;
		border-radius: 999px;
	}

	/* === stat-row === */
	.skeleton-stat-row {
		display: grid;
		grid-template-columns: 1fr auto;
		grid-template-rows: auto auto;
		column-gap: 0.85rem;
		row-gap: 0.3rem;
		align-items: center;
		padding: 0.6rem 1rem;
		border-bottom: 1px solid var(--color-border-light);
	}
	.skeleton-stat-row:last-child {
		border-bottom: none;
	}
	.skeleton-stat-row-label {
		height: 0.92rem;
	}
	.skeleton-stat-row-pill {
		height: 1.7rem;
		width: 2.4rem;
		border-radius: 999px;
	}
	.skeleton-stat-row-bar {
		grid-column: 1 / -1;
		grid-row: 2;
		height: 4px;
		border-radius: 999px;
	}

	/* === table-row === */
	.skeleton-table-row {
		display: flex;
		gap: 1rem;
		padding: 0.75rem 1rem;
		border-bottom: 1px solid var(--color-border-light);
		align-items: center;
	}
	.skeleton-table-row:last-child {
		border-bottom: none;
	}
	.skeleton-table-cell {
		height: 0.85rem;
		flex: 1 1 0;
		min-width: 4rem;
	}

	/* === badge === */
	.skeleton-badge {
		border-radius: 999px;
		height: 1.25rem;
	}

	/* === button === */
	.skeleton-button {
		border-radius: var(--radius-input);
	}

	/* === slot wrapper === */
	.skeleton-slot {
		display: contents;
	}

	/* Reduced motion — drop the shimmer, use a static mid-tone surface
	   that still conveys "loading" without movement. */
	@media (prefers-reduced-motion: reduce) {
		.skeleton,
		.skeleton-stat-card-title {
			animation: none;
			background-image: none;
			background: var(--skeleton-bg-static);
		}
	}
</style>
