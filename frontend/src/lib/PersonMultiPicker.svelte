<!--
  PersonMultiPicker — accessible typeahead combobox for picking MANY Persons.

  Why this exists:
    /casework/new rendered the entire Person catalog (~129 rows,
    growing) as a checkbox grid via {#each persons as person}.
    DOM bloat, no search, no keyboard nav beyond the browser
    default checkbox tab order. The selected-persons M2M field
    on CaseworkRecord is a real, useful relation — the answer is
    to fix the UI, not remove the feature.

  Sister component to PersonPicker (single-pick). Shares:
    - 200ms debounce on input
    - AbortController on in-flight fetch (race-free)
    - Page size capped at 10 so the DOM never balloons
    - Hits /api/persons/?search=<q>&page_size=N
    - Same RBAC posture: never asks for /source/ or any ciphertext

  Multi-pick UX:
    - Selected items render as removable chips ABOVE the input.
      Click ✕ on a chip to remove that one person. Empty state
      collapses the chip row.
    - Input stays visible after a pick (vs. single-pick where it
      collapses into a badge). User can keep typing.
    - Clicking an option that is already selected deselects it
      (toggle semantics, matches common multi-pick conventions).
    - Each chip has aria-label="Remove <name>".
    - listbox has aria-multiselectable="true".

  Performance:
    - Selected set is stored as a Set<number> for O(1) lookup.
    - Fetch + chip rendering only — no full catalog list.
-->
<script lang="ts">
	import { untrack } from 'svelte';

	interface Person {
		id: number;
		name: string;
		country: string | null;
		current_status: string | null;
	}

	interface Props {
		/** Currently-selected Person ids. Order is preserved for display. */
		value: number[];
		/** Fires whenever the selection changes (add or remove). */
		onChange: (ids: number[]) => void;
		disabled?: boolean;
		label?: string;
		inputId?: string;
		/** Optional cap on results per page. Default 10. */
		pageSize?: number;
	}

	let {
		value,
		onChange,
		disabled = false,
		label = 'Linked Persons',
		inputId = 'person-multi-picker',
		pageSize = 10,
	}: Props = $props();

	// --- Local state ---
	let query = $state('');
	let options = $state<Person[]>([]);
	let open = $state(false);
	let loading = $state(false);
	let highlight = $state(0);
	// Indexed by id for O(1) lookup when the API returns a page that
	// includes already-selected people (clicking one toggles them off).
	let optionById = $state<Map<number, Person>>(new Map());
	// Full Person metadata for each selected id (so chips show name).
	// Populated lazily from search results and the per-id fetch effect.
	let selectedById = $state<Map<number, Person>>(new Map());

	// Preserve insertion order so chips are stable (not sorted by id).
	let selectedIds = $state<number[]>(untrack(() => [...value]));

	// Debounce + race-free fetch plumbing.
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;
	let inFlight: AbortController | null = null;
	let inputEl: HTMLInputElement | null = $state(null);
	let listEl: HTMLUListElement | null = $state(null);

	// Sync external value -> local selectedIds. Parent owns the
	// truth; we mirror it on mount / edit-mode hydration.
	$effect(() => {
		// Replace wholesale — the parent has the canonical list.
		selectedIds = [...value];
	});

	async function runSearch(q: string) {
		const term = q.trim();
		if (!term) {
			options = [];
			loading = false;
			return;
		}
		if (inFlight) inFlight.abort();
		const ctrl = new AbortController();
		inFlight = ctrl;
		loading = true;
		try {
			const url = `/api/persons/?search=${encodeURIComponent(term)}&page_size=${pageSize}`;
			const res = await fetch(url, {
				credentials: 'include',
				signal: ctrl.signal,
			});
			if (!res.ok) {
				options = [];
				return;
			}
			const data = (await res.json()) as {
				results?: Array<Record<string, unknown>>;
			};
			const fresh: Person[] = (data.results ?? []).map((r) => ({
				id: Number(r.id),
				name: String(r.name ?? ''),
				country: (r.country as string | null | undefined) ?? null,
				current_status:
					(r.current_status as string | null | undefined) ?? null,
			}));
			options = fresh;
			// Refresh the lookup map; keep prior entries that aren't in
			// this page so we don't lose metadata for previously-seen
			// rows.
			const next = new Map(optionById);
			for (const p of fresh) next.set(p.id, p);
			optionById = next;
			// Mirror into selectedById so a chip immediately renders
			// name + country after a pick without a second fetch.
			const selNext = new Map(selectedById);
			for (const p of fresh) selNext.set(p.id, p);
			selectedById = selNext;
		} catch (err) {
			if ((err as { name?: string })?.name !== 'AbortError') {
				options = [];
			}
		} finally {
			if (inFlight === ctrl) {
				loading = false;
				inFlight = null;
			}
		}
	}

	function debouncedSearch(q: string) {
		if (debounceTimer) clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => {
			void runSearch(q);
		}, 200);
	}

	function isSelected(id: number): boolean {
		return selectedIds.includes(id);
	}

	function toggle(p: Person) {
		if (isSelected(p.id)) {
			remove(p.id);
		} else {
			selectedIds = [...selectedIds, p.id];
			selectedById = new Map(selectedById).set(p.id, p);
			onChange(selectedIds);
		}
		query = '';
		options = [];
		open = false;
		highlight = 0;
		if (inFlight) inFlight.abort();
		inputEl?.focus();
	}

	function remove(id: number) {
		selectedIds = selectedIds.filter((x) => x !== id);
		onChange(selectedIds);
		// Keep selectedById metadata in case the user re-picks later —
		// it's cheap, and avoids a re-fetch.
	}

	function clearAll() {
		selectedIds = [];
		onChange([]);
		inputEl?.focus();
	}

	function onInput(e: Event) {
		const v = (e.target as HTMLInputElement).value;
		query = v;
		open = true;
		highlight = 0;
		debouncedSearch(v);
	}

	function onKeydown(e: KeyboardEvent) {
		// Open the menu on first interaction even if the user hasn't typed.
		if (!open && (e.key === 'ArrowDown' || e.key === 'Enter')) {
			open = true;
			if (e.key === 'ArrowDown') e.preventDefault();
			return;
		}
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			highlight = Math.min(highlight + 1, options.length - 1);
			scrollHighlightIntoView();
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			highlight = Math.max(highlight - 1, 0);
			scrollHighlightIntoView();
		} else if (e.key === 'Enter') {
			if (options[highlight]) {
				e.preventDefault();
				toggle(options[highlight]);
			}
		} else if (e.key === 'Escape') {
			open = false;
		} else if (e.key === 'Backspace' && query === '' && selectedIds.length > 0) {
			// Convenient: backspace on empty input pops the most recent
			// chip — common UX in token-style multi-pickers.
			e.preventDefault();
			const last = selectedIds[selectedIds.length - 1];
			remove(last);
		}
	}

	function scrollHighlightIntoView() {
		queueMicrotask(() => {
			const el = listEl?.querySelector<HTMLElement>(
				`[data-index="${highlight}"]`,
			);
			el?.scrollIntoView({ block: 'nearest' });
		});
	}

	function onFocusInput() {
		open = true;
	}

	function onBlurInput() {
		// Delay so a mousedown on an option lands before the listbox
		// unmounts (browsers fire blur before click).
		setTimeout(() => {
			open = false;
		}, 120);
	}
</script>

<div class="person-multi-picker" data-testid="person-multi-picker">
	<label for={inputId} class="person-multi-picker-label">
		{label}
		<span class="person-multi-picker-hint">
			Type to search by name or country. Click a result to add or remove.
		</span>
	</label>

	{#if selectedIds.length > 0}
		<ul class="chips" aria-label="Selected persons">
			{#each selectedIds as id (id)}
				{@const person = selectedById.get(id)}
				<li class="chip">
					<span class="chip-name">{person?.name ?? `Person #${id}`}</span>
					{#if person?.country}
						<span class="chip-meta">{person.country}</span>
					{/if}
					<button
						type="button"
						class="chip-remove"
						onclick={() => remove(id)}
						disabled={disabled}
						aria-label={`Remove ${person?.name ?? `person ${id}`}`}
					>
						✕
					</button>
				</li>
			{/each}
			<li class="chip-clear-wrap">
				<button
					type="button"
					class="chip-clear-all"
					onclick={clearAll}
					disabled={disabled}
				>
					Clear all
				</button>
			</li>
		</ul>
	{/if}

	<div class="input-wrap">
		<input
			id={inputId}
			bind:this={inputEl}
			type="text"
			autocomplete="off"
			spellcheck="false"
			role="combobox"
			aria-expanded={open}
			aria-autocomplete="list"
			aria-controls={`${inputId}-listbox`}
			aria-activedescendant={
				open && options[highlight] ? `${inputId}-opt-${options[highlight].id}` : undefined
			}
			{disabled}
			value={query}
			placeholder="Search persons…"
			oninput={onInput}
			onkeydown={onKeydown}
			onfocus={onFocusInput}
			onblur={onBlurInput}
		/>

		{#if open}
			<ul
				id={`${inputId}-listbox`}
				role="listbox"
				aria-multiselectable="true"
				class="options"
				bind:this={listEl}
			>
				{#if loading && options.length === 0}
					<li class="loading" aria-busy="true">Loading…</li>
				{/if}
				{#if !loading && query.trim() !== '' && options.length === 0}
					<li class="empty">No matches.</li>
				{/if}
				{#each options as opt, i (opt.id)}
					<li
						id={`${inputId}-opt-${opt.id}`}
						role="option"
						data-index={i}
						aria-selected={isSelected(opt.id)}
						class="option"
						class:highlight={i === highlight}
						class:is-selected={isSelected(opt.id)}
						onmousedown={(e) => {
							e.preventDefault();
							toggle(opt);
						}}
					>
						<span class="opt-name">{opt.name}</span>
						{#if opt.country || opt.current_status}
							<span class="opt-meta">
								{#if opt.country}{opt.country}{/if}
								{#if opt.country && opt.current_status} · {/if}
								{#if opt.current_status}{opt.current_status}{/if}
							</span>
						{/if}
						{#if isSelected(opt.id)}
							<span class="opt-check" aria-hidden="true">✓</span>
						{/if}
					</li>
				{/each}
			</ul>
		{/if}
	</div>
</div>

<style>
	.person-multi-picker {
		position: relative;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.person-multi-picker-label {
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
		font-size: 0.85rem;
		font-weight: 600;
		color: var(--color-text, #222);
	}

	.person-multi-picker-hint {
		font-size: 0.72rem;
		font-weight: 400;
		color: var(--color-text-muted, #666);
	}

	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.chip {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.3rem 0.55rem;
		background: var(--color-primary-light, #dde5ff);
		border: 1px solid var(--color-primary, #256);
		border-radius: 999px;
		font-size: 0.82rem;
		color: var(--color-text, #222);
	}

	.chip-name {
		font-weight: 700;
	}

	.chip-meta {
		color: var(--color-text-muted, #666);
		font-size: 0.75rem;
	}

	.chip-remove {
		background: transparent;
		border: none;
		font-size: 0.9rem;
		line-height: 1;
		padding: 0 0.2rem;
		cursor: pointer;
		color: var(--color-text-muted, #666);
		border-radius: 999px;
	}

	.chip-remove:hover:not(:disabled) {
		background: var(--color-bg-white, #fff);
		color: var(--color-danger, #c00);
	}

	.chip-remove:focus-visible {
		outline: 2px solid var(--color-primary, #256);
		outline-offset: 1px;
	}

	.chip-clear-wrap {
		list-style: none;
	}

	.chip-clear-all {
		background: transparent;
		border: none;
		padding: 0.3rem 0.55rem;
		font-size: 0.78rem;
		font-weight: 600;
		color: var(--color-text-muted, #666);
		cursor: pointer;
		border-radius: var(--radius-input, 4px);
	}

	.chip-clear-all:hover:not(:disabled) {
		color: var(--color-text, #222);
		background: var(--color-section-bg, #f5f5f5);
	}

	.input-wrap {
		position: relative;
	}

	input[type='text'] {
		font: inherit;
		padding: 0.55rem 0.7rem;
		border: 1px solid var(--color-border, #ccc);
		border-radius: var(--radius-input, 6px);
		background: var(--color-bg-white, #fff);
		color: var(--color-text, #222);
		width: 100%;
		box-sizing: border-box;
	}

	input[type='text']:focus-visible {
		outline: 2px solid var(--color-primary, #256);
		outline-offset: 1px;
		border-color: var(--color-primary, #256);
	}

	.options {
		position: absolute;
		top: calc(100% + 0.25rem);
		left: 0;
		right: 0;
		margin: 0;
		padding: 0.25rem 0;
		list-style: none;
		background: var(--color-bg-white, #fff);
		border: 1px solid var(--color-border, #ccc);
		border-radius: var(--radius-input, 6px);
		box-shadow: var(--shadow-card, 0 4px 12px rgba(0, 0, 0, 0.08));
		max-height: 18rem;
		overflow-y: auto;
		z-index: 30;
	}

	.option {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 0.7rem;
		cursor: pointer;
		user-select: none;
	}

	.option.highlight,
	.option:hover {
		background: var(--color-section-bg, #f5f5f5);
	}

	.option.is-selected {
		background: var(--color-primary-light, #dde5ff);
	}

	.option.is-selected.highlight,
	.option.is-selected:hover {
		background: var(--color-primary, #256);
		color: var(--color-text-light, #fff);
	}

	.opt-name {
		font-weight: 600;
	}

	.opt-meta {
		font-size: 0.78rem;
		color: var(--color-text-muted, #666);
	}

	.opt-check {
		margin-left: auto;
		font-weight: 700;
	}

	.loading,
	.empty {
		padding: 0.6rem 0.7rem;
		color: var(--color-text-muted, #666);
		font-size: 0.85rem;
		font-style: italic;
	}
</style>