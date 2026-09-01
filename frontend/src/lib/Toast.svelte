<script lang="ts">
	import { toasts, dismiss, type Toast } from './toast';

	function iconFor(kind: Toast['kind']): string {
		switch (kind) {
			case 'success':
				return '✓';
			case 'error':
				return '✕';
			case 'warning':
				return '!';
			default:
				return 'i';
		}
	}
</script>

<div class="toast-stack" aria-live="polite" aria-atomic="false">
	{#each $toasts as t (t.id)}
		<div class="toast toast-{t.kind}" role={t.kind === 'error' ? 'alert' : 'status'}>
			<span class="toast-icon" aria-hidden="true">{iconFor(t.kind)}</span>
			<div class="toast-body">
				<p class="toast-title">{t.title}</p>
				{#if t.body}<p class="toast-text">{t.body}</p>{/if}
			</div>
			<button
				type="button"
				class="toast-dismiss"
				aria-label="Dismiss notification"
				onclick={() => dismiss(t.id)}
			>×</button>
		</div>
	{/each}
</div>

<style>
	.toast-stack {
		position: fixed;
		right: 1.25rem;
		bottom: 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 0.6rem;
		z-index: 1000;
		max-width: min(380px, calc(100vw - 2.5rem));
		pointer-events: none;
	}

	.toast {
		pointer-events: auto;
		display: flex;
		align-items: flex-start;
		gap: 0.7rem;
		padding: 0.8rem 0.95rem;
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-subtle);
		border-left: 4px solid var(--color-primary);
		border-radius: var(--radius-input);
		box-shadow: var(--shadow-card-lg);
		animation: slide-in 0.25s ease-out;
	}

	@keyframes slide-in {
		from {
			transform: translateX(20px);
			opacity: 0;
		}
		to {
			transform: translateX(0);
			opacity: 1;
		}
	}

	.toast-success {
		border-left-color: var(--color-success);
	}
	.toast-success .toast-icon {
		background: var(--color-success);
		color: white;
	}
	.toast-error {
		border-left-color: var(--color-danger);
	}
	.toast-error .toast-icon {
		background: var(--color-danger);
		color: white;
	}
	.toast-warning {
		border-left-color: #c97a0d;
	}
	.toast-warning .toast-icon {
		background: #c97a0d;
		color: white;
	}
	.toast-info .toast-icon {
		background: var(--color-primary);
		color: white;
	}

	.toast-icon {
		flex: 0 0 auto;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		border-radius: 50%;
		font-size: 0.85rem;
		font-weight: 700;
		line-height: 1;
		font-style: italic;
		font-family: 'Georgia', serif;
	}

	.toast-body {
		flex: 1 1 auto;
		min-width: 0;
	}
	.toast-title {
		margin: 0;
		color: var(--color-text);
		font-size: 0.92rem;
		font-weight: 600;
		line-height: 1.35;
	}
	.toast-text {
		margin: 0.2rem 0 0 0;
		color: var(--color-text-muted);
		font-size: 0.83rem;
		line-height: 1.45;
	}

	.toast-dismiss {
		flex: 0 0 auto;
		background: transparent;
		border: 0;
		color: var(--color-text-muted);
		font-size: 1.3rem;
		line-height: 1;
		cursor: pointer;
		padding: 0 0.15rem;
		margin-left: 0.2rem;
	}
	.toast-dismiss:hover {
		color: var(--color-text);
	}

	@media (max-width: 520px) {
		.toast-stack {
			right: 0.75rem;
			bottom: 0.75rem;
			max-width: calc(100vw - 1.5rem);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.toast {
			animation: none;
		}
	}
</style>
