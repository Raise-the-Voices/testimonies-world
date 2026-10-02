<!--
  MediaField — link-only media row component used on /submit.

  Per the 2026-10-02 product decision, the volunteer-facing surface
  accepts external URLs only. No file/binary uploads, no storage,
  no nginx serving — the media row stores `url` and the browser
  fetches the destination directly. The repeated row UI on /submit is
  the second place where the choice lives; this file mirrors the
  simplification in MediaUploadModal.svelte.

  The `allowFileUpload` prop has been removed: file uploads are no
  longer a volunteer option, so there is no second surface to gate.
-->
<script lang="ts">
	import type { Visibility } from '$lib/types';

	export interface MediaEntry {
		/** Monotonic local id for keyed `{#each}`. Not the backend id. */
		uid: number;
		media_type: 'link';
		visibility: Visibility;
		description: string;
		url: string;
	}

	interface Props {
		entries: MediaEntry[];
		disabled?: boolean;
		canMarkSensitive?: boolean;
	}
	let {
		entries = $bindable(),
		disabled = false,
		canMarkSensitive = true,
	}: Props = $props();

	const visibilityLabels: Record<Visibility, string> = {
		public: 'Public — anyone can view',
		restricted: 'Restricted — authenticated users only',
		sensitive: 'Sensitive — advocates/admin only',
	};
	const visibilities = $derived<Visibility[]>(
		canMarkSensitive
			? ['public', 'restricted', 'sensitive']
			: ['public', 'restricted'],
	);

	const MAX_DESC = 500;

	let moduleLocalUid = 1;
	function makeEntry(): MediaEntry {
		return {
			uid: moduleLocalUid++,
			media_type: 'link',
			visibility: 'public',
			description: '',
			url: '',
		};
	}
	function add() {
		entries = [...entries, makeEntry()];
	}
	function remove(idx: number) {
		entries = entries.filter((_, i) => i !== idx);
	}
</script>

{#each entries as entry, i (entry.uid)}
	<div class="repeatable-entry" data-index={i}>
		<div class="repeatable-entry-header">
			<h4 class="repeatable-entry-title">Media #{i + 1}</h4>
			<button
				type="button"
				class="repeatable-entry-remove"
				aria-label="Remove media {i + 1}"
				onclick={() => remove(i)}
				disabled={disabled}
			>✕ Remove</button>
		</div>

		<div class="grid-2">
			<div class="field">
				<label for="med-{entry.uid}-vis">Visibility</label>
				<select
					id="med-{entry.uid}-vis"
					class="input--search"
					bind:value={entry.visibility}
					disabled={disabled}
				>
					{#each visibilities as v (v)}
						<option value={v}>{visibilityLabels[v]}</option>
					{/each}
				</select>
			</div>

			<div class="field field-full">
				<label for="med-{entry.uid}-url">URL</label>
				<input
					id="med-{entry.uid}-url"
					type="url"
					class="input--search"
					bind:value={entry.url}
					placeholder="https://example.org/document.pdf"
					maxlength={1000}
					autocomplete="off"
					disabled={disabled}
					required
				/>
			</div>

			<div class="field field-full">
				<label for="med-{entry.uid}-desc">
					Description <span class="optional-mark">(optional)</span>
				</label>
				<input
					id="med-{entry.uid}-desc"
					type="text"
					class="input--search"
					bind:value={entry.description}
					placeholder="What is this link? Alt text for images."
					maxlength={MAX_DESC}
					autocomplete="off"
					disabled={disabled}
				/>
			</div>
		</div>
	</div>
{/each}

<button
	type="button"
	class="repeatable-add"
	onclick={add}
	disabled={disabled}
>+ Add another Media</button>

<style>
	.repeatable-entry {
		display: flex;
		flex-direction: column;
		gap: 0.85rem;
		padding: 1rem 1.1rem;
		border: 1px solid var(--color-border-light);
		border-left: 3px solid var(--color-primary-light, #aac0ff);
		border-radius: var(--radius-card);
		background: var(--color-surface, #f7f7f9);
	}
	.repeatable-entry + .repeatable-entry {
		margin-top: 0.75rem;
	}
	.repeatable-entry-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		margin-bottom: 0.1rem;
	}
	.repeatable-entry-title {
		margin: 0;
		font-size: 0.92rem;
		font-weight: 700;
		color: var(--color-text);
	}
	.repeatable-entry-remove {
		background: transparent;
		border: 1px solid var(--color-border-light);
		color: var(--color-danger, #c53030);
		font-size: 0.78rem;
		padding: 0.25rem 0.65rem;
		border-radius: var(--radius-card);
		cursor: pointer;
		font-weight: 600;
		min-height: 0;
	}
	.repeatable-entry-remove:hover:not(:disabled) {
		background: #fed7d7;
		border-color: #feb2b2;
	}
	.repeatable-entry-remove:disabled {
		opacity: 0.55;
		cursor: not-allowed;
	}
	.field {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
		min-width: 0;
	}
	.field label {
		font-size: 0.85rem;
		font-weight: 600;
		color: var(--color-text);
	}
	.optional-mark {
		font-weight: 400;
		color: var(--color-text-muted);
		font-size: 0.8rem;
	}
	.grid-2 {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.85rem;
	}
	.field-full { grid-column: 1 / -1; }
	.input--search {
		min-height: 38px;
		padding: 0.45rem 0.7rem;
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-input, 6px);
		background: var(--color-bg-white, #fff);
		color: var(--color-text, #222);
		font-size: 0.9rem;
	}
	.input--search:focus {
		outline: none;
		border-color: var(--color-primary);
		box-shadow: 0 0 0 3px rgba(64, 110, 192, 0.18);
	}
	.input--search:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}
	.repeatable-add {
		margin-top: 0.85rem;
		background: transparent;
		border: 1px dashed var(--color-primary-light, #aac0ff);
		color: var(--color-primary);
		font-size: 0.88rem;
		font-weight: 600;
		padding: 0.55rem 0.9rem;
		border-radius: var(--radius-card);
		cursor: pointer;
	}
	.repeatable-add:hover:not(:disabled) {
		background: var(--color-primary-tint, #eef3ff);
	}
	.repeatable-add:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	@media (max-width: 600px) {
		.grid-2 { grid-template-columns: 1fr; }
	}
</style>