<!--
	CaseInfoCard — the case card as a poster.

	Presentational only: it takes already-resolved data and renders it.
	The mapping from a Person record to that data lives in
	`caseCardData.ts` so it can be unit-tested without a DOM; the
	mapping from the server's masked publication payload lives in
	`caseCardPayload.ts`. Both produce the same shape, so this one
	component draws both.

	Layout (the editorial dossier):

	  ┌──────────────────────────────────────────────┐
	  │ REF: ED-2026-0042              7 NOV 2026   │  reference bar
	  ├──────────────────────────────────────────────┤
	  │ ENFORCED DISAPPEARANCE                        │  headline
	  │ [ DISAPPEARED ]                               │  status badge
	  ├───────────────────────┬──────────────────────┤
	  │  ┌─────────────────┐  │ NAME:            A…  │
	  │  │                 │  │ FATHER NAME:     Y…  │
	  │  │   [ photograph] │  │ AGE:                │
	  │  │                 │  │ RESIDENCE (R/O):    │
	  │  └─────────────────┘  │ PROFESSION:         │
	  ├───────────────────────┴──────────────────────┤
	  │ #EnforcedDisappearance   Testimonies.world…  │  footer
	  └──────────────────────────────────────────────┘

	The card carries no close button, no download button and no other
	control — it is the artefact. The modal that frames it supplies
	those, so the sheet can be captured as an image without any UI
	chrome on it.

	Scale: everything inside the card is sized in `em` against
	`--card-base-font`, so the same markup renders at 16px on screen
	(720px wide) and at 24px for the export (1080px wide) without a
	second stylesheet.
-->
<script lang="ts">
	import { base } from '$app/paths';
	import Icon from './Icon.svelte';
	import { sameOriginMediaUrl } from './caseCardExport';
	import type { CaseCardData } from './caseCardData';

	let {
		data,
		variant = 'screen',
	}: { data: CaseCardData; variant?: 'screen' | 'export' } = $props();

	// The photograph is the only element that can fail after the data
	// has already loaded — a media URL that has since been removed, or
	// a file the browser cannot decode.
	let photoFailed = $state(false);

	// Reset when the card is re-pointed at a different person.
	$effect(() => {
		data.photo?.src;
		photoFailed = false;
	});

	// What the frame says. A case file with no photograph and a
	// photograph that will not load are different facts, and the sheet
	// is a publication: it must not claim a photograph is missing when
	// one is on file.
	const photoNote = $derived(photoFailed ? 'Photograph unavailable' : 'No photograph');

	// The photograph is pulled onto the page's own origin: the export
	// reads its pixels into a canvas, and a canvas that has drawn a
	// cross-origin image cannot be written out. See caseCardExport.ts.
	const photoSrc = $derived(
		data.photo && typeof window !== 'undefined'
			? sameOriginMediaUrl(data.photo.src, window.location.origin, base)
			: (data.photo?.src ?? null),
	);

	// The footer signature. Text, not a logo: the project ships no
	// logo asset, and the sheet is a document rather than a badge.
	const SIGNATURE = 'Testimonies.world · cases.raisethevoices.org';

	// Unique per instance: the export renders a second, off-screen copy
	// of this card, and two elements with the same id would make the
	// label point at the wrong one.
	const uid = $props.id();
	const titleId = `case-card-title-${uid}`;
</script>

<div class="case-card-wrap">
	<article class="case-card" class:case-card--export={variant === 'export'} aria-labelledby={titleId}>
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
			<h3 class="case-card-title" id={titleId}>{data.title}</h3>
			{#if data.statusLabel}
				<p class="case-card-status">{data.statusLabel}</p>
			{/if}
		</div>

		<div class="case-card-body">
			<div class="case-card-photo-column">
				<div class="case-card-photo-frame">
					{#if photoSrc && !photoFailed}
						<img
							class="case-card-photo"
							src={photoSrc}
							alt={data.photo?.alt ?? ''}
							onerror={() => (photoFailed = true)}
						/>
					{:else}
						<!-- No photograph on the case file, or one that will
						     not load: a quiet block in the frame's place,
						     not a broken image and not an empty gap. -->
						<div class="case-card-photo-placeholder">
							<Icon name="people" size={40} strokeWidth={1.5} />
							<span>{photoNote}</span>
						</div>
					{/if}
				</div>
			</div>

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
	   fixed 720px sheet on wide screens and shrinks to the container
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

	/* The export copy of the card: the same sheet at poster scale.
	   Both the base font AND the width are overridden — a custom
	   property is substituted where it is used, but it is resolved
	   against the element that DECLARES it, so the width token has to
	   be re-pointed at the export scale too, or the sheet would be
	   exported at screen size. */
	.case-card--export {
		--card-base-font: var(--card-base-font-export);
		--card-poster-width: var(--card-poster-width-export);
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
		padding: 0.75em 1.25em 0.6em;
		border-bottom: 2px solid var(--color-text);
		font-family: var(--font-mono);
		font-size: 0.8em;
		letter-spacing: 0.14em;
		text-transform: uppercase;
	}
	.case-card-ref {
		font-weight: 700;
		/* A reference is one string. It is never split across two
		   lines in the middle of the number. */
		white-space: nowrap;
	}
	.case-card-date {
		font-weight: 700;
		color: var(--color-text-muted);
		white-space: nowrap;
	}

	/* --- title ------------------------------------------------------ */
	.case-card-title-block {
		padding: 1.15em 1.25em 1.05em;
	}
	.case-card-title {
		margin: 0;
		font-size: 2.6em;
		line-height: 1.04;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.01em;
		/* --color-primary on the paper tone is 6.4:1 — passes AA for
		   body text and comfortably for large text. */
		color: var(--color-primary);
		text-decoration: underline;
		text-decoration-thickness: 0.08em;
		text-underline-offset: 0.14em;
		text-decoration-color: var(--color-primary);
		/* A long heading breaks at a hyphen if the browser can find
		   one, and at the last resort inside the word — but never
		   past the edge of the sheet. */
		hyphens: auto;
		overflow-wrap: break-word;
	}

	/* The case's condition, as a stamp on the sheet. */
	.case-card-status {
		display: inline-block;
		margin: 0.75em 0 0;
		padding: 0.3em 0.75em;
		font-size: 0.95em;
		font-weight: 700;
		letter-spacing: 0.18em;
		text-transform: uppercase;
		color: var(--color-danger-text-strong);
		background: var(--color-danger-bg);
		border: 1px solid var(--color-danger-border);
		border-radius: var(--radius-card-poster);
	}

	/* --- body ------------------------------------------------------- */
	.case-card-body {
		display: grid;
		grid-template-columns: 38% 1fr;
		gap: 1.4em;
		padding: 1.2em 1.25em 1.3em;
		border-top: 2px solid var(--color-text);
	}

	/* The column is a flex container so the frame can take the full
	   height of the row: the photograph stands as tall as the list of
	   facts beside it, in portrait. */
	.case-card-photo-column {
		display: flex;
	}

	.case-card-photo-frame {
		/* The frame fills the height of the facts column. The floor
		   keeps it from collapsing to a sliver when a case has only
		   one or two facts. */
		flex: 1;
		min-height: 12em;
		border: 2px solid var(--color-primary);
		padding: 0.45em;
		background: var(--color-card-paper);
	}
	.case-card-photo {
		display: block;
		width: 100%;
		height: 100%;
		object-fit: cover;
		object-position: center 20%;
	}
	.case-card-photo-placeholder {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.6em;
		width: 100%;
		height: 100%;
		min-height: 11em;
		color: var(--color-text-muted);
		/* An empty slot, matted on the sheet — not a grey box dropped
		   onto it. The frame's own rule is the picture's edge; this is
		   the mat inside it. */
		background: var(--color-card-paper);
		border: 1px solid var(--color-card-rule);
	}
	/* The icon is a child component, so its <svg> carries no scope
	   class of this component's own. */
	.case-card-photo-placeholder :global(svg) {
		width: 2.6em;
		height: 2.6em;
	}
	.case-card-photo-placeholder span {
		font-size: 0.75em;
		letter-spacing: 0.08em;
		text-transform: uppercase;
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
		/* The label column is wide enough for the longest label on the
		   poster ("PLACE OF ABDUCTION:") without wrapping. */
		grid-template-columns: 11em 1fr;
		gap: 0.6em;
		align-items: baseline;
		padding: 0.5em 0;
		border-bottom: 1px solid var(--color-card-rule);
	}
	.case-card-meta-row:last-child {
		border-bottom: none;
	}
	.case-card-meta-label {
		margin: 0;
		font-size: 0.78em;
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
		font-size: 1.1em;
		overflow-wrap: anywhere;
	}

	/* --- footer ----------------------------------------------------- */
	.case-card-footer {
		border-top: 2px solid var(--color-text);
		padding: 0.9em 1.25em 1.1em;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 0.6em 1em;
	}
	.case-card-tags {
		display: flex;
		flex-wrap: wrap;
		/* The row takes the room the signature leaves, rather than
		   claiming its own width and leaving the two to compete for
		   the last pixel. Two flex items that exactly fill a row can
		   land on either side of a line break in two copies of the
		   same sheet — and the exported file is a copy. */
		flex: 1 1 0;
		min-width: 0;
		gap: 0.45em;
		margin: 0;
		padding: 0;
	}
	.case-card-tag {
		font-size: 0.8em;
		font-weight: 700;
		letter-spacing: 0.05em;
		text-transform: uppercase;
		color: var(--color-primary);
		background: var(--color-primary-tint);
		border: 1px solid var(--color-primary);
		padding: 0.2em 0.55em;
	}
	.case-card-brand {
		flex: 0 0 auto;
		margin: 0;
		font-size: 0.8em;
		letter-spacing: 0.06em;
		color: var(--color-text-muted);
		white-space: nowrap;
	}

	/* Narrow card (phone, or a sidebar later): the photograph moves
	   above the list, and each fact stacks its label over its value —
	   two columns of type would leave neither of them room. The frame
	   stays portrait, as it is on the wide sheet. */
	@container (max-width: 560px) {
		/* The heading comes down to the size the narrow sheet can
		   hold: at the poster's scale the longest word runs past the
		   edge and breaks in the wrong place. */
		.case-card-title {
			font-size: 2.1em;
		}
		/* The reference keeps its own line, the date takes the right
		   of the one below it. */
		.case-card-header {
			flex-wrap: wrap;
			row-gap: 0.25em;
		}
		.case-card-date {
			margin-left: auto;
		}
		.case-card-body {
			grid-template-columns: 1fr;
		}
		.case-card-photo-frame {
			/* The frame is as tall as the photograph now, so the floor
			   that keeps it from collapsing would leave a gap. */
			min-height: 0;
		}
		.case-card-photo {
			height: auto;
			aspect-ratio: 3 / 4;
		}
		.case-card-photo-placeholder {
			height: auto;
			aspect-ratio: 3 / 4;
			min-height: 0;
		}
		.case-card-meta-row {
			grid-template-columns: 1fr;
			gap: 0.2em;
		}
	}

	/* The export copy is laid out at a fixed width, so it never
	   collapses: a clone inside an SVG foreignObject has no reliable
	   container size for the query above to measure. */
	.case-card--export .case-card-body {
		grid-template-columns: 38% 1fr;
	}
	.case-card--export .case-card-photo {
		height: 100%;
		aspect-ratio: auto;
	}
</style>
