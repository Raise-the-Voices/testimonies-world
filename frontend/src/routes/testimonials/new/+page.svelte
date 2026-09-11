<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { user, isAdvocate } from '$lib/session';
	import {
		testimonialsCreate,
		testimonialsSubmitCreate,
	} from '$lib/api/generated/endpoints';
	import type { TestimonialWriteRequest } from '$lib/api/generated/endpoints.schemas';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// SSR-hydrated auth — see +layout.svelte for the rationale.
	let currentUser = $derived(data.user ?? $user);
	let canPublish = $derived(isAdvocate(currentUser));

	// Form state. Default to safe privacy posture: source visibility
	// 'hidden' until the submitter makes an explicit choice, location
	// visibility 'public_region' (no precise locations), family / contact
	// protection both on. The backend's serializer rejects
	// source_visibility='public_named' from non-Advocate users, so
	// the volunteer-side default 'hidden' is also the default that
	// doesn't surprise the server.
	let title = $state('');
	let country = $state('');
	let region = $state('');
	let incidentDate = $state('');
	let incidentDatePrecision = $state<'exact' | 'approximate' | 'unknown'>('unknown');
	let summary = $state('');
	let narrative = $state('');
	let outcome = $state('');
	let language = $state('en');
	let verificationLevel = $state('');
	let sourceVisibility = $state<'hidden' | 'public_anonymous' | 'public_named'>(
		'hidden'
	);
	let publicSourceLabel = $state('');
	let locationVisibility = $state<
		'public_precise' | 'public_region' | 'public_country' | 'hidden'
	>('public_region');
	let familyProtected = $state(true);
	let contactProtected = $state(true);

	// Submit state.
	let saving = $state(false);
	let errors = $state<Record<string, string>>({});
	let formError = $state('');
	/* Explicit success feedback for the 'Save as draft' path.
	   Navigation is the success indicator on 'Submit for review',
	   so this banner only fires when the user stays on the page. */
	let formSuccess = $state('');
	let createdId = $state<number | null>(null);

	/* `validate()` — runs locally before any network call. The
	   backend enforces the same rules server-side too, but
	   filtering at the client keeps the user from round-tripping
	   for obvious errors and prevents single-character "f" or
	   "m" gibberish that should never reach the DB.

	   Returns a per-field error map. Empty object = valid. */
	function validate(): Record<string, string> {
		const e: Record<string, string> = {};
		const t = title.trim();
		const c = country.trim();
		const s = summary.trim();
		const n = narrative.trim();
		const src = publicSourceLabel.trim();

		if (!t) {
			e.title = 'Title is required.';
		} else if (t.length < 5) {
			e.title = 'Title needs at least 5 characters — a single letter or a placeholder is not enough context.';
		}
		if (!c) {
			e.country = 'Country is required.';
		} else if (c.length < 2) {
			e.country = 'Country needs at least 2 characters.';
		}
		if (!s) {
			e.summary = 'Summary is required for readers.';
		} else if (s.length < 20) {
			e.summary = 'Summary should be at least 20 characters — a sentence, not a placeholder.';
		} else if (/^[\W_]+$/.test(s) || /^(.)\1{4,}$/.test(s)) {
			// Reject strings of punctuation / whitespace or single-
			// character spam like 'aaaaa' or '-----'.
			e.summary = 'Summary looks like gibberish — please write a real description.';
		}
		if (!n) {
			e.narrative = 'Narrative is required.';
		} else if (n.length < 50) {
			e.narrative = 'Narrative should be at least 50 characters — even a short testimony needs a paragraph.';
		} else if (/^[\W_]+$/.test(n) || /^(.)\1{4,}$/.test(n)) {
			e.narrative = 'Narrative looks like gibberish.';
		}
		if (sourceVisibility !== 'hidden' && src.length < 3) {
			e.public_source_label =
				'Public source label is required when source is not hidden — describe the role (e.g. "Family member", "Local witness").';
		}

		return e;
	}

	// Local submit lifecycle: create (always → status=draft) →
	// optional submit (status=under_review) → final redirect.
	async function save(submitAfter: boolean) {
		// Re-entrancy guard — if a fast double-click beats the
		// disabled={saving} DOM attribute, bail before any state
		// changes so we don't kick off two concurrent fetches.
		if (saving) return;

		// Client-side validation gate — never enter the network
		// path with placeholder or missing values.
		const v = validate();
		if (Object.keys(v).length > 0) {
			errors = v;
			formError = 'Some fields need attention — see below.';
			// Pull the user's eye to the first invalid field.
			if (typeof document !== 'undefined') {
				const firstKey = Object.keys(v)[0];
				const el = document.getElementById(firstKey);
				el?.focus();
				el?.scrollIntoView({ block: 'center' });
			}
			return;
		}

		saving = true;
		formError = '';
		formSuccess = '';
		errors = {};

		try {
			return await saveImpl(submitAfter);
		} finally {
			saving = false;
		}
	}

	async function saveImpl(submitAfter: boolean): Promise<void> {
		const body: TestimonialWriteRequest = {
			title: title.trim(),
			country: country.trim(),
			region: region.trim(),
			incident_date: incidentDate || null,
			summary: summary.trim(),
			narrative: narrative.trim(),
			outcome: outcome.trim(),
			language,
			verification_level: (verificationLevel || undefined) as
				| TestimonialWriteRequest['verification_level']
				| undefined,
			source_visibility: sourceVisibility,
			public_source_label: publicSourceLabel.trim(),
			location_visibility: locationVisibility,
			family_protected: familyProtected,
			contact_protected: contactProtected,
		};
		// `incident_date_precision` and `incident_types` exist on the
		// model but aren't in the generated `TestimonialWriteRequest`
		// (drf-spectacular skipped them during introspection). The
		// backend accepts them via raw POST; we lose the round-trip
		// type safety until the bug is fixed in the schema layer.
		const bodyWithExtras = body as TestimonialWriteRequest & {
			incident_date_precision?: string;
			incident_types?: string[];
		};
		bodyWithExtras.incident_date_precision = incidentDatePrecision;

		// Outer try/finally: `saving` resets on every exit so the
		// button never sticks in 'Submitting…' state.
		let id: number | null = null;
		try {
			const res = await testimonialsCreate(body);

			// Response-shape fix: DRF's ModelViewSet.create returns the
			// serializer data directly (NOT wrapped in {data, status}),
			// even though orval's generated TypeScript type assumes
			// the wrapper. The earlier code read `res.data.id` and
			// fell through to the 'did not include id' branch on
			// every successful create — surfacing 'broken cards' and
			// a frozen form. Read the shape defensively so both the
			// wrapped (orval spec) and unwrapped (DRF default) work.
			const record = res as unknown as
				| { id?: number; data?: { id?: number } }
				| null
				| undefined;
			const unwrapped = record && typeof record === 'object'
				? (record as Record<string, unknown>)
				: {};
			const candidate = unwrapped.data ?? unwrapped;
			const candidateId =
				typeof candidate === 'object' && candidate !== null
					? (candidate as { id?: unknown }).id
					: undefined;
			id = typeof candidateId === 'number' ? candidateId : null;

			if (id === null || !Number.isFinite(id)) {
				throw new Error(
					'The server accepted the testimonial but its response was missing a valid id. ' +
						'Please retry — if the problem persists, contact support via the audit log.'
				);
			}
			createdId = id;
		} catch (e: unknown) {
			formError =
				e instanceof Error ? e.message : 'Could not create the testimonial.';
			return; // finally clears saving
		}

		if (submitAfter) {
			try {
				await testimonialsSubmitCreate(id, {});
			} catch (e: unknown) {
				// Row was created but the workflow transition failed.
				// Tell the user both halves of the result so they don't
				// try to create the same row again.
				formError =
					e instanceof Error
						? `Saved as draft, but submission failed: ${e.message}. ` +
							'You can retry the submit from the testimonial page.'
						: 'Saved as draft, but the submit step failed. ' +
							'You can retry from the testimonial page.';
				return; // finally clears saving
			}
		}

		// Success. Two paths:
		//   - submitAfter: navigate to the detail page (the page
		//     itself IS the success confirmation).
		//   - !submitAfter (save draft): clear the form and show an
		//     explicit success banner with a link to the new draft,
		//     so the user gets unambiguous feedback that the click
		//     landed (no more 'nothing happens' UX).
		if (submitAfter) {
			await goto(`${base}/testimonials/${id}`);
		} else {
			formSuccess =
				'Draft saved. You can keep editing below, or jump to the new draft’s page.';
			// Reset form so the user can start a new entry without
			// manually clearing fields.
			title = '';
			country = '';
			region = '';
			incidentDate = '';
			incidentDatePrecision = 'unknown';
			summary = '';
			narrative = '';
			outcome = '';
			verificationLevel = '';
			publicSourceLabel = '';
			sourceVisibility = 'hidden';
			locationVisibility = 'public_region';
			familyProtected = true;
			contactProtected = true;
		}
	}
</script>

<svelte:head>
	<title>New testimonial — Testimonies.world</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="new-testimonial-page">
	<header class="page-header">
		<a href="{base}/testimonials" class="back-link">← Back to testimonials</a>
		<h1>New testimonial</h1>
		<p class="page-subtitle">
			{#if !currentUser.authenticated}
				You need to be signed in to submit a testimonial.
				<a href={data.anonHref}>Sign in with Google</a> to continue.
			{:else}
				{#if canPublish}
					You can publish directly. The default status is
					<strong>draft</strong>; the buttons below let you submit it for
					review (recommended for transparency) or publish immediately.
				{:else}
					Your draft is private to you until a reviewer approves it. Choose
					<em>Submit for review</em> when you're done — you'll see it
					under "My drafts" with its current status.
				{/if}
			{/if}
		</p>
	</header>

	{#if currentUser.authenticated}
		<form class="testimonial-form" onsubmit={(e) => e.preventDefault()}>
			<fieldset>
				<legend>Identity</legend>

				<div class="form-row">
					<label for="title">Title <span class="form-required" aria-hidden="true">*</span></label>
					<input
						id="title"
						type="text"
						maxlength="255"
						bind:value={title}
						placeholder="Detention in Erbil, March 2024"
						aria-invalid={errors.title ? 'true' : undefined}
						aria-describedby={errors.title ? 'title-error' : undefined}
					/>
					{#if errors.title}
						<p id="title-error" class="form-field-error">{errors.title}</p>
					{/if}
				</div>

				<div class="form-row form-row-grid">
					<div>
						<label for="country">Country <span class="form-required" aria-hidden="true">*</span></label>
						<input
							id="country"
							type="text"
							maxlength="100"
							bind:value={country}
							placeholder="Iraq"
							aria-invalid={errors.country ? 'true' : undefined}
							aria-describedby={errors.country ? 'country-error' : undefined}
						/>
						{#if errors.country}
							<p id="country-error" class="form-field-error">{errors.country}</p>
						{/if}
					</div>
					<div>
						<label for="region">Region / province</label>
						<input
							id="region"
							type="text"
							maxlength="255"
							bind:value={region}
							placeholder="Erbil"
						/>
					</div>
				</div>

				<div class="form-row form-row-grid">
					<div>
						<label for="incident-date">Incident date</label>
						<input id="incident-date" type="date" bind:value={incidentDate} />
					</div>
					<div>
						<label for="incident-precision">Date precision</label>
						<select id="incident-precision" bind:value={incidentDatePrecision}>
							<option value="unknown">Unknown</option>
							<option value="approximate">Approximate</option>
							<option value="exact">Exact</option>
						</select>
					</div>
				</div>

				<div class="form-row">
					<label for="language">Language</label>
					<select id="language" bind:value={language}>
						<option value="en">English</option>
						<option value="ar">Arabic</option>
						<option value="fa">Farsi</option>
						<option value="es">Spanish</option>
						<option value="fr">French</option>
					</select>
				</div>
			</fieldset>

			<fieldset>
				<legend>Narrative</legend>

				<div class="form-row">
					<label for="summary">Summary (1–2 paragraphs) <span class="form-required" aria-hidden="true">*</span></label>
					<textarea
						id="summary"
						rows="3"
						maxlength="2000"
						bind:value={summary}
						aria-invalid={errors.summary ? 'true' : undefined}
						aria-describedby={errors.summary ? 'summary-error' : undefined}
					></textarea>
					{#if errors.summary}
						<p id="summary-error" class="form-field-error">{errors.summary}</p>
					{/if}
				</div>

				<div class="form-row">
					<label for="narrative">Narrative (long form) <span class="form-required" aria-hidden="true">*</span></label>
					<textarea
						id="narrative"
						rows="8"
						maxlength="20000"
						bind:value={narrative}
						aria-invalid={errors.narrative ? 'true' : undefined}
						aria-describedby={errors.narrative ? 'narrative-error' : undefined}
					></textarea>
					{#if errors.narrative}
						<p id="narrative-error" class="form-field-error">{errors.narrative}</p>
					{/if}
				</div>

				<div class="form-row">
					<label for="outcome">Outcome</label>
					<textarea
						id="outcome"
						rows="3"
						maxlength="5000"
						bind:value={outcome}
					></textarea>
				</div>

				<div class="form-row">
					<label for="verification">Verification level</label>
					<select id="verification" bind:value={verificationLevel}>
						<option value="">— not set —</option>
						<option value="level_1_reported">Level 1 — Reported</option>
						<option value="level_2_partially_verified">
							Level 2 — Partially verified
						</option>
						<option value="level_3_corroborated">Level 3 — Corroborated</option>
						<option value="level_4_documented">Level 4 — Documented</option>
					</select>
				</div>
			</fieldset>

			<fieldset>
				<legend>Source privacy</legend>
				<p class="form-help">
					The real source identity stays encrypted on the server and is
					never shown to the public. The label below is what readers see.
				</p>

				<div class="form-row">
					<label for="source-visibility">Source visibility</label>
					<select id="source-visibility" bind:value={sourceVisibility}>
						<option value="hidden">Hidden (recommended for sensitive sources)</option>
						<option value="public_anonymous">Public — anonymous tag only</option>
						{#if canPublish}
							<option value="public_named">Public — named (requires Advocate role)</option>
						{/if}
					</select>
				</div>

				<div class="form-row">
					<label for="public-source-label">Public source label</label>
					<input
						id="public-source-label"
						type="text"
						maxlength="255"
						bind:value={publicSourceLabel}
						placeholder="Family member · Local witness · Press excerpt"
					/>
					<p class="form-help">
						Describe the source's role without revealing who they are
						(e.g. "Family member", "Wife of subject", "Local witness").
					</p>
				</div>
			</fieldset>

			<fieldset>
				<legend>Location privacy</legend>

				<div class="form-row">
					<label for="location-visibility">Location visibility</label>
					<select id="location-visibility" bind:value={locationVisibility}>
						<option value="hidden">Hidden</option>
						<option value="public_country">Public — country only</option>
						<option value="public_region">Public — region only</option>
						<option value="public_precise">Public — precise</option>
					</select>
					<p class="form-help">
						Precise addresses / coordinates stay encrypted on the server
						and require Advocate role to view.
					</p>
				</div>
			</fieldset>

			<fieldset>
				<legend>Auto-protection flags</legend>
				<label class="checkbox-row">
					<input type="checkbox" bind:checked={familyProtected} />
					Replace family member identities with role labels
				</label>
				<label class="checkbox-row">
					<input type="checkbox" bind:checked={contactProtected} />
					Never display contact information publicly
				</label>
			</fieldset>

			{#if formSuccess}
				<div class="form-success" role="status">
					<span>{formSuccess}</span>
					{#if createdId}
						<a class="form-success-link" href="{base}/testimonials/{createdId}">
							View draft →
						</a>
					{/if}
				</div>
			{/if}

			{#if formError}
				<div class="form-error" role="alert">{formError}</div>
			{/if}

			<div class="form-actions">
				<button
					type="button"
					class="btn btn-secondary"
					disabled={saving}
					onclick={() => save(false)}
				>
					Save as draft
				</button>
				<button
					type="button"
					class="btn btn-primary"
					disabled={saving}
					onclick={() => save(true)}
				>
					{saving ? 'Submitting…' : 'Submit for review'}
				</button>
				{#if createdId}
					<a class="form-saved-link" href="{base}/testimonials/{createdId}">
						View created testimonial →
					</a>
				{/if}
			</div>
		</form>
	{:else}
		<div class="signin-panel">
			<a class="btn btn-primary" href={data.anonHref}>Sign in with Google</a>
		</div>
	{/if}
</div>

<style>
	.new-testimonial-page {
		max-width: var(--max-w-prose);
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.page-header h1 {
		margin: 0.25rem 0 0.5rem 0;
		color: var(--color-primary);
	}
	.page-subtitle {
		margin: 0;
		color: var(--color-text-muted);
		max-width: var(--max-w-prose);
		line-height: 1.55;
	}
	.back-link {
		color: var(--color-primary);
		text-decoration: none;
		font-size: 0.9rem;
	}
	.back-link:hover {
		text-decoration: underline;
	}

	.testimonial-form {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}
	fieldset {
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		background: var(--color-bg-white);
		padding: 1.25rem 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 0.85rem;
	}
	legend {
		font-weight: 700;
		color: var(--color-primary);
		font-size: 0.95rem;
		padding: 0 0.4rem;
	}

	.form-row {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}
	.form-row-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.85rem;
	}
	@media (max-width: 600px) {
		.form-row-grid {
			grid-template-columns: 1fr;
		}
	}
	label {
		font-size: 0.85rem;
		font-weight: 700;
		color: var(--color-text);
		display: block;
	}
	input,
	select,
	textarea {
		font: inherit;
		padding: 0.5rem 0.65rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-input);
		background: var(--color-bg-white);
		color: var(--color-text);
		width: 100%;
		box-sizing: border-box;
	}
	input:focus-visible,
	select:focus-visible,
	textarea:focus-visible {
		outline: 3px solid var(--focus-ring);
		outline-offset: 1px;
		border-color: var(--color-primary);
	}
	textarea {
		resize: vertical;
		min-height: 4em;
	}
	.form-help {
		margin: 0;
		color: var(--color-text-muted);
		font-size: 0.82rem;
	}

	.checkbox-row {
		display: flex;
		align-items: center;
		gap: 0.55rem;
		font-size: 0.95rem;
		cursor: pointer;
	}
	.checkbox-row input[type='checkbox'] {
		width: 1.1rem;
		height: 1.1rem;
	}

	.form-error {
		padding: 0.85rem 1rem;
		border: 1px solid var(--color-danger);
		border-left: 3px solid var(--color-danger);
		border-radius: var(--radius-card);
		color: var(--color-danger);
		background: #fef2f2;
	}

	/* Success banner — explicit feedback when 'Save as draft'
	   succeeds (the submission path's success is the goto itself).
	   Uses the same emerald-700 palette as TestimonialCard's
	   'published' status pill for visual consistency. */
	.form-success {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex-wrap: wrap;
		padding: 0.85rem 1rem;
		border: 1px solid #86efac;
		border-left: 3px solid #16a34a;
		border-radius: var(--radius-card);
		color: #166534;
		background: #f0fdf4;
	}
	.form-success-link {
		color: #166534;
		font-weight: 700;
		text-decoration: underline;
	}

	/* Required-field indicator + inline field-error text. The red
	   underline on aria-invalid="true" mirrors the form-field-error
	   message below so screen-reader users and visual users get
	   the same signal at the same input. */
	.form-required {
		color: var(--color-danger);
		margin-left: 0.15rem;
	}
	.form-field-error {
		margin: 0;
		font-size: 0.82rem;
		color: var(--color-danger);
	}
	input[aria-invalid='true'],
	textarea[aria-invalid='true'] {
		border-color: var(--color-danger);
	}

	.form-actions {
		display: flex;
		gap: 0.75rem;
		align-items: center;
		flex-wrap: wrap;
	}
	.form-saved-link {
		color: var(--color-primary);
		text-decoration: none;
		font-size: 0.9rem;
	}
	.form-saved-link:hover {
		text-decoration: underline;
	}

	.signin-panel {
		text-align: center;
		padding: 2rem;
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
	}
</style>
