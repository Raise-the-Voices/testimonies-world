<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { fly, fade } from 'svelte/transition';
	import { user, isVolunteer } from '$lib/session';
	import { getPerson, createReport } from '$lib/api';

	let currentUser = $derived($user);
	let person: any = $state(null);
	let loading = $state(true);
	let saving = $state(false);
	let errorMsg = $state('');
	let fieldErrors = $state<Record<string, string>>({});

	let sourceType = $state('firsthand');
	let sourceAttribution = $state('');
	let reporterName = $state('');
	let reporterContact = $state('');
	let dateStart = $state('');
	let dateEnd = $state('');
	let roughLocation = $state('');
	let narrative = $state('');
	let suspectedReason = $state('');
	let officialReason = $state('');

	const MAX_NARRATIVE = 5000;
	const MAX_SHORT = 500;

	const sourceTypeLabels: Record<string, string> = {
		firsthand: 'Firsthand',
		secondhand: 'Secondhand',
		news: 'News report',
		document: 'Document',
	};
	const sourceTypeHelp: Record<string, string> = {
		firsthand: 'From someone who directly witnessed or experienced the event.',
		secondhand: 'From someone close to the event (family, neighbor, colleague).',
		news: 'From a media report — link the source in the attribution field.',
		document: 'From an official document, court filing, or organizational report.',
	};

	onMount(async () => {
		try {
			person = await getPerson(page.params.id!);
		} catch (e: unknown) {
			errorMsg = e instanceof Error ? e.message : "Couldn't load this case.";
		}
		loading = false;
	});

	function validate(): boolean {
		const e: Record<string, string> = {};
		if (!narrative.trim()) {
			e.narrative = 'Narrative is required.';
		} else if (narrative.length > MAX_NARRATIVE) {
			e.narrative = `Narrative is too long (max ${MAX_NARRATIVE} characters).`;
		}
		if (dateStart && dateEnd && dateEnd < dateStart) {
			e.date_end = 'End date must be on or after the start date.';
		}
		fieldErrors = e;
		return Object.keys(e).length === 0;
	}

	async function handleSubmit() {
		if (!validate()) return;
		saving = true;
		errorMsg = '';
		try {
			await createReport({
				person: person.id,
				source_type: sourceType,
				source_attribution: sourceAttribution,
				reporter_name: reporterName,
				reporter_contact: reporterContact,
				date_start: dateStart || null,
				date_end: dateEnd || null,
				rough_location: roughLocation,
				narrative,
				suspected_reason: suspectedReason,
				official_reason: officialReason,
			});
			await goto(`${base}/persons/${person.id}`);
		} catch (err: unknown) {
			errorMsg =
				err instanceof Error ? err.message : 'Failed to save the report.';
			saving = false;
		}
	}

	function cancel() {
		goto(`${base}/persons/${person.id}`);
	}
</script>

<svelte:head>
	<title>Add Report — {person?.name || 'Loading...'} — Testimonies.world</title>
</svelte:head>

{#if loading}
	<p class="muted">Loading…</p>
{:else if !isVolunteer(currentUser)}
	<p class="muted">
		You must be logged in as a volunteer to add reports.
		<a href="{base}/api/auth/login/?next={base}/persons/{page.params.id}/report">Login</a>
	</p>
{:else if person}
	<header class="report-page-header">
		<p class="breadcrumb">
			<a href="{base}/persons/{person.id}">{person.name}</a>
			<span class="breadcrumb-sep" aria-hidden="true">›</span>
			<span>Add report</span>
		</p>
		<h1>Add a report</h1>
		<p class="muted">
			Reports are chronological updates — what happened, when, and where.
			The more detail, the stronger the case. Required fields are marked with
			<span class="required-mark" aria-hidden="true">*</span>.
		</p>
	</header>

	{#if errorMsg}
		<div class="form-error" role="alert" transition:fly={{ y: -8, duration: 200 }}>
			<span class="form-error-icon" aria-hidden="true">!</span>
			<span>{errorMsg}</span>
		</div>
	{/if}

	<form class="report-form" onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} novalidate>
		<!-- ============================================================
		     Source information
		     ============================================================ -->
		<fieldset class="form-section">
			<legend class="section-legend">
				<span class="section-icon" aria-hidden="true">⚲</span>
				Source information
			</legend>
			<p class="section-hint">Who reported this, and how reliable is the source?</p>

			<div class="grid-2">
				<!-- Source type -->
				<div class="field">
					<label for="source_type">Source type</label>
					<select
						id="source_type"
						class="input--search"
						bind:value={sourceType}
					>
						{#each Object.entries(sourceTypeLabels) as [value, label] (value)}
							<option {value}>{label}</option>
						{/each}
					</select>
					<p class="field-hint">{sourceTypeHelp[sourceType]}</p>
				</div>

				<!-- Source attribution (public) -->
				<div class="field">
					<label for="source_attr">
						Source attribution
						<span class="badge-public" title="Shown publicly">public</span>
					</label>
					<input
						id="source_attr"
						type="text"
						class="input--search"
						bind:value={sourceAttribution}
						placeholder='e.g. "family member", "BBC article"'
						maxlength={MAX_SHORT}
						autocomplete="off"
					/>
				</div>

				<!-- Reporter name (private) -->
				<div class="field">
					<label for="reporter_name">
						Reporter name
						<span class="badge-private" title="Hidden from public view">
							<svg viewBox="0 0 16 16" width="11" height="11" aria-hidden="true">
								<path
									fill="currentColor"
									d="M4 7V5a4 4 0 1 1 8 0v2h1a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1h1zm2 0h4V5a2 2 0 1 0-4 0v2z"
								/>
							</svg>
							private
						</span>
					</label>
					<input
						id="reporter_name"
						type="text"
						class="input--search"
						bind:value={reporterName}
						placeholder="Not shown publicly"
						maxlength={255}
						autocomplete="off"
					/>
				</div>

				<!-- Reporter contact (private) -->
				<div class="field">
					<label for="reporter_contact">
						Reporter contact
						<span class="badge-private" title="Hidden from public view">
							<svg viewBox="0 0 16 16" width="11" height="11" aria-hidden="true">
								<path
									fill="currentColor"
									d="M4 7V5a4 4 0 1 1 8 0v2h1a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1h1zm2 0h4V5a2 2 0 1 0-4 0v2z"
								/>
							</svg>
							private
						</span>
					</label>
					<input
						id="reporter_contact"
						type="text"
						class="input--search"
						bind:value={reporterContact}
						placeholder="Email, phone, Signal — how we follow up"
						maxlength={500}
						autocomplete="off"
					/>
				</div>
			</div>
		</fieldset>

		<!-- ============================================================
		     Event timeline & location
		     ============================================================ -->
		<fieldset class="form-section">
			<legend class="section-legend">
				<span class="section-icon" aria-hidden="true">⌚</span>
				Event timeline &amp; location
			</legend>
			<p class="section-hint">
				When did it happen, and where? Leave the end date blank for a single-day event.
			</p>

			<div class="grid-2">
				<!-- Start date -->
				<div class="field">
					<label for="date_start">Start date</label>
					<input
						id="date_start"
						type="date"
						class="input--search"
						bind:value={dateStart}
						class:has-error={!!fieldErrors.date_start}
					/>
				</div>

				<!-- End date -->
				<div class="field">
					<label for="date_end">End date <span class="optional-mark">(optional)</span></label>
					<input
						id="date_end"
						type="date"
						class="input--search"
						bind:value={dateEnd}
						class:has-error={!!fieldErrors.date_end}
					/>
					{#if fieldErrors.date_end}
						<p class="field-error">{fieldErrors.date_end}</p>
					{/if}
				</div>

				<!-- Location (full width — single field but spans both columns) -->
				<div class="field field-full">
					<label for="location">
						Location <span class="optional-mark">(optional)</span>
					</label>
					<input
						id="location"
						type="text"
						class="input--search"
						bind:value={roughLocation}
						placeholder='e.g. "Karachi, Sindh, Pakistan" — keep it regional'
						maxlength={255}
						autocomplete="off"
					/>
					<p class="field-hint">
						Use the regional / public version here. Precise locations stay private and are added separately.
					</p>
				</div>
			</div>
		</fieldset>

		<!-- ============================================================
		     Report details (narrative + reasons)
		     ============================================================ -->
		<fieldset class="form-section">
			<legend class="section-legend">
				<span class="section-icon" aria-hidden="true">≡</span>
				Report details
			</legend>
			<p class="section-hint">What happened, in your own words. Be specific.</p>

			<!-- Narrative — full width, required -->
			<div class="field field-full">
				<label for="narrative">
					Narrative <span class="required-mark" aria-hidden="true">*</span>
					<span class="sr-only">required</span>
				</label>
				<textarea
					id="narrative"
					class="input--search narrative-textarea"
					class:has-error={!!fieldErrors.narrative}
					bind:value={narrative}
					maxlength={MAX_NARRATIVE}
					placeholder="What happened? What is known? Include dates, places, people, and any context that helps."
				></textarea>
				{#if fieldErrors.narrative}
					<p class="field-error">{fieldErrors.narrative}</p>
				{/if}
				<div class="field-counter" aria-live="polite">
					{narrative.length} / {MAX_NARRATIVE}
				</div>
			</div>

			<!-- Suspected / official reasons — 2-column -->
			<div class="grid-2">
				<div class="field">
					<label for="suspected_reason">
						Suspected reason <span class="optional-mark">(optional)</span>
					</label>
					<textarea
						id="suspected_reason"
						class="input--search"
						bind:value={suspectedReason}
						maxlength={MAX_NARRATIVE}
						placeholder="What do sources believe is the reason? Stay close to what they actually say."
					></textarea>
				</div>

				<div class="field">
					<label for="official_reason">
						Official reason <span class="optional-mark">(optional)</span>
					</label>
					<textarea
						id="official_reason"
						class="input--search"
						bind:value={officialReason}
						maxlength={MAX_NARRATIVE}
						placeholder="What did the state officially charge, if anything?"
					></textarea>
				</div>
			</div>
		</fieldset>

		<!-- ============================================================
		     Action footer — sticky on long forms
		     ============================================================ -->
		<footer class="form-footer">
			<p class="form-footer-hint">
				By submitting, you confirm the information is accurate to the best of your knowledge.
			</p>
			<div class="form-footer-actions">
				<button
					type="button"
					class="btn btn-secondary"
					onclick={cancel}
					disabled={saving}
				>Cancel</button>
				<button
					type="submit"
					class="btn btn-primary"
					disabled={saving}
				>
					{#if saving}
						<span class="spinner" aria-hidden="true"></span>
						Saving…
					{:else}
						Submit report
					{/if}
				</button>
			</div>
		</footer>
	</form>
{/if}

<style>
	/* === Page layout === */
	.report-page-header {
		width: 100%;
		max-width: 880px;
		margin: 0 auto 1.25rem auto;
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}
	.report-page-header h1 {
		margin: 0;
		color: var(--color-primary);
		font-size: 1.85rem;
		font-weight: 700;
		letter-spacing: -0.01em;
	}
	.breadcrumb {
		margin: 0;
		font-size: 0.88rem;
		color: var(--color-text-muted);
	}
	.breadcrumb a {
		color: var(--color-text-muted);
		text-decoration: underline;
		text-decoration-color: var(--color-border-light);
		text-underline-offset: 2px;
	}
	.breadcrumb a:hover { color: var(--color-primary); }
	.breadcrumb-sep {
		margin: 0 0.4rem;
		color: var(--color-text-muted);
	}

	.required-mark { color: var(--color-danger); font-weight: 700; }
	.optional-mark {
		color: var(--color-text-muted);
		font-size: 0.78rem;
		font-weight: 400;
	}
	.sr-only {
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

	/* === Form container === */
	.report-form {
		width: 100%;
		max-width: 880px;
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	/* === Form-level error banner === */
	.form-error {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.7rem 0.95rem;
		background: #fed7d7;
		color: #c53030;
		border: 1px solid #feb2b2;
		border-radius: var(--radius-card);
		font-size: 0.9rem;
	}
	.form-error-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 22px;
		height: 22px;
		border-radius: 50%;
		background: rgba(197, 48, 48, 0.2);
		font-weight: 700;
		font-size: 0.85rem;
	}

	/* === Section card (fieldset) === */
	.form-section {
		border: 1px solid var(--color-border-subtle);
		border-left: 3px solid var(--color-primary);
		border-radius: var(--radius-card-lg);
		background: var(--color-bg-white);
		padding: 1.5rem 1.75rem 1.75rem 1.75rem;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
	.section-legend {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0 0.5rem;
		font-size: 1rem;
		font-weight: 700;
		color: var(--color-text);
	}
	.section-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		border-radius: 50%;
		background: var(--color-primary-tint);
		color: var(--color-primary);
		font-size: 0.95rem;
	}
	.section-hint {
		margin: -0.4rem 0 0.2rem 0;
		font-size: 0.85rem;
		color: var(--color-text-muted);
		line-height: 1.5;
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
	.field-error {
		margin: 0;
		font-size: 0.82rem;
		color: var(--color-danger);
	}

	/* The .input--search class is defined globally in app.css for the
	   filter toolbar — we're reusing it here so fields match the same
	   chrome. */
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
	.narrative-textarea {
		min-height: 180px;
	}
	.input--search.has-error {
		border-color: var(--color-danger);
	}
	.input--search.has-error:focus {
		box-shadow: 0 0 0 3px rgba(217, 22, 22, 0.15);
	}

	/* === Privacy badges on labels === */
	.badge-public,
	.badge-private {
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
	}
	.badge-public {
		background: #c6f6d5;
		color: #22543d;
	}
	.badge-private {
		background: #fefcbf;
		color: #744210;
	}
	.badge-private svg { display: inline-block; }

	/* === Sticky action footer === */
	.form-footer {
		position: sticky;
		bottom: 0;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		padding: 1rem 1.25rem;
		margin: 0.5rem 0 0 0;
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-subtle);
		border-left: 3px solid var(--color-primary);
		border-radius: var(--radius-card-lg);
		box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.04);
		z-index: 5;
	}
	.form-footer-hint {
		margin: 0;
		font-size: 0.82rem;
		color: var(--color-text-muted);
		max-width: 480px;
		line-height: 1.45;
	}
	.form-footer-actions {
		display: flex;
		gap: 0.75rem;
		flex: 0 0 auto;
	}
	.form-footer-actions .btn {
		min-width: 120px;
	}
	.form-footer-actions .btn:disabled {
		opacity: 0.65;
		cursor: not-allowed;
	}

	/* === Loading spinner on the submit button === */
	.spinner {
		display: inline-block;
		width: 14px;
		height: 14px;
		border: 2px solid currentColor;
		border-right-color: transparent;
		border-radius: 50%;
		animation: spin 0.7s linear infinite;
		margin-right: 0.4rem;
		vertical-align: -2px;
	}
	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* === Responsive === */
	@media (max-width: 600px) {
		.report-page-header,
		.report-form {
			max-width: 100%;
		}
		.form-section {
			padding: 1.15rem 1.15rem 1.25rem 1.15rem;
		}
		.form-footer {
			flex-direction: column;
			align-items: stretch;
			text-align: center;
		}
		.form-footer-actions {
			justify-content: stretch;
		}
		.form-footer-actions .btn {
			flex: 1 1 auto;
			min-width: 0;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.spinner { animation: none; }
		.form-error { transition: none; }
	}
</style>