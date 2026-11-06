<!--
	CaseInfoCard — the case card as a poster.

	Presentational only: it takes already-resolved data and renders it.
	The mapping from a Person record to that data lives in
	`caseCardData.ts` so it can be unit-tested without a DOM.

	Layout (the "Modern Infographic Poster / Dossier" layout):

	  ┌────────────────────────────────────────┐
	  │ REF: ED-2026-0042          14 Mar 2026 │  header
	  ├────────────────────────────────────────┤
	  │ AHMED AL-HASSAN                        │  title (red, uppercase)
	  │ DISAPPEARED                            │  status
	  ├──────────────────┬─────────────────────┤
	  │  ┌────────────┐  │ AGE       34        │
	  │  │ photograph │  │ RESIDENCE Alexandria│
	  │  └────────────┘  │ PROFESSION Teacher   │
	  │                  │ FATHER    Yusuf      │
	  ├──────────────────┴─────────────────────┤
	  └────────────────────────────────────────┘

	The card carries no close button, no download button and no other
	control — it is the artefact, and the modal that frames it supplies
	those. That keeps the card renderable on its own (an image export
	would capture exactly this).

	Scale: everything inside the card is sized in `em` against
	`--card-base-font`, so the same markup renders at 14px on screen and
	at 28px for an export without a second stylesheet.
-->
<script lang="ts">
	import type { CaseCardData } from './caseCardData';

	let { data }: { data: CaseCardData } = $props();

	// The photograph is the only element that can fail after the data
	// has already loaded — a media URL that has since been removed, or
	// a file the browser cannot decode.
	let photoFailed = $state(false);

	// Reset when the card is re-pointed at a different person.
	$effect(() => {
		data.photo?.src;
		photoFailed = false;
	});

	// A case with no photograph gets no photograph column. An empty
	// frame would be a large blank rectangle on a poster whose whole
	// job is to state facts — the facts list reads better across the
	// full width instead.
	let showPhoto = $derived(!!data.photo && !photoFailed);
</script>

<div class="case-card-wrap">
	<article class="case-card" aria-labelledby="case-card-title">
		<header class="case-card-header">
			<span class="case-card-ref">
				{#if data.reference}
					Ref: {data.reference}
				{:else}
					Ref: Not assigned
				{/if}
			</span>
			{#if data.date}
				<span class="case-card-date">{data.date}</span>
			{/if}
		</header>

		<div class="case-card-title-block">
			<h3 class="case-card-title" id="case-card-title">{data.title}</h3>
			{#if data.statusLabel}
				<p class="case-card-status">{data.statusLabel}</p>
			{/if}
		</div>

		<div class="case-card-body" class:case-card-body--full={!showPhoto}>
			{#if showPhoto}
				<div class="case-card-photo-column">
					<div class="case-card-photo-frame">
						<img
							class="case-card-photo"
							src={data.photo!.src}
							alt={data.photo!.alt}
							onerror={() => (photoFailed = true)}
						/>
					</div>
				</div>
			{/if}

			<dl class="case-card-meta">
				{#each data.rows as row (row.label)}
					<div class="case-card-meta-row">
						<dt class="case-card-meta-label">{row.label}</dt>
						<dd class="case-card-meta-value">{row.value}</dd>
					</div>
				{/each}
			</dl>
		</div>
	</article>
</div>

<style>
	/* The wrap is the sizing container for the card. The card is a
	   fixed 540px sheet on wide screens and shrinks to the container
	   below that; the container query below collapses the two-column
	   body when the card gets narrow — for a phone, or for the card
	   moving into a sidebar later. */
	.case-card-wrap {
		container-type: inline-size;
		margin-inline: auto;
		width: 100%;
	}

	.case-card {
		font-size: var(--card-base-font);
		width: var(--card-poster-width);
		max-width: 100%;
		margin-inline: auto;
		background: var(--color-bg-white);
		border: 2px solid var(--color-text);
		border-radius: var(--radius-card-poster);
		color: var(--color-text);
		box-shadow: var(--shadow-card-lg);
		overflow: hidden;
	}

	/* --- header --------------------------------------------------- */
	.case-card-header {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: 1em;
		/* The top padding is generous so the close control that
		   overlaps the card's top-right corner (in the modal) never
		   reaches the header's text. */
		padding: 0.85em 0.9em 0.6em;
		border-bottom: 2px solid var(--color-text);
		font-size: 0.78em;
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}
	.case-card-ref {
		font-weight: 700;
	}
	.case-card-date {
		font-weight: 700;
		color: var(--color-text-muted);
		white-space: nowrap;
	}

	/* --- title ---------------------------------------------------- */
	.case-card-title-block {
		padding: 0.85em 0.9em 0.7em;
	}
	.case-card-title {
		margin: 0;
		font-size: 2.4em;
		line-height: 1.06;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.01em;
		/* --color-danger on white is 5.06:1 — passes AA for large
		   text. Red is for the title only; body copy stays on
		   --color-text. */
		color: var(--color-danger);
		overflow-wrap: anywhere;
	}
	.case-card-status {
		margin: 0.3em 0 0;
		font-size: 0.92em;
		font-weight: 700;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--color-text);
	}

	/* --- body ----------------------------------------------------- */
	.case-card-body {
		display: grid;
		grid-template-columns: 38% 1fr;
		gap: 1.1em;
		padding: 0 0.9em 0.95em;
	}

	/* No photograph: the facts take the whole sheet. */
	.case-card-body--full {
		grid-template-columns: 1fr;
	}

	.case-card-photo-frame {
		border: 2px solid var(--color-text);
		padding: 0.35em;
		background: var(--color-bg-white);
	}
	.case-card-photo {
		display: block;
		width: 100%;
		aspect-ratio: 3 / 4;
		object-fit: cover;
		object-position: center 20%;
	}

	/* --- metadata -------------------------------------------------
	   A ruled list, not a stack of boxes. The rules are hairlines and
	   the rows are flat, so the card reads as one sheet. */
	.case-card-meta {
		margin: 0;
		display: grid;
		align-content: start;
	}
	.case-card-meta-row {
		display: grid;
		grid-template-columns: 8em 1fr;
		gap: 0.5em;
		align-items: baseline;
		padding: 0.5em 0;
		border-bottom: 1px solid var(--color-border-subtle);
	}
	.case-card-meta-row:last-child {
		border-bottom: none;
	}
	.case-card-meta-label {
		margin: 0;
		font-size: 0.72em;
		font-weight: 700;
		letter-spacing: 0.09em;
		text-transform: uppercase;
		color: var(--color-text-muted);
	}
	.case-card-meta-value {
		margin: 0;
		font-size: 1em;
		overflow-wrap: anywhere;
	}

	/* Narrow card (phone, or a sidebar later): the photograph moves
	   above the list and the label column gets the full width. */
	@container (max-width: 480px) {
		.case-card-body {
			grid-template-columns: 1fr;
		}
		.case-card-photo {
			aspect-ratio: 16 / 9;
		}
		.case-card-meta-row {
			grid-template-columns: 7em 1fr;
		}
	}
</style>
