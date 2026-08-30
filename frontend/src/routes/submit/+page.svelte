<script lang="ts">
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { user, isVolunteer } from '$lib/session';
	import { createPerson, createReport, getCategories } from '$lib/api';

	let currentUser = $derived($user);
	let categories: any[] = $state([]);
	let saving = $state(false);
	let errorMsg = $state('');

	// Person fields
	let name = $state('');
	let country = $state('');
	let currentStatus = $state('unknown');
	let medicalStatus = $state('unknown');
	let roughLocation = $state('');
	let preciseLocation = $state('');
	let lastKnownDate = $state('');
	let summaryNarrative = $state('');
	let ethnicity = $state('');
	let gender = $state('');
	let dateOfBirth = $state('');
	let selectedCategories: number[] = $state([]);

	// Initial report fields
	let sourceType = $state('firsthand');
	let sourceAttribution = $state('');
	let reporterName = $state('');
	let reporterContact = $state('');
	let reportDateStart = $state('');
	let reportRoughLocation = $state('');
	let narrative = $state('');
	let suspectedReason = $state('');
	let officialReason = $state('');

	onMount(async () => {
		const data = await getCategories();
		categories = Array.isArray(data) ? data : data.results ?? [];
	});

	function toggleCategory(id: number) {
		if (selectedCategories.includes(id)) {
			selectedCategories = selectedCategories.filter((c) => c !== id);
		} else {
			selectedCategories = [...selectedCategories, id];
		}
	}

	async function handleSubmit() {
		if (!name || !country) {
			errorMsg = 'Name and country are required.';
			return;
		}
		if (!narrative) {
			errorMsg = 'Please provide a narrative for the initial report.';
			return;
		}

		saving = true;
		errorMsg = '';

		try {
			const personData: any = {
				name,
				country,
				current_status: currentStatus,
				medical_status: medicalStatus,
				rough_location: roughLocation,
				precise_location: preciseLocation,
				summary_narrative: summaryNarrative,
				ethnicity,
				gender: gender || undefined,
				category_ids: selectedCategories,
			};
			if (lastKnownDate) personData.last_known_date = lastKnownDate;
			if (dateOfBirth) personData.date_of_birth = dateOfBirth;

			const person = await createPerson(personData);

			await createReport({
				person: person.id,
				source_type: sourceType,
				source_attribution: sourceAttribution,
				reporter_name: reporterName,
				reporter_contact: reporterContact,
				date_start: reportDateStart || null,
				rough_location: reportRoughLocation,
				narrative,
				suspected_reason: suspectedReason,
				official_reason: officialReason,
			});

			goto(`${base}/persons/${person.id}`);
		} catch (e: any) {
			errorMsg = e.message || 'Failed to save.';
		}
		saving = false;
	}
</script>

<svelte:head>
	<title>Submit Case — Testimonies.world</title>
</svelte:head>

<div class="container">
	{#if !isVolunteer(currentUser)}
		<p class="muted">
			You must be logged in as a volunteer to submit cases.
			<a href="{base}/api/auth/login/?next={base}/submit">Login</a>
		</p>
	{:else}
		<header class="form-header">
			<h1>Submit a Case</h1>
			<p class="form-intro">
				Document someone facing oppression. Only <strong>name</strong>,
				<strong>country</strong>, and an <strong>initial narrative</strong> are required — every other field can
				be filled in later as more is known.
			</p>
		</header>

		{#if errorMsg}
			<div class="error-banner" role="alert">{errorMsg}</div>
		{/if}

		<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} novalidate>
			<!-- Section 1: Person Information -->
			<section class="form-section">
				<header class="form-section-header">
					<span class="section-number" aria-hidden="true">1</span>
					<div class="form-section-titles">
						<h2>Person Information</h2>
						<p class="form-section-desc">Basic identifying details about the person.</p>
					</div>
				</header>

				<div class="form-grid">
					<div class="field">
						<label for="name">Name <span class="required-mark" aria-hidden="true">*</span></label>
						<input id="name" bind:value={name} required aria-required="true" autocomplete="off" />
					</div>

					<div class="field">
						<label for="country">Country <span class="required-mark" aria-hidden="true">*</span></label>
						<input id="country" bind:value={country} required aria-required="true" autocomplete="country-name" />
					</div>

					<div class="field">
						<label for="status">Current Status</label>
						<select id="status" bind:value={currentStatus}>
							<option value="detained">Detained</option>
							<option value="disappeared">Disappeared</option>
							<option value="restricted_movement">Restricted Movement</option>
							<option value="released">Released</option>
							<option value="deceased">Deceased</option>
							<option value="unknown">Unknown</option>
							<option value="stateless">Stateless</option>
							<option value="rights_restricted">Rights Restricted</option>
						</select>
					</div>

					<div class="field">
						<label for="medical">Medical Status</label>
						<select id="medical" bind:value={medicalStatus}>
							<option value="unknown">Unknown</option>
							<option value="healthy">Healthy</option>
							<option value="health_concerns">Health Concerns</option>
							<option value="critical">Critical</option>
							<option value="deceased">Deceased</option>
						</select>
					</div>

					<div class="field">
						<label for="rough_location">Location <span class="field-tag">public</span></label>
						<input id="rough_location" bind:value={roughLocation} placeholder="Region or city" />
						<p class="field-help">Region- or city-level — shown publicly.</p>
					</div>

					<div class="field">
						<label for="precise_location">Precise Location <span class="field-tag field-tag-private">private</span></label>
						<input
							id="precise_location"
							bind:value={preciseLocation}
							placeholder="Street address or coordinates"
						/>
						<p class="field-help">Address or coordinates — stored privately, never displayed publicly.</p>
					</div>

					<div class="field">
						<label for="last_known_date">Last Known Date</label>
						<input id="last_known_date" type="date" bind:value={lastKnownDate} />
					</div>

					<div class="field">
						<label for="ethnicity">Ethnicity</label>
						<input id="ethnicity" bind:value={ethnicity} />
					</div>

					<div class="field">
						<label for="gender">Gender</label>
						<select id="gender" bind:value={gender}>
							<option value="">—</option>
							<option value="M">Male</option>
							<option value="F">Female</option>
							<option value="O">Other</option>
							<option value="U">Unknown</option>
						</select>
					</div>

					<div class="field">
						<label for="dob">Date of Birth</label>
						<input id="dob" type="date" bind:value={dateOfBirth} />
					</div>
				</div>
			</section>

			<!-- Section 2: Summary & Categories -->
			<section class="form-section">
				<header class="form-section-header">
					<span class="section-number" aria-hidden="true">2</span>
					<div class="form-section-titles">
						<h2>Summary &amp; Categories</h2>
						<p class="form-section-desc">
							A short overview and the categories that apply to this case.
						</p>
					</div>
				</header>

				<div class="field-stack">
					<div class="field">
						<label for="summary">Summary Narrative</label>
						<textarea
							id="summary"
							bind:value={summaryNarrative}
							placeholder="A few sentences is enough — this can grow later."
						></textarea>
						<p class="field-help">
							Plain prose — no need to be exhaustive. The first report below carries the detail.
						</p>
					</div>

					<div class="field">
						<span class="field-label">Categories</span>
						{#if categories.length === 0}
							<p class="field-help">No categories configured yet.</p>
						{:else}
							<div class="categories-grid" role="group" aria-label="Categories">
								{#each categories as cat (cat.id)}
									<label class="category-pill" class:is-selected={selectedCategories.includes(cat.id)}>
										<input
											type="checkbox"
											checked={selectedCategories.includes(cat.id)}
											onchange={() => toggleCategory(cat.id)}
										/>
										<span>{cat.name}</span>
									</label>
								{/each}
							</div>
						{/if}
					</div>
				</div>
			</section>

			<!-- Section 3: Initial Report -->
			<section class="form-section">
				<header class="form-section-header">
					<span class="section-number" aria-hidden="true">3</span>
					<div class="form-section-titles">
						<h2>Initial Report</h2>
						<p class="form-section-desc">
							The first testimony or report about this person — what happened, and what's known.
						</p>
					</div>
				</header>

				<div class="form-grid">
					<div class="field">
						<label for="source_type">Source Type</label>
						<select id="source_type" bind:value={sourceType}>
							<option value="firsthand">Firsthand</option>
							<option value="secondhand">Secondhand</option>
							<option value="news">News report</option>
							<option value="document">Document</option>
						</select>
					</div>

					<div class="field">
						<label for="source_attr">Source Attribution <span class="field-tag">public</span></label>
						<input
							id="source_attr"
							bind:value={sourceAttribution}
							placeholder='e.g. "family member", "BBC article"'
						/>
						<p class="field-help">Shown publicly — e.g. "family member" or a media outlet name.</p>
					</div>

					<div class="field">
						<label for="reporter_name">Reporter Name <span class="field-tag field-tag-private">private</span></label>
						<input
							id="reporter_name"
							bind:value={reporterName}
							placeholder="Not shown publicly"
							autocomplete="off"
						/>
						<p class="field-help">Stored privately — never displayed on the public case page.</p>
					</div>

					<div class="field">
						<label for="reporter_contact">Reporter Contact <span class="field-tag field-tag-private">private</span></label>
						<input
							id="reporter_contact"
							bind:value={reporterContact}
							placeholder="Email, phone, Signal — anything to follow up"
							autocomplete="off"
						/>
						<p class="field-help">Stored privately. Used only by casework volunteers to verify or follow up.</p>
					</div>

					<div class="field">
						<label for="report_date">Date of Event</label>
						<input id="report_date" type="date" bind:value={reportDateStart} />
					</div>

					<div class="field">
						<label for="report_location">Event Location</label>
						<input id="report_location" bind:value={reportRoughLocation} />
					</div>
				</div>

				<div class="field-stack" style="margin-top: 1.25rem;">
					<div class="field">
						<label for="narrative">
							What happened? <span class="required-mark" aria-hidden="true">*</span>
						</label>
						<textarea
							id="narrative"
							bind:value={narrative}
							required
							aria-required="true"
							rows="5"
							placeholder="Describe what happened, when, and what's known so far."
						></textarea>
						<p class="field-help">Plain prose. Dates, names, places — the more concrete the better.</p>
					</div>

					<div class="form-grid">
						<div class="field">
							<label for="suspected_reason">Suspected Reason</label>
							<textarea
								id="suspected_reason"
								bind:value={suspectedReason}
								rows="3"
								placeholder="What do sources believe is the reason?"
							></textarea>
						</div>

						<div class="field">
							<label for="official_reason">Official Reason</label>
							<textarea
								id="official_reason"
								bind:value={officialReason}
								rows="3"
								placeholder="What did the state officially charge?"
							></textarea>
						</div>
					</div>
				</div>
			</section>

			<!-- Submit -->
			<div class="form-actions">
				<p class="form-actions-note">
					You'll be taken to the case page after submission.
				</p>
				<button type="submit" class="btn btn-primary submit-btn" disabled={saving}>
					{#if saving}
						<span class="spinner" aria-hidden="true"></span>
						Saving…
					{:else}
						Submit Case
					{/if}
				</button>
			</div>
		</form>
	{/if}
</div>

<style>
	/* === Page header === */
	.form-header {
		margin-bottom: 1.75rem;
	}
	.form-header h1 {
		margin: 0 0 0.5rem 0;
		color: var(--color-text);
	}
	.form-intro {
		margin: 0;
		max-width: var(--max-w-prose);
		color: var(--color-text-muted);
		font-size: 1rem;
		line-height: 1.6;
	}
	.form-intro strong {
		color: var(--color-text);
		font-weight: 600;
	}

	/* === Section card === */
	.form-section {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-card);
		padding: 1.75rem 2rem;
		margin-bottom: 1.5rem;
	}
	.form-section-header {
		display: flex;
		align-items: flex-start;
		gap: 1rem;
		padding-bottom: 1.25rem;
		margin-bottom: 1.5rem;
		border-bottom: 1px solid var(--color-border-subtle);
	}
	.section-number {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		border-radius: 50%;
		background: var(--color-primary-tint);
		color: var(--color-primary);
		font-weight: 700;
		font-size: 0.95rem;
		flex: 0 0 32px;
		font-variant-numeric: tabular-nums;
	}
	.form-section-titles {
		min-width: 0;
	}
	.form-section h2 {
		margin: 0;
		font-size: 1.2rem;
		font-weight: 700;
		color: var(--color-text);
		line-height: 1.3;
	}
	.form-section-desc {
		margin: 0.3rem 0 0 0;
		color: var(--color-text-muted);
		font-size: 0.9rem;
		line-height: 1.5;
	}

	/* === Form grid === */
	.form-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 1.25rem 1.5rem;
	}
	.field-stack {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	/* === Field === */
	.field {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
		min-width: 0;
	}
	.field label,
	.field-label {
		font-size: 0.85rem;
		font-weight: 600;
		color: var(--color-text);
		line-height: 1.3;
	}
	.required-mark {
		color: var(--color-danger);
		font-weight: 700;
		margin-left: 0.15rem;
	}
	.field-tag {
		display: inline-block;
		font-size: 0.65rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04rem;
		padding: 0.1rem 0.4rem;
		border-radius: 999px;
		background: var(--color-surface);
		color: var(--color-text-muted);
		margin-left: 0.4rem;
		vertical-align: middle;
	}
	.field-tag-private {
		background: rgba(217, 22, 22, 0.08);
		color: var(--color-danger);
	}

	.field-help {
		margin: 0;
		font-size: 0.78rem;
		color: var(--color-text-muted);
		line-height: 1.45;
	}

	/* Inputs share one consistent look — single source of truth for border,
	   radius, padding, focus ring, and placeholder contrast. */
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
		background-image: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23666' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
		background-repeat: no-repeat;
		background-position: right 0.85rem center;
		background-size: 12px 12px;
	}
	.field input::placeholder,
	.field textarea::placeholder {
		color: var(--color-text-muted);
		opacity: 0.65;
	}
	.field input:hover:not(:focus):not(:disabled),
	.field select:hover:not(:focus):not(:disabled),
	.field textarea:hover:not(:focus):not(:disabled) {
		border-color: var(--color-border);
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

	/* === Categories as interactive pills === */
	.categories-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
		gap: 0.5rem;
	}
	.category-pill {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.55rem 0.9rem;
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
	.category-pill:hover {
		border-color: var(--color-primary-light);
		background: var(--color-surface);
	}
	.category-pill.is-selected {
		background: var(--color-primary-tint);
		border-color: var(--color-primary);
		color: var(--color-primary);
		font-weight: 600;
	}
	.category-pill input[type='checkbox'] {
		width: auto;
		margin: 0;
		accent-color: var(--color-primary);
		cursor: pointer;
	}
	.category-pill:focus-within {
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
		border: 1px solid var(--color-border-light);
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
		.form-section-header {
			gap: 0.75rem;
		}
		.form-grid {
			grid-template-columns: 1fr;
			gap: 1rem;
		}
		.categories-grid {
			grid-template-columns: repeat(2, minmax(0, 1fr));
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
	@media (max-width: 420px) {
		.categories-grid {
			grid-template-columns: 1fr;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.field input,
		.field select,
		.field textarea,
		.category-pill,
		.spinner {
			transition: none;
			animation: none;
		}
	}
</style>
