<!--
	Shared error UI for read-only load failures. Used on list pages
	that can't render their primary content because the API call
	failed. Forms keep their inline `.form-error` callouts; this
	component is for the "the whole list is gone" case.

	Before this, six list pages re-implemented the same icon +
	title + message + (optional) Try-again button markup. They used
	different class names (`.error-banner-inline`, `.state-card
	.state-error`, `.contacts-error`, `.watchdog-card-error`, the
	DashboardCard variant='error', etc.) and the same icon never
	looked the same twice. ErrorCard is the single source of
	truth for that shape.

	Behavior:
	  - `kind` picks the icon + palette (network/auth/server/validation/generic).
	    Each kind has a distinct copy-and-icon combo so a quick
	    glance tells the user what's wrong and what to do.
	  - `retry` adds a "Try again" button (matches the prior inline
	    patterns' behavior). Optional — some pages have no useful
	    retry (e.g. a 4xx validation error should be fixed, not
	    re-tried blind).
	  - `back` adds a "Back" link next to the retry button for
	    pages where the right move is to leave (auth failures,
	    404s, etc.).
	  - role="alert" + aria-live="polite" so screen readers
	    announce the failure as soon as the page renders.
-->
<script lang="ts">
	import Icon, { type IconName } from './Icon.svelte';

	type Kind = 'generic' | 'network' | 'auth' | 'server' | 'validation';

	interface Props {
		title: string;
		message?: string;
		kind?: Kind;
		retry?: () => void;
		back?: { href: string; label?: string };
		compact?: boolean;
	}

	let {
		title,
		message,
		kind = 'generic',
		retry,
		back,
		compact = false,
	}: Props = $props();

	const iconName: IconName = $derived(
		(
			{
				generic: 'help',
				network: 'globe',
				auth: 'help',
				server: 'help',
				validation: 'help',
			} as const
		)[kind]
	);
</script>

<div
	class="error-card error-card-{kind}"
	class:error-card-compact={compact}
	role="alert"
	aria-live="polite"
>
	<span class="error-card-icon" aria-hidden="true">
		<Icon name={iconName} size={20} />
	</span>
	<div class="error-card-body">
		<h3 class="error-card-title">{title}</h3>
		{#if message}
			<p class="error-card-message">{message}</p>
		{/if}
		{#if retry || back}
			<div class="error-card-actions">
				{#if retry}
					<button type="button" class="error-card-retry" onclick={retry}>
						Try again
					</button>
				{/if}
				{#if back}
					<a class="error-card-back" href={back.href}>
						{back.label ?? 'Back'}
					</a>
				{/if}
			</div>
		{/if}
	</div>
</div>

<style>
	.error-card {
		display: flex;
		gap: 0.9rem;
		padding: 1.1rem 1.2rem;
		border-radius: var(--radius-card);
		background: var(--color-danger-bg);
		color: var(--color-danger-text);
		border: 1px solid var(--color-danger-border);
	}
	.error-card-compact {
		padding: 0.7rem 0.9rem;
	}
	.error-card-network {
		background: #fffaf0;
		color: #5a3b00;
		border-color: #fbd38d;
	}
	.error-card-server {
		background: var(--color-danger-bg);
		color: var(--color-danger-text);
		border-color: var(--color-danger-border);
	}
	.error-card-auth {
		background: var(--color-surface);
		color: var(--color-text);
		border-color: var(--color-border-light);
	}
	.error-card-validation {
		background: var(--color-success-bg);
		color: var(--color-success-text);
		border-color: var(--color-success-border);
	}
	.error-card-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 36px;
		height: 36px;
		border-radius: 50%;
		background: var(--color-danger-icon-bg);
		color: var(--color-danger-text);
		flex: 0 0 auto;
	}
	.error-card-network .error-card-icon {
		background: rgba(159, 88, 0, 0.18);
		color: #5a3b00;
	}
	.error-card-server .error-card-icon {
		background: var(--color-danger-icon-bg);
		color: var(--color-danger-text);
	}
	.error-card-auth .error-card-icon {
		background: var(--color-primary-tint);
		color: var(--color-primary);
	}
	.error-card-validation .error-card-icon {
		background: var(--color-success-icon-bg);
		color: var(--color-success-text);
	}
	.error-card-compact .error-card-icon {
		width: 28px;
		height: 28px;
	}
	.error-card-body {
		flex: 1 1 auto;
		min-width: 0;
	}
	.error-card-title {
		margin: 0 0 0.25rem 0;
		font-size: 1rem;
		font-weight: 600;
		line-height: 1.3;
	}
	.error-card-compact .error-card-title {
		font-size: 0.92rem;
	}
	.error-card-message {
		margin: 0;
		font-size: 0.92rem;
		line-height: 1.45;
		opacity: 0.95;
	}
	.error-card-compact .error-card-message {
		font-size: 0.85rem;
	}
	.error-card-actions {
		display: flex;
		gap: 0.6rem;
		margin-top: 0.7rem;
		flex-wrap: wrap;
	}
	.error-card-retry,
	.error-card-back {
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
		padding: 0.4rem 0.85rem;
		border-radius: var(--radius-control);
		font-size: 0.88rem;
		font-weight: 500;
		text-decoration: none;
		cursor: pointer;
		border: 1px solid currentColor;
		background: transparent;
		color: inherit;
	}
	.error-card-retry:hover,
	.error-card-back:hover {
		background: rgba(0, 0, 0, 0.08);
	}
	.error-card-retry {
		background: currentColor;
		color: var(--color-danger-bg);
		border-color: transparent;
	}
	.error-card-network .error-card-retry {
		color: #fffaf0;
	}
	.error-card-server .error-card-retry {
		color: var(--color-danger-bg);
	}
	.error-card-retry:hover {
		opacity: 0.9;
		background: currentColor;
	}
</style>
