<!--
  ReportForm — single source of truth for the volunteer-facing
  "Add Report" form, used by both the per-case page at
  /persons/{id}/report and the global modal at /reports.

  Why one component:
    Both entry points must accept the same payload (same fields, same
    validation, same backend wire format). Duplicating the form
    markup + state + submit logic across two .svelte files guarantees
    drift — one gets a new field, the other forgets, the bug ships.

  Field set:
    - Source information: type / attribution / reporter name / contact
    - Event timeline & location: start / end date / rough_location
    - Report details: narrative (required) / suspected / official
    - Privacy: mark as private
    - Sources (repeating): type / attribution / date / narrative / is_private
    - Media (repeating): media_type / visibility / description / url

  Modes:
    - Page mode (props.person set): no PersonPicker — person is fixed
      by the route. Used at /persons/{id}/report.
    - Modal mode (props.person undefined): PersonPicker shown at the
      top so the volunteer can pick the case. Used at /reports.
    - Edit mode (props.reportId set): loads the existing report and
      pre-populates the main fields. Sources / Media sections are
      hidden on edit (DRF's nested writable serializer would REPLACE
      the collection on update, silently dropping existing rows).
      Edit-mode source / media management lives on /sources/ and
      /media/ endpoints.

  Submit flow:
    - Create: POST /reports/ with nested sources, then POST /media/
      per item with report=<newId>. Multi-step because
      ReportSerializer.media_files is read-only nested.
    - Update: PATCH /reports/{id}/ — no sources/media fields.
    - On success, fires `onsuccess` with { report, mediaFailures }.
    - On cancel, fires `oncancel`.

  Out of scope:
    - File upload (multipart) — the form only accepts URL-based media.
      Real file uploads happen on the per-case media gallery.
    - Loading existing sources / media on edit — see edit-mode note
      above. Add later via separate fetch when the UX warrants.
-->
<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { fly } from 'svelte/transition';
	import { ApiError, createReport, getReport, request, updateReport } from '$lib/api';
	import { focusFirstFormError } from '$lib/formFocus';
	import PersonPicker from '$lib/PersonPicker.svelte';
	import SourcesField from '$lib/SourcesField.svelte';
	import type { SourceEntry } from '$lib/SourcesField.svelte';
	import MediaField from '$lib/MediaField.svelte';
	import type { MediaEntry } from '$lib/MediaField.svelte';
	import type { Media, Report } from '$lib/types';

	// --- Public props ---------------------------------------------------
	interface Person {
		id: number;
		name: string;
	}
	interface Props {
		// Person is optional. When set, the PersonPicker is hidden and
		// `person.id` is used as the FK on submit. When unset, the
		// picker is shown and the volunteer's selection is the FK.
		person?: Person;
		// Edit-mode trigger. When set, the component loads the existing
		// report and pre-populates fields. When null/undefined, it's
		// create mode.
		reportId?: number | null;
		// Override the submit button label (default varies by mode).
		submitLabel?: string;
		// Called after a successful save. Receives the saved report and
		// any partial-failure warnings (empty array if everything
		// succeeded). The parent decides whether to close the modal,
		// navigate, refresh a list, etc.
		onSuccess?: (detail: { report: Report; mediaFailures: string[] }) => void;
		// Called when the user cancels (Cancel button or, in modal mode,
		// Escape/backdrop close). Optional — parents without a custom
		// cancel handler can simply not pass one.
		onCancel?: () => void;
		// Disable all inputs (e.g. while parent is doing unrelated work).
		// Submission is also blocked while saving internally.
		disabled?: boolean;
		// When true, the `sensitive` media visibility option is shown in
		// the per-row dropdown. Backend enforces this gate too
		// (MediaViewSet._can_mark_sensitive, views.py:904). Parents
		// derive this from the current user's groups.
		canMarkSensitive?: boolean;
	}
	let {
		person: personProp,
		reportId = null,
		submitLabel,
		onSuccess,
		onCancel,
		disabled = false,
		// Default `true` to preserve the prior inline-ReportForm behavior
		// (it always showed all 3 visibility options). New call sites that
		// want role-based gating — like /submit — pass `false` for non-
		// advocates and the dropdown filters accordingly.
		canMarkSensitive = true,
	}: Props = $props();

	const isEdit = $derived(reportId !== null);
	const effectiveSubmitLabel = $derived(
		submitLabel ?? (isEdit ? 'Save changes' : 'Submit report'),
	);

	// --- Form state -----------------------------------------------------

	// Person: in page mode we use personProp; in modal mode we hold the
	// picker's selection locally. `formPersonId` is the FK that goes on
	// the wire — null until the volunteer has either picked (modal) or
	// the page has loaded the person (page).
	//
	// Initial value uses `personProp` once at component construction.
	// personProp is expected to be stable for the lifetime of this
	// component (parent passes a single Person object); if it ever
	// changes, the picker / form fields below will desync from this
	// initial — `untrack` documents that intent and silences the
	// state-captured-locally warning.
	let formPersonId = $state<number | null>(untrack(() => personProp?.id ?? null));

	// Source information
	let sourceType = $state<Report['source_type']>('firsthand');
	let sourceAttribution = $state('');
	let reporterName = $state('');
	let reporterContact = $state('');

	// Event timeline & location
	let dateStart = $state('');
	let dateEnd = $state('');
	let roughLocation = $state('');

	// Report details
	let narrative = $state('');
	let suspectedReason = $state('');
	let officialReason = $state('');

	// Privacy
	let isPrivate = $state(false);

	// Repeating Sources — entries live in the child <SourcesField> component;
	// local `entries` array is mutated through `bind:entries`. The SourceEntry
	// shape is exported from SourcesField.svelte and imported above.
	let sourceEntries = $state<SourceEntry[]>([]);

	// Repeating Media — same pattern. The MediaEntry shape (including the
	// optional `file` field for uploads) is exported from MediaField.svelte.
	let mediaEntries = $state<MediaEntry[]>([]);

	// Submission state
	let saving = $state(false);
	// `loading` starts true on edit mode (we need to fetch the report)
	// and false on create mode. The value is captured once at mount;
	// if `isEdit` flips later, the user must re-mount (we don't
	// currently support that, and the parent doesn't change reportId).
	let loading = $state(untrack(() => isEdit));
	let errorMsg = $state('');
	let errorKind = $state<'generic' | 'network' | 'auth' | 'server' | 'validation'>('generic');
	let fieldErrors = $state<Record<string, string>>({});

	// Refetch-guard token so Back/Forward between ?id=5 and ?id=7
	// can't let a slow response for 5 clobber the form populated for 7.
	let loadToken = 0;
	function resetForm() {
		if (personProp === undefined) {
			formPersonId = null;
		}
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
		fieldErrors = {};
		errorMsg = '';
		errorKind = 'generic';
	}

	function onPersonPicked(id: number | null) {
		formPersonId = id;
		if (fieldErrors.person) {
			const { person: _drop, ...rest } = fieldErrors;
			fieldErrors = rest;
		}
	}

	// --- Constants used by both template and validation ------------------
	const MAX_NARRATIVE = 5000;
	const MAX_SHORT = 500;

	// Source-type labels + help — for the *primary* report's source
	// type/attribution. The repeating-sources list inside <SourcesField>
	// has its own copy of these constants.
	const sourceTypeLabels: Record<Report['source_type'], string> = {
		firsthand: 'Firsthand',
		secondhand: 'Secondhand',
		news: 'News report',
		document: 'Document',
	};
	const sourceTypeHelp: Record<Report['source_type'], string> = {
		firsthand: 'From someone who directly witnessed or experienced the event.',
		secondhand: 'From someone close to the event (family, neighbor, colleague).',
		news: 'From a media report — link the source in the attribution field.',
		document: 'From an official document, court filing, or organizational report.',
	};

	// --- Edit-mode hydration --------------------------------------------
	async function load() {
		if (!isEdit || reportId === null) return;
		const token = ++loadToken;
		loading = true;
		errorMsg = '';
		fieldErrors = {};
		try {
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
		} catch (e: unknown) {
			if (token !== loadToken) return;
			errorMsg = e instanceof Error ? e.message : "Couldn't load this report.";
		} finally {
			if (token === loadToken) loading = false;
		}
	}

	$effect(() => {
		void reportId;
		void load();
	});

	// --- Validation ------------------------------------------------------
	function validate(): boolean {
		const e: Record<string, string> = {};
		if (formPersonId === null) {
			e.person = 'Pick the case this report belongs to.';
		}
		if (!narrative.trim()) {
			e.narrative = 'Narrative is required.';
		} else if (narrative.length > MAX_NARRATIVE) {
			e.narrative = `Narrative is too long (max ${MAX_NARRATIVE} characters).`;
		}
		if (dateStart && dateEnd && dateEnd < dateStart) {
			e.date_end = 'End date must be on or after the start date.';
		}
		if (sourceAttribution.length > MAX_SHORT) {
			e.source_attribution = `Source attribution is too long (max ${MAX_SHORT} characters).`;
		}
		if (reporterContact.length > MAX_SHORT) {
			e.reporter_contact = `Reporter contact is too long (max ${MAX_SHORT} characters).`;
		}
		fieldErrors = e;
		return Object.keys(e).length === 0;
	}

	// Visual order of fields with potential validation errors. Focuses the
	// topmost broken field after a failed submit so the user lands where
	// they need to act, not at the submit button. The form's input ids
	// are rf-* prefixed; the map translates validator keys to those.
	const REPORT_FIELD_ORDER = [
		'person', 'narrative', 'date_end', 'source_attribution', 'reporter_contact',
	];
	const REPORT_FIELD_ID_MAP: Record<string, string[]> = {
		narrative: ['rf-narrative'],
		date_end: ['rf-date-end'],
		source_attribution: ['rf-source-attr'],
		reporter_contact: ['rf-reporter-contact'],
	};

	// --- Submit ----------------------------------------------------------
	async function handleSubmit() {
		if (saving || disabled) return;
		if (!validate()) {
			// Pull the user up to the topmost broken field instead of
			// leaving them stranded at the submit button.
			focusFirstFormError(fieldErrors, {
				order: REPORT_FIELD_ORDER,
				idMap: REPORT_FIELD_ID_MAP,
			});
			return;
		}
		if (formPersonId === null) return;
		saving = true;
		errorMsg = '';
		errorKind = 'generic';

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
			person: formPersonId,
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
			let created: Report | null = null;
			if (isEdit && reportId !== null) {
				const updated = await updateReport(reportId, payload);
				created = updated;
			} else {
				created = await createReport(payload);
			}

			// Attach each media item separately. ReportSerializer has
			// media_files as read-only nested, so a second POST per item
			// is required. Track failures but don't fail the whole flow —
			// the report itself is saved.
			const failures: string[] = [];
			if (!isEdit && created !== null) {
				for (let i = 0; i < mediaEntries.length; i++) {
					const m = mediaEntries[i];
					if (!m.url.trim() && !m.description.trim()) continue;
					try {
						await request<Media>('/media/', {
							method: 'POST',
							body: JSON.stringify({
								report: created.id,
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

			resetForm();
			onSuccess?.({ report: created, mediaFailures: failures });
		} catch (err: unknown) {
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
				errorMsg = err instanceof Error ? err.message : 'Failed to save the report.';
			}
		} finally {
			saving = false;
		}
	}

	function handleCancel() {
		if (saving) return;
		resetForm();
		onCancel?.();
	}
</script>

{#if loading}
	<div class="report-form-skeleton" aria-label="Loading report form">
		<div class="report-form-skeleton-row"></div>
		<div class="report-form-skeleton-row"></div>
		<div class="report-form-skeleton-row"></div>
		<div class="report-form-skeleton-row"></div>
		<div class="report-form-skeleton-row report-form-skeleton-row--wide"></div>
	</div>
{:else}
	<form
		class="report-form"
		onsubmit={(e) => {
			e.preventDefault();
			void handleSubmit();
		}}
		novalidate
	>
		{#if errorMsg}
			<div class="form-error form-error-{errorKind}" role="alert" transition:fly={{ y: -8, duration: 200 }}>
				<span class="form-error-icon" aria-hidden="true">!</span>
				<span>{errorMsg}</span>
				{#if errorKind === 'auth'}
					<div class="form-error-actions">
						<button type="button" onclick={() => location.reload()}>
							Refresh session
						</button>
					</div>
				{/if}
			</div>
		{/if}

		<!-- ============================================================
		     Case picker (modal mode only)
		     ============================================================ -->
		{#if !personProp}
			<fieldset class="form-section">
				<legend class="section-legend">
					<span class="section-icon" aria-hidden="true">◉</span>
					Case
				</legend>
				<p class="section-hint">
					Reports belong to a case (a Person). Pick one before
					filling in the rest.
				</p>
				<div class="field field-full">
					<PersonPicker
						inputId="report-form-person"
						value={formPersonId}
						onChange={onPersonPicked}
						disabled={saving || disabled}
					/>
					{#if fieldErrors.person}
						<p class="field-error">{fieldErrors.person}</p>
					{/if}
				</div>
			</fieldset>
		{/if}

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
				<div class="field">
					<label for="rf-source-type">Source type</label>
					<select
						id="rf-source-type"
						class="input--search"
						bind:value={sourceType}
						disabled={saving || disabled}
					>
						{#each Object.entries(sourceTypeLabels) as [value, label] (value)}
							<option {value}>{label}</option>
						{/each}
					</select>
					<p class="field-hint">{sourceTypeHelp[sourceType]}</p>
				</div>

				<div class="field">
					<label for="rf-source-attr">
						Source attribution
						<span class="badge-public" title="Shown publicly">public</span>
					</label>
					<input
						id="rf-source-attr"
						type="text"
						class="input--search"
						class:has-error={!!fieldErrors.source_attribution}
						bind:value={sourceAttribution}
						placeholder='e.g. "family member", "BBC article"'
						maxlength={MAX_SHORT}
						autocomplete="off"
						disabled={saving || disabled}
					/>
					{#if fieldErrors.source_attribution}
						<p class="field-error">{fieldErrors.source_attribution}</p>
					{/if}
				</div>

				<div class="field">
					<label for="rf-reporter-name">
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
						id="rf-reporter-name"
						type="text"
						class="input--search"
						bind:value={reporterName}
						placeholder="Not shown publicly"
						maxlength={255}
						autocomplete="off"
						disabled={saving || disabled}
					/>
				</div>

				<div class="field">
					<label for="rf-reporter-contact">
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
						id="rf-reporter-contact"
						type="text"
						class="input--search"
						class:has-error={!!fieldErrors.reporter_contact}
						bind:value={reporterContact}
						placeholder="Email, phone, Signal — how we follow up"
						maxlength={MAX_SHORT}
						autocomplete="off"
						disabled={saving || disabled}
					/>
					{#if fieldErrors.reporter_contact}
						<p class="field-error">{fieldErrors.reporter_contact}</p>
					{/if}
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
				<div class="field">
					<label for="rf-date-start">Start date</label>
					<input
						id="rf-date-start"
						type="date"
						class="input--search"
						class:has-error={!!fieldErrors.date_start}
						bind:value={dateStart}
						disabled={saving || disabled}
					/>
				</div>

				<div class="field">
					<label for="rf-date-end">End date <span class="optional-mark">(optional)</span></label>
					<input
						id="rf-date-end"
						type="date"
						class="input--search"
						class:has-error={!!fieldErrors.date_end}
						bind:value={dateEnd}
						disabled={saving || disabled}
					/>
					{#if fieldErrors.date_end}
						<p class="field-error">{fieldErrors.date_end}</p>
					{/if}
				</div>

				<div class="field field-full">
					<label for="rf-location">
						Location <span class="optional-mark">(optional)</span>
					</label>
					<input
						id="rf-location"
						type="text"
						class="input--search"
						bind:value={roughLocation}
						placeholder='e.g. "Karachi, Sindh, Pakistan" — keep it regional'
						maxlength={255}
						autocomplete="off"
						disabled={saving || disabled}
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

			<div class="field field-full">
				<label for="rf-narrative">
					Narrative <span class="required-mark" aria-hidden="true">*</span>
					<span class="sr-only">required</span>
				</label>
				<textarea
					id="rf-narrative"
					class="input--search narrative-textarea"
					class:has-error={!!fieldErrors.narrative}
					bind:value={narrative}
					maxlength={MAX_NARRATIVE}
					placeholder="What happened? What is known? Include dates, places, people, and any context that helps."
					disabled={saving || disabled}
				></textarea>
				{#if fieldErrors.narrative}
					<p class="field-error">{fieldErrors.narrative}</p>
				{/if}
				<div class="field-counter" aria-live="polite">
					{narrative.length} / {MAX_NARRATIVE}
				</div>
			</div>

			<div class="grid-2">
				<div class="field">
					<label for="rf-suspected">
						Suspected reason <span class="optional-mark">(optional)</span>
					</label>
					<textarea
						id="rf-suspected"
						class="input--search"
						bind:value={suspectedReason}
						maxlength={MAX_NARRATIVE}
						placeholder="What do sources believe is the reason? Stay close to what they actually say."
						disabled={saving || disabled}
					></textarea>
				</div>

				<div class="field">
					<label for="rf-official">
						Official reason <span class="optional-mark">(optional)</span>
					</label>
					<textarea
						id="rf-official"
						class="input--search"
						bind:value={officialReason}
						maxlength={MAX_NARRATIVE}
						placeholder="What did the state officially charge, if anything?"
						disabled={saving || disabled}
					></textarea>
				</div>
			</div>
		</fieldset>

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
					<input
						type="checkbox"
						bind:checked={isPrivate}
						disabled={saving || disabled}
					/>
					<span>Mark this report as private</span>
				</label>
			</div>
		</fieldset>

		<!-- ============================================================
		     Sources (repeating) — additional witnesses / news / docs
		     Hidden on edit mode (DRF nested-writable replaces on update).
		     Reusable row markup lives in <SourcesField>; this fieldset
		     owns the section chrome (icon + legend + count + hint).
		     ============================================================ -->
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

				<SourcesField bind:entries={sourceEntries} disabled={saving || disabled} />
			</fieldset>
		{/if}

		<!-- ============================================================
		     Media (repeating) — photos / documents / videos / links
		     Hidden on edit mode (multi-step submit only on create).
		     Reusable row markup lives in <MediaField>; the visibility
		     dropdown's `sensitive` option is filtered by `canMarkSensitive`
		     (Advocate/Admin only — see MediaViewSet line 904).
		     ============================================================ -->
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

				<MediaField
					bind:entries={mediaEntries}
					disabled={saving || disabled}
					{canMarkSensitive}
					allowFileUpload={false}
				/>
			</fieldset>
		{/if}

		<!-- ============================================================
		     Action footer
		     ============================================================ -->
		<footer class="form-footer">
			<p class="form-footer-hint">
				By submitting, you confirm the information is accurate
				to the best of your knowledge.
			</p>
			<div class="form-footer-actions">
				{#if onCancel}
					<button
						type="button"
						class="btn btn-secondary"
						onclick={handleCancel}
						disabled={saving || disabled}
					>Cancel</button>
				{/if}
				<button
					type="submit"
					class="btn btn-primary"
					disabled={saving || disabled}
				>
					{#if saving}
						<span class="spinner" aria-hidden="true"></span>
						Saving…
					{:else}
						{effectiveSubmitLabel}
					{/if}
				</button>
			</div>
		</footer>
	</form>
{/if}

<style>
	/* === Skeleton (edit mode only — page mode shows while loading) === */
	.report-form-skeleton {
		display: flex;
		flex-direction: column;
		gap: 0.8rem;
		width: 100%;
		max-width: 880px;
		margin: 2rem auto;
	}
	.report-form-skeleton-row {
		height: 2.5rem;
		background: var(--color-surface);
		border-radius: var(--radius-card);
		animation: rf-skeleton-pulse 1.4s ease-in-out infinite;
	}
	.report-form-skeleton-row--wide {
		height: 8rem;
	}
	@keyframes rf-skeleton-pulse {
		0%,
		100% { opacity: 1; }
		50% { opacity: 0.55; }
	}

	/* === Page layout === */
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
	.form-error-network { background: #fffaf0; color: #5a3b00; border-color: #fbd38d; }
	.form-error-server { background: #fed7d7; color: #c53030; border-color: #feb2b2; }
	.form-error-validation { background: #fef5e7; color: #744210; border-color: #f6ad55; }
	.form-error-auth { background: var(--color-surface); color: var(--color-text); border-color: var(--color-border-light); }
	.form-error-actions {
		display: flex;
		gap: 0.5rem;
		align-items: center;
		margin-left: auto;
	}
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
		background: var(--color-primary-tint, #e6efff);
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

	/* Inputs (reuses .input--search from app.css) */
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

	/* Privacy badges on labels */
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
	.badge-public { background: #c6f6d5; color: #22543d; }
	.badge-private { background: #fefcbf; color: #744210; }
	.badge-private svg { display: inline-block; }

	/* Required / optional markers */
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

	/* === Repeating entries (Sources / Media) === */
	/* Row markup lives in <SourcesField> / <MediaField>; the count badge
	   in the section legend is the only piece this parent still owns. */
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
		animation: rf-spin 0.7s linear infinite;
		margin-right: 0.4rem;
		vertical-align: -2px;
	}
	@keyframes rf-spin {
		to { transform: rotate(360deg); }
	}

	/* === Responsive === */
	@media (max-width: 600px) {
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
		.report-form-skeleton-row { animation: none; }
	}
</style>
