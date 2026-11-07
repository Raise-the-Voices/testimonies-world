<!--
	CaseInfoCardModal — the interactive "Case Information Card".

	Wraps <CaseInfoCard> in the app's shared modal shell, so the focus
	trap, Escape-to-close, backdrop click, body scroll lock and focus
	restore all come from <Modal> rather than being re-implemented.

	The card itself carries no controls: the close button lives here,
	overlapping the card's top corner, so the card stays a clean sheet
	that can be captured as an image without any UI chrome on it.

	The Download button lives here too — below the sheet, never inside
	it — for the same reason.

	What the poster may show is the server's decision, not the
	browser's: when the card opens, the masked card payload
	(`GET /api/persons/{id}/card/`) is fetched, and the button is only
	live when that payload says the case is cleared for publication.
	See `docs/case-info-card-architecture.md` §3.7.
-->
<script lang="ts">
	import Modal from './Modal.svelte';
	import CaseInfoCard from './CaseInfoCard.svelte';
	import Icon from './Icon.svelte';
	import { getCaseCard } from './api';
	import { buildCaseCardData, type CaseCardPerson } from './caseCardData';
	import { downloadPoster, posterFilename, renderPosterPng } from './caseCardExport';
	import { buildCardDataFromPayload } from './caseCardPayload';
	import { publicationBlocker } from './caseCardPublication';
	import type { CaseCardPayload } from './api/generated/endpoints.schemas';

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
	let personId = $derived(person?.id ?? null);

	/** What the server said about the case's publication status. */
	type Gate = 'checking' | 'ready' | 'blocked' | 'unavailable';
	let gate = $state<Gate>('checking');
	let payload = $state<CaseCardPayload | null>(null);
	let exportError = $state<string | null>(null);
	let exporting = $state(false);
	let exportHost = $state<HTMLElement | null>(null);

	// Ask the server what this case may be published as. The answer
	// gates the download; the browser does not decide.
	$effect(() => {
		if (!show || personId === null) return;
		let cancelled = false;
		gate = 'checking';
		payload = null;
		exportError = null;

		getCaseCard(personId)
			.then((card) => {
				if (cancelled) return;
				payload = card;
				gate = card.exportable ? 'ready' : 'blocked';
			})
			.catch(() => {
				if (cancelled) return;
				gate = 'unavailable';
			});

		return () => {
			cancelled = true;
		};
	});

	// The poster that gets exported: the masked payload, laid out by
	// the same component that draws the card on screen.
	const exportData = $derived(payload ? buildCardDataFromPayload(payload) : null);

	// Why the case is not cleared, read from the case file the advocate
	// is looking at. The server still decides — this only says which
	// field to go and set.
	const blocker = $derived(person ? publicationBlocker(person) : null);

	const gateNote = $derived.by(() => {
		switch (gate) {
			case 'checking':
				return 'Checking publication status…';
			case 'ready':
				return 'The poster carries only the fields cleared for publication.';
			case 'blocked':
				return blocker
					? `Publication not approved — ${blocker}.`
					: 'Publication not approved for this case.';
			case 'unavailable':
				return 'Publication status unavailable — the poster cannot be exported.';
		}
	});

	async function onDownload() {
		if (!payload || exporting || gate !== 'ready') return;
		exporting = true;
		exportError = null;
		try {
			// The sheet that gets captured is the off-screen copy below —
			// the same component at poster scale.
			const sheet = exportHost?.querySelector('.case-card');
			if (!sheet) throw new Error('The poster was not rendered.');
			const dataUrl = await renderPosterPng(sheet as HTMLElement);
			await downloadPoster(dataUrl, posterFilename(payload.reference));
		} catch (error) {
			console.error('Case poster export failed', error);
			exportError =
				'The poster could not be exported. Try again, or ask the documentation officer to check the case file.';
		} finally {
			exporting = false;
		}
	}
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

			<div class="case-card-export">
				<button
					type="button"
					class="btn btn-primary case-card-download"
					disabled={gate !== 'ready' || exporting}
					onclick={onDownload}
				>
					<Icon name="download" size={16} />
					<span>{exporting ? 'Preparing the poster…' : 'Download poster (PNG)'}</span>
				</button>
				<p class="case-card-export-note" class:case-card-export-note--error={exportError}>
					{exportError ?? gateNote}
				</p>
			</div>
		</div>
	</Modal>

	<!--
		The export copy of the sheet: the same component, at poster
		scale, laid out off-screen so the browser can measure and
		capture it. It is a duplicate of the card above, so it is
		hidden from assistive technology — and it is only built when
		the case can actually be exported.
	-->
	{#if exportData && gate === 'ready'}
		<div class="case-card-export-host" aria-hidden="true" bind:this={exportHost}>
			<CaseInfoCard data={exportData} variant="export" />
		</div>
	{/if}
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
		border: 1px solid var(--color-primary);
		background: var(--color-primary);
		color: var(--color-text-light);
		box-shadow: var(--shadow-card-lg);
		transition:
			background var(--transition-card),
			border-color var(--transition-card);
	}
	.case-card-modal-close:hover {
		background: var(--color-primary-light);
		border-color: var(--color-primary-light);
		color: var(--color-text-light);
	}

	/* The export action, below the sheet — never inside it, so the
	   exported file carries the poster and nothing else. */
	.case-card-export {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 0.5rem;
		margin-top: 1.25rem;
	}
	.case-card-download {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
	}
	.case-card-download:disabled {
		background: var(--color-border-light);
		color: var(--color-text-muted);
		cursor: not-allowed;
	}
	.case-card-download:disabled:hover {
		background: var(--color-border-light);
		color: var(--color-text-muted);
	}
	.case-card-export-note {
		margin: 0;
		font-size: 0.85rem;
		color: var(--color-text-muted);
	}
	.case-card-export-note--error {
		color: var(--color-danger-text-strong);
	}

	/* The off-screen poster. Fixed so it never affects the layout of
	   the page, and parked far to the left so it is never seen. It
	   stays laid out (not hidden) because the capture measures the
	   element it is given. */
	.case-card-export-host {
		position: fixed;
		top: 0;
		left: -20000px;
		width: var(--card-poster-width-export);
		pointer-events: none;
	}
</style>
