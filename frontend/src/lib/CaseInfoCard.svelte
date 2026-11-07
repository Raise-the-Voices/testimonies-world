<!--
	CaseInfoCard — the case card as a poster.

	Presentational only: it takes already-resolved data and renders it.
	The mapping from a Person record to that data lives in
	`caseCardData.ts` so it can be unit-tested without a DOM.

	Layout (the editorial dossier):

	  ┌────────────────────────────────────────┐
	  │ REF: ED-2026-0042         2 FEB 2026   │  reference bar
	  ├────────────────────────────────────────┤
	  │ ENFORCED DISAPPEARANCE                  │  category line
	  │ AHMED AL-HASSAN                        │  headline
	  │ DISAPPEARED                             │  status
	  ├──────────────────┬─────────────────────┤
	  │  ┌────────────┐  │ AGE:        34      │
	  │  │ photograph │  │ RESIDENCE:  Alex…  │
	  │  └────────────┘  │ FATHER:     Yusuf   │
	  ├──────────────────┴─────────────────────┤
	  │ #EnforcedDisappearance   Testimonies…  │  footer
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

	// The footer signature. Text, not a logo: the project ships no
	// logo asset, and the sheet is a document rather than a badge.
	const SIGNATURE = 'Testimonies.world · cases.raisethevoices.org';
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
			{#if data.category}
				<p class="case-card-category">{data.category}</p>
			{/if}
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

		<footer class="case-card-footer">
			{#if data.hashtags.length > 0}
				<ul class="case-card-tags">
					{#each data.hashtags as tag (tag)}
						<li class="case-card-tag">{tag}</li>
					{/each}
				</ul>
			{/if}
			<p class="case-card-brand">{SIGNATURE}</p>
		</footer>
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

	/* The sheet: warm paper, a sharp dark edge, and the brand accent
	   line along the top. Square corners — a dossier sheet has no
	   rounded corners. */
	.case-card {
		font-size: var(--card-base-font);
		width: var(--card-poster-width);
		max-width: 100%;
		margin-inline: auto;
		color: var(--color-text);
		background-color: var(--color-card-paper);
		background-image: var(--card-paper-wash), var(--card-paper-grain);
		border: 1px solid var(--color-text);
		border-top: 4px solid var(--color-primary);
		border-radius: var(--radius-card-poster);
		box-shadow: var(--shadow-card-lg);
		overflow: hidden;
	}

	/* --- reference bar ---------------------------------------------- */
	.case-card-header {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: 1em;
		/* The top padding is generous so the close control that
		   overlaps the card's top-right corner (in the modal) never
		   reaches the header's text. */
		padding: 0.7em 1.1em 0.55em;
		border-bottom: 2px solid var(--color-text);
		font-family: var(--font-mono);
		font-size: 0.78em;
		letter-spacing: 0.14em;
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

	/* --- title ------------------------------------------------------ */
	.case-card-title-block {
		padding: 1.05em 1.1em 0.95em;
	}
	/* The case category the poster leads with. */
	.case-card-category {
		margin: 0 0 0.4em;
		font-size: 0.78em;
		font-weight: 700;
		letter-spacing: 0.24em;
		text-transform: uppercase;
		color: var(--color-primary);
	}
	.case-card-title {
		margin: 0;
		font-size: 2.5em;
		line-height: 1.05;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.01em;
		/* --color-primary on the paper tone is 6.4:1 — passes AA for
		   body text and comfortably for large text. */
		color: var(--color-primary);
		text-decoration: underline;
		text-decoration-thickness: 0.09em;
		text-underline-offset: 0.16em;
		text-decoration-color: var(--color-primary);
		overflow-wrap: anywhere;
	}
	.case-card-status {
		margin: 0.55em 0 0;
		font-size: 0.95em;
		font-weight: 700;
		letter-spacing: 0.2em;
		text-transform: uppercase;
		/* --color-danger on the paper tone is 4.9:1 — passes AA for
		   body text. Red states the case's condition; everything else
		   on the sheet stays on the brand teal or the ink. */
		color: var(--color-danger);
	}

	/* --- body ------------------------------------------------------- */
	.case-card-body {
		display: grid;
		grid-template-columns: 38% 1fr;
		gap: 1.2em;
		padding: 0 1.1em 1.1em;
	}

	/* No photograph: the facts take the whole sheet. */
	.case-card-body--full {
		grid-template-columns: 1fr;
	}

	.case-card-photo-frame {
		border: 2px solid var(--color-primary);
		padding: 0.4em;
		background: var(--color-card-paper);
	}
	.case-card-photo {
		display: block;
		width: 100%;
		aspect-ratio: 3 / 4;
		object-fit: cover;
		object-position: center 20%;
	}

	/* --- metadata ---------------------------------------------------
	   A ruled list, not a stack of boxes. The rules are hairlines and
	   the rows are flat, so the card reads as one sheet. */
	.case-card-meta {
		margin: 0;
		display: grid;
		align-content: start;
	}
	.case-card-meta-row {
		display: grid;
		grid-template-columns: 9.6em 1fr;
		gap: 0.55em;
		align-items: baseline;
		padding: 0.55em 0;
		border-bottom: 1px solid var(--color-border-subtle);
	}
	.case-card-meta-row:last-child {
		border-bottom: none;
	}
	.case-card-meta-label {
		margin: 0;
		font-size: 0.68em;
		font-weight: 700;
		letter-spacing: 0.07em;
		text-transform: uppercase;
		color: var(--color-primary);
	}
	/* The dossier's label colon. Punctuation, not content — it stays
	   out of the DOM text so the label itself is still plain. */
	.case-card-meta-label::after {
		content: ':';
	}
	.case-card-meta-value {
		margin: 0;
		font-size: 1em;
		overflow-wrap: anywhere;
	}

	/* --- footer ----------------------------------------------------- */
	.case-card-footer {
		border-top: 2px solid var(--color-text);
		padding: 0.8em 1.1em 1em;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 0.6em 1em;
	}
	.case-card-tags {
		display: flex;
		flex-wrap: wrap;
		gap: 0.45em;
		margin: 0;
		padding: 0;
	}
	.case-card-tag {
		font-size: 0.78em;
		font-weight: 700;
		letter-spacing: 0.05em;
		text-transform: uppercase;
		color: var(--color-primary);
		background: var(--color-primary-tint);
		border: 1px solid var(--color-primary);
		padding: 0.2em 0.55em;
	}
	.case-card-brand {
		margin: 0 0 0 auto;
		font-size: 0.75em;
		letter-spacing: 0.06em;
		color: var(--color-text-muted);
		white-space: nowrap;
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
			grid-template-columns: 8.5em 1fr;
		}
	}
</style>
