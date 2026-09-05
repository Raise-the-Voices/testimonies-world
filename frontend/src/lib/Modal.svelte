<!--
	Generic modal shell — overlay + dialog chrome + accessibility.

	Responsibilities (single source of truth across <MediaUploadModal>,
	<ConfirmModal>, and any future dialog):
	  - Escape-to-close (when `dismissable`)
	  - Backdrop click-to-close (when `dismissable`)
	  - Body scroll lock while open
	  - Focus trap: focus first focusable on open, return focus to trigger
	    on close, trap Tab / Shift+Tab inside the dialog
	  - role="dialog" or role="alertdialog" for screen readers

	Parent components compose their own body via the `children` snippet.
	For more elaborate layouts (custom header / footer), pass
	`header` / `footer` snippets. The title prop is used as
	aria-labelledby; if you supply a `header` snippet it replaces the
	default title bar entirely (no aria-labelledby is set — provide
	your own aria-label on the dialog content).
-->
<script lang="ts">
	import type { Snippet } from 'svelte';
	import { fly, fade } from 'svelte/transition';

	interface Props {
		open: boolean;
		title?: string;
		role?: 'dialog' | 'alertdialog';
		dismissable?: boolean;
		onClose: () => void;
		children?: Snippet;
		header?: Snippet;
		footer?: Snippet;
	}

	let {
		open,
		title,
		role = 'dialog',
		dismissable = true,
		onClose,
		children,
		header,
		footer,
	}: Props = $props();

	const titleId = `modal-title-${Math.random().toString(36).slice(2, 9)}`;
	let dialogEl: HTMLDivElement | null = $state(null);
	let triggerEl: HTMLElement | null = null;

	// Open-side effects: lock body scroll, remember the trigger so we
	// can return focus on close, focus the first focusable inside.
	$effect(() => {
		if (!open) return;
		if (typeof document === 'undefined') return;
		triggerEl = (document.activeElement as HTMLElement) ?? null;
		const prevOverflow = document.body.style.overflow;
		document.body.style.overflow = 'hidden';
		// Defer focus until the dialog is rendered.
		queueMicrotask(() => {
			const first = dialogEl?.querySelector<HTMLElement>(
				'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
			);
			first?.focus();
		});

		const onKey = (e: KeyboardEvent) => {
			if (e.key === 'Escape' && dismissable) {
				e.preventDefault();
				onClose();
				return;
			}
			if (e.key === 'Tab' && dialogEl) {
				// Trap Tab inside the dialog.
				const focusables = Array.from(
					dialogEl.querySelectorAll<HTMLElement>(
						'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
					),
				).filter((el) => el.offsetParent !== null);
				if (focusables.length === 0) {
					e.preventDefault();
					return;
				}
				const first = focusables[0];
				const last = focusables[focusables.length - 1];
				const active = document.activeElement as HTMLElement | null;
				if (e.shiftKey && active === first) {
					e.preventDefault();
					last.focus();
				} else if (!e.shiftKey && active === last) {
					e.preventDefault();
					first.focus();
				}
			}
		};
		document.addEventListener('keydown', onKey);
		return () => {
			document.removeEventListener('keydown', onKey);
			document.body.style.overflow = prevOverflow;
			triggerEl?.focus();
		};
	});

	function onBackdropClick() {
		if (dismissable) onClose();
	}
</script>

{#if open}
	<!-- Backdrop -->
	<div
		class="modal-overlay"
		onclick={onBackdropClick}
		onkeydown={(e) => {
			if (e.key === 'Enter' || e.key === ' ') {
				e.preventDefault();
				onBackdropClick();
			}
		}}
		role="presentation"
		transition:fade={{ duration: 150 }}
	></div>

	<!-- Dialog -->
	<div
		bind:this={dialogEl}
		class="modal"
		role={role}
		aria-modal="true"
		aria-labelledby={title ? titleId : undefined}
		transition:fly={{ y: -16, duration: 200, opacity: 0 }}
	>
		{#if header}
			{@render header()}
		{:else if title}
			<header class="modal-header">
				<h2 id={titleId}>{title}</h2>
				{#if dismissable}
					<button
						type="button"
						class="modal-close"
						aria-label="Close"
						onclick={onClose}
					>×</button>
				{/if}
			</header>
		{/if}

		{#if children}
			{@render children()}
		{/if}

		{#if footer}
			{@render footer()}
		{/if}
	</div>
{/if}

<style>
	.modal-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.45);
		backdrop-filter: blur(2px);
		-webkit-backdrop-filter: blur(2px);
		z-index: 80;
	}

	.modal {
		position: fixed;
		top: 1.25rem;
		left: 50%;
		transform: translateX(-50%);
		width: calc(100% - 2rem);
		max-width: 540px;
		max-height: calc(100vh - 2.5rem);
		overflow-y: auto;
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-left: 3px solid var(--color-primary);
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-card-lg);
		z-index: 90;
		display: flex;
		flex-direction: column;
	}

	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1rem 1.25rem;
		border-bottom: 1px solid var(--color-border-subtle);
	}
	.modal-header h2 {
		margin: 0;
		font-size: 1.1rem;
		font-weight: 700;
		color: var(--color-text);
	}
	.modal-close {
		background: transparent;
		border: none;
		color: var(--color-text-muted);
		font-size: 1.4rem;
		line-height: 1;
		padding: 0 0.25rem;
		cursor: pointer;
	}
	.modal-close:hover {
		color: var(--color-text);
	}

	@media (prefers-reduced-motion: reduce) {
		.modal,
		.modal-overlay {
			transition: none;
		}
	}
</style>