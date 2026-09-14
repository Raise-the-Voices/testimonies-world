<!--
	WorkflowActions — role-aware action bar for a single testimonial.

	Surfaces the state-machine transitions (submit / approve / reject /
	publish / archive / re-submit) and the "Edit draft →" affordance for
	the current viewer. Server is the source of truth for authorization
	— we render the buttons the viewer *might* be allowed to use, and
	let the backend reject with a typed 400/403 if the row state or
	ownership doesn't match. Errors surface inline so the user gets
	unambiguous feedback (the same silent-failure UX the queue page
	fixes for the Review queue tab on /testimonials).

	The shape is consistent with the Review queue tab on
	/testimonials:
	  - one in-flight action at a time (`busy` guard)
	  - 4-second auto-dismiss success banner
	  - inline reject modal (notes required, same contract as backend)
	  - error banner stays until user dismisses
-->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import {
		testimonialsSubmitCreate,
		testimonialsApproveCreate,
		testimonialsRejectCreate,
		testimonialsPublishCreate,
		testimonialsArchiveCreate,
		testimonialsRetrieve,
	} from '$lib/api/generated/endpoints';
	import type { TestimonialPublic } from '$lib/api/generated/endpoints.schemas';
	import { isAdvocate } from '$lib/session';
	import Modal from '$lib/Modal.svelte';
	import { STATUS_LABEL } from '$lib/statusPresentation';
	import { showToast } from '$lib/toast';
	import type { User } from '$lib/types';

	/* Wire-shape extends TestimonialPublic with the workflow metadata
	   fields returned by `TestimonialInternalSerializer` (which is what
	   the backend returns for any authenticated GET). The fields are
	   in the JSON payload today; we widen the type here so the
	   workflow card can show the submit/review timestamps without a
	   separate fetch. Anonymous GETs use the public serializer and
	   don't include these — they don't need workflow either, since
	   the visibility gate filters the buttons below. */
	type WorkflowFields = {
		created_by?: number | null;
		submitted_at?: string | null;
		reviewed_at?: string | null;
		approved_at?: string | null;
		archived_at?: string | null;
		published_at?: string | null;
	};
	type Props = {
		testimonial: TestimonialPublic & WorkflowFields;
		currentUser: User;
		/* Called after a successful transition with the freshly-
		   fetched row payload, so the parent can re-render with
		   the new status. The component also re-fetches the row
		   internally to keep its own state in sync (status pill +
		   button set). The callback is the documented child-to-
		   parent state-refresh idiom — using `bind:` would force
		   the parent to give up its `derived` prop binding. */
		onUpdated?: (row: TestimonialPublic & WorkflowFields) => void;
	};

	let { testimonial, currentUser, onUpdated }: Props = $props();

	let id = $derived(testimonial.id);
	let status = $derived(testimonial.status);
	let isAuthed = $derived(currentUser.authenticated);
	let canReviewPublish = $derived(isAdvocate(currentUser));

	// In-flight guard + banners — same shape as the queue page.
	let busy = $state(false);
	let actionError = $state<string | null>(null);
	let actionSuccess = $state<string | null>(null);
	let actionSuccessTimer: ReturnType<typeof setTimeout> | null = null;

	// Inline reject modal state. Notes are required per the backend's
	// transition contract — see TestimonialViewSet.reject().
	let rejectOpen = $state(false);
	let rejectNotes = $state('');
	let rejectSaving = $state(false);

	/* The visibility matrix: which transitions are *plausible* for
	   the current viewer. Server is the authz boundary — a button
	   shown here is a hint, not a guarantee. The error banner
	   surfaces the real rejection.
	   - draft     : Volunteer can submit; Advocate+ same
	   - under_review: Advocate+ can approve or reject
	   - approved  : Advocate+ can publish
	   - published : Advocate+ can archive
	   - rejected  : Volunteer or Advocate+ can re-submit
	   - archived  : terminal (no transitions in this UI) */
	const visibleActions = $derived.by<readonly TransitionAction[]>(() => {
		if (!isAuthed) return [];
		switch (status) {
			case 'draft':
				return ['submit'];
			case 'under_review':
				return canReviewPublish ? ['approve', 'reject'] : [];
			case 'approved':
				return canReviewPublish ? ['publish'] : [];
			case 'published':
				return canReviewPublish ? ['archive'] : [];
			case 'rejected':
				return ['submit'];
			case 'archived':
				return [];
			default:
				return [];
		}
	});

	// Friendly labels for the action buttons + success banner copy.
	// Mirrors the queue page's ACTION_LABEL map so copy stays
	// consistent across surfaces.
	type TransitionAction = 'submit' | 'approve' | 'reject' | 'publish' | 'archive';
	const ACTION_LABEL: Record<TransitionAction, string> = {
		submit: 'Submit for review',
		approve: 'Approve',
		reject: 'Reject…',
		publish: 'Publish',
		archive: 'Archive',
	};
	const ACTION_SUCCESS_LABEL: Record<TransitionAction, string> = {
		submit: 'Submitted for review',
		approve: 'Approved',
		reject: 'Rejected',
		publish: 'Published',
		archive: 'Archived',
	};

	// Re-submit from `rejected` uses the same backend action as the
	// draft→under_review path (TestimonialViewSet.submit accepts both
	// from_states). The user-visible verb differs, though, so the
	// button label tracks the current status.
	const submitLabel = $derived(
		status === 'rejected' ? 'Re-submit for review' : ACTION_LABEL.submit,
	);
	const submitSuccessLabel = $derived(
		status === 'rejected' ? 'Re-submitted for review' : ACTION_SUCCESS_LABEL.submit,
	);

	// Visible only on draft rows for an authenticated user. Server
	// enforces authorship (403 if not the author + not staff), but
	// the list query already scopes Volunteers to own drafts so
	// reaching a draft page via the UI implies edit permission for
	// that user — Advocate+ can always edit drafts in the queue.
	const canEditDraft = $derived(status === 'draft' && isAuthed);

	// Status pill — uses the centralised label from
	// $lib/statusPresentation so a new status is added in one place.
	// `status` is widened to string at the type level because the
	// public schema types `status` as a string union; STATUS_LABEL
	// keys by string so any value passes through safely (a typo
	// would just fall back to status.replace('_', ' ') via the
	// helper, not break).
	const pillLabel = $derived(STATUS_LABEL[status] ?? status);

	// Sub-line for the latest workflow timestamp. Pick the most
	// recent non-null field — they're mutually exclusive in normal
	// flow (each transition stamps exactly one of these).
	const lastTransition = $derived.by<{ label: string; at: string } | null>(() => {
		const candidates: Array<{ label: string; at: string | null | undefined }> = [
			{ label: 'Submitted for review', at: testimonial.submitted_at },
			{ label: 'Reviewed', at: testimonial.reviewed_at },
			{ label: 'Approved', at: testimonial.approved_at },
			{ label: 'Published', at: testimonial.published_at },
			{ label: 'Archived', at: testimonial.archived_at },
		];
		const next = candidates.find((c) => !!c.at);
		return next ? { label: next.label, at: next.at as string } : null;
	});

	function formatDate(iso: string | null | undefined): string {
		if (!iso) return '';
		return new Date(iso).toLocaleDateString(undefined, {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
		});
	}

	/* Single action dispatcher. Same shape as the queue page's
	   ACTION_DISPATCH map — keeps the call sites uniform and lets a
	   new transition be added with one line. The submit action is
	   conditional on the current status (re-submit from rejected
	   uses the same endpoint), so it isn't in the map directly. */
	async function runTransition(action: TransitionAction) {
		if (busy) return;
		if (action === 'reject') {
			rejectNotes = '';
			rejectOpen = true;
			return;
		}
		busy = true;
		actionError = null;
		try {
			switch (action) {
				case 'submit':
					await testimonialsSubmitCreate(id, {});
					break;
				case 'approve':
					await testimonialsApproveCreate(id, {});
					break;
				case 'publish':
					await testimonialsPublishCreate(id, {});
					break;
				case 'archive':
					await testimonialsArchiveCreate(id, {});
					break;
			}
			await refreshRow();
			const label =
				action === 'submit' ? submitSuccessLabel : ACTION_SUCCESS_LABEL[action];
			// Post-action navigation: send the user to the list page
			// scoped to the destination tab. submit → review queue,
			// approve (single-step to published) / publish → published,
			// archive → published. Each redirect fires a toast on
			// the destination page.
			const tab = postActionTab(action);
			showToast(`${label}.`, { variant: 'success' });
			await goto(`${base}/testimonials?tab=${tab}`);
		} catch (e) {
			actionError =
				e instanceof Error
					? `${ACTION_LABEL[action]} failed: ${e.message}`
					: `${ACTION_LABEL[action]} failed.`;
		} finally {
			busy = false;
		}
	}

	async function submitReject() {
		const notes = rejectNotes.trim();
		if (!notes) return;
		rejectSaving = true;
		actionError = null;
		try {
			await testimonialsRejectCreate(id, {
				method: 'POST',
				body: JSON.stringify({ review_notes: notes }),
				headers: { 'Content-Type': 'application/json' },
			});
			rejectOpen = false;
			rejectNotes = '';
			await refreshRow();
			showToast(`${ACTION_SUCCESS_LABEL.reject}.`, { variant: 'success' });
			await goto(`${base}/testimonials?tab=rejected`);
		} catch (e) {
			actionError =
				e instanceof Error ? `Reject failed: ${e.message}` : 'Reject failed.';
		} finally {
			rejectSaving = false;
		}
	}

	/** Map a successful transition to the list-page tab that should
	 *  receive the post-action redirect. Keeps the navigation
	 *  decision in one place (rather than scattered across each
	 *  call site). */
	function postActionTab(action: TransitionAction): 'review' | 'published' {
		if (action === 'submit') return 'review';
		return 'published';
	}

	/* Re-fetch the row so the status pill + button set reflect the
	   new state. The transition endpoints all return the updated row
	   payload, but we re-fetch to stay uniform with the queue page
	   (and to pick up server-side stamp changes — submitted_at,
	   approved_at, etc. — that the response shape might not surface
	   on every transition). */
	async function refreshRow(): Promise<TestimonialPublic & WorkflowFields> {
		const fresh = await testimonialsRetrieve(id);
		const row = fresh as unknown as TestimonialPublic & WorkflowFields;
		// Notify the parent with the refreshed row so its `derived`
		// binding can re-render with the new fields. Svelte 5 props
		// are reactive at the parent binding; the child cannot
		// mutate the parent's source. `bind:testimonial` was the
		// alternative — see the prop docstring for why we chose a
		// callback instead.
		onUpdated?.(row);
		return row;
	}

	function flashSuccess(msg: string) {
		actionSuccess = msg;
		if (actionSuccessTimer) clearTimeout(actionSuccessTimer);
		actionSuccessTimer = setTimeout(() => {
			actionSuccess = null;
			actionSuccessTimer = null;
		}, 4000);
	}

	function closeRejectModal() {
		rejectOpen = false;
		rejectNotes = '';
	}
</script>

{#if isAuthed && (visibleActions.length > 0 || canEditDraft)}
	<aside class="workflow-actions" aria-label="Workflow actions">
		<header class="workflow-header">
			<span class="status-pill status-pill-{status}">
				{pillLabel}
			</span>
			{#if lastTransition}
				<p class="workflow-subline">
					{lastTransition.label} on
					<time datetime={lastTransition.at}>{formatDate(lastTransition.at)}</time>
				</p>
			{/if}
		</header>

		{#if actionError}
			<div class="action-error" role="alert">{actionError}</div>
		{/if}
		{#if actionSuccess}
			<div class="action-success" role="status">{actionSuccess}</div>
		{/if}

		<div class="action-buttons">
			{#each visibleActions as action (action)}
				<button
					type="button"
					class="action-btn action-btn-{action === 'reject' || action === 'archive' ? 'secondary' : 'primary'}"
					class:action-btn-danger={action === 'reject'}
					disabled={busy}
					onclick={() => runTransition(action)}
				>
					{busy ? 'Working…' : (action === 'submit' ? submitLabel : ACTION_LABEL[action])}
				</button>
			{/each}
			{#if canEditDraft}
				<a class="action-btn action-btn-edit" href="{base}/testimonials/{id}/edit">
					Edit draft →
				</a>
			{/if}
		</div>
	</aside>
{/if}

{#if rejectOpen}
	<Modal
		open={rejectOpen}
		onClose={closeRejectModal}
	>
		{#snippet header()}
			<div class="reject-modal-header">
				<div class="reject-modal-icon" aria-hidden="true">
					<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round">
						<path d="M12 9v4" />
						<path d="M12 17h.01" />
						<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
					</svg>
				</div>
				<div class="reject-modal-title-block">
					<h2 id={undefined} class="reject-modal-title">
						Reject testimonial <span class="reject-modal-id">#{id}</span>
					</h2>
					<p class="reject-modal-subtitle">
						This action sends the draft back to the submitter.
					</p>
				</div>
			</div>
		{/snippet}

		<div class="reject-modal-body">
			<p class="reject-modal-description">
				Rejection requires a reason. The submitter will see this
				note on their draft so they can address it before
				re-submitting.
			</p>

			<div class="reject-modal-field">
				<div class="reject-modal-label-row">
					<label class="reject-modal-label" for="reject-notes">
						Reason
						<span class="reject-modal-required" aria-hidden="true">*</span>
					</label>
					<span class="reject-modal-count" aria-live="polite">
						{rejectNotes.trim().length} characters
					</span>
				</div>
				<textarea
					id="reject-notes"
					class="reject-modal-textarea"
					rows="6"
					maxlength="2000"
					bind:value={rejectNotes}
					placeholder="e.g. Source unreliable; needs re-verification."
				></textarea>
			</div>
		</div>

		{#snippet footer()}
			<div class="reject-modal-actions">
				<button
					type="button"
					class="reject-btn reject-btn-cancel"
					onclick={closeRejectModal}
					disabled={rejectSaving}
				>
					Cancel
				</button>
				<button
					type="button"
					class="reject-btn reject-btn-confirm"
					disabled={!rejectNotes.trim() || rejectSaving}
					onclick={submitReject}
				>
					{rejectSaving ? 'Rejecting…' : 'Reject testimonial'}
				</button>
			</div>
		{/snippet}
	</Modal>
{/if}

<style>
	.workflow-actions {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card-lg);
		padding: 1.25rem 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 0.85rem;
	}

	.workflow-header {
		display: flex;
		align-items: baseline;
		gap: 0.85rem;
		flex-wrap: wrap;
	}

	.workflow-subline {
		margin: 0;
		font-size: 0.85rem;
		color: var(--color-text-muted);
	}

	.status-pill {
		display: inline-block;
		padding: 0.2rem 0.65rem;
		border-radius: 999px;
		font-size: 0.78rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.04rem;
	}

	.status-pill-draft {
		background: #f1f5f9;
		color: #475569;
	}
	.status-pill-under_review {
		background: #fef3c7;
		color: #92400e;
	}
	.status-pill-approved {
		background: #dcfce7;
		color: #15803d;
	}
	.status-pill-published {
		background: var(--color-primary);
		color: var(--color-text-light);
	}
	.status-pill-rejected {
		background: #fee2e2;
		color: #b91c1c;
	}
	.status-pill-archived {
		background: #e5e7eb;
		color: #4b5563;
	}

	.action-buttons {
		display: flex;
		gap: 0.55rem;
		flex-wrap: wrap;
	}

	.action-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: 0.55rem 1rem;
		border-radius: var(--radius-input);
		font: inherit;
		font-weight: 700;
		font-size: 0.9rem;
		text-decoration: none;
		cursor: pointer;
		transition: background-color 0.15s ease;
		border: 1px solid transparent;
	}

	.action-btn-primary {
		background: var(--color-primary);
		color: var(--color-text-light);
	}
	.action-btn-primary:hover {
		background: var(--color-primary-dark, var(--color-primary));
	}
	.action-btn-primary:disabled,
	.action-btn-secondary:disabled,
	.action-btn-danger:disabled {
		opacity: 0.55;
		cursor: not-allowed;
	}

	.action-btn-secondary {
		background: var(--color-bg-white);
		color: var(--color-primary);
		border-color: var(--color-primary);
	}
	.action-btn-secondary:hover {
		background: var(--color-section-bg);
	}

	.action-btn-danger {
		background: var(--color-danger);
		color: var(--color-text-light);
	}
	.action-btn-danger:hover {
		filter: brightness(0.92);
	}

	.action-btn-edit {
		background: transparent;
		color: var(--color-primary);
		border-color: var(--color-border);
	}
	.action-btn-edit:hover {
		border-color: var(--color-primary);
	}

	/* Reject modal — clean typography hierarchy, padded textarea with
	   focus ring, distinct outline (Cancel) and destructive (Reject)
	   action buttons. Tokens from app.css; no hardcoded values. */

	/* Header bar — warning glyph + title + subtitle on a tinted
	   background. Distinct from the body so the destructive action
	   reads as "two sections: explain what this is, do the action". */
	.reject-modal-header {
		display: flex;
		align-items: flex-start;
		gap: 0.85rem;
		padding: 1.25rem 1.5rem;
		background: var(--color-danger-bg);
		border-bottom: 1px solid var(--color-danger-border);
		border-top-left-radius: var(--radius-card-lg);
		border-top-right-radius: var(--radius-card-lg);
	}

	.reject-modal-icon {
		flex: 0 0 auto;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 2.5rem;
		height: 2.5rem;
		border-radius: 999px;
		background: var(--color-danger-icon-bg);
		color: var(--color-danger-text-strong);
	}

	.reject-modal-title-block {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
		min-width: 0;
	}

	.reject-modal-title {
		margin: 0;
		font-size: 1.15rem;
		font-weight: 700;
		color: var(--color-danger-text-strong);
		letter-spacing: -0.01em;
	}

	.reject-modal-id {
		font-weight: 700;
		color: var(--color-danger);
		font-variant-numeric: tabular-nums;
	}

	.reject-modal-subtitle {
		margin: 0;
		font-size: 0.82rem;
		color: var(--color-danger-text);
		line-height: 1.4;
	}

	.reject-modal-body {
		padding: 1.25rem 1.5rem 0.5rem;
	}

	.reject-modal-description {
		margin: 0 0 1.15rem 0;
		color: var(--color-text-muted);
		font-size: 0.92rem;
		line-height: 1.55;
	}

	.reject-modal-field {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.reject-modal-label-row {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 0.5rem;
	}

	.reject-modal-label {
		display: block;
		font-size: 0.85rem;
		font-weight: 700;
		color: var(--color-text);
		letter-spacing: 0.01em;
	}

	.reject-modal-required {
		color: var(--color-danger);
		margin-left: 0.15rem;
		font-weight: 700;
	}

	.reject-modal-count {
		font-size: 0.72rem;
		color: var(--color-text-muted);
		font-variant-numeric: tabular-nums;
	}

	.reject-modal-textarea {
		font: inherit;
		width: 100%;
		min-height: 7.5em;
		padding: 0.75rem 0.85rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-input);
		background: var(--color-bg-white);
		color: var(--color-text);
		resize: vertical;
		box-sizing: border-box;
		line-height: 1.55;
		font-size: 0.92rem;
		transition: border-color 0.15s ease, box-shadow 0.15s ease;
	}
	.reject-modal-textarea:hover:not(:disabled) {
		border-color: var(--color-text-muted);
	}
	.reject-modal-textarea:focus-visible {
		outline: none;
		border-color: var(--color-danger);
		box-shadow: 0 0 0 3px var(--color-danger-icon-bg);
	}

	.reject-modal-actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.65rem;
		flex-wrap: wrap;
		padding: 0.85rem 1.5rem 1.25rem;
		border-top: 1px solid var(--color-border-light);
		background: var(--color-bg);
		border-bottom-left-radius: var(--radius-card-lg);
		border-bottom-right-radius: var(--radius-card-lg);
		margin: 1rem -0 0 0;
	}

	.reject-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: 0.6rem 1.25rem;
		border-radius: var(--radius-input);
		font: inherit;
		font-weight: 700;
		font-size: 0.92rem;
		line-height: 1.2;
		cursor: pointer;
		transition: background-color 0.15s ease, border-color 0.15s ease,
			color 0.15s ease, box-shadow 0.15s ease;
		border: 1px solid transparent;
		min-width: 6.5rem;
	}
	.reject-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
	.reject-btn:focus-visible {
		outline: none;
		box-shadow: 0 0 0 3px var(--focus-ring);
	}

	.reject-btn-cancel {
		background: var(--color-bg-white);
		color: var(--color-text);
		border-color: var(--color-border);
	}
	.reject-btn-cancel:hover:not(:disabled) {
		background: var(--color-section-bg);
		border-color: var(--color-text-muted);
	}

	.reject-btn-confirm {
		background: var(--color-danger);
		color: var(--color-text-light);
		border-color: var(--color-danger);
		box-shadow: 0 1px 2px rgba(217, 22, 22, 0.18);
	}
	.reject-btn-confirm:hover:not(:disabled) {
		background: var(--color-danger-text-strong);
		border-color: var(--color-danger-text-strong);
		box-shadow: 0 2px 6px rgba(217, 22, 22, 0.28);
	}
	.reject-btn-confirm:focus-visible {
		outline: none;
		box-shadow: 0 0 0 3px var(--color-danger-icon-bg);
	}

	.action-error {
		padding: 0.7rem 0.85rem;
		border: 1px solid var(--color-danger);
		border-left: 3px solid var(--color-danger);
		border-radius: var(--radius-card);
		color: var(--color-danger);
		background: #fef2f2;
		font-size: 0.9rem;
	}

	.action-success {
		padding: 0.7rem 0.85rem;
		border: 1px solid #86efac;
		border-left: 3px solid #16a34a;
		border-radius: var(--radius-card);
		color: #166534;
		background: #f0fdf4;
		font-size: 0.9rem;
	}

	/* Reject modal — same shape as the Review queue tab on /testimonials */
	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.4);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
		padding: 1rem;
	}

	.modal {
		background: var(--color-bg-white);
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-card-lg);
		padding: 1.5rem;
		max-width: 32rem;
		width: 100%;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.modal h2 {
		margin: 0;
		font-size: 1.05rem;
		color: var(--color-primary);
	}

	.modal p {
		margin: 0;
		color: var(--color-text-muted);
		font-size: 0.9rem;
	}

	.modal-label {
		font-size: 0.85rem;
		font-weight: 700;
	}

	.modal textarea {
		font: inherit;
		padding: 0.5rem 0.65rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-input);
		resize: vertical;
		min-height: 5em;
	}

	.modal-actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.5rem;
	}

	.btn {
		display: inline-flex;
		align-items: center;
		padding: 0.5rem 1rem;
		border-radius: var(--radius-input);
		font: inherit;
		font-weight: 700;
		font-size: 0.9rem;
		text-decoration: none;
		cursor: pointer;
		border: 1px solid transparent;
	}

	.btn-secondary {
		background: var(--color-bg-white);
		color: var(--color-primary);
		border-color: var(--color-border);
	}

	.btn-danger {
		background: var(--color-danger);
		color: var(--color-text-light);
	}

	.btn:disabled {
		opacity: 0.55;
		cursor: not-allowed;
	}
</style>