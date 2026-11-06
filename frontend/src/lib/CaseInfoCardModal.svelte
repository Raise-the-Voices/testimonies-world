<!--
	CaseInfoCardModal — the interactive "Case Information Card".

	Wraps <CaseInfoCard> in the app's shared modal shell, so the focus
	trap, Escape-to-close, backdrop click, body scroll lock and focus
	restore all come from <Modal> rather than being re-implemented.

	The card itself carries no controls: the close button lives here,
	overlapping the card's top corner, so the card stays a clean sheet
	that could be captured as an image without any UI chrome on it.

	The card is built from the MASKED payload the server returns for
	this case — GET /api/persons/{id}/card/ — and never from the
	person record the page already holds. The card is the artefact that
	leaves the platform, so what may appear on it is decided by the
	consent flags on the case, on the server. See
	backend/cases/card/serializers.py.
-->
<script lang="ts">
	import Modal from './Modal.svelte';
	import CaseInfoCard from './CaseInfoCard.svelte';
	import Icon from './Icon.svelte';
	import Skeleton from './Skeleton.svelte';
	import ErrorState from './ErrorState.svelte';
	import { buildCaseCardData, type CaseCardPayload } from './caseCardData';
	import { personsCardRetrieve } from '$lib/api/generated/endpoints';
	import type { CaseCardPayload as GeneratedCaseCardPayload } from '$lib/api/generated/endpoints.schemas';
	import { asBody } from '$lib/api/drfCompat';
	import { normaliseError } from '$lib/api/handleError';

	let {
		open,
		personId,
		onClose,
	}: {
		open: boolean;
		personId: number | null;
		onClose: () => void;
	} = $props();

	let payload = $state<CaseCardPayload | null>(null);
	let loading = $state(false);
	let error = $state('');
	/** Bumped by the Retry button to re-run the fetch. */
	let attempt = $state(0);

	$effect(() => {
		const id = personId;
		// Read `attempt` so a retry re-runs this effect.
		void attempt;

		if (!open || id == null) {
			payload = null;
			error = '';
			loading = false;
			return;
		}

		let cancelled = false;
		loading = true;
		error = '';
		personsCardRetrieve(id)
			.then((res) => {
				if (cancelled) return;
				// The generated client is typed as `{ data, status,
				// headers }`, but the shared mutator hands back the raw
				// DRF body — `asBody` reconciles the two.
				payload = asBody<GeneratedCaseCardPayload>(res);
				loading = false;
			})
			.catch((e) => {
				if (cancelled) return;
				payload = null;
				loading = false;
				error = normaliseError(e).message || 'Could not load the case card.';
			});

		return () => {
			cancelled = true;
		};
	});

	let data = $derived(payload ? buildCaseCardData(payload) : null);
</script>

{#if open}
	<Modal
		open={open}
		variant="poster"
		ariaLabel="Case information card"
		onClose={onClose}
	>
		<div class="case-card-modal">
			<button
				type="button"
				class="case-card-modal-close"
				aria-label="Close case information card"
				onclick={onClose}
			>
				<Icon name="x" size={18} strokeWidth={2.5} />
			</button>
			{#if loading}
				<!-- The card's own geometry, so the sheet does not jump
				     when the payload lands. -->
				<div class="case-card-skeleton" aria-hidden="true">
					<div class="case-card-skeleton-header">
						<Skeleton variant="text" width="7rem" />
						<Skeleton variant="text" width="5rem" />
					</div>
					<div class="case-card-skeleton-title">
						<Skeleton variant="text" width="60%" height="2rem" />
					</div>
					<div class="case-card-skeleton-rows">
						{#each [0, 1, 2, 3, 4, 5] as row (row)}
							<div class="case-card-skeleton-row">
								<Skeleton variant="text" width="5rem" />
								<Skeleton variant="text" width="55%" />
							</div>
						{/each}
					</div>
				</div>
			{:else if error}
				<ErrorState
					error={error}
					title="Could not load the case card"
					onRetry={() => (attempt += 1)}
				/>
			{:else if data}
				<CaseInfoCard data={data} />
			{/if}
		</div>
	</Modal>
{/if}

<style>
	/* Sized to the card so the close button sits on the card's own
	   corner rather than on the dialog's.

	   The width is explicit rather than `fit-content`: the card inside
	   is a size container, and a size container contributes nothing to
	   its parent's intrinsic width — `fit-content` would collapse the
	   whole card to zero. */
	.case-card-modal {
		position: relative;
		width: min(100%, var(--card-poster-width));
		margin-inline: auto;
	}

	.case-card-modal-close {
		position: absolute;
		/* The button straddles the card's top-right corner: mostly
		   above it, so it never covers the header's date. The modal's
		   top padding (see Modal.svelte) reserves the room it needs. */
		top: -2.5rem;
		right: -0.75rem;
		z-index: 2;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		/* WCAG 2.5.5 — the app's own minimum target size, the same
		   floor .btn uses. */
		width: 44px;
		height: 44px;
		padding: 0;
		border-radius: 50%;
		border: 1px solid var(--color-text);
		background: var(--color-bg-white);
		color: var(--color-text);
		transition:
			background var(--transition-card),
			color var(--transition-card);
	}
	.case-card-modal-close:hover {
		background: var(--color-text);
		color: var(--color-text-light);
	}

	/* The loading state mirrors the card's geometry: a ruled header, a
	   title band, and the metadata rows. It keeps the sheet from
	   resizing when the payload lands. */
	.case-card-skeleton {
		background: var(--color-bg-white);
		border: 2px solid var(--color-text);
		border-radius: var(--radius-card-poster);
		padding: 0.85em 0.9em 0.95em;
	}
	.case-card-skeleton-header {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		padding-bottom: 0.6em;
		border-bottom: 2px solid var(--color-text);
	}
	.case-card-skeleton-title {
		padding: 0.85em 0 0.7em;
	}
	.case-card-skeleton-rows {
		display: grid;
		gap: 0.5em;
	}
	.case-card-skeleton-row {
		display: grid;
		grid-template-columns: 8em 1fr;
		gap: 0.5em;
		align-items: baseline;
		padding: 0.5em 0;
		border-bottom: 1px solid var(--color-border-subtle);
	}
	.case-card-skeleton-row:last-child {
		border-bottom: none;
	}
</style>
