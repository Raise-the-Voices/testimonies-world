<script lang="ts">
	interface Props {
		open: boolean;
		title: string;
		body?: string;
		confirmLabel?: string;
		cancelLabel?: string;
		kind?: 'danger' | 'primary';
		confirming?: boolean;
		onConfirm: () => void;
		onCancel: () => void;
	}

	let {
		open,
		title,
		body = '',
		confirmLabel = 'Confirm',
		cancelLabel = 'Cancel',
		kind = 'danger',
		confirming = false,
		onConfirm,
		onCancel,
	}: Props = $props();

	function onKey(e: KeyboardEvent) {
		if (!open) return;
		if (e.key === 'Escape') {
			e.preventDefault();
			onCancel();
		} else if (e.key === 'Enter' && !confirming) {
			e.preventDefault();
			onConfirm();
		}
	}

	$effect(() => {
		if (typeof window === 'undefined') return;
		if (open) {
			window.addEventListener('keydown', onKey);
			document.body.style.overflow = 'hidden';
			return () => {
				window.removeEventListener('keydown', onKey);
				document.body.style.overflow = '';
			};
		}
	});
</script>

{#if open}
	<div
		class="confirm-backdrop"
		onclick={onCancel}
		role="presentation"
	></div>
	<div
		class="confirm-dialog"
		role="alertdialog"
		aria-modal="true"
		aria-labelledby="confirm-title"
		aria-describedby={body ? 'confirm-body' : undefined}
	>
		<div class="confirm-header">
			<span class="confirm-icon confirm-icon-{kind}" aria-hidden="true">
				{kind === 'danger' ? '!' : '?'}
			</span>
			<h3 id="confirm-title">{title}</h3>
		</div>
		{#if body}
			<p id="confirm-body" class="confirm-body">{body}</p>
		{/if}
		<div class="confirm-actions">
			<button
				type="button"
				class="btn btn-secondary"
				onclick={onCancel}
				disabled={confirming}
			>{cancelLabel}</button>
			<button
				type="button"
				class="btn btn-{kind === 'danger' ? 'danger' : 'primary'}"
				onclick={onConfirm}
				disabled={confirming}
			>
				{#if confirming}
					<span class="spinner" aria-hidden="true"></span>
					Working…
				{:else}
					{confirmLabel}
				{/if}
			</button>
		</div>
	</div>
{/if}

<style>
	.confirm-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(15, 23, 25, 0.45);
		z-index: 900;
		animation: fade-in 0.18s ease-out;
	}
	.confirm-dialog {
		position: fixed;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		z-index: 1000;
		width: min(420px, calc(100vw - 2rem));
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-subtle);
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-card-lg);
		padding: 1.5rem 1.5rem 1.25rem;
		animation: pop-in 0.2s cubic-bezier(0.16, 1, 0.3, 1);
	}

	@keyframes fade-in {
		from { opacity: 0; }
		to { opacity: 1; }
	}
	@keyframes pop-in {
		from {
			opacity: 0;
			transform: translate(-50%, -45%) scale(0.96);
		}
		to {
			opacity: 1;
			transform: translate(-50%, -50%) scale(1);
		}
	}

	.confirm-header {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		margin-bottom: 0.75rem;
	}
	.confirm-icon {
		flex: 0 0 auto;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		border-radius: 50%;
		font-family: 'Georgia', serif;
		font-style: italic;
		font-weight: 700;
		font-size: 1.05rem;
		line-height: 1;
		color: white;
	}
	.confirm-icon-danger {
		background: var(--color-danger);
	}
	.confirm-icon-primary {
		background: var(--color-primary);
	}
	.confirm-dialog h3 {
		margin: 0;
		color: var(--color-text);
		font-size: 1.1rem;
		font-weight: 700;
		line-height: 1.3;
	}
	.confirm-body {
		margin: 0 0 1.25rem;
		color: var(--color-text-muted);
		font-size: 0.92rem;
		line-height: 1.5;
		padding-left: 2.5rem;
	}
	.confirm-actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.5rem;
		padding-left: 2.5rem;
		flex-wrap: wrap;
	}
	.confirm-actions .btn {
		min-width: 100px;
	}
	.spinner {
		display: inline-block;
		width: 13px;
		height: 13px;
		border: 2px solid currentColor;
		border-right-color: transparent;
		border-radius: 50%;
		animation: spin 0.7s linear infinite;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* Danger button — uses our existing palette */
	:global(.btn.btn-danger) {
		background: var(--color-danger);
		color: var(--color-text-light);
		border: 1px solid var(--color-danger);
	}
	:global(.btn.btn-danger:hover:not(:disabled)) {
		background: #b51313;
		border-color: #b51313;
	}
	:global(.btn.btn-danger:disabled) {
		opacity: 0.7;
		cursor: not-allowed;
	}

	@media (max-width: 480px) {
		.confirm-body,
		.confirm-actions {
			padding-left: 0;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.confirm-backdrop,
		.confirm-dialog,
		.spinner {
			animation: none;
		}
	}
</style>
