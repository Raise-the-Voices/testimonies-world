<!--
	CaseInfoCardModal — the interactive "Case Information Card".

	Wraps <CaseInfoCard> in the app's shared modal shell, so the focus
	trap, Escape-to-close, backdrop click, body scroll lock and focus
	restore all come from <Modal> rather than being re-implemented.

	The card itself carries no controls: the close button lives here,
	overlapping the card's top corner, so the card stays a clean sheet
	that could be captured as an image without any UI chrome on it.
-->
<script lang="ts">
	import Modal from './Modal.svelte';
	import CaseInfoCard from './CaseInfoCard.svelte';
	import Icon from './Icon.svelte';
	import { buildCaseCardData, type CaseCardPerson } from './caseCardData';

	let {
		open,
		person,
		onClose,
	}: {
		open: boolean;
		person: CaseCardPerson | null;
		onClose: () => void;
	} = $props();

	let data = $derived(person ? buildCaseCardData(person) : null);
	let show = $derived(open && data !== null);
</script>

{#if show}
	<Modal
		open={show}
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
			<CaseInfoCard data={data!} />
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
</style>
