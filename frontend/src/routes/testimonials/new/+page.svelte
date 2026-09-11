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
	let createdId = $state<number | null>(null);

	// Local submit lifecycle: create (always → status=draft) →
	// optional submit (status=under_review) → final redirect.
	async function save(submitAfter: boolean) {
		if (saving) return;
		saving = true;
		formError = '';
		errors = {};

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

		let id: number | null = null;
		try {
			const res = await testimonialsCreate(body);
			const data = (res as { data?: { id?: number } }).data;
			id = data?.id ?? null;
			createdId = id;
		} catch (e: unknown) {
			formError =
				e instanceof Error ? e.message : 'Could not create the testimonial.';
			saving = false;
			return;
		}

		if (submitAfter && id !== null) {
			try {
				await testimonialsSubmitCreate(id, {});
			} catch (e: unknown) {
				formError =
					e instanceof Error
						? 'Saved as draft, but submission failed: ' + e.message
						: 'Saved as draft, but the submit call failed.';
				saving = false;
				return;
			}
		}

		saving = false;
		if (id !== null) {
			await goto(`${base}/testimonials/${id}`);
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
					<label for="title">Title</label>
					<input
						id="title"
						type="text"
						maxlength="255"
						bind:value={title}
						placeholder="Detention in Erbil, March 2024"
					/>
				</div>

				<div class="form-row form-row-grid">
					<div>
						<label for="country">Country</label>
						<input
							id="country"
							type="text"
							maxlength="100"
							bind:value={country}
							placeholder="Iraq"
						/>
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
					<label for="summary">Summary (1–2 paragraphs)</label>
					<textarea
						id="summary"
						rows="3"
						maxlength="2000"
						bind:value={summary}
					></textarea>
				</div>

				<div class="form-row">
					<label for="narrative">Narrative (long form)</label>
					<textarea
						id="narrative"
						rows="8"
						maxlength="20000"
						bind:value={narrative}
					></textarea>
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
