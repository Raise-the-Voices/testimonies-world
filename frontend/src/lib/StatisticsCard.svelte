<!--
  StatisticsCard - the single primitive for every stat surface on the
  platform. Replaces StatCard, StatTile, and SkeletonStatItem with a
  discriminated `variant` prop.

    variant="section"   card chrome + title/meta header + children slot
    variant="kpi"       card chrome + value/label/hint, optional href
    variant="skeleton"  no chrome — centered two-line skeleton for the
                        inline stats-bar loading state

  Chrome (border, shadow, radius, padding, entrance animation,
  hover/focus, reduced-motion fallback) lives once on the `.card`
  class. Section and KPI both compose off it; skeleton does not, by
  design — it has to fit inside a divider-separated inline stats-bar
  on the home page, where card chrome would be wrong.

  The section variant animates in one of two ways, chosen by the
  caller: a load-time fade by default, or the scroll reveal when
  `revealIndex` is passed. The dashboard uses the default; the public
  statistics page opts in.

  All visuals are tokens: --color-*, --radius-card, --shadow-card,
  --transition-card, --skeleton-bg, --skeleton-bg-static. No raw
  hex / spacing / radius values (SYSTEM_RULES §4).
-->
<script lang="ts" module>
	export type StatisticsCardVariant = 'section' | 'kpi' | 'skeleton';

	export interface StatisticsCardSectionProps {
		variant: 'section';
		title: string;
		meta?: string;
		/**
		 * Opt in to the scroll-reveal entrance (the editorial register).
		 * The value is the card's position in the grid and drives the
		 * stagger delay. Leave it undefined and the card keeps the
		 * load-time fade instead — that is what the dashboard wants.
		 */
		revealIndex?: number;
		children?: import('svelte').Snippet;
	}

	export interface StatisticsCardKpiProps {
		variant: 'kpi';
		label: string;
		value: number | null;
		href?: string;
		hint?: string;
		/**
		 * When true, renders a skeleton bar inside the tile instead of
		 * the value. Currently unused by callers — the dashboard renders
		 * its loading state with `<Skeleton variant="rect">` directly —
		 * but kept for API parity with the prior StatTile component.
		 */
		loading?: boolean;
	}

	export interface StatisticsCardSkeletonProps {
		variant: 'skeleton';
	}

	export type StatisticsCardProps =
		| StatisticsCardSectionProps
		| StatisticsCardKpiProps
		| StatisticsCardSkeletonProps;
</script>

<script lang="ts">
	import Skeleton from './Skeleton.svelte';
	import { reveal } from './motion';

	let props: StatisticsCardProps = $props();

	// Localised to the kpi branch, but TS narrows `props` after the
	// discriminator check below so `props.value` is correctly typed
	// when we read it here.
	const displayValue = $derived.by<string | null>(() => {
		if (props.variant !== 'kpi') return null;
		const v = props.value;
		return v === null || v === undefined ? '-' : v.toLocaleString('en-US');
	});
</script>

{#snippet sectionBody(
	title: string,
	meta: string | undefined,
	children: import('svelte').Snippet | undefined
)}
	<header class="section-header">
		<h2>{title}</h2>
		{#if meta}<span class="section-meta">{meta}</span>{/if}
	</header>
	{@render children?.()}
{/snippet}

{#if props.variant === 'section'}
	{#if props.revealIndex !== undefined}
		<!-- The reveal owns the entrance here, so the load-time fade is
		     switched off (`.section-reveal`): a CSS animation outranks
		     the `[data-reveal]` opacity/transform rules and would pin
		     the card visible while it is still meant to be hidden. -->
		<article class="card section section-reveal" use:reveal={{ index: props.revealIndex }}>
			{@render sectionBody(props.title, props.meta, props.children)}
		</article>
	{:else}
		<article class="card section">
			{@render sectionBody(props.title, props.meta, props.children)}
		</article>
	{/if}
{:else if props.variant === 'kpi'}
	{#if props.href}
		<a
			class="card kpi kpi-link"
			href={props.href}
			aria-label="{props.label}: {displayValue}"
		>
			<span class="kpi-value">{displayValue}</span>
			<span class="kpi-label">{props.label}</span>
			{#if props.hint}<span class="kpi-hint">{props.hint}</span>{/if}
		</a>
	{:else}
		<div class="card kpi" aria-label="{props.label}: {displayValue}">
			{#if props.loading}
				<span class="kpi-skeleton" aria-hidden="true"></span>
			{:else}
				<span class="kpi-value">{displayValue}</span>
			{/if}
			<span class="kpi-label">{props.label}</span>
			{#if props.hint}<span class="kpi-hint">{props.hint}</span>{/if}
		</div>
	{/if}
{:else}
	<!-- variant === 'skeleton' — no card chrome. Lives inside an
	     inline stats-bar (see +page.svelte) where dividers separate
	     items. Matches the prior SkeletonStatItem geometry. -->
	<div class="skeleton-row" aria-hidden="true">
		<span class="skeleton-number">
			<Skeleton variant="text" width="3rem" />
		</span>
		<span class="skeleton-label">
			<Skeleton variant="text" width="4rem" />
		</span>
	</div>
{/if}

<style>
	/* === Shared card chrome (section + kpi) ===
	   Defined once. Variant-specific layout lives below.
	   NOTE: no `animation` here — the fadeSlideUp entrance animation
	   was on StatCard (section) only. The old StatTile had no entry
	   animation. Adding one to KPI tiles would be a visible behavior
	   change for the dashboard summary row. */
	.card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		box-shadow: var(--shadow-card);
		overflow: hidden;
		display: flex;
		flex-direction: column;
		transition:
			box-shadow var(--transition-card),
			border-color var(--transition-card);
	}

	/* Section-only entrance animation (matches prior StatCard). */
	.section {
		animation: fadeSlideUp var(--motion-duration-enter) var(--motion-ease-editorial) both;
	}
	/* The scroll reveal replaces the load-time fade — see the template. */
	.section-reveal {
		animation: none;
	}

	/* === Section variant === */
	.section-header {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 0.75rem;
		padding: 1rem 1.25rem 0.6rem 1.25rem;
		border-bottom: 1px solid var(--color-border-light);
	}
	.section-header h2 {
		font-size: 0.78rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		margin: 0;
		color: var(--color-text-muted);
	}
	.section-meta {
		font-size: 0.72rem;
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05rem;
		white-space: nowrap;
	}

	/* === KPI variant === */
	.kpi {
		padding: 1.1rem 1.25rem;
		gap: 0.25rem;
		min-width: 0;
	}
	.kpi-link {
		text-decoration: none;
		color: inherit;
	}
	.kpi-link:hover {
		box-shadow: var(--shadow-card-hover);
		border-color: var(--color-primary-light);
	}
	.kpi-link:focus-visible {
		outline: none;
		box-shadow: 0 0 0 3px var(--color-primary-tint);
	}
	.kpi-value {
		font-size: 1.75rem;
		font-weight: 700;
		color: var(--color-primary);
		line-height: 1.1;
		font-variant-numeric: tabular-nums;
	}
	.kpi-label {
		font-size: 0.78rem;
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.06rem;
	}
	.kpi-hint {
		font-size: 0.78rem;
		color: var(--color-text-muted);
		line-height: 1.3;
		margin-top: 0.15rem;
	}
	.kpi-skeleton {
		display: block;
		width: 60%;
		height: 1.75rem;
		background: var(--skeleton-bg);
		border-radius: 4px;
		animation: skeleton-shimmer 1.4s ease-in-out infinite;
	}

	/* === Skeleton variant ===
	   Inline stats-bar geometry — no chrome. Matches the prior
	   SkeletonStatItem layout pixel-for-pixel. */
	.skeleton-row {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 0.25rem 0.5rem;
	}
	.skeleton-number {
		font-size: 1.5rem;
		line-height: 1.1;
	}
	.skeleton-label {
		font-size: 0.78rem;
		margin-top: 0.15rem;
	}

	/* === Reduced-motion === */
	@media (prefers-reduced-motion: reduce) {
		.section {
			animation: none;
		}
		.card {
			transition: none;
		}
		.kpi-link:hover {
			box-shadow: var(--shadow-card);
		}
		.kpi-skeleton {
			animation: none;
			background: var(--skeleton-bg-static);
		}
	}
</style>
