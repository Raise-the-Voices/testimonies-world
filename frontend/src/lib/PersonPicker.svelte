<!--
  PersonPicker — accessible typeahead combobox for picking one Person.

  Why this exists:
    The TestimonialForm previously had no UI for the testimonial's
    `person` FK (the API accepts `person: number | null` on write,
    but the form dropped it). The operator was expected to know
    a Person ID by heart. For a single-pick UX we replace that
    with this component.

  UX contract:
    - Type to search; debounced 200ms; results fetched from
      `GET /api/persons/?search=<q>&page_size=10`.
    - Up to 10 matches shown. Each row: name · country · current_status.
    - Keyboard nav: ArrowDown / ArrowUp / Enter / Escape.
    - Selected value rendered as a removable badge ("Asma Khan
      · Pakistan ✕"). Click ✕ to clear.
    - ARIA combobox pattern: input is the combobox, options live
      in role="listbox", each option has aria-selected.

  Security / RBAC:
    - Hits `GET /api/persons/`. RBAC is enforced server-side via
      `IsAuthenticatedOrReadOnly` plus per-field gates on the
      serializer (medical_notes / precise_location / encrypted
      columns are server-side stripped for unprivileged viewers).
      We never request `source_encrypted` or any ciphertext —
      the open API serializer doesn't expose them.
    - No person IDs are logged or echoed to the page outside the
      ARIA wiring.
    - The picker does NOT load the encrypted-source fields from
      `/api/testimonials/{id}/source/` even if the user has
      `CanViewEncryptedSource` — that's a separate code path and
      out of scope for a UI picker.

  Performance:
    - 200ms debounce on input.
    - Aborts in-flight requests when the query changes (race-free).
    - Page size capped at 10 so the DOM never balloons. The previous
      "129 static checkboxes" failure mode (which motivated this
      component) is impossible here regardless of catalog size.

  Out of scope (intentionally):
    - Linking a testimonial to MULTIPLE persons. The data model only
      supports `person` (singular FK). Multi-link would require a
      schema change, an export-contract bump, and a separate review.
-->
<script lang="ts">
	interface Person {
		id: number;
		name: string;
		country: string | null;
		current_status: string | null;
	}

	interface Props {
		/** Currently-selected Person id (the FK stored on the testimonial). */
		value: number | null;
		/** Fires when the user picks a person or clears the selection. */
		onChange: (id: number | null) => void;
		disabled?: boolean;
		label?: string;
		inputId?: string;
		/** Optional cap on results. Default 10 keeps the DOM small. */
		pageSize?: number;
	}

	let {
		value,
		onChange,
		disabled = false,
		label = 'Linked Person',
		inputId = 'person-picker',
		pageSize = 10,
	}: Props = $props();

	// --- Local state ---
	let query = $state('');
	let options = $state<Person[]>([]);
	let open = $state(false);
	let loading = $state(false);
	let highlight = $state(0);
	let selected = $state<Person | null>(null);
	let inputEl: HTMLInputElement | null = $state(null);
	let listEl: HTMLUListElement | null = $state(null);

	// Debounce + race-free fetch. We keep an AbortController per request;
	// a newer keystroke aborts the older one so the dropdown never shows
	// stale results that landed after the user typed past them.
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;
	let inFlight: AbortController | null = null;

	function debouncedSearch(q: string) {
		if (debounceTimer) clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => {
			void runSearch(q);
		}, 200);
	}

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
			const data = (await res.json()) as { results?: Array<Record<string, unknown>> };
			options = (data.results ?? []).map((r) => ({
				id: Number(r.id),
				name: String(r.name ?? ''),
				country: (r.country as string | null | undefined) ?? null,
				current_status:
					(r.current_status as string | null | undefined) ?? null,
			}));
		} catch (err) {
			// AbortError from our own cancel; silent. Anything else is
			// network — the dropdown just stays empty.
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

	// Fetch the selected Person by id when the parent supplies a value
	// (edit-mode hydration) — gives us the badge text without the
	// parent having to pre-load the full Person row.
	$effect(() => {
		if (value === null) {
			selected = null;
			return;
		}
		if (selected && selected.id === value) return;
		void (async () => {
			try {
				const res = await fetch(`/api/persons/${value}/`, {
					credentials: 'include',
				});
				if (!res.ok) return;
				const r = (await res.json()) as Record<string, unknown>;
				selected = {
					id: Number(r.id),
					name: String(r.name ?? ''),
					country: (r.country as string | null | undefined) ?? null,
					current_status:
						(r.current_status as string | null | undefined) ?? null,
				};
			} catch {
				/* ignore — badge stays empty if the fetch fails */
			}
		})();
	});

	// --- Input handlers ---

	function onInput(e: Event) {
		const v = (e.target as HTMLInputElement).value;
		query = v;
		open = true;
		highlight = 0;
		debouncedSearch(v);
	}

	function pick(p: Person) {
		onChange(p.id);
		selected = p;
		query = '';
		options = [];
		open = false;
		highlight = 0;
		if (inFlight) inFlight.abort();
		inputEl?.blur();
	}

	function clear() {
		onChange(null);
		selected = null;
		query = '';
		options = [];
		open = false;
		highlight = 0;
		if (inFlight) inFlight.abort();
		inputEl?.focus();
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
				pick(options[highlight]);
			}
		} else if (e.key === 'Escape') {
			open = false;
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

	function onFocus() {
		open = true;
	}

	function onBlur() {
		// Delay closing so a mousedown on an option has time to land
		// before the listbox unmounts (browsers fire blur before click).
		setTimeout(() => {
			open = false;
		}, 120);
	}
</script>

<div class="person-picker" data-testid="person-picker">
	<label for={inputId} class="person-picker-label">
		{label}
		<span class="person-picker-hint">Type to search by name or country</span>
	</label>

	{#if selected && !open}
		<div class="selected-badge" role="status">
			<span class="badge-name">{selected.name}</span>
			{#if selected.country || selected.current_status}
				<span class="badge-meta">
					{#if selected.country}{selected.country}{/if}
					{#if selected.country && selected.current_status} · {/if}
					{#if selected.current_status}{selected.current_status}{/if}
				</span>
			{/if}
			<button
				type="button"
				class="clear-btn"
				onclick={clear}
				disabled={disabled}
				aria-label="Clear selection"
			>
				✕
			</button>
		</div>
	{:else}
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
			placeholder="e.g. Khuzdar, Pakistan, or a name…"
			oninput={onInput}
			onkeydown={onKeydown}
			onfocus={onFocus}
			onblur={onBlur}
		/>

		{#if open}
			<ul
				id={`${inputId}-listbox`}
				role="listbox"
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
						aria-selected={i === highlight}
						class="option"
						class:highlight={i === highlight}
						onmousedown={(e) => {
							e.preventDefault();
							pick(opt);
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
					</li>
				{/each}
			</ul>
		{/if}
	{/if}
</div>

<style>
	.person-picker {
		position: relative;
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}

	.person-picker-label {
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
		font-size: 0.85rem;
		font-weight: 600;
		color: var(--color-text, #222);
	}

	.person-picker-hint {
		font-size: 0.72rem;
		font-weight: 400;
		color: var(--color-text-muted, #666);
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
		flex-direction: column;
		gap: 0.1rem;
		padding: 0.5rem 0.7rem;
		cursor: pointer;
		user-select: none;
	}

	.option.highlight,
	.option:hover {
		background: var(--color-section-bg, #f5f5f5);
	}

	.option[aria-selected='true'] {
		background: var(--color-primary-light, #dde5ff);
	}

	.opt-name {
		font-weight: 600;
		color: var(--color-text, #222);
	}

	.opt-meta {
		font-size: 0.78rem;
		color: var(--color-text-muted, #666);
	}

	.loading,
	.empty {
		padding: 0.6rem 0.7rem;
		color: var(--color-text-muted, #666);
		font-size: 0.85rem;
		font-style: italic;
	}

	.selected-badge {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.55rem 0.7rem;
		background: var(--color-section-bg, #f5f5f5);
		border: 1px solid var(--color-border-light, #e0e0e0);
		border-radius: var(--radius-input, 6px);
	}

	.badge-name {
		font-weight: 700;
		color: var(--color-text, #222);
	}

	.badge-meta {
		font-size: 0.8rem;
		color: var(--color-text-muted, #666);
	}

	.clear-btn {
		margin-left: auto;
		background: transparent;
		border: none;
		font-size: 1rem;
		line-height: 1;
		padding: 0.2rem 0.5rem;
		cursor: pointer;
		color: var(--color-text-muted, #666);
		border-radius: var(--radius-input, 4px);
	}

	.clear-btn:hover:not(:disabled) {
		background: var(--color-bg-white, #fff);
		color: var(--color-danger, #c00);
	}

	.clear-btn:focus-visible {
		outline: 2px solid var(--color-primary, #256);
		outline-offset: 1px;
	}
</style>