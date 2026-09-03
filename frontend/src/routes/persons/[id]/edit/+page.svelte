<script lang="ts">
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { user, isVolunteer, isAdmin, loadSession } from '$lib/session';
	import { getPerson, updatePerson, getCategories, ApiError } from '$lib/api';
	import type { Person } from '$lib/types';

	let currentUser = $derived($user);
	let isAdminUser = $derived(isAdmin(currentUser));
	let categories: any[] = $state([]);
	let saving = $state(false);
	let loading = $state(true);
	let refreshing = $state(false);
	// Top-level banner — API / auth / server failures.
	let formError = $state('');
	let formErrorKind = $state<'auth' | 'server' | 'other'>('other');
	let errors = $state<Record<string, string>>({});

	const MAX_NARRATIVE = 5000;
	const MAX_SHORT = 1000;
	const MAX_LEGAL_NAME = 255;
	const MAX_ALIASES = 500;        // matches models.Person.aliases
	const MAX_PROFILE_IMAGE = 5 * 1024 * 1024; // 5 MB

	// Person fields — identity
	let name = $state('');
	let legalName = $state('');
	let aliasesRaw = $state('');   // tag input, comma-joined on save
	let country = $state('');

	// Demographics & location
	let currentStatus = $state('unknown');
	let medicalStatus = $state('unknown');
	let roughLocation = $state('');
	let preciseLocation = $state('');
	let lastKnownDate = $state('');
	let summaryNarrative = $state('');
	let ethnicity = $state('');
	let gender = $state('');
	let dateOfBirth = $state('');

	// Media, evidence quality, privacy, verification
	let qualityTier = $state<number | ''>('');
	let profileImageFile = $state<File | null>(null);
	let profileImagePreview = $state<string | null>(null);
	let profileImageCleared = $state(false);
	let existingProfileImageUrl = $state<string | null>(null);
	let medicalNotes = $state('');
	let authoritativeSource = $state('');
	let authoritativeUrl = $state('');
	let isPublished = $state(true);
	let selectedCategories: number[] = $state([]);

	let personId = $derived(page.params.id!);

	onMount(async () => {
		try {
			const [person, catData] = await Promise.all([
				getPerson(personId),
				getCategories(),
			]);
			categories = Array.isArray(catData) ? catData : catData.results ?? [];

			populateFromPerson(person);
		} catch (e: unknown) {
			formError = e instanceof Error ? e.message : 'Failed to load case data.';
		}
		loading = false;
	});

	function populateFromPerson(person: Person) {
		name = person.name || '';
		legalName = person.legal_name || '';
		aliasesRaw = person.aliases || '';
		country = person.country || '';
		currentStatus = (person.current_status as string) || 'unknown';
		medicalStatus = (person.medical_status as string) || 'unknown';
		roughLocation = person.rough_location || '';
		preciseLocation = person.precise_location || '';
		lastKnownDate = person.last_known_date || '';
		summaryNarrative = person.summary_narrative || '';
		ethnicity = person.ethnicity || '';
		gender = (person.gender as string) || '';
		dateOfBirth = person.date_of_birth || '';
		qualityTier = person.quality_tier ?? '';
		medicalNotes = person.medical_notes || '';
		authoritativeSource = person.authoritative_source || '';
		authoritativeUrl = person.authoritative_url || '';
		isPublished = person.is_published ?? true;
		existingProfileImageUrl = person.profile_image_url ?? null;
		selectedCategories = (person.categories || []).map((c: any) => c.id);
	}

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

	/* --- Aliases — tag-style input ----------------------------------- */
	function getAliases(): string[] {
		return aliasesRaw.split(',').map((s) => s.trim()).filter(Boolean);
	}
	function setAliases(list: string[]) {
		aliasesRaw = list.join(', ');
	}
	function addAliasFromInput(raw: string) {
		const parts = raw.split(',').map((s) => s.trim()).filter(Boolean);
		if (parts.length === 0) return;
		setAliases(Array.from(new Set([...getAliases(), ...parts])));
	}
	function removeAlias(target: string) {
		setAliases(getAliases().filter((a) => a !== target));
	}

	/* --- Profile image ----------------------------------------------- */
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
		existingProfileImageUrl = null;
	}

	/* --- Validation -------------------------------------------------- */
	function validate(): Record<string, string> {
		const e: Record<string, string> = {};
		if (!name.trim()) e.name = 'Name is required.';
		else if (name.length > MAX_SHORT) e.name = `Keep the name under ${MAX_SHORT.toLocaleString()} characters.`;
		if (!country.trim()) e.country = 'Country is required.';
		else if (country.length > MAX_SHORT) e.country = `Keep this under ${MAX_SHORT.toLocaleString()} characters.`;
		if (legalName && legalName.length > MAX_LEGAL_NAME) {
			e.legal_name = `Keep this under ${MAX_LEGAL_NAME.toLocaleString()} characters.`;
		}
		if (aliasesRaw && aliasesRaw.length > MAX_ALIASES) {
			e.aliases = `Total aliases are too long (max ${MAX_ALIASES.toLocaleString()} characters).`;
		}
		if (authoritativeUrl && !/^https?:\/\//i.test(authoritativeUrl.trim())) {
			e.authoritative_url = 'URL must start with http:// or https://';
		}
		if (lastKnownDate && Number.isNaN(new Date(lastKnownDate).getTime())) {
			e.last_known_date = "That doesn't look like a valid date.";
		}
		if (dateOfBirth && Number.isNaN(new Date(dateOfBirth).getTime())) {
			e.dob = "That doesn't look like a valid date.";
		}
		return e;
	}

	function focusFirstError(errs: Record<string, string>) {
		const order = [
			'name', 'legal_name', 'aliases', 'country', 'status', 'medical',
			'rough_location', 'precise_location', 'last_known_date', 'ethnicity',
			'gender', 'dob', 'quality_tier', 'profile_image', 'medical_notes',
			'authoritative_source', 'authoritative_url',
			'summary',
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

			const baseData: Record<string, unknown> = {
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
			baseData.last_known_date = lastKnownDate || null;
			baseData.date_of_birth = dateOfBirth || null;
			if (legalName.trim()) baseData.legal_name = legalName.trim();
			else baseData.legal_name = null;
			if (aliases.length) baseData.aliases = aliases.join(', ');
			else baseData.aliases = '';
			if (qualityTier !== '') baseData.quality_tier = qualityTier;
			else baseData.quality_tier = null;
			if (medicalNotes.trim()) baseData.medical_notes = medicalNotes.trim();
			else baseData.medical_notes = '';
			if (authoritativeSource.trim()) baseData.authoritative_source = authoritativeSource.trim();
			else baseData.authoritative_source = '';
			if (authoritativeUrl.trim()) baseData.authoritative_url = authoritativeUrl.trim();
			else baseData.authoritative_url = '';
			// Only include is_published if the user can edit it (admin).
			if (isAdminUser) baseData.is_published = isPublished;

			let payload: Record<string, unknown> | FormData;
			if (hasProfileImage) {
				const fd = new FormData();
				for (const [k, v] of Object.entries(baseData)) {
					if (v === null || v === undefined) continue;
					if (Array.isArray(v)) {
						for (const item of v) fd.append(k, String(item));
					} else {
						fd.append(k, String(v));
					}
				}
				fd.append('profile_image', profileImageFile!);
				payload = fd;
			} else {
				payload = baseData;
			}

			await updatePerson(personId, payload);
			goto(`${base}/persons/${personId}`);
		} catch (e: unknown) {
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
						'Your session has expired, or you don’t have permission to edit cases. ' +
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

	function cancel() {
		goto(`${base}/persons/${personId}`);
	}
</script>

<svelte:head>
	<title>Edit Case — Testimonies.world</title>
</svelte:head>

<div class="container">
	{#if loading}
		<p class="muted">Loading…</p>
	{:else if !isVolunteer(currentUser)}
		<p class="muted">
			You must be logged in as a volunteer to edit cases.
			<a href="{base}/api/auth/login/?next={base}/persons/{personId}/edit">Login</a>
		</p>
	{:else}
		<header class="form-header">
			<p class="breadcrumb">
				<a href="{base}/persons/{personId}">Case</a>
				<span class="breadcrumb-sep" aria-hidden="true">›</span>
				<span>Edit</span>
			</p>
			<h1>Edit case</h1>
			<p class="form-intro">
				Update information for this person. Fields marked <span class="required-mark" aria-hidden="true">*</span> are required.
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
							>{refreshing ? 'Refreshing…' : 'Refresh session'}</button>
							<a href="{base}/api/auth/login/?next={base}/persons/{personId}/edit" class="btn btn-primary btn-sm">
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
				<h2 id="sec-person" class="form-section-title">Person information</h2>
				<p class="form-section-desc">Basic identifying details about the person.</p>

				<div class="form-grid">
					<div class="field" class:has-error={errors.name}>
						<label for="name">Name <span class="required-mark" aria-hidden="true">*</span></label>
						<input
							id="name"
							type="text"
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
							type="text"
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

					<div class="field" class:has-error={errors.legal_name}>
						<label for="legal_name">Legal name <span class="optional-mark">(optional)</span></label>
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

					<!-- Aliases — tag input -->
					<div class="field field-full" class:has-error={errors.aliases}>
						<label for="aliases-input">
							Aliases <span class="optional-mark">(optional)</span>
						</label>
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
							<p class="field-help" id="aliases-help">Other names this person goes by — birth name, common misspelling.</p>
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
						<label for="rough_location">Location <span class="field-tag">public</span></label>
						<input id="rough_location" type="text" bind:value={roughLocation} placeholder="Region or city" />
					</div>

					<div class="field">
						<label for="precise_location">
							Precise Location
							<span class="field-tag-private">
								<svg viewBox="0 0 16 16" width="11" height="11" aria-hidden="true">
									<path fill="currentColor" d="M4 7V5a4 4 0 1 1 8 0v2h1a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1h1zm2 0h4V5a2 2 0 1 0-4 0v2z" />
								</svg>
								private
							</span>
						</label>
						<input id="precise_location" type="text" bind:value={preciseLocation} placeholder="Street address or coordinates" />
					</div>

					<div class="field" class:has-error={errors.last_known_date}>
						<label for="last_known_date">Last Known Date</label>
						<input
							id="last_known_date"
							type="date"
							bind:value={lastKnownDate}
							oninput={() => clearError('last_known_date')}
							aria-invalid={errors.last_known_date ? 'true' : 'false'}
							aria-describedby={errors.last_known_date ? 'lkd-error' : 'lkd-help'}
						/>
						{#if errors.last_known_date}<p class="field-error" id="lkd-error" role="alert">{errors.last_known_date}</p>{/if}
					</div>

					<div class="field">
						<label for="ethnicity">Ethnicity</label>
						<input id="ethnicity" type="text" bind:value={ethnicity} placeholder="Ethnicity or heritage" />
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

					<div class="field" class:has-error={errors.dob}>
						<label for="dob">Date of Birth</label>
						<input
							id="dob"
							type="date"
							bind:value={dateOfBirth}
							oninput={() => clearError('dob')}
							aria-invalid={errors.dob ? 'true' : 'false'}
							aria-describedby={errors.dob ? 'dob-error' : undefined}
						/>
						{#if errors.dob}<p class="field-error" id="dob-error" role="alert">{errors.dob}</p>{/if}
					</div>

					<div class="field">
						<label for="quality_tier">Evidence tier <span class="optional-mark">(optional)</span></label>
						<select id="quality_tier" bind:value={qualityTier}>
							<option value={''}>Not yet rated</option>
							<option value={1}>Tier 1 — strong evidence</option>
							<option value={2}>Tier 2 — average evidence</option>
							<option value={3}>Tier 3 — weak evidence</option>
						</select>
						<p class="field-help">How confident are we in the facts of this case?</p>
					</div>

					<!-- Profile image — show existing OR preview OR placeholder -->
					<div class="field field-full" class:has-error={errors.profile_image}>
						<label for="profile_image">
							Profile image <span class="optional-mark">(optional)</span>
						</label>
						<div class="profile-image-row">
							{#if profileImagePreview}
								<img src={profileImagePreview} alt="Preview of new image" class="profile-image-preview" />
							{:else if existingProfileImageUrl}
								<img src={existingProfileImageUrl} alt="Current profile image" class="profile-image-preview" />
							{:else}
								<div class="profile-image-placeholder" aria-hidden="true">
									<span>No image</span>
								</div>
							{/if}
							<div class="profile-image-controls">
								<input
									id="profile_image"
									type="file"
									accept="image/*"
									onchange={onProfileImageChange}
									aria-describedby="profile-image-help"
								/>
								{#if profileImageFile || existingProfileImageUrl}
									<button
										type="button"
										class="btn btn-secondary btn-sm"
										onclick={clearProfileImage}
									>{profileImageFile ? 'Discard new upload' : 'Remove image'}</button>
								{/if}
							</div>
						</div>
						{#if errors.profile_image}
							<p class="field-error" role="alert">{errors.profile_image}</p>
						{:else}
							<p class="field-help" id="profile-image-help">
								PNG or JPG, up to 5 MB. Replaces the current image on save.
							</p>
						{/if}
					</div>
				</div>
			</section>

			<!-- ============== Section 1b: Privacy ============== -->
			<section class="form-section" aria-labelledby="sec-privacy">
				<h2 id="sec-privacy" class="form-section-title">Privacy</h2>
				<p class="form-section-desc">Sensitive details — hidden from public view.</p>

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
						placeholder="Health conditions, medications, ongoing treatment."
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
			</section>

			<!-- ============== Section 1c: Verification & publication ============== -->
			<section class="form-section" aria-labelledby="sec-verify">
				<h2 id="sec-verify" class="form-section-title">Verification &amp; publication</h2>
				<p class="form-section-desc">
					Where did the case come from, and who should see it?
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
							placeholder='e.g. "AAPP", "HRW", "shahit.biz"'
							autocomplete="off"
						/>
						<p class="field-help">Name of the source database or organization.</p>
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
							placeholder="https://example.org/case/12345"
							autocomplete="off"
						/>
						{#if errors.authoritative_url}
							<p class="field-error" role="alert">{errors.authoritative_url}</p>
						{/if}
					</div>

					<!-- is_published — admin only -->
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
				<h2 id="sec-summary" class="form-section-title">Summary &amp; categories</h2>
				<p class="form-section-desc">A short overview and the categories that apply.</p>

				<div class="field-stack">
					<div class="field">
						<label for="summary">Summary Narrative</label>
						<textarea
							id="summary"
							bind:value={summaryNarrative}
							rows="4"
							placeholder="A few sentences is enough. The first report carries the detail."
						></textarea>
						<p class="field-help">
							Plain prose — no need to be exhaustive.
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

			<!-- ============== Actions ============== -->
			<div class="form-actions">
				<p class="form-actions-note">You'll be taken back to the case page after saving.</p>
				<button
					type="button"
					class="btn btn-secondary"
					onclick={cancel}
					disabled={saving}
				>Cancel</button>
				<button
					type="submit"
					class="btn btn-primary submit-btn"
					disabled={saving}
				>
					{#if saving}
						<span class="spinner" aria-hidden="true"></span>
						Saving…
					{:else}
						Save changes
					{/if}
				</button>
			</div>
		</form>
	{/if}
</div>

<style>
	/* Match the /submit form's design language exactly — the rest of the
	   app expects these two forms to feel like the same product. */

	.form-header {
		margin-bottom: 1.75rem;
	}
	.form-header h1 {
		margin: 0 0 0.4rem 0;
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
	.breadcrumb {
		margin: 0 0 0.4rem 0;
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

	.required-mark {
		color: var(--color-danger);
		font-weight: 700;
		margin-left: 0.1rem;
	}
	.optional-mark {
		color: var(--color-text-muted);
		font-size: 0.78rem;
		font-weight: 400;
	}

	/* Top-level error banner — mirrors /submit */
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
	.form-error-dismiss:hover { color: var(--color-text); }

	.field-error {
		margin: 0;
		font-size: 0.82rem;
		color: var(--color-danger);
		font-weight: 500;
	}
	.field.has-error input,
	.field.has-error select,
	.field.has-error textarea {
		border-color: var(--color-danger);
		background: rgba(217, 22, 22, 0.03);
	}

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
	}
	.form-section-desc {
		margin: 0 0 1.25rem 0;
		color: var(--color-text-muted);
		font-size: 0.92rem;
		line-height: 1.5;
	}

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
	.field-full {
		grid-column: 1 / -1;
	}

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

	.field-tag {
		display: inline-block;
		margin-left: 0.35rem;
		font-size: 0.72rem;
		font-weight: 500;
		color: var(--color-text-muted);
		text-transform: lowercase;
		letter-spacing: 0.02em;
	}
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

	.field-help {
		margin: 0;
		font-size: 0.78rem;
		color: var(--color-text-muted);
		line-height: 1.45;
	}

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
	.field input:focus,
	.field select:focus,
	.field textarea:focus {
		outline: none;
		border-color: var(--color-primary);
		box-shadow: 0 0 0 3px var(--color-primary-tint);
	}
	.field input::placeholder,
	.field textarea::placeholder {
		color: var(--color-text-muted);
		opacity: 0.6;
	}

	/* === Aliases — pill list under the input === */
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

	/* === Profile image preview === */
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
	.profile-image-placeholder {
		width: 96px;
		height: 96px;
		border-radius: var(--radius-card);
		border: 1px dashed var(--color-border-light);
		background: var(--color-surface);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.78rem;
		color: var(--color-text-muted);
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

	/* === Toggle row === */
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

	/* === Categories as pills === */
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

	/* === Actions === */
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
		to { transform: rotate(360deg); }
	}

	@media (max-width: 720px) {
		.form-section { padding: 1.25rem 1.25rem; }
		.form-grid { grid-template-columns: 1fr; gap: 1rem; }
		.categories-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
		.form-actions {
			padding: 1.25rem;
			flex-direction: column;
			align-items: stretch;
		}
		.form-actions-note { text-align: center; }
		.submit-btn { width: 100%; }
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