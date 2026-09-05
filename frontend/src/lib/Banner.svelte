<!--
	Top-of-page banner — success / error / info. Replaces the duplicated
	`.banner-success` / `.banner-error` markup across /persons,
	/contacts, /casework. All styling is design-system tokens.

	Behavior:
	  - Renders as `role="status"` (live region, polite) for transient
	    notifications so screen readers announce changes.
	  - Auto-dismisses after `ttlMs` (default 3500ms). Set `ttlMs={0}`
	    to disable auto-dismiss (caller owns lifetime via `onDismiss`).
	  - Optional × button when `dismissable={true}`.
-->
<script lang="ts">
	import { fly } from 'svelte/transition';

	interface Props {
		kind: 'success' | 'error' | 'info';
		message: string;
		dismissable?: boolean;
		ttlMs?: number;
		onDismiss?: () => void;
	}

	let {
		kind,
		message,
		dismissable = true,
		ttlMs = 3500,
		onDismiss,
	}: Props = $props();

	const icon = $derived(kind === 'success' ? '✓' : kind === 'error' ? '!' : 'i');

	function dismiss() {
		onDismiss?.();
	}

	$effect(() => {
		// Touch reactive deps so the effect re-runs when message/kind
		// change (auto-dismiss timer resets on a new banner).
		void message;
		void kind;
		if (ttlMs <= 0) return;
		const id = setTimeout(dismiss, ttlMs);
		return () => clearTimeout(id);
	});
</script>

{#if message}
	<div
		class="banner banner-{kind}"
		role="status"
		transition:fly={{ y: -8, duration: 220, opacity: 0 }}
	>
		<span class="banner-icon" aria-hidden="true">{icon}</span>
		<span class="banner-text">{message}</span>
		{#if dismissable}
			<button
				type="button"
				class="banner-dismiss"
				aria-label="Dismiss"
				onclick={dismiss}
			>×</button>
		{/if}
	</div>
{/if}

<style>
	.banner {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.65rem 0.9rem;
		border-radius: var(--radius-card);
		font-size: 0.92rem;
		margin-bottom: 1rem;
	}
	.banner-success {
		background: var(--color-success-bg);
		color: var(--color-success-text);
		border: 1px solid var(--color-success-border);
	}
	.banner-error {
		background: var(--color-danger-bg);
		color: var(--color-danger-text);
		border: 1px solid var(--color-danger-border);
	}
	.banner-info {
		background: var(--color-surface);
		color: var(--color-text);
		border: 1px solid var(--color-border-light);
	}
	.banner-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 22px;
		height: 22px;
		border-radius: 50%;
		font-weight: 700;
		font-size: 0.85rem;
		flex: 0 0 auto;
	}
	.banner-success .banner-icon {
		background: var(--color-success-icon-bg);
		color: var(--color-success-text);
	}
	.banner-error .banner-icon {
		background: var(--color-danger-icon-bg);
		color: var(--color-danger-text);
	}
	.banner-info .banner-icon {
		background: var(--color-primary-tint);
		color: var(--color-primary);
	}
	.banner-text {
		flex: 1 1 auto;
	}
	.banner-dismiss {
		background: transparent;
		border: none;
		color: inherit;
		font-size: 1.1rem;
		padding: 0 0.25rem;
		line-height: 1;
		cursor: pointer;
	}
</style>