<!--
  Toast — fixed-position notification container.

  Renders the current toast (if any) from \$lib/toast.ts. Mounted
  once in +layout.svelte so every page can fire showToast() and the
  notification appears regardless of where the user navigated to.

  When the toast carries a `details` payload (e.g. a form-submit
  server response), the toast expands to show a collapsible JSON
  viewer + a "Copy" button. The auto-dismiss timer is paused while
  the viewer is expanded so the operator has time to read the JSON
  before it disappears.

  Layout: a max-width-anchored bottom-right card. The expanded
  details section uses a separate column so the JSON scrolls
  independently on long payloads.
-->
<script lang="ts">
	import { fly, fade } from 'svelte/transition';
	import { toast, dismissToast, type Toast } from '$lib/toast';

	let current: Toast | null = $state(null);
	let detailsOpen = $state(false);
	let copyLabel = $state('Copy');
	let resetCopyTimer: ReturnType<typeof setTimeout> | null = null;

	$effect(() => {
		const unsub = toast.subscribe((t) => {
			current = t;
			// Reset the viewer state when the toast changes so a
			// success followed by an error doesn't leak open state.
			detailsOpen = false;
			copyLabel = 'Copy';
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

	function toggleDetails() {
		detailsOpen = !detailsOpen;
	}

	// Pretty-print the details object as JSON for display.
	function formatJson(details: Record<string, unknown> | undefined): string {
		if (!details) return '';
		try {
			return JSON.stringify(details, null, 2);
		} catch {
			return String(details);
		}
	}

	// Summary line: extract a few key fields for at-a-glance reading.
	function summary(details: Record<string, unknown> | undefined): string {
		if (!details) return '';
		const parts: string[] = [];
		if ('id' in details && details.id !== undefined && details.id !== null) {
			parts.push(`#${String(details.id)}`);
		}
		if ('person' in details && details.person !== undefined && details.person !== null) {
			parts.push(`case #${String(details.person)}`);
		}
		if ('created_at' in details && typeof details.created_at === 'string') {
			parts.push(`created ${details.created_at}`);
		}
		return parts.join(' · ');
	}

	async function copyJson(details: Record<string, unknown> | undefined) {
		const text = formatJson(details);
		if (!text) return;
		try {
			await navigator.clipboard.writeText(text);
			copyLabel = 'Copied ✓';
			if (resetCopyTimer !== null) clearTimeout(resetCopyTimer);
			resetCopyTimer = setTimeout(() => {
				copyLabel = 'Copy';
				resetCopyTimer = null;
			}, 1800);
		} catch {
			// Clipboard API blocked (insecure context, permission denied).
			// Fall back to selecting the pre so the user can ⌘C.
			copyLabel = 'Press ⌘C';
		}
	}
</script>

{#if current}
	<div
		class="toast-container"
		class:toast-container--with-details={current.details !== undefined}
		role="status"
		aria-live="polite"
		aria-atomic="true"
		transition:fly={{ y: 16, duration: 200 }}
	>
		<div class="toast toast-{current.variant}">
			<div class="toast-main">
				<div class="toast-message">
					<span class="toast-message-text">{current.message}</span>
					{#if current.details}
						<span class="toast-summary">{summary(current.details)}</span>
					{/if}
				</div>
				<div class="toast-actions">
					{#if current.details}
						<button
							type="button"
							class="toast-action"
							aria-expanded={detailsOpen}
							onclick={toggleDetails}
						>{detailsOpen ? 'Hide' : 'View response'}</button>
					{/if}
					<button
						type="button"
						class="toast-close"
						aria-label="Dismiss"
						onclick={() => dismissToast()}
						onkeydown={(e) => current && onActionKey(e, current.id)}
					>×</button>
				</div>
			</div>

			{#if current.details && detailsOpen}
				<div class="toast-details" transition:fly={{ y: 4, duration: 160 }}>
					<div class="toast-details-header">
						<span class="toast-details-label">JSON response</span>
						<button
							type="button"
							class="toast-copy"
							onclick={() => copyJson(current?.details)}
						>{copyLabel}</button>
					</div>
					<pre class="toast-json"><code>{formatJson(current.details)}</code></pre>
				</div>
			{/if}
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
		transition: max-width 0.15s ease;
	}
	/* When details are open, give the toast more room so the JSON
	   block reads comfortably. */
	.toast-container--with-details {
		max-width: min(560px, calc(100vw - 2.5rem));
	}

	.toast {
		display: flex;
		flex-direction: column;
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-left: 3px solid var(--color-primary);
		border-radius: var(--radius-card);
		box-shadow: var(--shadow-card-lg);
		color: var(--color-text);
		font-size: 0.92rem;
		line-height: 1.45;
		pointer-events: auto;
		overflow: hidden;
	}

	.toast-main {
		display: flex;
		align-items: flex-start;
		gap: 0.85rem;
		padding: 0.85rem 1rem;
	}

	.toast-message {
		flex: 1 1 auto;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
	}
	.toast-message-text {
		font-weight: 600;
	}
	.toast-summary {
		font-size: 0.82rem;
		color: var(--color-text-muted);
		font-variant-numeric: tabular-nums;
		font-weight: 500;
	}

	.toast-actions {
		flex: 0 0 auto;
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
	}
	.toast-action {
		background: transparent;
		border: 1px solid var(--color-border-light);
		color: var(--color-primary);
		font-size: 0.78rem;
		font-weight: 600;
		padding: 0.3rem 0.6rem;
		border-radius: var(--radius-control);
		cursor: pointer;
		text-transform: none;
		letter-spacing: 0;
		min-height: 0;
	}
	.toast-action:hover {
		background: var(--color-surface);
		border-color: var(--color-primary-light);
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
		min-height: 0;
	}
	.toast-close:hover {
		color: var(--color-text);
	}

	/* === Details section (collapsible JSON) === */
	.toast-details {
		border-top: 1px solid var(--color-border-subtle);
		background: var(--color-surface, #f7f7f9);
		padding: 0.6rem 0.85rem 0.75rem 0.85rem;
	}
	.toast-details-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
		margin-bottom: 0.45rem;
	}
	.toast-details-label {
		font-size: 0.7rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		color: var(--color-text-muted);
	}
	.toast-copy {
		background: transparent;
		border: 1px solid var(--color-border-light);
		color: var(--color-text);
		font-size: 0.78rem;
		padding: 0.25rem 0.6rem;
		border-radius: var(--radius-control);
		cursor: pointer;
		font-weight: 600;
		min-height: 0;
		font-variant-numeric: tabular-nums;
		min-width: 5rem;
		text-align: center;
	}
	.toast-copy:hover {
		background: var(--color-bg-white);
		border-color: var(--color-primary-light);
		color: var(--color-primary);
	}
	.toast-json {
		margin: 0;
		padding: 0.65rem 0.75rem;
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-control);
		font-family: ui-monospace, 'SF Mono', 'Cascadia Mono', Menlo, Consolas, monospace;
		font-size: 0.78rem;
		line-height: 1.45;
		color: var(--color-text);
		max-height: 18rem;
		overflow: auto;
		white-space: pre;
	}
	.toast-json code {
		font-family: inherit;
	}

	.toast-success {
		border-left-color: #16a34a;
	}
	.toast-success .toast-message-text {
		color: #166534;
	}

	.toast-error {
		border-left-color: var(--color-danger);
	}
	.toast-error .toast-message-text {
		color: var(--color-danger);
	}

	.toast-warning {
		border-left-color: #d97706;
	}
	.toast-warning .toast-message-text {
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

	@media (max-width: 480px) {
		.toast-container,
		.toast-container--with-details {
			left: 0.85rem;
			right: 0.85rem;
			max-width: none;
		}
	}
</style>
