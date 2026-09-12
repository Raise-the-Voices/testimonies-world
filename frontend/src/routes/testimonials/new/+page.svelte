<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { user, isAdvocate } from '$lib/session';
	import {
		testimonialsCreate,
		testimonialsSubmitCreate,
	} from '$lib/api/generated/endpoints';
	import type { TestimonialWriteRequest } from '$lib/api/generated/endpoints.schemas';
	import {
		newTestimonialSchema,
		zodToFieldErrors,
		type NewTestimonialInput,
	} from '$lib/schemas/testimonialForm';
	import type { PageData } from './$types';

	// `incident_date_precision` and `incident_types` exist on the model
	// but aren't in the generated `TestimonialWriteRequest` —
	// drf-spectacular skipped them during introspection. The backend
	// still accepts them on POST, so we extend the request type once
	// at module scope and build a single typed body below. This keeps
	// the call site from doing post-hoc mutation on an aliased copy
	// (`body as Foo & Bar`) and keeps the request contract auditable
	// in one place.
	type TestimonialWriteRequestWithExtras = TestimonialWriteRequest & {
		incident_date_precision?: 'exact' | 'approximate' | 'unknown';
		incident_types?: string[];
	};

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

	/* Build a single payload object from the reactive form state. The
	   field names match the keys in `newTestimonialSchema`, so the
	   schema's `safeParse` validates without a translation step. */
	function buildInput() {
		return {
			title,
			country,
			region,
			incidentDate,
			incidentDatePrecision,
			language,
			summary,
			narrative,
			outcome,
			verificationLevel,
			sourceVisibility,
			publicSourceLabel,
			locationVisibility,
			familyProtected,
			contactProtected,
		};
	}

	// Local submit lifecycle: create (always → status=draft) →
	// optional submit (status=under_review) → final redirect.
	async function save(submitAfter: boolean) {
		// Re-entrancy guard — if a fast double-click beats the
		// disabled={saving} DOM attribute, bail before any state
		// changes so we don't kick off two concurrent fetches.
		if (saving) return;

		// Client-side validation gate — never enter the network
		// path with placeholder or missing values. The schema lives
		// in `$lib/schemas/testimonialForm.ts` so the rules are
		// shared with any future editor/publish flow.
		const result = newTestimonialSchema.safeParse(buildInput());
		if (!result.success) {
			const v = zodToFieldErrors(result.error);
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
			return await saveImpl(submitAfter, result.data);
		} finally {
			saving = false;
		}
	}

	async function saveImpl(
		submitAfter: boolean,
		data: NewTestimonialInput,
	): Promise<void> {
		// Build ONE body. The schema has already trimmed every string
		// field, so the request payload is constructed directly from
		// `data` — no extra `.trim()` calls scattered through here.
		// `verification_level` accepts an empty string from the form
		// ("not set"), which the backend treats as null; coerce to
		// undefined so JSON.stringify drops it from the wire payload.
		const body: TestimonialWriteRequestWithExtras = {
			title: data.title,
			country: data.country,
			region: data.region,
			incident_date: data.incidentDate || null,
			incident_date_precision: incidentDatePrecision,
			summary: data.summary,
			narrative: data.narrative,
			outcome: data.outcome,
			language: data.language,
			verification_level: (data.verificationLevel || undefined) as
				| TestimonialWriteRequest['verification_level']
				| undefined,
			source_visibility: data.sourceVisibility,
			public_source_label: data.publicSourceLabel,
			location_visibility: data.locationVisibility,
			family_protected: data.familyProtected,
			contact_protected: data.contactProtected,
		};

		// One create call, regardless of submit/draft — `testimonialsCreate`
		// always lands the row at status='draft'. The optional submit
		// transition below is a separate, idempotent call against the
		// already-saved id; if it fails the row stays a draft on the
		// server and the user can retry.
		let id: number;
		try {
			const res = await testimonialsCreate(body);
			id = extractCreatedId(res);
		} catch (e: unknown) {
			formError =
				e instanceof Error ? e.message : 'Could not create the testimonial.';
			return;
		}
		createdId = id;

		if (!submitAfter) {
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
			return;
		}

		// submitAfter === true: transition draft → under_review. If
		// this fails the row is still a draft on the server; surface
		// both halves of the result so the user doesn't re-submit and
		// double-create.
		try {
			await testimonialsSubmitCreate(id, {});
		} catch (e: unknown) {
			formError =
				e instanceof Error
					? `Saved as draft, but submission failed: ${e.message}. ` +
						'You can retry the submit from the testimonial page.'
					: 'Saved as draft, but the submit step failed. ' +
						'You can retry from the testimonial page.';
			return;
		}
		// The detail page IS the success confirmation for the submit
		// path — no banner needed (and no banner would be visible
		// anyway after navigation).
		await goto(`${base}/testimonials/${id}`);
	}

	/**
	 * DRF's `ModelViewSet.create` returns the serializer data
	 * directly — NOT wrapped in `{ data, status }` — even though
	 * orval's generated TypeScript type assumes the wrapper. Earlier
	 * code read `res.data.id` and fell through to the
	 * "did not include id" branch on every successful create,
	 * surfacing "broken cards" and a frozen form. Accept either
	 * shape; throw a typed error if the id is missing or wrong-type
	 * so the caller surfaces a clear, user-friendly message.
	 */
	function extractCreatedId(res: unknown): number {
		const outer = (res ?? {}) as Record<string, unknown>;
		const candidate =
			outer.data && typeof outer.data === 'object'
				? (outer.data as Record<string, unknown>)
				: outer;
		const id = candidate.id;
		if (typeof id !== 'number' || !Number.isFinite(id)) {
			throw new Error(
				'The server accepted the testimonial but its response was missing a valid id. ' +
					'Please retry — if the problem persists, contact support via the audit log.',
			);
		}
		return id;
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
