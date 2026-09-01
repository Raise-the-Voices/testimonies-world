<script lang="ts">
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { user, isVolunteer, loadSession } from '$lib/session';
	import { createPerson, createReport, getCategories, ApiError } from '$lib/api';

	let currentUser = $derived($user);
	let categories: any[] = $state([]);
	let saving = $state(false);
	let refreshing = $state(false);
	// Top-level banner — ONLY for API / auth / server failures.
	let formError = $state('');
	let formErrorKind = $state<'auth' | 'server' | 'other'>('other');
	// Per-field errors — shown inline below each field.
	let errors = $state<Record<string, string>>({});

	// Character-counter ceilings
	const MAX_NARRATIVE = 5000;
	const MAX_SHORT = 1000;

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
		try {
			const data = await getCategories();
			categories = Array.isArray(data) ? data : data.results ?? [];
		} catch (e) {
			console.error(e);
		}
	});

	function toggleCategory(id: number) {
		if (selectedCategories.includes(id)) {
			selectedCategories = selectedCategories.filter((c) => c !== id);
		} else {
			selectedCategories = [...selectedCategories, id];
		}
	}

	function clearError(field: string) {
		if (errors[field]) {
			const next = { ...errors };
			delete next[field];
			errors = next;
		}
		if (formError) formError = '';
	}

	function validate(): Record<string, string> {
		const e: Record<string, string> = {};
		if (!name.trim()) e.name = 'Add the person’s name — even a partial name helps.';
		else if (name.length > MAX_SHORT) e.name = `Keep the name under ${MAX_SHORT.toLocaleString()} characters.`;

		if (!country.trim()) e.country = 'Which country is this case in?';
		else if (country.length > MAX_SHORT) e.country = `Keep this under ${MAX_SHORT.toLocaleString()} characters.`;

		if (!narrative.trim())
			e.narrative = 'Tell us what happened — even one sentence about the first report is required.';
		else if (narrative.length > MAX_NARRATIVE)
			e.narrative = `Trim this down — please keep it under ${MAX_NARRATIVE.toLocaleString()} characters.`;

		if (summaryNarrative.length > MAX_NARRATIVE)
			e.summary = `Trim this down — please keep it under ${MAX_NARRATIVE.toLocaleString()} characters.`;
		if (sourceAttribution.length > MAX_SHORT)
			e.source_attr = `Keep this under ${MAX_SHORT.toLocaleString()} characters.`;
		if (reportRoughLocation.length > MAX_SHORT)
			e.report_location = `Keep this under ${MAX_SHORT.toLocaleString()} characters.`;
		if (suspectedReason.length > MAX_NARRATIVE)
			e.suspected_reason = `Keep this under ${MAX_NARRATIVE.toLocaleString()} characters.`;
		if (officialReason.length > MAX_NARRATIVE)
			e.official_reason = `Keep this under ${MAX_NARRATIVE.toLocaleString()} characters.`;

		if (lastKnownDate) {
			if (Number.isNaN(new Date(lastKnownDate).getTime())) e.last_known_date = 'That doesn’t look like a valid date.';
		}
		if (dateOfBirth) {
			if (Number.isNaN(new Date(dateOfBirth).getTime())) e.dob = 'That doesn’t look like a valid date.';
		}
		if (reportDateStart) {
			if (Number.isNaN(new Date(reportDateStart).getTime())) e.report_date = 'That doesn’t look like a valid date.';
		}

		return e;
	}

	function focusFirstError(errs: Record<string, string>) {
		const order = [
			'name', 'country', 'status', 'medical', 'rough_location', 'precise_location',
			'last_known_date', 'ethnicity', 'gender', 'dob',
			'summary', 'source_type', 'source_attr', 'reporter_name', 'reporter_contact',
			'report_date', 'report_location', 'narrative', 'suspected_reason', 'official_reason',
		];
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

	async function doRefreshSession() {
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
			const personData: any = {
				name: name.trim(),
				country: country.trim(),
				current_status: currentStatus,
				medical_status: medicalStatus,
				rough_location: roughLocation.trim(),
				precise_location: preciseLocation.trim(),
				summary_narrative: summaryNarrative.trim(),
				ethnicity: ethnicity.trim(),
				gender: gender || undefined,
				category_ids: selectedCategories,
			};
			if (lastKnownDate) personData.last_known_date = lastKnownDate;
			if (dateOfBirth) personData.date_of_birth = dateOfBirth;

			const person = await createPerson(personData);

			await createReport({
				person: person.id,
				source_type: sourceType,
				source_attribution: sourceAttribution.trim(),
				reporter_name: reporterName.trim(),
				reporter_contact: reporterContact.trim(),
				date_start: reportDateStart || null,
				rough_location: reportRoughLocation.trim(),
				narrative: narrative.trim(),
				suspected_reason: suspectedReason.trim(),
				official_reason: officialReason.trim(),
			});

			goto(`${base}/persons/${person.id}`);
		} catch (e: any) {
			if (e instanceof ApiError) {
				if (e.isValidation && Object.keys(e.fieldErrors).length > 0) {
					const mapped: Record<string, string> = {};
					for (const [k, msgs] of Object.entries(e.fieldErrors)) {
						mapped[k] = msgs[0];
					}
					errors = mapped;
					focusFirstError(mapped);
				} else if (e.isUnauthorized) {
					formErrorKind = 'auth';
					formError =
						'Your session has expired, or you don’t have permission to submit cases. ' +
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
	const narrativeCount = $derived(narrative.length);
	const summaryCount = $derived(summaryNarrative.length);
	const suspectedCount = $derived(suspectedReason.length);
	const officialCount = $derived(officialReason.length);
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
				Document someone facing oppression. Only <em>name</em>, <em>country</em>, and an
				<em>initial narrative</em> are required — every other field can be filled in later as more is known.
			</p>
		</header>

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
								onclick={doRefreshSession}
								disabled={refreshing}
							>
								{refreshing ? 'Refreshing…' : 'Refresh session'}
							</button>
							<a
								href="{base}/api/auth/login/?next={base}/submit"
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
			<!-- ============== Section 1: Person Information ============== -->
			<section class="form-section" aria-labelledby="sec-person">
				<h2 id="sec-person" class="form-section-title">
					<span class="title-bar" aria-hidden="true"></span>
					Person Information
				</h2>
				<p class="form-section-desc">Basic identifying details about the person.</p>

				<div class="form-grid">
					<div class="field" class:has-error={errors.name}>
						<label for="name">Name <span class="required-mark" aria-hidden="true">*</span></label>
						<input
							id="name"
							bind:value={name}
							oninput={() => clearError('name')}
							required
							aria-required="true"
							placeholder="Person's full name"
							autocomplete="off"
							aria-invalid={errors.name ? 'true' : 'false'}
							aria-describedby={errors.name ? 'name-error' : 'name-help'}
						/>
						{#if errors.name}
							<p class="field-error" id="name-error" role="alert">{errors.name}</p>
						{:else}
							<p class="field-help" id="name-help">Full name, partial name, or alias — anything that identifies them.</p>
						{/if}
					</div>

					<div class="field" class:has-error={errors.country}>
						<label for="country">Country <span class="required-mark" aria-hidden="true">*</span></label>
						<input
							id="country"
							bind:value={country}
							oninput={() => clearError('country')}
							required
							aria-required="true"
							placeholder="Country where the case is"
							autocomplete="country-name"
							aria-invalid={errors.country ? 'true' : 'false'}
							aria-describedby={errors.country ? 'country-error' : 'country-help'}
						/>
						{#if errors.country}
							<p class="field-error" id="country-error" role="alert">{errors.country}</p>
						{:else}
							<p class="field-help" id="country-help">Where the case is happening — country-level is enough.</p>
						{/if}
					</div>

					<div class="field">
						<label for="status">Current Status</label>
						<select id="status" bind:value={currentStatus}>
							<option value="unknown" disabled hidden>Select current status…</option>
							<option value="detained">Detained</option>
							<option value="disappeared">Disappeared</option>
							<option value="restricted_movement">Restricted Movement</option>
							<option value="released">Released</option>
							<option value="deceased">Deceased</option>
							<option value="stateless">Stateless</option>
							<option value="rights_restricted">Rights Restricted</option>
						</select>
					</div>

					<div class="field">
						<label for="medical">Medical Status</label>
						<select id="medical" bind:value={medicalStatus}>
							<option value="unknown" disabled hidden>Select medical status…</option>
							<option value="healthy">Healthy</option>
							<option value="health_concerns">Health Concerns</option>
							<option value="critical">Critical</option>
							<option value="deceased">Deceased</option>
						</select>
					</div>

					<div class="field">
						<label for="rough_location">
							Location
							<span class="privacy-dot privacy-dot-public" aria-label="Public"></span>
							<span class="visually-hidden">(public)</span>
						</label>
						<input
							id="rough_location"
							bind:value={roughLocation}
							placeholder="Region or city"
						/>
						<p class="field-help">Region- or city-level — shown publicly.</p>
					</div>

					<div class="field">
						<label for="precise_location">
							Precise Location
							<span class="privacy-dot privacy-dot-private" aria-label="Private"></span>
							<span class="visually-hidden">(private)</span>
						</label>
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
						<input id="ethnicity" bind:value={ethnicity} placeholder="Ethnicity or heritage" />
					</div>

					<div class="field">
						<label for="gender">Gender</label>
						<select id="gender" bind:value={gender}>
							<option value="" disabled hidden>Select gender…</option>
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

			<!-- ============== Section 2: Summary & Categories ============== -->
			<section class="form-section" aria-labelledby="sec-summary">
				<h2 id="sec-summary" class="form-section-title">
					<span class="title-bar" aria-hidden="true"></span>
					Summary &amp; Categories
				</h2>
				<p class="form-section-desc">A short overview and the categories that apply to this case.</p>

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
										<span class="category-check" aria-hidden="true">
											{#if selectedCategories.includes(cat.id)}
												<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
													<polyline points="20 6 9 17 4 12" />
												</svg>
											{/if}
										</span>
										<input
											type="checkbox"
											checked={selectedCategories.includes(cat.id)}
											onchange={() => toggleCategory(cat.id)}
										/>
										<span class="category-name">{cat.name}</span>
									</label>
								{/each}
							</div>
						{/if}
					</div>
				</div>
			</section>

			<!-- ============== Section 3: Initial Report ============== -->
			<section class="form-section" aria-labelledby="sec-report">
				<h2 id="sec-report" class="form-section-title">
					<span class="title-bar" aria-hidden="true"></span>
					Initial Report
				</h2>
				<p class="form-section-desc">The first testimony or report about this person — what happened, and what's known.</p>

				<div class="form-grid">
					<div class="field">
						<label for="source_type">Source Type</label>
						<select id="source_type" bind:value={sourceType}>
							<option value="firsthand" disabled hidden>Select source type…</option>
							<option value="firsthand">Firsthand</option>
							<option value="secondhand">Secondhand</option>
							<option value="news">News report</option>
							<option value="document">Document</option>
						</select>
					</div>

					<div class="field">
						<label for="source_attr">
							Source Attribution
							<span class="privacy-dot privacy-dot-public" aria-label="Public"></span>
							<span class="visually-hidden">(public)</span>
						</label>
						<input
							id="source_attr"
							bind:value={sourceAttribution}
							placeholder='e.g. "family member", "BBC article"'
						/>
						<p class="field-help">Shown publicly — e.g. "family member" or a media outlet name.</p>
					</div>

					<div class="field">
						<label for="reporter_name">
							Reporter Name
							<span class="privacy-dot privacy-dot-private" aria-label="Private"></span>
							<span class="visually-hidden">(private)</span>
						</label>
						<input
							id="reporter_name"
							bind:value={reporterName}
							placeholder="Reporter's name"
							autocomplete="off"
						/>
						<p class="field-help">Stored privately — never displayed on the public case page.</p>
					</div>

					<div class="field">
						<label for="reporter_contact">
							Reporter Contact
							<span class="privacy-dot privacy-dot-private" aria-label="Private"></span>
							<span class="visually-hidden">(private)</span>
						</label>
						<input
							id="reporter_contact"
							bind:value={reporterContact}
							placeholder="Email, phone, or Signal handle"
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
						<input id="report_location" bind:value={reportRoughLocation} placeholder="Where the event took place" />
					</div>
				</div>

				<div class="field-stack" style="margin-top: 1.25rem;">
					<div class="field" class:has-error={errors.narrative}>
						<label for="narrative">
							What happened? <span class="required-mark" aria-hidden="true">*</span>
						</label>
						<textarea
							id="narrative"
							bind:value={narrative}
							oninput={() => clearError('narrative')}
							required
							aria-required="true"
							rows="5"
							placeholder="Describe what happened, when, and what's known so far."
							aria-invalid={errors.narrative ? 'true' : 'false'}
							aria-describedby={[
								errors.narrative ? 'narrative-error' : 'narrative-help',
								'narrative-counter',
							]
								.filter(Boolean)
								.join(' ')}
						></textarea>
						<div class="field-meta">
							{#if errors.narrative}
								<p class="field-error" id="narrative-error" role="alert">{errors.narrative}</p>
							{:else}
								<p class="field-help" id="narrative-help">
									Plain prose. Dates, names, places — the more concrete the better.
								</p>
							{/if}
							<p
								id="narrative-counter"
								class="char-counter"
								class:over={narrativeCount > MAX_NARRATIVE}
							>
								{narrativeCount.toLocaleString()} / {MAX_NARRATIVE.toLocaleString()}
							</p>
						</div>
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
				<p class="form-actions-note">You'll be taken to the case page after submission.</p>
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

	/* === Per-field error message === */
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

	/* Privacy dot — small colored circle after the label.
	   Green dot = public, red dot = private. */
	.privacy-dot {
		display: inline-block;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex: 0 0 8px;
	}
	.privacy-dot-public {
		background: var(--color-success);
		box-shadow: 0 0 0 3px rgba(47, 133, 90, 0.18);
	}
	.privacy-dot-private {
		background: var(--color-danger);
		box-shadow: 0 0 0 3px rgba(217, 22, 22, 0.18);
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

	/* === Categories as interactive pills with visible check mark === */
	.categories-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
		gap: 0.5rem;
	}
	.category-pill {
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

	/* Visible check indicator — an empty box that fills with
	   primary color and a white check when selected. */
	.category-check {
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
	.category-pill.is-selected .category-check {
		background: var(--color-primary);
		border-color: var(--color-primary);
		color: white;
	}
	.category-pill:hover .category-check {
		border-color: var(--color-primary-light);
	}

	/* Native checkbox hidden but accessible */
	.category-pill input[type='checkbox'] {
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
	.category-pill input[type='checkbox']:focus-visible + .category-check,
	.category-pill:focus-within .category-check {
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
		.form-error-actions {
			flex-direction: column;
			align-items: stretch;
		}
		.form-error-actions .btn-sm {
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
		.category-check,
		.spinner {
			transition: none;
			animation: none;
		}
	}
</style>
