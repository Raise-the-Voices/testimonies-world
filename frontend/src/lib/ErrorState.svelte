<!--
  ErrorState - shared inline error component with an optional retry
  button. Replaces the .error-state block previously duplicated in
  statistics/+page.svelte and any other page that needed it.

  Accepts any of the common error shapes so callers don't have to
  pre-normalise before passing in:
    - NormalisedError (from $lib/api/handleError)
    - native Error
    - string (treated as the message)

  When `error` is null the component renders nothing — that's the
  expected "no error" state, so callers can drop it into the error
  branch of {#if error}{#snippet fallback}{:else}{:else if}{/if}
  without a guard.
-->
<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { NormalisedError } from '$lib/api/handleError';

	type ErrorInput = NormalisedError | Error | string | null;

	interface Props {
		error: ErrorInput;
		/** Optional override for the headline. Defaults to a generic copy. */
		title?: string;
		/** When provided, renders a Retry button that invokes this. */
		onRetry?: () => void;
		children?: Snippet;
	}

	let { error, title = 'Could not load this section', onRetry, children }: Props = $props();

	const message = $derived.by<string>(() => {
		if (!error) return '';
		if (typeof error === 'string') return error;
		return error.message;
	});
</script>

{#if error}
	<div class="error-state" role="alert">
		<p class="error-state-message">{title}: {message}</p>
		{#if children}{@render children()}{/if}
		{#if onRetry}
			<button type="button" class="btn btn-secondary" onclick={onRetry}>Retry</button>
		{/if}
	</div>
{/if}

<style>
	.error-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
		padding: 3rem 1rem;
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-left: 3px solid var(--color-danger);
		border-radius: var(--radius-card);
		text-align: center;
	}
	.error-state-message {
		margin: 0;
		color: var(--color-text-muted);
		max-width: var(--max-w-prose);
	}
</style>
