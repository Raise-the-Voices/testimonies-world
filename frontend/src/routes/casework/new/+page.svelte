<script lang="ts">
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { user, isAdvocate } from '$lib/session';
	import { createCasework, getPersons } from '$lib/api';

	let currentUser = $derived($user);
	let saving = $state(false);
	let errorMsg = $state('');
	let persons: any[] = $state([]);
	let selectedPersons: number[] = $state([]);

	let actionType = $state('outreach');
	let description = $state('');
	let date = $state(new Date().toISOString().split('T')[0]);
	let status = $state('open');
	let nextSteps = $state('');
	let notes = $state('');

	const actionLabels: Record<string, string> = {
		outreach: 'Outreach',
		legal_filing: 'Legal Filing',
		media: 'Media',
		advocacy: 'Advocacy',
		investigation: 'Investigation',
		other: 'Other',
	};

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

	async function handleSubmit() {
		if (!description) {
			errorMsg = 'Description is required.';
			return;
		}
		saving = true;
		errorMsg = '';
		try {
			await createCasework({
				action_type: actionType,
				description,
				date,
				status,
				next_steps: nextSteps,
				notes,
				persons: selectedPersons,
			});
			goto(`${base}/casework`);
		} catch (e: any) {
			errorMsg = e.message || 'Failed to save.';
		}
		saving = false;
	}
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
				else you've done for a case. Only the <em>description</em> is required; link the
				person(s) it concerns at the bottom.
			</p>
		</header>

		{#if errorMsg}
			<div class="error-banner" role="alert">{errorMsg}</div>
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
					<div class="field">
						<label for="action_type">Action Type</label>
						<select id="action_type" bind:value={actionType}>
							<option value="outreach" disabled hidden>Select action type…</option>
							{#each Object.entries(actionLabels) as [value, label]}
								<option {value}>{label}</option>
							{/each}
						</select>
						<p class="field-help">What category of advocacy was this?</p>
					</div>

					<div class="field">
						<label for="date">Date</label>
						<input id="date" type="date" bind:value={date} />
						<p class="field-help">When the action took place — defaults to today.</p>
					</div>

					<div class="field">
						<label for="status">Status</label>
						<select id="status" bind:value={status}>
							<option value="open" disabled hidden>Select status…</option>
							<option value="open">Open</option>
							<option value="in_progress">In Progress</option>
							<option value="done">Done</option>
						</select>
						<p class="field-help">Open while it's still pending; done when complete.</p>
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

				<div class="field">
					<label for="description">
						Description <span class="required-mark" aria-hidden="true">*</span>
					</label>
					<textarea
						id="description"
						bind:value={description}
						required
						aria-required="true"
						rows="5"
						placeholder="What action was taken or needs to be taken?"
					></textarea>
					<p class="field-help">
						Concrete details help the next advocate pick up where you left off.
					</p>
				</div>
			</section>

			<!-- ============== Section 3: Follow-up ============== -->
			<section class="form-section" aria-labelledby="sec-followup">
				<h2 id="sec-followup" class="form-section-title">
					<span class="title-bar" aria-hidden="true"></span>
					Follow-up
				</h2>
				<p class="form-section-desc">What's next, plus any private notes for fellow advocates.</p>

				<div class="form-grid">
					<div class="field">
						<label for="next_steps">Next Steps</label>
						<textarea
							id="next_steps"
							bind:value={nextSteps}
							rows="4"
							placeholder="What should happen next?"
						></textarea>
						<p class="field-help">Open tasks or follow-ups — visible to fellow advocates.</p>
					</div>

					<div class="field">
						<label for="notes">Internal Notes</label>
						<textarea
							id="notes"
							bind:value={notes}
							rows="4"
							placeholder="Anything sensitive only advocates should see"
						></textarea>
						<p class="field-help">Private to the casework team — never shown publicly.</p>
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
				<p class="form-actions-note">You'll be returned to the casework list after saving.</p>
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
