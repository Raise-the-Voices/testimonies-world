<!--
	Toast — fixed-position notification container.

	Renders the current toast (if any) from \$lib/toast.ts. Mounted
	once in +layout.svelte so every page can fire showToast() and the
	notification appears regardless of where the user navigated to.

	The container is fixed bottom-right, max-width clamps on narrow
	viewports, and the slide animation respects prefers-reduced-motion.
-->
<script lang="ts">
	import { fly, fade } from 'svelte/transition';
	import { toast, dismissToast, type Toast } from '$lib/toast';

	let current: Toast | null = $state(null);
	$effect(() => {
		const unsub = toast.subscribe((t) => {
			current = t;
		});
		return unsub;
	});

	function onActionKey(e: KeyboardEvent, id: number): void {
		// Dismiss on Escape when the toast is focused.
		if (e.key === 'Escape') {
			e.preventDefault();
			dismissToast();
			void id;
		}
	}
</script>

{#if current}
	<div
		class="toast-container"
		role="status"
		aria-live="polite"
		aria-atomic="true"
		transition:fly={{ y: 16, duration: 200 }}
	>
		<div class="toast toast-{current.variant}">
			<span class="toast-message">{current.message}</span>
			<button
				type="button"
				class="toast-close"
				aria-label="Dismiss"
				onclick={() => dismissToast()}
				onkeydown={(e) => current && onActionKey(e, current.id)}
			>×</button>
		</div>
	</div>
{/if}

<style>
	.toast-container {
		position: fixed;
		right: 1.25rem;
		bottom: 1.25rem;
		z-index: 200;
		max-width: min(420px, calc(100vw - 2.5rem));
		pointer-events: none;
	}

	.toast {
		display: flex;
		align-items: flex-start;
		gap: 0.85rem;
		padding: 0.85rem 1rem;
		border-radius: var(--radius-card);
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-left: 3px solid var(--color-primary);
		box-shadow: var(--shadow-card-lg);
		color: var(--color-text);
		font-size: 0.92rem;
		line-height: 1.45;
		pointer-events: auto;
	}

	.toast-message {
		flex: 1 1 auto;
		min-width: 0;
	}

	.toast-close {
		flex: 0 0 auto;
		background: transparent;
		border: none;
		color: var(--color-text-muted);
		font-size: 1.3rem;
		line-height: 1;
		padding: 0 0.25rem;
		cursor: pointer;
	}
	.toast-close:hover {
		color: var(--color-text);
	}

	.toast-success {
		border-left-color: #16a34a;
	}
	.toast-success .toast-message {
		color: #166534;
	}

	.toast-error {
		border-left-color: var(--color-danger);
	}
	.toast-error .toast-message {
		color: var(--color-danger);
	}

	.toast-warning {
		border-left-color: #d97706;
	}
	.toast-warning .toast-message {
		color: #92400e;
	}

	.toast-info {
		border-left-color: var(--color-primary);
	}

	@media (prefers-reduced-motion: reduce) {
		.toast-container {
			transition: none;
		}
	}
</style>