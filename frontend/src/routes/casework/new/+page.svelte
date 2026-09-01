<script lang="ts">
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { user, isAdvocate, loadSession } from '$lib/session';
	import { createCasework, getPersons, ApiError } from '$lib/api';

	let currentUser = $derived($user);
	let saving = $state(false);
	let refreshing = $state(false);
	let formError = $state('');
	let formErrorKind = $state<'auth' | 'server' | 'other'>('other');
	let errors = $state<Record<string, string>>({});
	let persons: any[] = $state([]);
	let selectedPersons: number[] = $state([]);

	let actionType = $state('outreach');
	let description = $state('');
	let date = $state(new Date().toISOString().split('T')[0]);
	let status = $state('open');
	let nextSteps = $state('');
	let notes = $state('');

	const MAX_FIELD = 5000;

	const actionLabels: Record<string, string> = {
		outreach: 'Outreach',
		legal_filing: 'Legal Filing',
		media: 'Media',
		advocacy: 'Advocacy',
		investigation: 'Investigation',
		other: 'Other',
	};

	const validActions = new Set(Object.keys(actionLabels));
	const validStatuses = new Set(['open', 'in_progress', 'done']);

	onMount(async () => {
		try {
			const data = await getPersons({ page_size: '1000' });
			persons = data.results;
		} catch (e) {
			console.error(e);
		}
	});

	function togglePerson(id: number) {
		if (selectedPersons.includes(id)) {
			selectedPersons = selectedPersons.filter((p) => p !== id);
		} else {
			selectedPersons = [...selectedPersons, id];
		}
	}

	/** Remove a field's error — fires on every input so users see instant feedback when they fix it. */
	function clearError(field: string) {
		if (errors[field]) {
			const next = { ...errors };
			delete next[field];
			errors = next;
		}
		// Also clear the top-level banner once the user is editing again.
		if (formError) formError = '';
	}

	/** Map server error field names → our form's field ids (DRF uses snake_case). */
	function mapServerField(name: string): string {
		if (name === 'action_type' || name === 'date' || name === 'status' ||
			name === 'description' || name === 'next_steps' || name === 'notes' ||
			name === 'persons') {
			return name;
		}
		return name; // unknown fields stay as-is — they surface at top
	}

	/** Run client-side validation. Returns a map of field → message; empty if all good. */
	function validate(): Record<string, string> {
		const e: Record<string, string> = {};
		if (!actionType) e.action_type = 'Pick the type of action.';
		else if (!validActions.has(actionType))
			e.action_type = 'That action type isn’t recognized.';

		if (!date) e.date = 'Pick a date for this action.';
		else {
			const d = new Date(date);
			if (Number.isNaN(d.getTime())) e.date = 'That doesn’t look like a valid date.';
		}

		if (!status) e.status = 'Pick a status.';
		else if (!validStatuses.has(status)) e.status = 'That status isn’t recognized.';

		const descTrim = description.trim();
		if (!descTrim) e.description = 'Tell us what happened — even one sentence helps.';
		else if (descTrim.length > MAX_FIELD)
			e.description = `Trim this down — please keep it under ${MAX_FIELD.toLocaleString()} characters.`;

		if (nextSteps.length > MAX_FIELD)
			e.next_steps = `Trim this down — please keep it under ${MAX_FIELD.toLocaleString()} characters.`;
		if (notes.length > MAX_FIELD)
			e.notes = `Trim this down — please keep it under ${MAX_FIELD.toLocaleString()} characters.`;

		return e;
	}

	function focusFirstError(errs: Record<string, string>) {
		const order = ['action_type', 'date', 'status', 'description', 'next_steps', 'notes'];
		for (const f of order) {
			if (errs[f]) {
				const el = document.getElementById(f) as HTMLElement | null;
				if (el) {
					el.focus();
					el.scrollIntoView({ behavior: 'smooth', block: 'center' });
					return;
				}
			}
		}
	}

	async function refreshSession() {
		refreshing = true;
		try {
			await loadSession();
		} finally {
			refreshing = false;
		}
	}

	async function handleSubmit() {
		errors = {};
		formError = '';

		const v = validate();
		if (Object.keys(v).length > 0) {
			errors = v;
			focusFirstError(v);
			return;
		}

		saving = true;
		try {
			await createCasework({
				action_type: actionType,
				description: description.trim(),
				date,
				status,
				next_steps: nextSteps.trim(),
				notes: notes.trim(),
				persons: selectedPersons,
			});
			goto(`${base}/casework`);
		} catch (e: any) {
			if (e instanceof ApiError) {
				if (e.isValidation && Object.keys(e.fieldErrors).length > 0) {
					const mapped: Record<string, string> = {};
					for (const [k, msgs] of Object.entries(e.fieldErrors)) {
						mapped[mapServerField(k)] = msgs[0];
					}
					errors = mapped;
					focusFirstError(mapped);
				} else if (e.isUnauthorized) {
					formErrorKind = 'auth';
					formError =
						'Your session has expired, or you don’t have permission to add records. ' +
						'Try refreshing your session — if that doesn’t work, log in again.';
				} else if (e.isServer || e.status === 0) {
					formErrorKind = 'server';
					formError = e.message || 'The server hit a snag. Please try again in a moment.';
				} else {
					formErrorKind = 'other';
					formError = e.message || 'Something went wrong. Please try again.';
				}
			} else {
				formErrorKind = 'other';
				formError = 'Something went wrong. Please try again.';
			}
		} finally {
			saving = false;
		}
	}

	// Live counts for character counters
	const descCount = $derived(description.length);
	const nextCount = $derived(nextSteps.length);
	const notesCount = $derived(notes.length);
</script>

<svelte:head>
	<title>New Casework Record — Testimonies.world</title>
</svelte:head>

<div class="container">
	{#if !isAdvocate(currentUser)}
		<p class="muted">
			You must be logged in as an advocate to create casework records.
			<a href="{base}/api/auth/login/?next={base}/casework/new">Login</a>
		</p>
	{:else}
		<header class="form-header">
			<h1>New Casework Record</h1>
			<p class="form-intro">
				Log an advocacy action — outreach, a legal filing, media engagement, or anything
				else you’ve done for a case. Only the <em>description</em> is required; link the
				person(s) it concerns at the bottom.
			</p>
		</header>

		<!-- ============== Top-level error banner (only auth / server / unknown) ============== -->
		{#if formError}
			<div
				class="form-error-banner form-error-{formErrorKind}"
				role="alert"
				aria-live="assertive"
			>
				<div class="form-error-body">
					<p class="form-error-message">{formError}</p>
					{#if formErrorKind === 'auth'}
						<div class="form-error-actions">
							<button
								type="button"
								class="btn btn-secondary btn-sm"
								onclick={refreshSession}
								disabled={refreshing}
							>
								{refreshing ? 'Refreshing…' : 'Refresh session'}
							</button>
							<a
								href="{base}/api/auth/login/?next={base}/casework/new"
								class="btn btn-primary btn-sm"
							>
								Log in again
							</a>
						</div>
					{/if}
				</div>
				<button
					type="button"
					class="form-error-dismiss"
					aria-label="Dismiss error"
					onclick={() => (formError = '')}
				>×</button>
			</div>
		{/if}

		<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} novalidate>
			<!-- ============== Section 1: Action Details ============== -->
			<section class="form-section" aria-labelledby="sec-action">
				<h2 id="sec-action" class="form-section-title">
					<span class="title-bar" aria-hidden="true"></span>
					Action Details
				</h2>
				<p class="form-section-desc">What kind of action, when, and where it stands.</p>

				<div class="form-grid">
					<div class="field" class:has-error={errors.action_type}>
						<label for="action_type">Action Type</label>
						<select
							id="action_type"
							bind:value={actionType}
							onchange={() => clearError('action_type')}
							aria-invalid={errors.action_type ? 'true' : 'false'}
							aria-describedby={errors.action_type ? 'action_type-error' : 'action_type-help'}
						>
							{#each Object.entries(actionLabels) as [value, label]}
								<option {value}>{label}</option>
							{/each}
						</select>
						{#if errors.action_type}
							<p class="field-error" id="action_type-error" role="alert">{errors.action_type}</p>
						{:else}
							<p class="field-help" id="action_type-help">What category of advocacy was this?</p>
						{/if}
					</div>

					<div class="field" class:has-error={errors.date}>
						<label for="date">Date</label>
						<input
							id="date"
							type="date"
							bind:value={date}
							oninput={() => clearError('date')}
							aria-invalid={errors.date ? 'true' : 'false'}
							aria-describedby={errors.date ? 'date-error' : 'date-help'}
						/>
						{#if errors.date}
							<p class="field-error" id="date-error" role="alert">{errors.date}</p>
						{:else}
							<p class="field-help" id="date-help">When the action took place — defaults to today.</p>
						{/if}
					</div>

					<div class="field" class:has-error={errors.status}>
						<label for="status">Status</label>
						<select
							id="status"
							bind:value={status}
							onchange={() => clearError('status')}
							aria-invalid={errors.status ? 'true' : 'false'}
							aria-describedby={errors.status ? 'status-error' : 'status-help'}
						>
							<option value="open">Open</option>
							<option value="in_progress">In Progress</option>
							<option value="done">Done</option>
						</select>
						{#if errors.status}
							<p class="field-error" id="status-error" role="alert">{errors.status}</p>
						{:else}
							<p class="field-help" id="status-help">Open while it’s still pending; done when complete.</p>
						{/if}
					</div>
				</div>
			</section>

			<!-- ============== Section 2: What Happened? ============== -->
			<section class="form-section" aria-labelledby="sec-description">
				<h2 id="sec-description" class="form-section-title">
					<span class="title-bar" aria-hidden="true"></span>
					What Happened?
				</h2>
				<p class="form-section-desc">
					A clear description of the action taken — what was done, with whom, and the outcome.
				</p>

				<div class="field" class:has-error={errors.description}>
					<label for="description">
						Description <span class="required-mark" aria-hidden="true">*</span>
					</label>
					<textarea
						id="description"
						bind:value={description}
						oninput={() => clearError('description')}
						required
						aria-required="true"
						aria-invalid={errors.description ? 'true' : 'false'}
						aria-describedby={[
							errors.description ? 'description-error' : 'description-help',
							'description-counter',
						]
							.filter(Boolean)
							.join(' ')}
						rows="5"
						placeholder="What action was taken or needs to be taken?"
					></textarea>
					<div class="field-meta">
						{#if errors.description}
							<p class="field-error" id="description-error" role="alert">{errors.description}</p>
						{:else}
							<p class="field-help" id="description-help">
								Concrete details help the next advocate pick up where you left off.
							</p>
						{/if}
						<p
							id="description-counter"
							class="char-counter"
							class:over={descCount > MAX_FIELD}
						>
							{descCount.toLocaleString()} / {MAX_FIELD.toLocaleString()}
						</p>
					</div>
				</div>
			</section>

			<!-- ============== Section 3: Follow-up ============== -->
			<section class="form-section" aria-labelledby="sec-followup">
				<h2 id="sec-followup" class="form-section-title">
					<span class="title-bar" aria-hidden="true"></span>
					Follow-up
				</h2>
				<p class="form-section-desc">What’s next, plus any private notes for fellow advocates.</p>

				<div class="form-grid">
					<div class="field" class:has-error={errors.next_steps}>
						<label for="next_steps">Next Steps</label>
						<textarea
							id="next_steps"
							bind:value={nextSteps}
							oninput={() => clearError('next_steps')}
							rows="4"
							placeholder="What should happen next?"
							aria-invalid={errors.next_steps ? 'true' : 'false'}
							aria-describedby={errors.next_steps ? 'next_steps-error' : 'next_steps-help'}
						></textarea>
						<div class="field-meta">
							{#if errors.next_steps}
								<p class="field-error" id="next_steps-error" role="alert">{errors.next_steps}</p>
							{:else}
								<p class="field-help" id="next_steps-help">
									Open tasks or follow-ups — visible to fellow advocates.
								</p>
							{/if}
							<p
								class="char-counter"
								class:over={nextCount > MAX_FIELD}
							>
								{nextCount.toLocaleString()} / {MAX_FIELD.toLocaleString()}
							</p>
						</div>
					</div>

					<div class="field" class:has-error={errors.notes}>
						<label for="notes">Internal Notes</label>
						<textarea
							id="notes"
							bind:value={notes}
							oninput={() => clearError('notes')}
							rows="4"
							placeholder="Anything sensitive only advocates should see"
							aria-invalid={errors.notes ? 'true' : 'false'}
							aria-describedby={errors.notes ? 'notes-error' : 'notes-help'}
						></textarea>
						<div class="field-meta">
							{#if errors.notes}
								<p class="field-error" id="notes-error" role="alert">{errors.notes}</p>
							{:else}
								<p class="field-help" id="notes-help">
									Private to the casework team — never shown publicly.
								</p>
							{/if}
							<p
								class="char-counter"
								class:over={notesCount > MAX_FIELD}
							>
								{notesCount.toLocaleString()} / {MAX_FIELD.toLocaleString()}
							</p>
						</div>
					</div>
				</div>
			</section>

			<!-- ============== Section 4: Linked Persons ============== -->
			{#if persons.length > 0}
				<section class="form-section" aria-labelledby="sec-persons">
					<h2 id="sec-persons" class="form-section-title">
						<span class="title-bar" aria-hidden="true"></span>
						Linked Persons
					</h2>
					<p class="form-section-desc">
						Select the case file(s) this action relates to. Skip if not yet linked to a person.
					</p>

					{#if selectedPersons.length > 0}
						<p class="linked-summary" aria-live="polite">
							{selectedPersons.length}
							{selectedPersons.length === 1 ? 'person' : 'people'} linked
							<button
								type="button"
								class="link-button"
								onclick={() => (selectedPersons = [])}
								aria-label="Clear all linked persons"
							>Clear</button>
						</p>
					{/if}

					<div class="persons-grid" role="group" aria-label="Linked persons">
						{#each persons as person (person.id)}
							<label class="person-pill" class:is-selected={selectedPersons.includes(person.id)}>
								<span class="person-check" aria-hidden="true">
									{#if selectedPersons.includes(person.id)}
										<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
											<polyline points="20 6 9 17 4 12" />
										</svg>
									{/if}
								</span>
								<input
									type="checkbox"
									checked={selectedPersons.includes(person.id)}
									onchange={() => togglePerson(person.id)}
								/>
								<span class="person-name">{person.name}</span>
								{#if person.country}
									<span class="person-country">({person.country})</span>
								{/if}
							</label>
						{/each}
					</div>
				</section>
			{/if}

			<!-- Submit -->
			<div class="form-actions">
				<p class="form-actions-note">You’ll be returned to the casework list after saving.</p>
				<button type="submit" class="btn btn-primary submit-btn" disabled={saving}>
					{#if saving}
						<span class="spinner" aria-hidden="true"></span>
						Saving…
					{:else}
						Create Record
					{/if}
				</button>
			</div>
		</form>
	{/if}
</div>

<style>
	/* === Accessibility helper === */
	.visually-hidden {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
		border: 0;
	}

	/* === Page header === */
	.form-header {
		margin-bottom: 1.75rem;
	}
	.form-header h1 {
		margin: 0 0 0.5rem 0;
		color: var(--color-primary);
		font-size: 1.85rem;
		font-weight: 700;
		letter-spacing: -0.01em;
	}
	.form-intro {
		margin: 0;
		max-width: var(--max-w-prose);
		color: var(--color-text);
		font-size: 1rem;
		line-height: 1.6;
	}
	.form-intro em {
		color: var(--color-primary);
		font-weight: 600;
		font-style: normal;
		text-decoration: underline;
		text-decoration-color: var(--color-primary-tint);
		text-underline-offset: 3px;
	}

	/* === Top-level error banner (auth / server / unknown) === */
	.form-error-banner {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		padding: 0.9rem 1rem;
		margin-bottom: 1.5rem;
		background: var(--color-bg-white);
		border: 1px solid var(--color-danger);
		border-left: 4px solid var(--color-danger);
		border-radius: var(--radius-input);
		box-shadow: var(--shadow-card);
	}
	.form-error-auth {
		border-color: var(--color-danger);
		background: linear-gradient(
			180deg,
			rgba(217, 22, 22, 0.04),
			var(--color-bg-white) 60%
		);
	}
	.form-error-server {
		border-color: #c97a0d;
		background: linear-gradient(
			180deg,
			rgba(201, 122, 13, 0.05),
			var(--color-bg-white) 60%
		);
		border-left-color: #c97a0d;
	}
	.form-error-body {
		flex: 1 1 auto;
		min-width: 0;
	}
	.form-error-message {
		margin: 0 0 0.6rem 0;
		color: var(--color-text);
		font-size: 0.95rem;
		line-height: 1.5;
	}
	.form-error-actions {
		display: flex;
		gap: 0.5rem;
		flex-wrap: wrap;
	}
	.btn-sm {
		padding: 0.4rem 0.85rem;
		font-size: 0.85rem;
		min-width: 0;
	}
	.form-error-dismiss {
		flex: 0 0 auto;
		background: transparent;
		border: 0;
		color: var(--color-text-muted);
		font-size: 1.4rem;
		line-height: 1;
		cursor: pointer;
		padding: 0 0.25rem;
		margin-left: auto;
	}
	.form-error-dismiss:hover {
		color: var(--color-text);
	}

	/* === Section card — colored left bar + colored title === */
	.form-section {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-subtle);
		border-left: 3px solid var(--color-primary);
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-card);
		padding: 1.5rem 1.75rem 1.75rem;
		margin-bottom: 1.5rem;
	}
	.form-section-title {
		display: flex;
		align-items: center;
		gap: 0.65rem;
		margin: 0 0 0.4rem 0;
		color: var(--color-primary);
		font-size: 1.2rem;
		font-weight: 700;
		letter-spacing: -0.005em;
		line-height: 1.3;
	}
	.title-bar {
		display: inline-block;
		width: 22px;
		height: 2px;
		background: var(--color-primary);
		border-radius: 2px;
	}
	.form-section-desc {
		margin: 0 0 1.25rem 0;
		color: var(--color-text-muted);
		font-size: 0.92rem;
		line-height: 1.5;
	}

	/* === Form grid === */
	.form-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
		gap: 1.25rem 1.5rem;
	}

	/* === Field === */
	.field {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
		min-width: 0;
	}
	.field label {
		font-size: 0.85rem;
		font-weight: 600;
		color: var(--color-primary);
		line-height: 1.3;
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
	}
	.required-mark {
		color: var(--color-danger);
		font-weight: 700;
		margin-left: 0.1rem;
	}
	.field-help {
		margin: 0;
		font-size: 0.78rem;
		color: var(--color-text-muted);
		line-height: 1.45;
	}
	.field-error {
		margin: 0;
		font-size: 0.82rem;
		color: var(--color-danger);
		font-weight: 500;
		line-height: 1.4;
		display: flex;
		align-items: flex-start;
		gap: 0.35rem;
	}
	.field-error::before {
		content: '⚠';
		flex: 0 0 auto;
		font-size: 0.9rem;
		line-height: 1.2;
	}

	/* Meta row — counter on the right, help/error on the left */
	.field-meta {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 0.75rem;
		flex-wrap: wrap;
	}
	.field-meta .field-help,
	.field-meta .field-error {
		flex: 1 1 auto;
		min-width: 0;
	}
	.char-counter {
		flex: 0 0 auto;
		margin: 0;
		font-size: 0.74rem;
		color: var(--color-text-muted);
		font-variant-numeric: tabular-nums;
		line-height: 1.45;
	}
	.char-counter.over {
		color: var(--color-danger);
		font-weight: 600;
	}

	/* Inputs share one consistent look */
	.field input,
	.field select,
	.field textarea {
		appearance: none;
		-webkit-appearance: none;
		width: 100%;
		padding: 0.65rem 0.85rem;
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-input);
		background: var(--color-bg-white);
		color: var(--color-text);
		font-family: inherit;
		font-size: 0.95rem;
		line-height: 1.45;
		transition:
			border-color 0.15s ease,
			box-shadow 0.15s ease,
			background 0.15s ease;
	}
	.field textarea {
		min-height: 5rem;
		resize: vertical;
		font-family: inherit;
	}
	.field select {
		padding-right: 2.25rem;
		background-image: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2325646a' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
		background-repeat: no-repeat;
		background-position: right 0.85rem center;
		background-size: 12px 12px;
	}
	.field input::placeholder,
	.field textarea::placeholder {
		color: var(--color-text-muted);
		opacity: 0.6;
	}
	.field input:hover:not(:focus):not(:disabled),
	.field select:hover:not(:focus):not(:disabled),
	.field textarea:hover:not(:focus):not(:disabled) {
		border-color: var(--color-primary-light);
	}
	.field input:focus,
	.field select:focus,
	.field textarea:focus {
		outline: none;
		border-color: var(--color-primary);
		box-shadow: 0 0 0 3px var(--color-primary-tint);
	}
	.field input:disabled,
	.field select:disabled,
	.field textarea:disabled {
		background: var(--color-surface);
		color: var(--color-text-muted);
		cursor: not-allowed;
	}

	/* Error state on a field — red border + light red wash */
	.field.has-error input,
	.field.has-error select,
	.field.has-error textarea {
		border-color: var(--color-danger);
		background: rgba(217, 22, 22, 0.03);
	}
	.field.has-error input:focus,
	.field.has-error select:focus,
	.field.has-error textarea:focus {
		border-color: var(--color-danger);
		box-shadow: 0 0 0 3px rgba(217, 22, 22, 0.15);
	}
	.field.has-error label {
		color: var(--color-danger);
	}

	/* === Linked persons as interactive pills with visible check mark === */
	.persons-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
		gap: 0.5rem;
	}
	.person-pill {
		display: inline-flex;
		align-items: center;
		gap: 0.6rem;
		padding: 0.55rem 0.9rem 0.55rem 0.7rem;
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-input);
		background: var(--color-bg-white);
		color: var(--color-text);
		font-size: 0.88rem;
		font-weight: 500;
		cursor: pointer;
		user-select: none;
		transition:
			background 0.15s ease,
			border-color 0.15s ease,
			color 0.15s ease,
			box-shadow 0.15s ease;
	}
	.person-pill:hover {
		border-color: var(--color-primary-light);
		background: var(--color-surface);
	}
	.person-pill.is-selected {
		background: var(--color-primary-tint);
		border-color: var(--color-primary);
		color: var(--color-primary);
		font-weight: 600;
	}
	.person-country {
		color: var(--color-text-muted);
		font-weight: 400;
		font-size: 0.82rem;
	}
	.person-pill.is-selected .person-country {
		color: var(--color-primary-light);
	}

	/* Visible check indicator — empty box that fills with primary
	   color and a white check when selected. */
	.person-check {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 18px;
		height: 18px;
		border: 1.5px solid var(--color-border-light);
		border-radius: 4px;
		background: var(--color-bg-white);
		color: transparent;
		flex: 0 0 18px;
		transition:
			background 0.15s ease,
			border-color 0.15s ease,
			color 0.15s ease;
	}
	.person-pill.is-selected .person-check {
		background: var(--color-primary);
		border-color: var(--color-primary);
		color: white;
	}
	.person-pill:hover .person-check {
		border-color: var(--color-primary-light);
	}

	/* Native checkbox hidden but accessible */
	.person-pill input[type='checkbox'] {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
		border: 0;
	}
	.person-pill input[type='checkbox']:focus-visible + .person-check,
	.person-pill:focus-within .person-check {
		outline: none;
		box-shadow: 0 0 0 3px var(--color-primary-tint);
	}

	/* === Linked persons summary + clear link === */
	.linked-summary {
		margin: 0 0 0.75rem;
		font-size: 0.85rem;
		color: var(--color-primary);
		font-weight: 600;
		display: flex;
		align-items: center;
		gap: 0.6rem;
	}
	.link-button {
		background: transparent;
		border: 0;
		color: var(--color-primary-light);
		font-size: 0.85rem;
		font-weight: 500;
		text-decoration: underline;
		text-underline-offset: 2px;
		cursor: pointer;
		padding: 0;
	}
	.link-button:hover {
		color: var(--color-primary);
	}

	/* === Submit actions === */
	.form-actions {
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: 1rem;
		margin-top: 0.5rem;
		padding: 1.5rem 2rem;
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-subtle);
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-card);
		flex-wrap: wrap;
	}
	.form-actions-note {
		margin: 0;
		font-size: 0.85rem;
		color: var(--color-text-muted);
		flex: 1 1 auto;
	}
	.submit-btn {
		min-width: 160px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
	}
	.spinner {
		display: inline-block;
		width: 14px;
		height: 14px;
		border: 2px solid currentColor;
		border-right-color: transparent;
		border-radius: 50%;
		animation: spin 0.7s linear infinite;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* === Responsive === */
	@media (max-width: 720px) {
		.form-section {
			padding: 1.25rem 1.25rem;
		}
		.form-grid {
			grid-template-columns: 1fr;
			gap: 1rem;
		}
		.persons-grid {
			grid-template-columns: 1fr;
		}
		.form-actions {
			padding: 1.25rem;
			flex-direction: column;
			align-items: stretch;
		}
		.form-actions-note {
			text-align: center;
		}
		.submit-btn {
			width: 100%;
		}
		.form-error-actions {
			flex-direction: column;
			align-items: stretch;
		}
		.form-error-actions .btn-sm {
			width: 100%;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.field input,
		.field select,
		.field textarea,
		.person-pill,
		.person-check,
		.spinner {
			transition: none;
			animation: none;
		}
	}
</style>
