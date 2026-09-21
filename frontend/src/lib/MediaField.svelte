<!--
  MediaField — repeating-row list of `Media` entries for a Report.

  Extracted from ReportForm.svelte's inline section (originally lines
  142-149, 178-198, 853-955) so the same UX powers both the
  `/reports` modal and the `/submit` form. The component emits only
  the repeating rows + the "+ Add another" button; the parent wraps it
  in its own section chrome (fieldset on ReportForm, div+h2 on /submit).

  Data model: each MediaEntry mirrors the backend `Media` writable
  fields (`media_type`, `visibility`, `description`, `url`). The
  optional `file: File | null` lives only on the client — it is set
  by the file input, consumed by the parent's multipart POST on submit,
  and stripped before any draft persistence.

  Wire-format note: parent branches on `entry.file ? 'multipart' :
  'json'` per row (see submit/+page.svelte handleSubmit). A row with
  both file and url is a programmer error — the multipart branch wins
  and url is dropped.

  Props:
    entries          — bound array of MediaEntry.
    disabled         — disables inputs and the Add button.
    canMarkSensitive — when false, the `sensitive` visibility option
                       is hidden from the dropdown (matches
                       MediaUploadModal's UX; backend still 403s as a
                       last line of defense per MediaViewSet line 904).
    allowFileUpload  — when true, each row shows a file input in
                       addition to the URL input. The two are not
                       mutually exclusive in the UI; the parent's
                       submit handler picks one wire format per row.
-->
<script lang="ts">
	import type { MediaType, Visibility } from '$lib/types';

	export interface MediaEntry {
		/** Monotonic local id for keyed `{#each}`. Not the backend id. */
		uid: number;
		media_type: MediaType;
		visibility: Visibility;
		description: string;
		url: string;
		/** Optional file picked via the file input. Never persisted to
		 *  the draft — see submit/+page.svelte buildDraftPayload for the
		 *  strip-on-serialize rule. */
		file?: File | null;
	}

	interface Props {
		entries: MediaEntry[];
		disabled?: boolean;
		canMarkSensitive?: boolean;
		allowFileUpload?: boolean;
	}
	let {
		entries = $bindable(),
		disabled = false,
		// Default `true` to preserve the prior inline ReportForm behavior
		// (it always showed all 3 visibility options). New call sites that
		// want role-based gating — like /submit — pass `false` for non-
		// advocates and the dropdown filters accordingly.
		canMarkSensitive = true,
		allowFileUpload = false,
	}: Props = $props();

	const mediaTypeLabels: Record<MediaType, string> = {
		photo: 'Photo',
		video: 'Video',
		document: 'Document',
		link: 'External link',
	};
	// Order matches MediaUploadModal (line 38) so the dropdown reads
	// the same on both surfaces.
	const mediaTypes: MediaType[] = ['photo', 'video', 'document', 'link'];

	const visibilityLabels: Record<Visibility, string> = {
		public: 'Public — anyone can view',
		restricted: 'Restricted — authenticated users only',
		sensitive: 'Sensitive — advocates/admin only',
	};
	// Reactive: hide `sensitive` if the user can't mark it. `$derived`
	// re-evaluates when the prop changes (e.g. session refresh upgrades
	// role) so the option appears without remount.
	const visibilities = $derived<Visibility[]>(
		canMarkSensitive
			? ['public', 'restricted', 'sensitive']
			: ['public', 'restricted'],
	);

	const MAX_DESC = 500;
	// Mirrors MediaUploadModal line 64 — keep client-side cap consistent
	// so the inline error message and the modal error message read the
	// same. Backend accepts up to 50 MB (models.py MAX_UPLOAD_BYTES);
	// the lower client cap avoids the user picking something the server
	// will reject with a less-helpful message.
	const MAX_FILE_BYTES = 25 * 1024 * 1024;

	let moduleLocalUid = 1;
	function makeEntry(): MediaEntry {
		return {
			uid: moduleLocalUid++,
			media_type: 'photo',
			visibility: 'public',
			description: '',
			url: '',
			file: null,
		};
	}
	function add() {
		entries = [...entries, makeEntry()];
	}
	function remove(idx: number) {
		entries = entries.filter((_, i) => i !== idx);
	}
	function onFileChange(idx: number, e: Event) {
		const input = e.currentTarget as HTMLInputElement;
		const file = input.files && input.files.length > 0 ? input.files[0] : null;
		// Mutate the array in place — `bind:entries` reflects the
		// reactive write because we're inside the component. Parent
		// reads the final array on submit.
		entries[idx] = { ...entries[idx], file };
	}

	/** Per-row file-size error message, surfaced under the file input.
	 *  Empty string when the row's file is within the cap. */
	function fileSizeError(entry: MediaEntry): string {
		if (!entry.file) return '';
		if (entry.file.size > MAX_FILE_BYTES) {
			return `File too large (${(entry.file.size / 1024 / 1024).toFixed(1)} MB). Max 25 MB.`;
		}
		return '';
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
				<label for="med-{entry.uid}-type">Media type</label>
				<select
					id="med-{entry.uid}-type"
					class="input--search"
					bind:value={entry.media_type}
					disabled={disabled}
				>
					{#each mediaTypes as t (t)}
						<option value={t}>{mediaTypeLabels[t]}</option>
					{/each}
				</select>
			</div>

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
				<label for="med-{entry.uid}-desc">
					Description <span class="optional-mark">(optional)</span>
				</label>
				<input
					id="med-{entry.uid}-desc"
					type="text"
					class="input--search"
					bind:value={entry.description}
					placeholder="What's in this media? Alt text for images."
					maxlength={MAX_DESC}
					autocomplete="off"
					disabled={disabled}
				/>
			</div>

			{#if allowFileUpload}
				<div class="field field-full">
					<label for="med-{entry.uid}-file">
						Upload a file <span class="optional-mark">(optional — pick a file or paste a URL)</span>
					</label>
					<input
						id="med-{entry.uid}-file"
						type="file"
						class="input--file"
						accept="image/*,video/*,application/pdf"
						onchange={(e) => onFileChange(i, e)}
						disabled={disabled}
					/>
					{#if entry.file}
						<p class="field-hint">
							Selected: <strong>{entry.file.name}</strong>
							({(entry.file.size / 1024 / 1024).toFixed(2)} MB)
						</p>
					{/if}
					{#if fileSizeError(entry)}
						<p class="field-error">{fileSizeError(entry)}</p>
					{/if}
				</div>
			{/if}

			<div class="field field-full">
				<label for="med-{entry.uid}-url">
					{allowFileUpload ? 'Or paste a URL' : 'File URL'}
					<span class="optional-mark">(optional)</span>
				</label>
				<input
					id="med-{entry.uid}-url"
					type="url"
					class="input--search"
					bind:value={entry.url}
					placeholder="https://…"
					maxlength={1000}
					autocomplete="off"
					disabled={disabled}
				/>
				<p class="field-hint">
					{#if allowFileUpload}
						{#if entry.file}
							URL ignored — file takes precedence on submit.
						{:else}
							Use this when you only have a link, no file to upload.
						{/if}
					{:else}
						Paste a URL to an external link.
					{/if}
				</p>
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
	/* === Repeating entries (Media) === */
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
	.repeatable-add {
		width: 100%;
		margin-top: 0.85rem;
		padding: 0.6rem 0.85rem;
		background: var(--color-bg-white);
		border: 1px dashed var(--color-border-light);
		color: var(--color-primary);
		font-size: 0.9rem;
		font-weight: 600;
		border-radius: var(--radius-card);
		cursor: pointer;
		min-height: 0;
	}
	.repeatable-add:hover:not(:disabled) {
		background: var(--color-surface, #f7f7f9);
		border-style: solid;
		border-color: var(--color-primary-light);
	}
	.repeatable-add:disabled {
		opacity: 0.55;
		cursor: not-allowed;
	}

	/* === 2-column grid === */
	.grid-2 {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 1rem 1.25rem;
	}
	.field-full {
		grid-column: 1 / -1;
	}
	@media (max-width: 720px) {
		.grid-2 {
			grid-template-columns: 1fr;
		}
	}

	/* === Field chrome === */
	.field {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
		min-width: 0;
	}
	.field label {
		display: inline-flex;
		align-items: center;
		gap: 0.45rem;
		font-size: 0.85rem;
		font-weight: 600;
		color: var(--color-text);
		margin: 0;
		flex-wrap: wrap;
	}
	.field-hint {
		margin: 0;
		font-size: 0.78rem;
		color: var(--color-text-muted);
		line-height: 1.45;
	}
	.field-error {
		margin: 0;
		font-size: 0.82rem;
		color: var(--color-danger);
	}
	.field .input--search,
	.field .input--file {
		font-size: 0.95rem;
		padding: 0.55rem 0.85rem;
	}

	/* === Required / optional markers === */
	.optional-mark {
		color: var(--color-text-muted);
		font-size: 0.78rem;
		font-weight: 400;
	}
</style>
