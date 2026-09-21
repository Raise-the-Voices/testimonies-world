<!--
  SourcesField — repeating-row list of `Source` entries for a Report.

  Extracted from ReportForm.svelte's inline sections (originally lines
  130-198, 233-244, 737-847) so the same UX powers both the
  `/reports` modal and the `/submit` form. The component emits only
  the repeating rows + the "+ Add another" button; the parent wraps it
  in its own section chrome (fieldset on ReportForm, div+h2 on /submit).

  Data model: each SourceEntry mirrors the backend `Source` writable
  fields (`source_type`, `source_attribution`, `date_start`, `narrative`,
  `is_private`). The parent filters out empty rows before submit; see
  ReportForm.handleSubmit for the filter rule.

  Props:
    entries  — bound array of SourceEntry. The parent reads it on
               submit; the component owns add/remove mutations.
    disabled — disables inputs and the Add button (used during save).
-->
<script lang="ts">
	import type { Report } from '$lib/types';

	export interface SourceEntry {
		/** Monotonic local id for keyed `{#each}`. Not the backend id. */
		uid: number;
		source_type: Report['source_type'];
		source_attribution: string;
		date_start: string;
		narrative: string;
		is_private: boolean;
	}

	interface Props {
		entries: SourceEntry[];
		disabled?: boolean;
	}
	let { entries = $bindable(), disabled = false }: Props = $props();

	// Mirrors backend `Report.SourceType.choices` + the per-type help
	// strings used by the existing report-create form. Kept here (not
	// in api.ts) so the source-of-truth for display stays next to the
	// form that renders it.
	const sourceTypeLabels: Record<Report['source_type'], string> = {
		firsthand: 'Firsthand',
		secondhand: 'Secondhand',
		news: 'News report',
		document: 'Document',
	};
	const sourceTypeHelp: Record<Report['source_type'], string> = {
		firsthand: 'From someone who directly witnessed or experienced the event.',
		secondhand: 'From someone close to the event (family, neighbor, colleague).',
		news: 'From a media report — link the source in the attribution field.',
		document: 'From an official document, court filing, or organizational report.',
	};

	// Field ceilings — kept in sync with backend model fields.
	const MAX_NARRATIVE = 5000;
	const MAX_SHORT = 500;

	// Module-local counter so successive `+ Add another` clicks produce
	// distinct uids even if entries are added/removed across mounts.
	let nextLocalUid = 1;
	function makeEntry(): SourceEntry {
		return {
			uid: nextLocalUid++,
			source_type: 'firsthand',
			source_attribution: '',
			date_start: '',
			narrative: '',
			is_private: false,
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
			<h4 class="repeatable-entry-title">Source #{i + 1}</h4>
			<button
				type="button"
				class="repeatable-entry-remove"
				aria-label="Remove source {i + 1}"
				onclick={() => remove(i)}
				disabled={disabled}
			>✕ Remove</button>
		</div>

		<div class="grid-2">
			<div class="field">
				<label for="src-{entry.uid}-type">Source type</label>
				<select
					id="src-{entry.uid}-type"
					class="input--search"
					bind:value={entry.source_type}
					disabled={disabled}
				>
					{#each Object.entries(sourceTypeLabels) as [value, label] (value)}
						<option {value}>{label}</option>
					{/each}
				</select>
				<p class="field-hint">{sourceTypeHelp[entry.source_type]}</p>
			</div>

			<div class="field">
				<label for="src-{entry.uid}-attr">
					Source attribution
					<span class="badge-public" title="Shown publicly">public</span>
				</label>
				<input
					id="src-{entry.uid}-attr"
					type="text"
					class="input--search"
					bind:value={entry.source_attribution}
					placeholder='e.g. "family member", "BBC article"'
					maxlength={MAX_SHORT}
					autocomplete="off"
					disabled={disabled}
				/>
			</div>

			<div class="field">
				<label for="src-{entry.uid}-date">Date start</label>
				<input
					id="src-{entry.uid}-date"
					type="date"
					class="input--search"
					bind:value={entry.date_start}
					disabled={disabled}
				/>
			</div>

			<div class="field">
				<label class="field-checkbox">
					<input
						type="checkbox"
						bind:checked={entry.is_private}
						disabled={disabled}
					/>
					<span>Mark this source as private</span>
				</label>
				<p class="field-hint">
					Private sources are hidden from public reads,
					even on a public report.
				</p>
			</div>
		</div>

		<div class="field field-full">
			<label for="src-{entry.uid}-narrative">Narrative</label>
			<textarea
				id="src-{entry.uid}-narrative"
				class="input--search"
				bind:value={entry.narrative}
				maxlength={MAX_NARRATIVE}
				placeholder="What does this source say happened? Dates, places, context."
				disabled={disabled}
			></textarea>
			<div class="field-counter" aria-live="polite">
				{entry.narrative.length} / {MAX_NARRATIVE}
			</div>
		</div>
	</div>
{/each}

<button
	type="button"
	class="repeatable-add"
	onclick={add}
	disabled={disabled}
>+ Add another</button>

<style>
	/* === Repeating entries (Sources) === */
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

	/* === 2-column grid for paired fields === */
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
	.field-counter {
		font-size: 0.78rem;
		color: var(--color-text-muted);
		text-align: right;
	}
	.field-checkbox {
		display: inline-flex;
		align-items: center;
		gap: 0.55rem;
		font-size: 0.95rem;
		color: var(--color-text);
		cursor: pointer;
		user-select: none;
	}
	.field-checkbox input[type='checkbox'] {
		width: 18px;
		height: 18px;
		accent-color: var(--color-primary);
		cursor: pointer;
	}
	.field .input--search,
	.field textarea.input--search {
		font-size: 0.95rem;
		padding: 0.55rem 0.85rem;
	}
	.field textarea.input--search {
		min-height: 110px;
		resize: vertical;
		font-family: inherit;
		line-height: 1.55;
	}

	/* === Privacy badges on labels === */
	.badge-public {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.1rem 0.5rem;
		border-radius: 999px;
		font-size: 0.68rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.04rem;
		line-height: 1.2;
		background: #c6f6d5;
		color: #22543d;
	}
</style>
