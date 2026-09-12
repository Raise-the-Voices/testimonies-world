<script lang="ts">
	import { base } from '$app/paths';
	import type { TestimonialPublic } from '$lib/api/generated/endpoints.schemas';
	import { isEmptyAfterSanitization, safeText, safeTextOr } from '$lib/testimonial-sanitize';

	/**
	 * One-testimonial card for the public list and the "My drafts"
	 * and "Review queue" tabs. Renders only fields from the
	 * `TestimonialPublic` serializer — the backend never sends
	 * `source_encrypted` / `precise_location_encrypted` to the public
	 * surface, so we don't have to worry about accidentally rendering
	 * ciphertext here. The `source_visible` boolean is the server-
	 * computed mask: when `false` (the row's `source_visibility`
	 * is `hidden`) the source descriptor is omitted entirely.
	 *
	 * Defensive text rendering (see lib/testimonial-sanitize.ts):
	 * every text field is run through `safeText()` so a row containing
	 * raw Git conflict markers (<<<<<<< / ======= / >>>>>>>) or other
	 * corruption never renders that text verbatim. If the row is so
	 * corrupted that EVERY display field is empty after sanitisation,
	 * the card renders nothing at all — the list page hides it via
	 * `{#if !isEmpty}`. This is the post-validation safety net for
	 * rows that pre-date the client-side form validation gate.
	 */

	interface Props {
		testimonial: TestimonialPublic;
		showStatus?: boolean;
	}

	let { testimonial, showStatus = false }: Props = $props();

	const safeTitle = $derived(safeText(testimonial.title));
	const safeSummary = $derived(safeText(testimonial.summary));
	const safeCountry = $derived(safeText(testimonial.country));
	const safeRegion = $derived(safeText(testimonial.region));
	const safeLocationDisplay = $derived(safeText(testimonial.public_location_display));
	const safeSourceLabel = $derived(safeText(testimonial.public_source_label));

	const isEmpty = $derived(
		isEmptyAfterSanitization({
			title: testimonial.title,
			summary: testimonial.summary,
			country: testimonial.country,
			public_location_display: testimonial.public_location_display,
		})
	);

	const publishedLabel = $derived(
		testimonial.published_at
			? new Date(testimonial.published_at).toLocaleDateString(undefined, {
					year: 'numeric',
					month: 'short',
					day: 'numeric',
				})
			: ''
	);
</script>

{#if !isEmpty}
	<a class="testimonial-card" href="{base}/testimonials/{testimonial.id}">
		{#if safeLocationDisplay || safeCountry}
			<p class="testimonial-card-location">
				{#if safeLocationDisplay}
					{safeLocationDisplay}
				{:else if safeCountry}
					{safeCountry}{#if safeRegion}, {safeRegion}{/if}
				{/if}
			</p>
		{/if}

		<h3 class="testimonial-card-title">
			{#if safeTitle}
				{safeTitle}
			{:else}
				{safeCountry || 'Untitled'} case
			{/if}
		</h3>

		{#if safeSummary}
			<p class="testimonial-card-summary">{safeSummary}</p>
		{/if}

		<dl class="testimonial-card-meta">
			{#if testimonial.source_visible && safeSourceLabel}
				<dt>Source</dt>
				<dd>{safeSourceLabel}</dd>
			{/if}
			{#if testimonial.incident_date}
				<dt>Incident</dt>
				<dd>
					<time datetime={testimonial.incident_date ?? ''}>
						{new Date(testimonial.incident_date ?? '').toLocaleDateString(undefined, {
							year: 'numeric',
							month: 'short',
							day: 'numeric',
						})}
					</time>
				</dd>
			{/if}
			{#if testimonial.verification_level}
				<dt>Verification</dt>
				<dd class="testimonial-card-verification">{(testimonial.verification_level ?? '').replace(/_/g, ' ').replace('level ', 'Level ')}</dd>
			{/if}
		</dl>

		{#if testimonial.tags && testimonial.tags.length > 0}
			<ul class="testimonial-card-tags" aria-label="Tags">
				{#each testimonial.tags as tag (tag.id)}
					<li class="testimonial-card-tag">{safeText(tag.name)}</li>
				{/each}
			</ul>
		{/if}

		<footer class="testimonial-card-footer">
			{#if publishedLabel}
				<time datetime={testimonial.published_at ?? ''}>Published {publishedLabel}</time>
			{/if}
			{#if showStatus}
				<span class="testimonial-card-status testimonial-card-status-{testimonial.status}">
					{testimonial.status.replace('_', ' ')}
				</span>
			{/if}
		</footer>
	</a>
{/if}

<style>
	.testimonial-card {
		display: flex;
		flex-direction: column;
		gap: 0.65rem;
		padding: 1.25rem 1.5rem;
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		box-shadow: var(--shadow-card);
		color: inherit;
		text-decoration: none;
		/* Perf: hover lift only transitions `transform` — a
		   compositor-only property. Earlier this transitioned
		   `box-shadow` and `border-color` as well, both of which
		   are paint-triggering; on a list of 20 cards each hover
		   frame painted a 300×200px shadow region for the full
		   0.2s window. The lift is still visible (translateY(-2px))
		   and the resting/hover shadow values are unchanged —
		   the only difference is the snap from rest→hover is
		   instant for the shadow. Browsers without `contain`
		   degrade gracefully. */
		transition: transform 0.2s ease;
		/* See PersonCard for the rationale — scope layout/style/
		   paint to this card so off-card hover / image decode
		   doesn't invalidate the whole list. */
		contain: layout style paint;
		content-visibility: auto;
		contain-intrinsic-size: 0 200px;
	}
	.testimonial-card:hover {
		transform: translateY(-2px);
		box-shadow: var(--shadow-card-hover);
		border-color: var(--color-primary-light);
	}
	.testimonial-card:focus-visible {
		outline: 3px solid var(--focus-ring);
		outline-offset: 2px;
	}

	.testimonial-card-location {
		margin: 0;
		font-size: 0.78rem;
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.06rem;
	}

	.testimonial-card-title {
		margin: 0;
		font-size: 1.15rem;
		color: var(--color-primary);
		line-height: 1.3;
	}

	.testimonial-card-summary {
		margin: 0;
		color: var(--color-text);
		font-size: 0.95rem;
		line-height: 1.55;
		/* Multi-line clamp keeps card grids visually aligned even when
		   summaries vary in length. Three lines ≈ 4.65em. */
		display: -webkit-box;
		-webkit-line-clamp: 3;
		line-clamp: 3;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.testimonial-card-meta {
		margin: 0.25rem 0 0 0;
		display: grid;
		grid-template-columns: max-content 1fr;
		gap: 0.15rem 0.75rem;
		font-size: 0.82rem;
	}
	.testimonial-card-meta dt {
		color: var(--color-text-muted);
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.04rem;
		font-size: 0.7rem;
		align-self: center;
	}
	.testimonial-card-meta dd {
		margin: 0;
		color: var(--color-text);
	}
	.testimonial-card-verification {
		text-transform: capitalize;
	}

	.testimonial-card-tags {
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
		list-style: none;
		margin: 0.25rem 0 0 0;
		padding: 0;
	}
	.testimonial-card-tag {
		padding: 0.18rem 0.55rem;
		background: var(--color-section-bg);
		color: var(--color-primary);
		border-radius: 999px;
		font-size: 0.72rem;
		font-weight: 700;
		text-transform: lowercase;
	}

	.testimonial-card-footer {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-top: auto;
		padding-top: 0.5rem;
		border-top: 1px solid var(--color-border-subtle);
		font-size: 0.75rem;
		color: var(--color-text-muted);
	}
	.testimonial-card-status {
		padding: 0.18rem 0.5rem;
		border-radius: 999px;
		font-size: 0.7rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.04rem;
	}
	.testimonial-card-status-draft {
		background: #f1f5f9;
		color: #475569;
	}
	.testimonial-card-status-under_review {
		background: #fef3c7;
		color: #92400e;
	}
	.testimonial-card-status-approved {
		background: #dcfce7;
		color: #15803d;
	}
	.testimonial-card-status-published {
		background: var(--color-primary);
		color: var(--color-text-light);
	}
	.testimonial-card-status-rejected {
		background: #fee2e2;
		color: #b91c1c;
	}
	.testimonial-card-status-archived {
		background: #e5e7eb;
		color: #4b5563;
	}
</style>
