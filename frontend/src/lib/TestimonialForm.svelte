<!--
	TestimonialForm — shared form body for create + edit flows.

	Extracted from /testimonials/new/+page.svelte so the edit route
	(/testimonials/[id]/edit) can reuse the exact same validation,
	sanitization, and submit lifecycle. Two modes:

	  - `mode="create"` — POSTs testimonialsCreate(), optionally
	    transitions draft → under_review via testimonialsSubmitCreate.
	    After a successful create the form resets to a fresh blank
	    entry (the create flow's "save another" affordance).
	  - `mode="edit"`   — PATCHes testimonialsUpdate(id, body). Only
	    callable on rows where the current viewer can edit (the
	    backend's CanEditOwnOrReview gate). Published/archived rows
	    are immutable from the volunteer side — the edit page should
	    never reach this component for them; if it does, the server
	    will 403.

	The component is the single source of truth for the testimonial
	field set — adding / renaming a field happens here, not in two
	places.
-->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { user } from '$lib/session';
	import type { User } from '$lib/types';
	import {
		testimonialsCreate,
		testimonialsSubmitCreate,
		testimonialsUpdate,
	} from '$lib/api/generated/endpoints';
	import type { TestimonialWriteRequest } from '$lib/api/generated/endpoints.schemas';
	import {
		newTestimonialSchema,
		zodToFieldErrors,
		type NewTestimonialInput,
	} from '$lib/schemas/testimonialForm';
	import type { TestimonialPublic } from '$lib/api/generated/endpoints.schemas';

	type Mode = 'create' | 'edit';
	type TestimonialWriteRequestWithExtras = TestimonialWriteRequest & {
		incident_date_precision?: 'exact' | 'approximate' | 'unknown';
		incident_types?: string[];
	};

	// Widen TestimonialPublic with the Internal-only fields the edit
	// form needs (source_visibility / location_visibility / status).
	// Anonymous GETs won't reach the edit page (it requires owning
	// the row, which is auth-gated), but the widen is safe either way.
	type EditableTestimonial = TestimonialPublic & {
		readonly status?: string;
		readonly source_visibility?: string;
		readonly location_visibility?: string;
	};

	interface Props {
		mode: Mode;
		/** Required when mode='edit' — the row to PATCH. */
		testimonial?: EditableTestimonial | null;
		/** SSR-hydrated current user (from +layout.svelte). */
		pageUser?: User | null;
		/** anonHref for the sign-in CTA when not authenticated. */
		anonHref?: string | null;
	}

	let { mode, testimonial = null, pageUser = null, anonHref }: Props = $props();

	let currentUser = $derived(pageUser ?? $user);
	let canPublish = $derived(
		currentUser?.authenticated
			? currentUser.is_staff === true
				|| (currentUser.groups ?? []).includes('Advocate')
			: false,
	);

	// Form state — pre-populated from `testimonial` in edit mode.
	let title = $state(testimonial?.title ?? '');
	let country = $state(testimonial?.country ?? '');
	let region = $state(testimonial?.region ?? '');
	let incidentDate = $state(testimonial?.incident_date ?? '');
	let incidentDatePrecision = $state<'exact' | 'approximate' | 'unknown'>(
		'unknown',
	);
	let summary = $state(testimonial?.summary ?? '');
	let narrative = $state(testimonial?.narrative ?? '');
	let outcome = $state(testimonial?.outcome ?? '');
	let language = $state(testimonial?.language ?? 'en');
	let verificationLevel = $state(testimonial?.verification_level ?? '');
	let sourceVisibility = $state<
		'hidden' | 'public_anonymous' | 'public_named'
	>(
		(testimonial?.source_visibility as
			| 'hidden' | 'public_anonymous' | 'public_named' | undefined) ?? 'hidden',
	);
	let publicSourceLabel = $state(testimonial?.public_source_label ?? '');
	let locationVisibility = $state<
		'public_precise' | 'public_region' | 'public_country' | 'hidden'
	>(
		(testimonial?.location_visibility as
			| 'public_precise' | 'public_region' | 'public_country' | 'hidden'
			| undefined) ?? 'public_region',
	);
	let familyProtected = $state(testimonial?.family_protected ?? true);
	let contactProtected = $state(testimonial?.contact_protected ?? true);

	let saving = $state(false);
	let errors = $state<Record<string, string>>({});
	let formError = $state('');
	let formSuccess = $state('');

	function buildInput(): NewTestimonialInput {
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

	function buildBody(): TestimonialWriteRequestWithExtras {
		return {
			title,
			country,
			region,
			incident_date: incidentDate || null,
			incident_date_precision: incidentDatePrecision,
			summary,
			narrative,
			outcome,
			language,
			verification_level: (verificationLevel || undefined) as
				| TestimonialWriteRequest['verification_level']
				| undefined,
			source_visibility: sourceVisibility,
			public_source_label: publicSourceLabel,
			location_visibility: locationVisibility,
			family_protected: familyProtected,
			contact_protected: contactProtected,
		};
	}

	async function save(submitAfter: boolean) {
		if (saving) return;
		const result = newTestimonialSchema.safeParse(buildInput());
		if (!result.success) {
			const v = zodToFieldErrors(result.error);
			errors = v;
			formError = 'Some fields need attention — see below.';
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
			if (mode === 'edit' && testimonial) {
				await testimonialsUpdate(
					testimonial.id,
					buildBody() as TestimonialWriteRequest,
					{ method: 'PATCH' },
				);
				formSuccess = 'Changes saved.';
				await goto(`${base}/testimonials/${testimonial.id}`);
				return;
			}

			// Create mode.
			let id: number;
			try {
				const res = await testimonialsCreate(buildBody());
				const outer = (res ?? {}) as Record<string, unknown>;
				const candidate =
					outer.data && typeof outer.data === 'object'
						? (outer.data as Record<string, unknown>)
						: outer;
				if (typeof candidate.id !== 'number') {
					throw new Error('Server response missing a valid id.');
				}
				id = candidate.id;
			} catch (e: unknown) {
				formError =
					e instanceof Error ? e.message : 'Could not create the testimonial.';
				return;
			}
			if (!submitAfter) {
				formSuccess = 'Draft saved.';
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
			try {
				await testimonialsSubmitCreate(id, {});
			} catch (e: unknown) {
				formError =
					e instanceof Error
						? `Saved as draft, but submission failed: ${e.message}. You can retry the submit from the testimonial page.`
						: 'Saved as draft, but submission failed. You can retry from the testimonial page.';
				return;
			}
			await goto(`${base}/testimonials/${id}`);
		} finally {
			saving = false;
		}
	}
</script>

{#if currentUser?.authenticated}
	<form class="testimonial-form" onsubmit={(e) => e.preventDefault()}>
		<fieldset>
			<legend>Identity</legend>

			<div class="form-row">
				<label for="title">Title <span class="form-required" aria-hidden="true">*</span></label>
				<input id="title" type="text" maxlength="255" bind:value={title}
					placeholder="Detention in Erbil, March 2024"
					aria-invalid={errors.title ? 'true' : undefined}
					aria-describedby={errors.title ? 'title-error' : undefined} />
				{#if errors.title}<p id="title-error" class="form-field-error">{errors.title}</p>{/if}
			</div>

			<div class="form-row form-row-grid">
				<div>
					<label for="country">Country <span class="form-required" aria-hidden="true">*</span></label>
					<input id="country" type="text" maxlength="100" bind:value={country}
						placeholder="Iraq"
						aria-invalid={errors.country ? 'true' : undefined}
						aria-describedby={errors.country ? 'country-error' : undefined} />
					{#if errors.country}<p id="country-error" class="form-field-error">{errors.country}</p>{/if}
				</div>
				<div>
					<label for="region">Region / province</label>
					<input id="region" type="text" maxlength="255" bind:value={region} placeholder="Erbil" />
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
				<textarea id="summary" rows="3" maxlength="2000" bind:value={summary}
					aria-invalid={errors.summary ? 'true' : undefined}
					aria-describedby={errors.summary ? 'summary-error' : undefined}></textarea>
				{#if errors.summary}<p id="summary-error" class="form-field-error">{errors.summary}</p>{/if}
			</div>

			<div class="form-row">
				<label for="narrative">Narrative (long form) <span class="form-required" aria-hidden="true">*</span></label>
				<textarea id="narrative" rows="8" maxlength="20000" bind:value={narrative}
					aria-invalid={errors.narrative ? 'true' : undefined}
					aria-describedby={errors.narrative ? 'narrative-error' : undefined}></textarea>
				{#if errors.narrative}<p id="narrative-error" class="form-field-error">{errors.narrative}</p>{/if}
			</div>

			<div class="form-row">
				<label for="outcome">Outcome</label>
				<textarea id="outcome" rows="3" maxlength="5000" bind:value={outcome}></textarea>
			</div>

			<div class="form-row">
				<label for="verification">Verification level</label>
				<select id="verification" bind:value={verificationLevel}>
					<option value="">— not set —</option>
					<option value="level_1_reported">Level 1 — Reported</option>
					<option value="level_2_partially_verified">Level 2 — Partially verified</option>
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
				<input id="public-source-label" type="text" maxlength="255"
					bind:value={publicSourceLabel}
					placeholder="Family member · Local witness · Press excerpt" />
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

		{#if formSuccess}<div class="form-success" role="status">{formSuccess}</div>{/if}
		{#if formError}<div class="form-error" role="alert">{formError}</div>{/if}

		<div class="form-actions">
			{#if mode === 'create'}
				<button type="button" class="btn btn-secondary" disabled={saving}
					onclick={() => save(false)}>Save as draft</button>
				<button type="button" class="btn btn-primary" disabled={saving}
					onclick={() => save(true)}>
					{saving ? 'Submitting…' : 'Submit for review'}
				</button>
			{:else}
				<button type="button" class="btn btn-primary" disabled={saving}
					onclick={() => save(false)}>
					{saving ? 'Saving…' : 'Save changes'}
				</button>
				<a class="form-saved-link" href="{base}/testimonials/{testimonial?.id}">Cancel</a>
			{/if}
		</div>
	</form>
{:else if anonHref}
	<div class="signin-panel">
		<a class="btn btn-primary" href={anonHref}>Sign in with Google</a>
	</div>
{/if}

<style>
	.testimonial-form { display: flex; flex-direction: column; gap: 1.25rem; }
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
	.form-row { display: flex; flex-direction: column; gap: 0.35rem; }
	.form-row-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.85rem;
	}
	@media (max-width: 600px) {
		.form-row-grid { grid-template-columns: 1fr; }
	}
	label {
		font-size: 0.85rem;
		font-weight: 700;
		color: var(--color-text);
		display: block;
	}
	input, select, textarea {
		font: inherit;
		padding: 0.5rem 0.65rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-input);
		background: var(--color-bg-white);
		color: var(--color-text);
		width: 100%;
		box-sizing: border-box;
	}
	input:focus-visible, select:focus-visible, textarea:focus-visible {
		outline: 3px solid var(--focus-ring);
		outline-offset: 1px;
		border-color: var(--color-primary);
	}
	textarea { resize: vertical; min-height: 4em; }
	.form-help { margin: 0; color: var(--color-text-muted); font-size: 0.82rem; }
	.checkbox-row {
		display: flex; align-items: center; gap: 0.55rem;
		font-size: 0.95rem; cursor: pointer;
	}
	.checkbox-row input[type='checkbox'] { width: 1.1rem; height: 1.1rem; }
	.form-error {
		padding: 0.85rem 1rem;
		border: 1px solid var(--color-danger);
		border-left: 3px solid var(--color-danger);
		border-radius: var(--radius-card);
		color: var(--color-danger);
		background: #fef2f2;
	}
	.form-success {
		padding: 0.85rem 1rem;
		border: 1px solid #86efac;
		border-left: 3px solid #16a34a;
		border-radius: var(--radius-card);
		color: #166534;
		background: #f0fdf4;
	}
	.form-required { color: var(--color-danger); margin-left: 0.15rem; }
	.form-field-error {
		margin: 0;
		font-size: 0.82rem;
		color: var(--color-danger);
	}
	input[aria-invalid='true'], textarea[aria-invalid='true'] {
		border-color: var(--color-danger);
	}
	.form-actions { display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap; }
	.form-saved-link {
		color: var(--color-primary);
		text-decoration: none;
		font-size: 0.9rem;
	}
	.form-saved-link:hover { text-decoration: underline; }
	.signin-panel {
		text-align: center;
		padding: 2rem;
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
	}
</style>