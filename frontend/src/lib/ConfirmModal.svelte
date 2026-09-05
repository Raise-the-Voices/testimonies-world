<!--
	Destructive / action confirmation dialog. Wraps <Modal> for chrome
	+ a11y (focus trap, body scroll lock, Escape).

	State machine: the parent owns the open/closed flag and the current
	stage (`confirming` / `pending` / `success` / `error`). The dialog
	renders different button sets per stage:

	  confirming: Cancel + Confirm
	  pending:    Cancel (disabled) + spinner + Confirm (disabled)
	  success:    Close (calls onCancel so the parent can hide the dialog)
	  error:      Close + Retry (Retry calls onConfirm; Close calls
	              onCancel)

	Use this anywhere you have a "are you sure?" dialog plus optional
	post-action feedback. For simple confirm-only flows (delete a row
	and redirect), just stay in `confirming` and let the page close the
	dialog via `onCancel` after the action completes.
-->
<script lang="ts">
	import Modal from './Modal.svelte';

	interface Props {
		open: boolean;
		stage?: 'confirming' | 'pending' | 'success' | 'error';
		title: string;
		body: string;
		confirmLabel?: string;
		cancelLabel?: string;
		destructive?: boolean;
		errorMessage?: string;
		/** Override the default body text with a custom snippet. Use this
			when the body needs more than plain text — e.g. inline `<strong>`
			highlighting or a nested error callout. The snippet name
			`bodyContent` is required (to avoid shadowing the `body` prop). */
		bodyContent?: import('svelte').Snippet;
		onConfirm: () => void;
		onCancel: () => void;
	}

	let {
		open,
		stage = 'confirming',
		title,
		body,
		confirmLabel = 'Delete',
		cancelLabel = 'Cancel',
		destructive = true,
		errorMessage,
		bodyContent,
		onConfirm,
		onCancel,
	}: Props = $props();

	const showSpinner = $derived(stage === 'pending');
</script>

<Modal
	{open}
	{title}
	role={destructive ? 'alertdialog' : 'dialog'}
	dismissable={stage !== 'pending'}
	onClose={onCancel}
>
	<div class="modal-body">
		{#if bodyContent}
			{@render bodyContent()}
		{:else if stage === 'error' && errorMessage}
			<p class="confirm-body">{errorMessage}</p>
		{:else}
			<p class="confirm-body">{body}</p>
		{/if}
	</div>

	{#snippet footer()}
		<div class="modal-actions">
			{#if stage === 'confirming'}
				<button type="button" class="btn btn-secondary" onclick={onCancel}>
					{cancelLabel}
				</button>
				<button
					type="button"
					class={destructive ? 'btn btn-danger' : 'btn btn-primary'}
					onclick={onConfirm}
				>
					{confirmLabel}
				</button>
			{:else if stage === 'pending'}
				<button type="button" class="btn btn-secondary" disabled>
					{cancelLabel}
				</button>
				<button type="button" class="btn btn-primary" disabled>
					<span class="spinner" aria-hidden="true"></span>
					Working…
				</button>
			{:else if stage === 'success'}
				<button type="button" class="btn btn-primary" onclick={onCancel}>
					Close
				</button>
			{:else}
				<button type="button" class="btn btn-secondary" onclick={onCancel}>
					Close
				</button>
				<button type="button" class="btn btn-primary" onclick={onConfirm}>
					Retry
				</button>
			{/if}
		</div>
	{/snippet}
</Modal>

<style>
	.modal-body {
		padding: 1.25rem;
		color: var(--color-text);
		line-height: 1.55;
	}
	.confirm-body {
		margin: 0;
		font-size: 0.95rem;
	}
	.modal-actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.75rem;
		padding: 1rem 1.25rem;
		border-top: 1px solid var(--color-border-subtle);
	}
	.modal-actions .btn {
		min-width: 110px;
	}
	.modal-actions .btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.spinner {
		display: inline-block;
		width: 14px;
		height: 14px;
		border: 2px solid currentColor;
		border-top-color: transparent;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
		margin-right: 0.4rem;
		vertical-align: -2px;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	@media (max-width: 600px) {
		.modal-actions {
			flex-direction: column-reverse;
		}
		.modal-actions .btn {
			width: 100%;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.spinner {
			animation: none;
		}
	}
</style>