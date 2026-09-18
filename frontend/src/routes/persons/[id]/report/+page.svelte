<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { fly, fade } from 'svelte/transition';
	import { user, isVolunteer } from '$lib/session';
	import { getPerson, createReport, getReport, updateReport, ApiError, request } from '$lib/api';
	import type { Media, MediaType, Report, Visibility } from '$lib/types';
import Skeleton from '$lib/Skeleton.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// SSR-hydrated auth (see +layout.svelte for the full rationale).
	let currentUser = $derived(data.user ?? $user);
	let person: any = $state(null);
	let loading = $state(true);
	let saving = $state(false);
	let errorMsg = $state('');
	let errorKind = $state<'generic' | 'network' | 'auth' | 'server' | 'validation'>('generic');
	let fieldErrors = $state<Record<string, string>>({});

	// `?id=` in the URL → edit mode. Without it → create mode.
	// Reactive so Back/Forward between /persons/X/report?id=5 and
	// /persons/X/report?id=7 re-hydrates the form with the right report.
	let reportId: number | null = $derived.by(() => {
		const raw = page.url.searchParams.get('id');
		if (!raw) return null;
		const n = Number(raw);
		return Number.isFinite(n) ? n : null;
	});
	let isEdit = $derived(reportId !== null);

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
	let isPrivate = $state(false);

	// --- Repeating Sources (witnesses / news / docs) -------------------
	// Mirrors the Sources section on the /reports modal. Created via the
	// writable nested `sources` slot on POST /reports/ — one POST carries
	// the report + all its sources. Empty entries (no attribution, no
	// narrative) are dropped on submit.
	interface SourceEntry {
		uid: number;
		source_type: Report['source_type'];
		source_attribution: string;
		date_start: string;
		narrative: string;
		is_private: boolean;
	}
	let sourceEntries = $state<SourceEntry[]>([]);

	// --- Repeating Media (photos / docs / videos / links) --------------
	// ReportSerializer.media_files is read-only nested, so each media
	// row is POSTed separately to /media/ with report=<newId> after the
	// report creates. Multi-step on purpose (see modal for the rationale).
	interface MediaEntry {
		uid: number;
		media_type: MediaType;
		visibility: Visibility;
		description: string;
		url: string;
	}
	let mediaEntries = $state<MediaEntry[]>([]);

	// Monotonic local id for keyed each. Not the backend id.
	let nextEntryUid = 1;
	function makeSourceEntry(): SourceEntry {
		return {
			uid: nextEntryUid++,
			source_type: 'firsthand',
			source_attribution: '',
			date_start: '',
			narrative: '',
			is_private: false,
		};
	}
	function makeMediaEntry(): MediaEntry {
		return {
			uid: nextEntryUid++,
			media_type: 'photo',
			visibility: 'public',
			description: '',
			url: '',
		};
	}
	function addSource() {
		sourceEntries = [...sourceEntries, makeSourceEntry()];
	}
	function removeSource(idx: number) {
		sourceEntries = sourceEntries.filter((_, i) => i !== idx);
	}
	function addMedia() {
		mediaEntries = [...mediaEntries, makeMediaEntry()];
	}
	function removeMedia(idx: number) {
		mediaEntries = mediaEntries.filter((_, i) => i !== idx);
	}

	// Partial-failure tracking — the page-level banner shows after a
	// successful Report create if any media item failed to attach.
	let mediaFailures = $state<string[]>([]);
	function dismissMediaFailures() {
		mediaFailures = [];
	}

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

	// Refetch-guard token so Back/Forward between /persons/X/report?id=5
	// and /persons/X/report?id=7 can't let a slow response for 5 clobber
	// the form populated for 7.
	let loadToken = 0;

	async function load() {
		const token = ++loadToken;
		loading = true;
		errorMsg = '';
		fieldErrors = {};
		try {
			const p = await getPerson(page.params.id!);
			if (token !== loadToken) return;
			person = p;
			// Edit mode → hydrate the form from the existing report.
			if (reportId !== null) {
				const r = await getReport(reportId);
				if (token !== loadToken) return;
				sourceType = r.source_type;
				sourceAttribution = r.source_attribution ?? '';
				reporterName = r.reporter_name ?? '';
				reporterContact = r.reporter_contact ?? '';
				dateStart = r.date_start ?? '';
				dateEnd = r.date_end ?? '';
				roughLocation = r.rough_location ?? '';
				narrative = r.narrative ?? '';
				suspectedReason = r.suspected_reason ?? '';
				officialReason = r.official_reason ?? '';
				isPrivate = !!r.is_private;
			} else {
				// Switching from edit → create: reset fields that would
				// otherwise leak from the previous report.
				sourceType = 'firsthand';
				sourceAttribution = '';
				reporterName = '';
				reporterContact = '';
				dateStart = '';
				dateEnd = '';
				roughLocation = '';
				narrative = '';
				suspectedReason = '';
				officialReason = '';
				isPrivate = false;
				sourceEntries = [];
				mediaEntries = [];
			}
		} catch (e: unknown) {
			if (token !== loadToken) return;
			errorMsg = e instanceof Error ? e.message : "Couldn't load this case.";
		} finally {
			if (token === loadToken) loading = false;
		}
	}

	// Re-fetch whenever either the route param (person) or the ?id=
	// query param (report) changes. $effect dedupes unchanged deps, so
	// this is effectively onMount + reactive on subsequent nav.
	$effect(() => {
		void page.params.id;
		void reportId;
		void load();
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
		// Re-entrancy guard — see contacts/new for the rationale.
		if (saving) return;
		if (!validate()) return;
		saving = true;
		errorMsg = '';
		errorKind = 'generic';
		fieldErrors = {};
		mediaFailures = [];

		// Drop empty source entries — a user who clicked "Add another"
		// by mistake shouldn't create a blank row.
		const sources = sourceEntries
			.filter((s) => s.source_attribution.trim() || s.narrative.trim())
			.map((s) => ({
				source_type: s.source_type,
				source_attribution: s.source_attribution,
				date_start: s.date_start || null,
				narrative: s.narrative,
				is_private: s.is_private,
			}));

		const payload = {
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
			is_private: isPrivate,
			// Only include nested sources on CREATE — DRF's nested writable
			// serializer REPLACES the collection on update, which would
			// silently delete any sources the volunteer already attached.
			// Edit-mode source management lives on /sources/ instead.
			...(isEdit ? {} : { sources }),
		};
		try {
			let createdId: number | null = null;
			if (isEdit && reportId !== null) {
				await updateReport(reportId, payload);
			} else {
				const created = await createReport(payload);
				createdId = created.id;
			}

			// Attach each media item separately. ReportSerializer has
			// media_files as read-only nested, so a second POST per item
			// is required. Track failures but don't fail the whole flow —
			// the report itself is saved.
			const failures: string[] = [];
			if (createdId !== null) {
				for (let i = 0; i < mediaEntries.length; i++) {
					const m = mediaEntries[i];
					if (!m.url.trim() && !m.description.trim()) continue; // skip empty
					try {
						await request<Media>('/media/', {
							method: 'POST',
							body: JSON.stringify({
								report: createdId,
								media_type: m.media_type,
								visibility: m.visibility,
								description: m.description,
								url: m.url,
							}),
						});
					} catch (mErr: unknown) {
						const msg = mErr instanceof Error ? mErr.message : 'unknown error';
						failures.push(`Media #${i + 1}: ${msg}`);
					}
				}
			}

			// Success — replaceState so Back from the case page doesn't
			// return to a stale form.
			if (failures.length > 0) {
				mediaFailures = failures;
			}
			await goto(`${base}/persons/${person.id}`, { replaceState: true });
		} catch (err: unknown) {
			// DRF returns per-field errors on 400 — surface them inline.
			if (err instanceof ApiError) {
				if (err.isValidation && err.fieldErrors && Object.keys(err.fieldErrors).length) {
					fieldErrors = Object.fromEntries(
						Object.entries(err.fieldErrors).map(([k, v]) => [k, v[0] ?? '']),
					);
					errorMsg = err.message;
					errorKind = 'validation';
				} else if (err.isUnauthorized) {
					errorMsg = 'Your session has expired. Please log in again to continue.';
					errorKind = 'auth';
				} else if (err.isServer || err.status === 0) {
					errorMsg = err.status === 0
						? err.message
						: "The server hit a snag. Please try again in a moment.";
					errorKind = err.status === 0 ? 'network' : 'server';
				} else {
					errorMsg = err.message;
					errorKind = 'generic';
				}
			} else {
				errorMsg =
					err instanceof Error ? err.message : 'Failed to save the report.';
			}
		} finally {
			saving = false;
		}
	}

	function cancel() {
		goto(`${base}/persons/${person.id}`);
	}
</script>

<svelte:head>
	<title>Add Report — {person?.name ?? 'Testimonies.world'} — Testimonies.world</title>
	<meta name="description" content="Add a new report to this person — incident, observation, or update." />
	<meta property="og:description" content="Add a new report to this person — incident, observation, or update." />
	<meta property="og:type" content="website" />
	<meta name="twitter:description" content="Add a new report to this person — incident, observation, or update." />
</svelte:head>

{#if loading}
	<div class="report-skeleton" aria-label="Loading report form">
		<Skeleton variant="rect" width="100%" height="2.5rem" />
		<Skeleton variant="rect" width="100%" height="2.5rem" />
		<Skeleton variant="rect" width="100%" height="2.5rem" />
		<Skeleton variant="rect" width="100%" height="2.5rem" />
		<Skeleton variant="badge" />
		<Skeleton variant="rect" width="100%" height="8rem" />
	</div>
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
			<span>{isEdit ? 'Edit report' : 'Add report'}</span>
		</p>
		<h1>{isEdit ? 'Edit report' : 'Add a report'}</h1>
		<p class="muted">
			{isEdit
				? 'Update the report below. Only the author, an advocate, or staff can edit a report.'
				: 'Reports are chronological updates — what happened, when, and where. The more detail, the stronger the case. Required fields are marked with'}
			{#if !isEdit}
				<span class="required-mark" aria-hidden="true">*</span>.
			{/if}
		</p>
	</header>

	{#if errorMsg}
		<div class="form-error form-error-{errorKind}" role="alert" transition:fly={{ y: -8, duration: 200 }}>
			<span class="form-error-icon" aria-hidden="true">!</span>
			<span>{errorMsg}</span>
			{#if errorKind === 'auth'}
				<div class="form-error-actions">
					<button type="button" onclick={() => location.reload()}>
						Refresh session
					</button>
					<a href="{base}/api/auth/login/?next={base}/persons/{person.id}/report">Log in again</a>
				</div>
			{/if}
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

		<!-- Sources (repeating) -->
		{#if !isEdit}
			<fieldset class="form-section">
				<legend class="section-legend">
					<span class="section-icon" aria-hidden="true">⚲</span>
					Sources
					<span class="legend-count">{sourceEntries.length}</span>
				</legend>
				<p class="section-hint">
					Add additional sources backing this report — each witness,
					news article, or supporting document gets its own entry
					with its own attribution, narrative, and privacy flag.
				</p>

				{#each sourceEntries as entry, i (entry.uid)}
					<div class="repeatable-entry" data-index={i}>
						<div class="repeatable-entry-header">
							<h4 class="repeatable-entry-title">Source #{i + 1}</h4>
							<button
								type="button"
								class="repeatable-entry-remove"
								aria-label="Remove source {i + 1}"
								onclick={() => removeSource(i)}
								disabled={saving}
							>✕ Remove</button>
						</div>

						<div class="grid-2">
							<div class="field">
								<label for="src-{entry.uid}-type">Source type</label>
								<select
									id="src-{entry.uid}-type"
									class="input--search"
									bind:value={entry.source_type}
									disabled={saving}
								>
									{#each Object.entries(sourceTypeLabels) as [value, label] (value)}
										<option {value}>{label}</option>
									{/each}
								</select>
								<p class="field-hint">{sourceTypeHelp[entry.source_type]}</p>
							</div>

							<div class="field">
								<label for="src-{entry.uid}-attr">
									Source attribution
									<span class="badge-public" title="Shown publicly">public</span>
								</label>
								<input
									id="src-{entry.uid}-attr"
									type="text"
									class="input--search"
									bind:value={entry.source_attribution}
									placeholder='e.g. "family member", "BBC article"'
									maxlength={MAX_SHORT}
									autocomplete="off"
									disabled={saving}
								/>
							</div>

							<div class="field">
								<label for="src-{entry.uid}-date">Date start</label>
								<input
									id="src-{entry.uid}-date"
									type="date"
									class="input--search"
									bind:value={entry.date_start}
									disabled={saving}
								/>
							</div>

							<div class="field">
								<label class="field-checkbox">
									<input
										type="checkbox"
										bind:checked={entry.is_private}
										disabled={saving}
									/>
									<span>Mark this source as private</span>
								</label>
								<p class="field-hint">
									Private sources are hidden from public reads,
									even on a public report.
								</p>
							</div>
						</div>

						<div class="field field-full">
							<label for="src-{entry.uid}-narrative">Narrative</label>
							<textarea
								id="src-{entry.uid}-narrative"
								class="input--search"
								bind:value={entry.narrative}
								maxlength={MAX_NARRATIVE}
								placeholder="What does this source say happened? Dates, places, context."
								disabled={saving}
							></textarea>
							<div class="field-counter" aria-live="polite">
								{entry.narrative.length} / {MAX_NARRATIVE}
							</div>
						</div>
					</div>
				{/each}

				<button
					type="button"
					class="repeatable-add"
					onclick={addSource}
					disabled={saving}
				>+ Add another</button>
			</fieldset>
		{/if}

		<!-- Media (repeating) -->
		{#if !isEdit}
			<fieldset class="form-section">
				<legend class="section-legend">
					<span class="section-icon" aria-hidden="true">▣</span>
					Media
					<span class="legend-count">{mediaEntries.length}</span>
				</legend>
				<p class="section-hint">
					Attach supporting evidence — photos, documents, videos,
					or external links. Each item gets its own visibility
					tier; "Sensitive" requires Advocate/Admin role.
				</p>

				{#each mediaEntries as entry, i (entry.uid)}
					<div class="repeatable-entry" data-index={i}>
						<div class="repeatable-entry-header">
							<h4 class="repeatable-entry-title">Media #{i + 1}</h4>
							<button
								type="button"
								class="repeatable-entry-remove"
								aria-label="Remove media {i + 1}"
								onclick={() => removeMedia(i)}
								disabled={saving}
							>✕ Remove</button>
						</div>

						<div class="grid-2">
							<div class="field">
								<label for="med-{entry.uid}-type">Media type</label>
								<select
									id="med-{entry.uid}-type"
									class="input--search"
									bind:value={entry.media_type}
									disabled={saving}
								>
									<option value="photo">Photo</option>
									<option value="document">Document</option>
									<option value="video">Video</option>
									<option value="link">External link</option>
								</select>
							</div>

							<div class="field">
								<label for="med-{entry.uid}-vis">Visibility</label>
								<select
									id="med-{entry.uid}-vis"
									class="input--search"
									bind:value={entry.visibility}
									disabled={saving}
								>
									<option value="public">Public — anyone can view</option>
									<option value="restricted">Restricted — authenticated users only</option>
									<option value="sensitive">Sensitive — advocates/admin only</option>
								</select>
							</div>

							<div class="field field-full">
								<label for="med-{entry.uid}-desc">
									Description <span class="optional-mark">(optional)</span>
								</label>
								<input
									id="med-{entry.uid}-desc"
									type="text"
									class="input--search"
									bind:value={entry.description}
									placeholder="What's in this media? Alt text for images."
									maxlength={500}
									autocomplete="off"
									disabled={saving}
								/>
							</div>

							<div class="field field-full">
								<label for="med-{entry.uid}-url">
									File URL <span class="optional-mark">(URL or upload via Media gallery)</span>
								</label>
								<input
									id="med-{entry.uid}-url"
									type="url"
									class="input--search"
									bind:value={entry.url}
									placeholder="https://… (paste a link, or upload via the case page)"
									maxlength={1000}
									autocomplete="off"
									disabled={saving}
								/>
								<p class="field-hint">
									File uploads (multipart) happen on the case page
									media gallery — this form accepts external links.
								</p>
							</div>
						</div>
					</div>
				{/each}

				<button
					type="button"
					class="repeatable-add"
					onclick={addMedia}
					disabled={saving}
				>+ Add another Media</button>
			</fieldset>
		{/if}

		<!-- ============================================================
		     Privacy — controls whether the report is publicly visible
		     ============================================================ -->
		<fieldset class="form-section">
			<legend class="section-legend">
				<span class="section-icon" aria-hidden="true">
					<svg viewBox="0 0 16 16" width="14" height="14">
						<path
							fill="currentColor"
							d="M4 7V5a4 4 0 1 1 8 0v2h1a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1h1zm2 0h4V5a2 2 0 1 0-4 0v2z"
						/>
					</svg>
				</span>
				Privacy
			</legend>
			<p class="section-hint">
				Private reports are hidden from the public case page. Volunteers and
				advocates can still see them when logged in.
			</p>
			<div class="field">
				<label class="field-checkbox">
					<input type="checkbox" bind:checked={isPrivate} />
					<span>Mark this report as private</span>
				</label>
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
						{isEdit ? 'Save changes' : 'Submit report'}
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
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem 0.85rem;
		padding: 0.7rem 0.95rem;
		background: #fed7d7;
		color: #c53030;
		border: 1px solid #feb2b2;
		border-radius: var(--radius-card);
		font-size: 0.9rem;
	}
	.form-error-network {
		background: #fffaf0;
		color: #5a3b00;
		border-color: #fbd38d;
	}
	.form-error-server {
		background: #fed7d7;
		color: #c53030;
		border-color: #feb2b2;
	}
	.form-error-validation {
		background: #fef5e7;
		color: #744210;
		border-color: #f6ad55;
	}
	.form-error-auth {
		background: var(--color-surface);
		color: var(--color-text);
		border-color: var(--color-border-light);
	}
	.form-error-actions {
		display: flex;
		gap: 0.5rem;
		align-items: center;
		margin-left: auto;
	}
	.form-error-actions a,
	.form-error-actions button {
		font-size: 0.85rem;
		font-weight: 500;
		text-decoration: none;
		padding: 0.3rem 0.7rem;
		border-radius: var(--radius-control);
		border: 1px solid currentColor;
		background: transparent;
		color: inherit;
		cursor: pointer;
	}
	.form-error-actions a:hover,
	.form-error-actions button:hover {
		background: rgba(0, 0, 0, 0.06);
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

	/* Checkbox row — used for the Privacy toggle */
	.field-checkbox {
		display: inline-flex;
		align-items: center;
		gap: 0.55rem;
		font-size: 0.95rem;
		color: var(--color-text);
		cursor: pointer;
		user-select: none;
	}
	.field-checkbox input[type='checkbox'] {
		width: 18px;
		height: 18px;
		accent-color: var(--color-primary);
		cursor: pointer;
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

	.report-skeleton {
		display: flex;
		flex-direction: column;
		gap: 0.8rem;
		max-width: 640px;
		margin: 2rem auto;
	}

	/* === Repeating Sources / Media entries ============================
	   Mirrors the .report-form--modal .repeatable-* styles for visual
	   parity between the per-case form and the /reports modal. */
	.repeatable-entry {
		display: flex;
		flex-direction: column;
		gap: 0.85rem;
		padding: 1rem 1.1rem;
		border: 1px solid var(--color-border-light);
		border-left: 3px solid var(--color-primary-light, #aac0ff);
		border-radius: var(--radius-card);
		background: var(--color-surface, #f7f7f9);
	}
	.repeatable-entry + .repeatable-entry {
		margin-top: 0.75rem;
	}
	.repeatable-entry-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		margin-bottom: 0.1rem;
	}
	.repeatable-entry-title {
		margin: 0;
		font-size: 0.92rem;
		font-weight: 700;
		color: var(--color-text);
	}
	.repeatable-entry-remove {
		background: transparent;
		border: 1px solid var(--color-border-light);
		color: var(--color-danger, #c53030);
		font-size: 0.78rem;
		padding: 0.25rem 0.65rem;
		border-radius: var(--radius-card);
		cursor: pointer;
		font-weight: 600;
		min-height: 0;
	}
	.repeatable-entry-remove:hover:not(:disabled) {
		background: #fed7d7;
		border-color: #feb2b2;
	}
	.repeatable-entry-remove:disabled {
		opacity: 0.55;
		cursor: not-allowed;
	}
	.repeatable-add {
		width: 100%;
		margin-top: 0.85rem;
		padding: 0.6rem 0.85rem;
		background: var(--color-bg-white);
		border: 1px dashed var(--color-border-light);
		color: var(--color-primary);
		font-size: 0.9rem;
		font-weight: 600;
		border-radius: var(--radius-card);
		cursor: pointer;
		min-height: 0;
	}
	.repeatable-add:hover:not(:disabled) {
		background: var(--color-surface, #f7f7f9);
		border-style: solid;
		border-color: var(--color-primary-light);
	}
	.repeatable-add:disabled {
		opacity: 0.55;
		cursor: not-allowed;
	}
	.legend-count {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 24px;
		padding: 0.05rem 0.55rem;
		margin-left: 0.5rem;
		background: var(--color-primary-tint, #e6efff);
		color: var(--color-primary);
		font-size: 0.75rem;
		font-weight: 700;
		border-radius: 999px;
		vertical-align: middle;
	}
</style>