<script lang="ts">
	/**
	 * PersonCard — the redesigned card used on /persons (cards view).
	 *
	 * Layout:
	 *   ┌────────────────────────────┐
	 *   │ image      [status badge]  │   <- card-media + overlay badge
	 *   ├────────────────────────────┤
	 *   │ Name (truncated)           │
	 *   │ · country · location       │   <- card-body, metadata rows
	 *   │ · last seen · N reports    │
	 *   ├────────────────────────────┤
	 *   │ View details →             │   <- card-cta (footer)
	 *   └────────────────────────────┘
	 *
	 * Hover lifts the card (-4px), deepens the shadow, scales the image
	 * to 1.05x, and slides the CTA arrow right. All transitions are
	 * disabled under prefers-reduced-motion: reduce.
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
</script>

<article class="person-card" style="animation-delay: {delayMs}ms">
	<a class="card-media" {href} aria-label="View details for {person.name}">
		{#if person.profile_image_url}
			<img src={person.profile_image_url} alt={person.name} loading="lazy" />
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

		<ul class="card-meta">
			{#if person.country}
				<li><Icon name="globe" size={14} /> {person.country}</li>
			{/if}
			{#if person.rough_location}
				<li><Icon name="pin" size={14} /> {person.rough_location}</li>
			{/if}
			{#if formattedLastSeen}
				<li><Icon name="clock" size={14} /> Last seen {formattedLastSeen}</li>
			{/if}
			{#if hasReportCount}
				<li>
					<Icon name="newspaper" size={14} />
					{person.report_count} report{person.report_count === 1 ? '' : 's'}
				</li>
			{/if}
		</ul>

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
		transition: box-shadow 0.3s ease, transform 0.3s ease, border-color 0.3s ease;
	}
	.person-card:hover {
		box-shadow: var(--shadow-card-lg);
		transform: translateY(-4px);
		border-color: var(--color-primary-light);
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
		transition: transform 0.5s ease;
		display: block;
	}
	.person-card:hover .card-media :global(img) {
		transform: scale(1.05);
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
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}
	.card-meta li {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-size: 0.78rem;
		color: var(--color-text-muted);
		line-height: 1.4;
	}
	.card-meta li :global(svg) {
		flex: 0 0 auto;
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
	.card-cta-arrow {
		display: inline-flex;
		transition: transform 0.2s ease;
	}
	.person-card:hover .card-cta-arrow {
		transform: translateX(4px);
	}

	@media (prefers-reduced-motion: reduce) {
		.person-card {
			animation: none;
			transition: none;
		}
		.card-media :global(img),
		.card-cta-arrow {
			transition: none;
		}
		.person-card:hover {
			transform: none;
		}
		.person-card:hover .card-media :global(img) {
			transform: none;
		}
		.person-card:hover .card-cta-arrow {
			transform: none;
		}
	}
</style>
