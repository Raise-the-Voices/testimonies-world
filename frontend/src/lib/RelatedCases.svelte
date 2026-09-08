<!--
  RelatedCases — sidebar widget showing persons related to the
  current person detail page.

  Data flow:
    <RelatedCases personId={...} />  →  GET /api/persons/{id}/related/
    Backend scoring: same country + shared category overlap,
    ranked by shared-category count, capped at 6.

  Empty state: when the backend returns [] (no matches), we hide the
  section entirely rather than render a "No related cases" panel —
  a sidebar widget that's empty 90% of the time is worse than one
  that appears only when it has something to say.
-->
<script lang="ts">
	import { ApiError } from '$lib/api';
	import { personsRelatedRetrieve } from '$lib/api/generated/endpoints';
	import type { PersonList } from '$lib/api/generated/endpoints.schemas';
	import StatusBadge from '$lib/StatusBadge.svelte';

	interface Props {
		/** The person whose related-cases we want. */
		personId: number;
	}

	let { personId }: Props = $props();

	let items = $state<PersonList[]>([]);
	let loading = $state(true);
	let errored = $state(false);

	async function load() {
		loading = true;
		errored = false;
		try {
			const res = await personsRelatedRetrieve(personId);
			// The generated client returns { data: { results: PersonList[] } }
			// because the @extend_schema declares a `results` field on
			// the inline RelatedPersonsResponse serializer. Normalize
			// defensively in case the schema shape evolves.
			const body: any = res.data;
			items = Array.isArray(body?.results) ? body.results : (Array.isArray(body) ? body : []);
		} catch (e) {
			// Don't surface a hard error for the widget — a failed
			// related-cases fetch shouldn't break the rest of the
			// person detail page. Log + hide.
			console.error('[RelatedCases] fetch failed:', e);
			errored = true;
			items = [];
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		// Re-fetch whenever the person changes (Back/Forward navigation
		// between person detail pages reuses the same component).
		void personId;
		void load();
	});

	function personHref(id: number): string {
		return `/persons/${id}`;
	}
</script>

{#if loading}
	<!-- Skeleton matching the real grid shape so layout doesn't jump -->
	<section class="related-cases" aria-busy="true" aria-label="Loading related cases">
		<h2 class="related-cases-title">Related cases</h2>
		<div class="related-cases-grid">
			{#each Array(3) as _, i (i)}
				<div class="related-card-skeleton" aria-hidden="true"></div>
			{/each}
		</div>
	</section>
{:else if !errored && items.length > 0}
	<section class="related-cases" aria-label="Related cases">
		<header class="related-cases-header">
			<h2 class="related-cases-title">Related cases</h2>
			<p class="related-cases-subtitle">
				Same country or shared category — ranked by strongest match.
			</p>
		</header>
		<div class="related-cases-grid">
			{#each items as person (person.id)}
				<a class="related-card" href={personHref(person.id)} aria-label="Open case: {person.name}">
					{#if person.profile_image_url}
						<img
							class="related-card-thumb"
							src={person.profile_image_url}
							alt={person.name}
							loading="lazy"
							decoding="async"
							width="48"
							height="48"
						/>
					{:else}
						<span class="related-card-thumb related-card-thumb-placeholder" aria-hidden="true">
							{person.name.charAt(0).toUpperCase()}
						</span>
					{/if}
					<div class="related-card-body">
						<span class="related-card-name">{person.name}</span>
						<span class="related-card-meta">
							<span class="related-card-country">{person.country}</span>
							{#if person.current_status}
								<StatusBadge status={person.current_status as any} variant="default" />
							{/if}
						</span>
					</div>
				</a>
			{/each}
		</div>
	</section>
{/if}

<style>
	.related-cases {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}
	.related-cases-header {
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
	}
	.related-cases-title {
		margin: 0;
		font-size: 0.85rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		color: var(--color-text-muted);
	}
	.related-cases-subtitle {
		margin: 0;
		font-size: 0.78rem;
		color: var(--color-text-muted);
	}
	.related-cases-grid {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	.related-card {
		display: flex;
		align-items: center;
		gap: 0.65rem;
		padding: 0.55rem 0.7rem;
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-input);
		background: var(--color-bg-white);
		text-decoration: none;
		color: var(--color-text);
		transition:
			box-shadow var(--transition-card),
			border-color var(--transition-card),
			background var(--transition-card);
	}
	.related-card:hover {
		box-shadow: var(--shadow-card-hover);
		border-color: var(--color-primary-light);
	}
	.related-card:focus-visible {
		outline: none;
		box-shadow: 0 0 0 3px var(--color-primary-tint);
	}
	.related-card-thumb {
		flex-shrink: 0;
		width: 40px;
		height: 40px;
		border-radius: 50%;
		object-fit: cover;
		background: var(--color-bg);
		display: flex;
		align-items: center;
		justify-content: center;
		font-weight: 700;
		color: var(--color-primary);
		font-size: 0.95rem;
	}
	.related-card-thumb-placeholder {
		background: var(--color-primary-tint);
	}
	.related-card-body {
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
		min-width: 0;
		flex: 1;
	}
	.related-card-name {
		font-weight: 700;
		font-size: 0.92rem;
		color: var(--color-text);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.related-card-meta {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		min-width: 0;
		font-size: 0.78rem;
		color: var(--color-text-muted);
	}
	.related-card-country {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.related-card-skeleton {
		height: 56px;
		border-radius: var(--radius-input);
		background: var(--skeleton-bg);
		animation: skeleton-shimmer 1.4s ease-in-out infinite;
	}
	@media (prefers-reduced-motion: reduce) {
		.related-card,
		.related-card:hover {
			transition: none;
		}
		.related-card-skeleton {
			animation: none;
			background: var(--skeleton-bg-static);
		}
	}
</style>
