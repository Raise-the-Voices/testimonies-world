<script lang="ts">
	/**
	 * PersonCard — used on /persons (cards view).
	 *
	 * Layout:
	 *   ┌────────────────────────────┐
	 *   │ image      [status badge]  │   <- card-media + overlay badge
	 *   ├────────────────────────────┤
	 *   │ Name (truncated)           │
	 *   │ Country · Last seen · N rpts│   <- single inline metadata line
	 *   ├────────────────────────────┤
	 *   │ View details →             │   <- card-cta (footer)
	 *   └────────────────────────────┘
	 *
	 * Humanized variant: no icon-prefixed metadata lines (each line used to
	 * start with a small globe/pin/clock/newspaper icon, which read as
	 * "AI-template"). No hover-lift, no image scale-on-hover. The card
	 * itself still has its border + shadow, but the interaction is just
	 * a color change on the title.
	 */
	import { base } from '$app/paths';
	import Icon from './Icon.svelte';
	import StatusBadge from './StatusBadge.svelte';

	let {
		person,
		delayMs = 0,
	}: {
		person: any;
		delayMs?: number;
	} = $props();

	// Local date formatting — keeps the card self-contained.
	function formatDate(iso: string | null | undefined): string {
		if (!iso) return '';
		try {
			return new Date(iso).toLocaleDateString('en-US', {
				year: 'numeric',
				month: 'short',
				day: 'numeric',
			});
		} catch {
			return iso;
		}
	}

	let href = $derived(`${base}/persons/${person.id}`);
	let formattedLastSeen = $derived(formatDate(person.last_known_date));
	let hasReportCount = $derived(Number(person.report_count) > 0);

	// Build a single inline metadata string: "Country · Last seen DATE · N reports"
	let metaLine = $derived.by(() => {
		const parts: string[] = [];
		if (person.country) parts.push(person.country);
		if (formattedLastSeen) parts.push(`Last seen ${formattedLastSeen}`);
		if (hasReportCount) {
			parts.push(
				`${person.report_count} report${person.report_count === 1 ? '' : 's'}`,
			);
		}
		return parts.join(' · ');
	});
</script>

<article class="person-card" style="animation-delay: {delayMs}ms">
	<a class="card-media" {href} aria-label="View details for {person.name}">
		{#if person.profile_image_url}
			<img
				src={person.profile_image_url}
				alt={person.name}
				loading="lazy"
				decoding="async"
				width="400"
				height="300"
			/>
		{:else}
			<div class="card-media-placeholder" aria-hidden="true">
				<Icon name="cases" size={36} />
			</div>
		{/if}
		{#if person.current_status}
			<span class="card-media-overlay">
				<StatusBadge status={person.current_status} variant="overlay" />
			</span>
		{/if}
	</a>

	<div class="card-body">
		<h3 class="card-name"><a {href}>{person.name}</a></h3>

		{#if metaLine}
			<p class="card-meta">{metaLine}</p>
		{/if}

		<a class="card-cta" {href}>
			<span>View details</span>
			<span class="card-cta-arrow"><Icon name="arrow-right" size={16} /></span>
		</a>
	</div>
</article>

<style>
	.person-card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-card);
		overflow: hidden;
		display: flex;
		flex-direction: column;
		animation: fadeSlideUp 0.4s ease both;
		/* Perf: scope layout, style, and paint invalidation to this
		   card. Without `contain`, an image decode, hover, or
		   animation frame inside ONE card invalidates the entire
		   list — and on a 20-row listing the mobile profiler
		   showed 1.5s of Recalculate Style + 2.4s of Paint mostly
		   attributable to cascading invalidation. `layout` keeps
		   the card's box from affecting siblings; `style` keeps
		   counters / `content` etc. from leaking out; `paint`
		   keeps the card's shadow + image clipped to its own
		   layer. Browsers without `contain` degrade gracefully. */
		contain: layout style paint;
		/* Perf: skip rendering for cards below the fold on first
		   paint. The browser reserves `contain-intrinsic-size`
		   space so the layout doesn't shift when a card wakes
		   up. 320px ≈ image (aspect-ratio 4/3 on a ~280px-wide
		   card = 210px) + card-body padding + 3-line clamp +
		   CTA footer. Slight over-estimate is preferable to
		   jitter when a card suddenly paints. */
		content-visibility: auto;
		contain-intrinsic-size: 0 320px;
	}

	.card-media {
		position: relative;
		display: block;
		aspect-ratio: 4 / 3;
		background: var(--color-section-bg);
		overflow: hidden;
	}
	.card-media :global(img) {
		width: 100%;
		height: 100%;
		object-fit: cover;
		display: block;
	}

	.card-media-placeholder {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 100%;
		height: 100%;
		color: var(--color-text-muted);
		background: var(--color-bg);
	}

	.card-media-overlay {
		position: absolute;
		top: 0.75rem;
		right: 0.75rem;
	}

	.card-body {
		padding: 1.25rem;
		display: flex;
		flex-direction: column;
		flex-grow: 1;
		gap: 0.75rem;
	}

	.card-name {
		font-size: 1rem;
		font-weight: 700;
		color: var(--color-text);
		margin: 0;
		line-height: 1.3;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.card-name :global(a) {
		color: inherit;
		text-decoration: none;
	}
	.card-name :global(a:hover) {
		color: var(--color-primary);
	}

	.card-meta {
		margin: 0;
		font-size: 0.82rem;
		color: var(--color-text-muted);
		line-height: 1.4;
	}

	.card-cta {
		margin-top: auto;
		padding-top: 0.85rem;
		border-top: 1px solid var(--color-border-light);
		display: inline-flex;
		align-items: center;
		justify-content: space-between;
		color: var(--color-primary);
		font-weight: 700;
		font-size: 0.78rem;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		text-decoration: none;
	}
	.card-cta:hover {
		color: var(--color-text);
	}

	@media (prefers-reduced-motion: reduce) {
		.person-card {
			animation: none;
		}
	}
</style>
