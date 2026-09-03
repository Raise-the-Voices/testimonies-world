<script lang="ts">
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { user, isVolunteer, isAdmin, loadSession } from '$lib/session';
	import { createPerson, createReport, getCategories, ApiError } from '$lib/api';

	let currentUser = $derived($user);
	let isAdminUser = $derived(isAdmin(currentUser));
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
	const MAX_ALIASES = 500;       // matches models.Person.aliases
	const MAX_LEGAL_NAME = 255;
	const MAX_PROFILE_IMAGE = 5 * 1024 * 1024; // 5 MB

	// Person fields — identity
	let name = $state('');
	let legalName = $state('');
	let aliasesRaw = $state('');         // comma-separated; presented as tags
	let country = $state('');

	// Person fields — demographics & location
	let currentStatus = $state('unknown');
	let medicalStatus = $state('unknown');
	let roughLocation = $state('');
	let preciseLocation = $state('');
	let lastKnownDate = $state('');
	let ethnicity = $state('');
	let gender = $state('');
	let dateOfBirth = $state('');

	// Person fields — media, evidence quality, privacy, verification
	let qualityTier = $state<number | ''>('');
	let profileImageFile = $state<File | null>(null);
	let profileImagePreview = $state<string | null>(null);
	let profileImageCleared = $state(false);  // explicit "remove image" signal
	let medicalNotes = $state('');
	let authoritativeSource = $state('');
	let authoritativeUrl = $state('');
	let isPublished = $state(true);
	let selectedCategories: number[] = $state([]);

	// Re-added — was lost in the script-block rewrite above.
	let summaryNarrative = $state('');

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

	/* --- Aliases — comma-joined tag-style input ----------------------- */
	function getAliases(): string[] {
		return aliasesRaw
			.split(',')
			.map((s) => s.trim())
			.filter(Boolean);
	}
	function setAliases(list: string[]) {
		aliasesRaw = list.join(', ');
	}
	function addAliasFromInput(raw: string) {
		// Split on commas so users can paste "A, B, C" in one go.
		const parts = raw
			.split(',')
			.map((s) => s.trim())
			.filter(Boolean);
		if (parts.length === 0) return;
		const merged = Array.from(new Set([...getAliases(), ...parts]));
		setAliases(merged);
	}
	function removeAlias(target: string) {
		setAliases(getAliases().filter((a) => a !== target));
	}

	/* --- Profile image preview --------------------------------------- */
	$effect(() => {
		if (profileImageFile && profileImageFile.type.startsWith('image/')) {
			const url = URL.createObjectURL(profileImageFile);
			profileImagePreview = url;
			return () => URL.revokeObjectURL(url);
		} else {
			profileImagePreview = null;
		}
	});
	function onProfileImageChange(e: Event) {
		const input = e.currentTarget as HTMLInputElement;
		const f = input.files?.[0] ?? null;
		if (f && f.size > MAX_PROFILE_IMAGE) {
			errors.profile_image = `Image is too large (${(f.size / 1024 / 1024).toFixed(1)} MB). Max 5 MB.`;
			input.value = '';
			profileImageFile = null;
			return;
		}
		if (errors.profile_image) clearError('profile_image');
		profileImageFile = f;
		profileImageCleared = false;
	}
	function clearProfileImage() {
		profileImageFile = null;
		profileImageCleared = true;
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
		if (legalName && legalName.length > MAX_LEGAL_NAME) {
			e.legal_name = `Keep this under ${MAX_LEGAL_NAME.toLocaleString()} characters.`;
		}
		if (aliasesRaw && aliasesRaw.length > MAX_ALIASES) {
			e.aliases = `Total aliases are too long (max ${MAX_ALIASES.toLocaleString()} characters).`;
		}
		if (authoritativeUrl && !/^https?:\/\//i.test(authoritativeUrl.trim())) {
			e.authoritative_url = 'URL must start with http:// or https://';
		}

		return e;
	}

	function focusFirstError(errs: Record<string, string>) {
		const order = [
			'name', 'legal_name', 'aliases', 'country', 'status', 'medical',
			'rough_location', 'precise_location', 'last_known_date', 'ethnicity',
			'gender', 'dob', 'quality_tier', 'profile_image', 'medical_notes',
			'authoritative_source', 'authoritative_url', 'is_published',
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
			const aliases = getAliases();
			const hasProfileImage = !!profileImageFile;

			let payload: Record<string, unknown> | FormData;
			if (hasProfileImage) {
				// multipart path — the file forces multipart/form-data.
				const fd = new FormData();
				fd.append('name', name.trim());
				fd.append('country', country.trim());
				fd.append('current_status', currentStatus);
				fd.append('medical_status', medicalStatus);
				fd.append('rough_location', roughLocation.trim());
				fd.append('precise_location', preciseLocation.trim());
				fd.append('summary_narrative', summaryNarrative.trim());
				fd.append('ethnicity', ethnicity.trim());
				if (gender) fd.append('gender', gender);
				if (lastKnownDate) fd.append('last_known_date', lastKnownDate);
				if (dateOfBirth) fd.append('date_of_birth', dateOfBirth);
				if (legalName.trim()) fd.append('legal_name', legalName.trim());
				if (aliases.length) fd.append('aliases', aliases.join(', '));
				if (qualityTier !== '') fd.append('quality_tier', String(qualityTier));
				if (medicalNotes.trim()) fd.append('medical_notes', medicalNotes.trim());
				if (authoritativeSource.trim()) fd.append('authoritative_source', authoritativeSource.trim());
				if (authoritativeUrl.trim()) fd.append('authoritative_url', authoritativeUrl.trim());
				fd.append('is_published', String(isPublished));
				for (const catId of selectedCategories) fd.append('category_ids', String(catId));
				fd.append('profile_image', profileImageFile!);
				payload = fd;
			} else {
				payload = {
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
				if (lastKnownDate) payload.last_known_date = lastKnownDate;
				if (dateOfBirth) payload.date_of_birth = dateOfBirth;
				if (legalName.trim()) payload.legal_name = legalName.trim();
				if (aliases.length) payload.aliases = aliases.join(', ');
				if (qualityTier !== '') payload.quality_tier = qualityTier;
				if (medicalNotes.trim()) payload.medical_notes = medicalNotes.trim();
				if (authoritativeSource.trim()) payload.authoritative_source = authoritativeSource.trim();
				if (authoritativeUrl.trim()) payload.authoritative_url = authoritativeUrl.trim();
				payload.is_published = isPublished;
			}

			const person = await createPerson(payload);

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

					<!-- Legal name -->
					<div class="field">
						<label for="legal_name">
							Legal name <span class="optional-mark">(optional)</span>
						</label>
						<input
							id="legal_name"
							type="text"
							bind:value={legalName}
							oninput={() => clearError('legal_name')}
							placeholder="Full legal name, if it differs"
							maxlength={MAX_LEGAL_NAME}
							autocomplete="off"
							aria-invalid={errors.legal_name ? 'true' : 'false'}
							aria-describedby={errors.legal_name ? 'legal-name-error' : 'legal-name-help'}
						/>
						{#if errors.legal_name}
							<p class="field-error" id="legal-name-error" role="alert">{errors.legal_name}</p>
						{:else}
							<p class="field-help" id="legal-name-help">For verification only.</p>
						{/if}
					</div>

					<!-- Aliases — tag input, comma-joined on submit -->
					<div class="field field-full" class:has-error={errors.aliases}>
						<label for="aliases-input">
							Aliases <span class="optional-mark">(optional)</span>
						</label>
						<!-- Hidden input lets users submit tags via Enter or comma.
						     We don't bind this to state — we read from aliasesRaw on save. -->
						<input
							id="aliases-input"
							type="text"
							placeholder="Type an alias, press Enter or comma to add"
							onkeydown={(e) => {
								if (e.key === 'Enter' || e.key === ',') {
									e.preventDefault();
									const v = (e.currentTarget as HTMLInputElement).value.trim();
									if (v) {
										addAliasFromInput(v);
										(e.currentTarget as HTMLInputElement).value = '';
									}
								} else if (e.key === 'Backspace' && (e.currentTarget as HTMLInputElement).value === '' && getAliases().length > 0) {
									e.preventDefault();
									const all = getAliases();
									all.pop();
									setAliases(all);
								}
							}}
							onblur={(e) => {
								const v = (e.currentTarget as HTMLInputElement).value.trim();
								if (v) {
									addAliasFromInput(v);
									(e.currentTarget as HTMLInputElement).value = '';
								}
							}}
							aria-describedby="aliases-help"
						/>
						{#if getAliases().length > 0}
							<div class="alias-pills" role="list" aria-label="Aliases">
								{#each getAliases() as alias (alias)}
									<span class="alias-pill" role="listitem">
										{alias}
										<button
											type="button"
											class="alias-pill-remove"
											aria-label={`Remove alias "${alias}"`}
											onclick={() => removeAlias(alias)}
										>×</button>
									</span>
								{/each}
							</div>
						{/if}
						{#if errors.aliases}
							<p class="field-error" role="alert">{errors.aliases}</p>
						{:else}
							<p class="field-help" id="aliases-help">
								Other names this person goes by — birth name, nom de guerre, common misspelling.
							</p>
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
							
							<span class="field-tag">public</span>
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
							
							<span class="field-tag">private</span>
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

					<!-- Quality tier — evidence reliability rating -->
					<div class="field">
						<label for="quality_tier">
							Evidence tier <span class="optional-mark">(optional)</span>
						</label>
						<select id="quality_tier" bind:value={qualityTier}>
							<option value={''}>Not yet rated</option>
							<option value={1}>Tier 1 — strong evidence</option>
							<option value={2}>Tier 2 — average evidence</option>
							<option value={3}>Tier 3 — weak evidence</option>
						</select>
						<p class="field-help">How confident are we in the facts of this case?</p>
					</div>

					<!-- Profile image upload -->
					<div class="field field-full" class:has-error={errors.profile_image}>
						<label for="profile_image">
							Profile image <span class="optional-mark">(optional)</span>
						</label>
						<div class="profile-image-row">
							{#if profileImagePreview}
								<img src={profileImagePreview} alt="" class="profile-image-preview" />
							{/if}
							<div class="profile-image-controls">
								<input
									id="profile_image"
									type="file"
									accept="image/*"
									onchange={onProfileImageChange}
									aria-describedby="profile-image-help"
								/>
								{#if profileImageFile}
									<button
										type="button"
										class="btn btn-secondary btn-sm"
										onclick={clearProfileImage}
									>Clear</button>
								{/if}
							</div>
						</div>
						{#if errors.profile_image}
							<p class="field-error" role="alert">{errors.profile_image}</p>
						{:else}
							<p class="field-help" id="profile-image-help">
								PNG or JPG, up to 5 MB. Shown on the public case page if it exists.
							</p>
						{/if}
					</div>
				</div>
			</section>

			<!-- ============== Section 1b: Privacy ============== -->
			<section class="form-section" aria-labelledby="sec-privacy">
				<h2 id="sec-privacy" class="form-section-title">Privacy</h2>
				<p class="form-section-desc">Sensitive details about this person's health and situation.</p>

				<div class="field-stack">
					<div class="field" class:has-error={errors.medical_notes}>
						<label for="medical_notes">
							Medical notes
							<span class="field-tag-private">
								<svg viewBox="0 0 16 16" width="11" height="11" aria-hidden="true">
									<path fill="currentColor" d="M4 7V5a4 4 0 1 1 8 0v2h1a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1h1zm2 0h4V5a2 2 0 1 0-4 0v2z" />
								</svg>
								private
							</span>
						</label>
						<textarea
							id="medical_notes"
							bind:value={medicalNotes}
							oninput={() => clearError('medical_notes')}
							rows="4"
							maxlength={MAX_NARRATIVE}
							placeholder="Health conditions, medications, ongoing treatment — anything that helps the team support this person safely."
							aria-invalid={errors.medical_notes ? 'true' : 'false'}
							aria-describedby={errors.medical_notes ? 'medical-notes-error' : 'medical-notes-help'}
						></textarea>
						{#if errors.medical_notes}
							<p class="field-error" id="medical-notes-error" role="alert">{errors.medical_notes}</p>
						{:else}
							<p class="field-help" id="medical-notes-help">
								Hidden from the public case page — visible only to volunteers and admins.
							</p>
						{/if}
					</div>
				</div>
			</section>

			<!-- ============== Section 1c: Verification & publication ============== -->
			<section class="form-section" aria-labelledby="sec-verify">
				<h2 id="sec-verify" class="form-section-title">Verification &amp; publication</h2>
				<p class="form-section-desc">
					Where did this case come from, and who should see it?
				</p>

				<div class="form-grid">
					<div class="field" class:has-error={errors.authoritative_source}>
						<label for="authoritative_source">
							Authoritative source <span class="optional-mark">(optional)</span>
						</label>
						<input
							id="authoritative_source"
							type="text"
							bind:value={authoritativeSource}
							oninput={() => clearError('authoritative_source')}
							maxlength={MAX_SHORT}
							autocomplete="off"
							placeholder='e.g. "AAPP", "HRW", "shahit.biz"'
							aria-invalid={errors.authoritative_source ? 'true' : 'false'}
							aria-describedby={errors.authoritative_source ? 'auth-source-error' : 'auth-source-help'}
						/>
						{#if errors.authoritative_source}
							<p class="field-error" id="auth-source-error" role="alert">{errors.authoritative_source}</p>
						{:else}
							<p class="field-help" id="auth-source-help">Name of the source database or organization.</p>
						{/if}
					</div>

					<div class="field" class:has-error={errors.authoritative_url}>
						<label for="authoritative_url">
							Source URL <span class="optional-mark">(optional)</span>
						</label>
						<input
							id="authoritative_url"
							type="url"
							bind:value={authoritativeUrl}
							oninput={() => clearError('authoritative_url')}
							maxlength={1000}
							autocomplete="off"
							placeholder="https://example.org/case/12345"
							aria-invalid={errors.authoritative_url ? 'true' : 'false'}
							aria-describedby={errors.authoritative_url ? 'auth-url-error' : 'auth-url-help'}
						/>
						{#if errors.authoritative_url}
							<p class="field-error" id="auth-url-error" role="alert">{errors.authoritative_url}</p>
						{:else}
							<p class="field-help" id="auth-url-help">Link to this case in the original source.</p>
						{/if}
					</div>

					<!-- is_published — admin-only toggle -->
					{#if isAdminUser}
						<div class="field field-full">
							<label class="toggle-row">
								<input
									id="is_published"
									type="checkbox"
									bind:checked={isPublished}
								/>
								<span class="toggle-row-text">
									<strong>Published on the public site</strong>
									<span class="field-help">
										When off, the case is hidden from public listings and search. Admins only.
									</span>
								</span>
							</label>
						</div>
					{/if}
				</div>
			</section>

			<!-- ============== Section 2: Summary & Categories ============== -->
			<section class="form-section" aria-labelledby="sec-summary">
				<h2 id="sec-summary" class="form-section-title">
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
							
							<span class="field-tag">public</span>
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
							
							<span class="field-tag">private</span>
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
							
							<span class="field-tag">private</span>
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
		/* Just red text — no warning glyph. The danger color + field-has-error
		   wash is enough signal; adding ⚠ made the page feel alert-heavy. */
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
		margin: 0 0 0.4rem 0;
		color: var(--color-primary);
		font-size: 1.2rem;
		font-weight: 700;
		letter-spacing: -0.005em;
		line-height: 1.3;
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

	/* Small inline tag that sits next to a field label — "public" or "private".
	   Replaces the colored dot that used to live here. Plain, readable,
	   no decoration. */
	.field-tag {
		display: inline-block;
		margin-left: 0.35rem;
		font-size: 0.72rem;
		font-weight: 500;
		color: var(--color-text-muted);
		text-transform: lowercase;
		letter-spacing: 0.02em;
	}

	/* Private-tag variant — yellow tint with a small lock icon.
	   Visually signals "this is sensitive and hidden from public view". */
	.field-tag-private {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		margin-left: 0.35rem;
		padding: 0.1rem 0.5rem 0.1rem 0.4rem;
		border-radius: 999px;
		background: #fefcbf;
		color: #744210;
		font-size: 0.68rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.04rem;
		line-height: 1.2;
	}
	.field-tag-private svg {
		display: inline-block;
		vertical-align: -1px;
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

	/* Native checkbox hidden but accessible. Selection is signalled by
	   the .is-selected background + border + weight on the pill itself —
	   no separate check-mark icon. */
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
		.spinner {
			transition: none;
			animation: none;
		}
	}

	/* === Aliases: pill list under the input ============================ */
	.alias-pills {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
		margin: 0.1rem 0 0.25rem 0;
	}
	.alias-pill {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.3rem 0.4rem 0.3rem 0.7rem;
		background: var(--color-primary-tint);
		color: var(--color-primary);
		border-radius: 999px;
		font-size: 0.82rem;
		font-weight: 600;
		line-height: 1.2;
	}
	.alias-pill-remove {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 18px;
		height: 18px;
		border-radius: 50%;
		border: 0;
		background: transparent;
		color: var(--color-primary);
		font-size: 1rem;
		line-height: 1;
		padding: 0;
		cursor: pointer;
	}
	.alias-pill-remove:hover {
		background: rgba(37, 100, 106, 0.2);
	}

	/* === Profile image upload row ===================================== */
	.profile-image-row {
		display: flex;
		align-items: flex-start;
		gap: 1rem;
		flex-wrap: wrap;
	}
	.profile-image-preview {
		width: 96px;
		height: 96px;
		object-fit: cover;
		border-radius: var(--radius-card);
		border: 1px solid var(--color-border-light);
		background: var(--color-surface);
		flex: 0 0 96px;
	}
	.profile-image-controls {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		min-width: 0;
		flex: 1 1 220px;
	}
	.profile-image-controls input[type='file'] {
		padding: 0.45rem 0.6rem;
		font-size: 0.88rem;
	}

	/* === Toggle row (used for is_published) ============================ */
	.toggle-row {
		display: inline-flex;
		align-items: flex-start;
		gap: 0.65rem;
		cursor: pointer;
		padding: 0.85rem 1rem;
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		background: var(--color-surface);
		width: 100%;
	}
	.toggle-row:hover { border-color: var(--color-primary-light); }
	.toggle-row input[type='checkbox'] {
		width: 18px;
		height: 18px;
		margin-top: 0.15rem;
		flex: 0 0 18px;
		accent-color: var(--color-primary);
	}
	.toggle-row-text {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
		min-width: 0;
	}
	.toggle-row-text strong {
		font-size: 0.92rem;
		font-weight: 600;
		color: var(--color-text);
	}
</style>
