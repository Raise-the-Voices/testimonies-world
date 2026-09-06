<script lang="ts">
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import {
		getPerson,
		getMedia,
		getPersons,
		getRelationships,
		createRelationship,
		updateRelationship,
		deleteRelationship,
		deleteMedia,
		deletePerson,
		deleteReport,
	} from '$lib/api';
	import { user, isVolunteer, isAdvocate } from '$lib/session';
	import StatusBadge from '$lib/StatusBadge.svelte';
	import Skeleton from '$lib/Skeleton.svelte';
	import ConfirmModal from '$lib/ConfirmModal.svelte';
	import MediaUploadModal from '$lib/MediaUploadModal.svelte';
	import type { FamilyRelationshipRow, Media, Person, Report } from '$lib/types';

	let currentUser = $derived($user);
	let mediaList = $state<Media[]>([]);
	let loadingMedia = $state(true);
	let mediaError = $state('');
	let uploadOpen = $state(false);
	let editTarget = $state<Media | null>(null);
	let deleteTarget = $state<Media | null>(null);
	let deleting = $state(false);
	let deleteError = $state('');

	/* Report delete state — mirrors the Media pattern but uses `report*`
	   prefixes to avoid name collisions with the Media delete state above. */
	let reportDeleteTarget = $state<Report | null>(null);
	let reportDeleting = $state(false);
	let reportDeleteError = $state('');

	/* Person delete state — only one person in scope (this page IS the
	   person), so no `personDeleteTarget` object is needed; we reuse
	   the `person` value itself. Distinct `person*` names avoid
	   collisions with the media / report delete state above. */
	let personDeleteOpen = $state(false);
	let personDeleting = $state(false);
	let personDeleteError = $state('');

	/* Family relationships state — full CRUD via /api/relationships/.
	   We store the *full row* (not the flattened display shape) so we
	   have the `id` for edit/delete. `relationshipPickerList` is the
	   one-shot fetch used by the create/edit picker; we exclude the
	   current person on the client (the picker doesn't include them). */
	let relationships = $state<FamilyRelationshipRow[]>([]);
	let loadingRelationships = $state(true);
	let relationshipError = $state('');
	let relationshipPickerList = $state<Array<{ id: number; name: string; country: string }>>([]);
	let pickerLoaded = $state(false);

	// Create/edit form state.
	let relationshipFormOpen = $state(false);
	let editingRel = $state<FamilyRelationshipRow | null>(null);
	let relationshipSaving = $state(false);
	let relationshipFormOtherId = $state<number | ''>('');
	let relationshipFormType = $state<FamilyRelationshipRow['relationship_type']>('sibling');
	let relationshipFormNotes = $state('');
	let relationshipFormError = $state('');

	// Delete state.
	let relationshipDelTarget = $state<FamilyRelationshipRow | null>(null);
	let relationshipDeleting = $state(false);
	let relationshipDeleteError = $state('');

	// Permission helper: only advocates+admin can put media in the
	// 'sensitive' tier. Mirrors backend `_can_mark_sensitive` in
	// cases/views.py.
	const canMarkSensitive = $derived(isAdvocate(currentUser));

	// Source-type display labels (mirror backend Report.SourceType.choices)
	const sourceTypeLabels: Record<string, string> = {
		firsthand: 'Firsthand',
		secondhand: 'Secondhand',
		news: 'News',
		document: 'Document',
	};

	// Media type / visibility display labels — mirror backend
	// Media.MediaType + Media.Visibility.
	const mediaTypeLabels: Record<string, string> = {
		photo: 'Photo',
		video: 'Video',
		document: 'Document',
		link: 'External link',
	};
	const visibilityLabels: Record<string, string> = {
		public: 'Public',
		restricted: 'Restricted',
		sensitive: 'Sensitive',
	};

	// URL extraction — finds http(s):// and bare www. links in narrative text,
	// trims trailing punctuation users commonly leave after pasting URLs.
	const URL_RE = /\b((?:https?:\/\/|www\.)[^\s<>"']+)/gi;
	function scanNarrative(text: string): Array<{ kind: 'text' | 'url'; value: string }> {
		if (!text) return [];
		const out: Array<{ kind: 'text' | 'url'; value: string }> = [];
		let last = 0;
		let m: RegExpExecArray | null;
		URL_RE.lastIndex = 0;
		while ((m = URL_RE.exec(text)) !== null) {
			if (m.index > last) out.push({ kind: 'text', value: text.slice(last, m.index) });
			let url = m[0];
			const trail = url.match(/[),.;]+$/);
			if (trail) url = url.slice(0, -trail[0].length);
			out.push({ kind: 'url', value: url });
			last = m.index + m[0].length;
		}
		if (last < text.length) out.push({ kind: 'text', value: text.slice(last) });
		return out;
	}
	function domainOf(url: string): string {
		try {
			const u = new URL(url.startsWith('http') ? url : 'http://' + url);
			return u.hostname.replace(/^www\./, '');
		} catch {
			return url;
		}
	}
	function normalizeUrl(url: string): string {
		return url.startsWith('http') ? url : 'https://' + url;
	}

	// Paragraph split — narrative uses newlines between paragraphs.
	// Returns trimmed non-empty paragraphs.
	function paragraphs(text: string): string[] {
		if (!text) return [];
		return text.split(/\n+/).map((s) => s.trim()).filter(Boolean);
	}

	// Date detection — bold temporal milestones for scannability.
	// Covers: "July 25, 2025", "25 July 2025", "Jul 25, 2025", "2025-07-25",
	// plus ordinal suffixes (1st, 2nd, 3rd, 4th, ...).
	const MONTH_RE =
		'(?:January|February|March|April|May|June|July|August|' +
		'September|October|November|December|' +
		'Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)';
	const DATE_RE = new RegExp(
		'\\b(?:' +
			// Month-name + day + year: "July 25, 2025" or "Jul 25 2025"
			MONTH_RE + '\\s+\\d{1,2}(?:st|nd|rd|th)?,?\\s+\\d{4}' +
			// Day + month-name + year: "25 July 2025"
			'|\\d{1,2}\\s+' + MONTH_RE + '\\s+\\d{4}' +
			// ISO: "2025-07-25"
			'|\\d{4}-\\d{2}-\\d{2}' +
			')\\b',
		'gi',
	);
	function scanNarrativeDates(text: string): Array<{ kind: 'text' | 'date'; value: string }> {
		if (!text) return [];
		const out: Array<{ kind: 'text' | 'date'; value: string }> = [];
		let last = 0;
		let m: RegExpExecArray | null;
		DATE_RE.lastIndex = 0;
		while ((m = DATE_RE.exec(text)) !== null) {
			if (m.index > last) out.push({ kind: 'text', value: text.slice(last, m.index) });
			out.push({ kind: 'date', value: m[0] });
			last = m.index + m[0].length;
		}
		if (last < text.length) out.push({ kind: 'text', value: text.slice(last) });
		return out;
	}

	let person: Person | null = $state(null);
	let loading = $state(true);
	let error: string = $state('');
	let expandedId: number | null = $state(null);

	// Refetch-guard token: increments on every navigation-driven refetch.
	// Async helpers capture it locally and bail out if loadToken has moved on,
	// so a slow request for person 123 doesn't clobber state after they've
	// already navigated to person 456 (Back/Forward race).
	let loadToken = 0;
	let currentId = $derived(page.params.id);

	const medicalLabels: Record<string, string> = {
		unknown: 'Unknown',
		healthy: 'Healthy',
		health_concerns: 'Health Concerns',
		critical: 'Critical',
		deceased: 'Deceased',
	};

	async function loadPerson() {
		const token = ++loadToken;
		// Reset per-page UI that doesn't survive a person switch. Without
		// these resets, an expanded report card or an open delete-modal from
		// the previous person would carry over to the new one.
		expandedId = null;
		deleteTarget = null;
		reportDeleteTarget = null;
		personDeleteOpen = false;
		relationshipFormOpen = false;
		relationshipDelTarget = null;
		uploadOpen = false;
		editTarget = null;

		loading = true;
		error = '';
		try {
			const p = await getPerson(currentId!);
			if (token !== loadToken) return;
			person = p;
			// Reload media + family links with the freshly-loaded person.
			await Promise.all([loadMedia(token), loadRelationships(token)]);
		} catch (e: unknown) {
			if (token !== loadToken) return;
			error = e instanceof Error ? e.message : 'Failed to load case.';
		} finally {
			if (token === loadToken) loading = false;
		}
	}

	async function loadRelationships(tok: number = loadToken) {
		if (!person) return;
		loadingRelationships = true;
		relationshipError = '';
		try {
			const data = await getRelationships({ person: String(person.id) });
			if (tok !== loadToken) return;
			relationships = Array.isArray(data) ? data : data.results ?? [];
		} catch (e: unknown) {
			if (tok !== loadToken) return;
			relationshipError =
				e instanceof Error ? e.message : 'Failed to load family links.';
			relationships = [];
		} finally {
			if (tok === loadToken) loadingRelationships = false;
		}
	}

	// Picker: single-shot fetch of all published persons. Used by the
	// create/edit form so the user can pick the *other* side of the
	// relationship. Fails gracefully — if the fetch errors, the form
	// still opens with an empty picker and a visible error.
	async function loadPicker() {
		if (pickerLoaded) return;
		try {
			const data = await getPersons({
				is_published: 'true',
				page_size: '1000',
			});
			const list = Array.isArray(data) ? data : data.results ?? [];
			relationshipPickerList = list.map((p) => ({
				id: p.id,
				name: p.name,
				country: p.country,
			}));
			pickerLoaded = true;
		} catch (e: unknown) {
			relationshipPickerList = [];
		}
	}

	async function loadMedia(tok: number = loadToken) {
		if (!person) return;
		loadingMedia = true;
		mediaError = '';
		try {
			const data = await getMedia({ person: String(person.id) });
			if (tok !== loadToken) return;
			mediaList = Array.isArray(data) ? data : data.results ?? [];
		} catch (e: unknown) {
			if (tok !== loadToken) return;
			mediaError =
				e instanceof Error ? e.message : 'Failed to load media for this case.';
			mediaList = [];
		} finally {
			if (tok === loadToken) loadingMedia = false;
		}
	}

	function openUpload() {
		editTarget = null;
		uploadOpen = true;
	}

	function openEdit(m: Media) {
		editTarget = m;
		uploadOpen = true;
	}

	function onMediaSaved(saved: Media) {
		// Upsert: if we already have this row (edit case), replace; else add.
		const idx = mediaList.findIndex((m) => m.id === saved.id);
		if (idx >= 0) {
			mediaList[idx] = saved;
		} else {
			mediaList = [saved, ...mediaList];
		}
	}

	function startDelete(m: Media) {
		deleteTarget = m;
		deleteError = '';
	}

	function cancelDelete() {
		deleteTarget = null;
		deleteError = '';
	}

	async function confirmDelete() {
		if (!deleteTarget) return;
		deleting = true;
		try {
			await deleteMedia(deleteTarget.id);
			mediaList = mediaList.filter((m) => m.id !== deleteTarget!.id);
			deleteTarget = null;
		} catch (e: unknown) {
			deleteError =
				e instanceof Error ? e.message : "Couldn't delete that media item.";
		} finally {
			deleting = false;
		}
	}

	/* Report delete — optimistic remove from `person.reports`. The backend
	   may return 403 if the current user isn't the author (and isn't staff /
	   advocate); we surface that via `reportDeleteError` rather than silently
	   hiding the buttons, so the user understands why the action failed. */
	function startReportDelete(r: Report) {
		reportDeleteTarget = r;
		reportDeleteError = '';
	}

	function cancelReportDelete() {
		reportDeleteTarget = null;
		reportDeleteError = '';
	}

	async function confirmReportDelete() {
		if (!reportDeleteTarget || !person) return;
		reportDeleting = true;
		try {
			await deleteReport(reportDeleteTarget.id);
			person.reports = (person.reports ?? []).filter(
				(r) => r.id !== reportDeleteTarget!.id,
			);
			// If the user had this report's body open, collapse it.
			if (expandedId === reportDeleteTarget.id) expandedId = null;
			reportDeleteTarget = null;
		} catch (e: unknown) {
			reportDeleteError =
				e instanceof Error ? e.message : "Couldn't delete that report.";
		} finally {
			reportDeleting = false;
		}
	}

	/* Person delete — hard delete; on success we navigate away because
	   the page itself is gone. The destination reads `?deleted=1` and
	   surfaces a transient success banner (see /persons/+page.svelte).
	   CASCADE on the FKs in cases/models.py means reports, media, and
	   family links vanish along with the Person row; the audit row in
	   AuditLog is the only surviving trace. */
	function startPersonDelete() {
		personDeleteOpen = true;
		personDeleteError = '';
	}

	function cancelPersonDelete() {
		if (personDeleting) return;
		personDeleteOpen = false;
		personDeleteError = '';
	}

	async function confirmPersonDelete() {
		if (!person) return;
		personDeleting = true;
		try {
			await deletePerson(person.id);
			personDeleteOpen = false;
			// `goto` preserves the `base` prefix automatically. The query
			// param drives the success banner on /persons.
			await goto(`${base}/persons?deleted=1`);
		} catch (e: unknown) {
			personDeleteError =
				e instanceof Error ? e.message : "Couldn't delete that case.";
			personDeleting = false;
		}
		// On success we navigate away — keep `personDeleting = true` so the
		// modal button stays disabled during the redirect (no flicker).
	}

	/* --- Family relationship handlers ------------------------------------
	   Mirrors the media / report / case delete patterns: distinct
	   `relationship*` state, inline error via `.form-error`, in-place
	   list refresh on success. The create/edit form posts
	   `person_a = currentPerson.id, person_b = otherPerson.id` — we
	   fix the direction so the same row doesn't get re-created in the
	   opposite direction by mistake. */

	const RELATIONSHIP_TYPE_LABELS: Record<FamilyRelationshipRow['relationship_type'], string> = {
		parent: 'Parent',
		child: 'Child',
		sibling: 'Sibling',
		spouse: 'Spouse',
		other: 'Other relative',
	};

	// The "other" side from the current person's perspective.
	function otherPerson(rel: FamilyRelationshipRow): { id: number; name: string } {
		if (rel.person_a === person?.id) return { id: rel.person_b, name: rel.person_b_name };
		return { id: rel.person_a, name: rel.person_a_name };
	}

	function resetRelForm() {
		editingRel = null;
		relationshipFormOtherId = '';
		relationshipFormType = 'sibling';
		relationshipFormNotes = '';
		relationshipFormError = '';
		relationshipSaving = false;
	}

	function startRelCreate() {
		resetRelForm();
		relationshipFormOpen = true;
		void loadPicker();
	}

	function startRelEdit(rel: FamilyRelationshipRow) {
		editingRel = rel;
		const other = otherPerson(rel);
		relationshipFormOtherId = other.id;
		relationshipFormType = rel.relationship_type;
		relationshipFormNotes = rel.notes ?? '';
		relationshipFormError = '';
		relationshipSaving = false;
		relationshipFormOpen = true;
		void loadPicker();
	}

	function cancelRelForm() {
		if (relationshipSaving) return;
		relationshipFormOpen = false;
		resetRelForm();
	}

	async function submitRelForm() {
		if (!person) return;
		if (relationshipFormOtherId === '' || relationshipFormOtherId === person.id) {
			relationshipFormError = 'Pick a different person to relate to.';
			return;
		}
		relationshipSaving = true;
		relationshipFormError = '';
		try {
			if (editingRel) {
				// Edit preserves direction (we never change person_a/person_b).
				// The backend validator accepts a PATCH that omits them.
				const updated = await updateRelationship(editingRel.id, {
					relationship_type: relationshipFormType,
					notes: relationshipFormNotes,
				});
				relationships = relationships.map((r) =>
					r.id === updated.id ? updated : r,
				);
			} else {
				const created = await createRelationship({
					person_a: person.id,
					person_b: relationshipFormOtherId,
					relationship_type: relationshipFormType,
					notes: relationshipFormNotes,
				});
				relationships = [...relationships, created];
			}
			relationshipFormOpen = false;
			resetRelForm();
		} catch (e: unknown) {
			relationshipFormError =
				e instanceof Error ? e.message : "Couldn't save the relationship.";
		} finally {
			relationshipSaving = false;
		}
	}

	function startRelDelete(rel: FamilyRelationshipRow) {
		relationshipDelTarget = rel;
		relationshipDeleteError = '';
	}

	function cancelRelDelete() {
		if (relationshipDeleting) return;
		relationshipDelTarget = null;
		relationshipDeleteError = '';
	}

	async function confirmRelDelete() {
		if (!relationshipDelTarget) return;
		relationshipDeleting = true;
		try {
			await deleteRelationship(relationshipDelTarget.id);
			relationships = relationships.filter((r) => r.id !== relationshipDelTarget!.id);
			relationshipDelTarget = null;
		} catch (e: unknown) {
			relationshipDeleteError =
				e instanceof Error ? e.message : "Couldn't delete that link.";
		} finally {
			relationshipDeleting = false;
		}
	}

	// Refetch whenever the route param changes (Back/Forward between
	// different person IDs). The loadToken guard inside loadPerson / loadMedia /
	// loadRelationships discards any in-flight response from a prior param.
	$effect(() => {
		void currentId;
		void loadPerson();
	});
</script>

<svelte:head>
	<title>{person ? person.name : 'Loading...'} — Testimonies.world</title>
</svelte:head>

{#if loading}
	<div class="view-container" aria-busy="true" aria-label="Loading case">
		<!-- Main content skeleton (reports column) -->
		<div class="victim-item-container">
			<div class="view-title"><span class="view-item-title">Summary</span></div>
			<div class="summary-card">
				<div class="summary-card-body">
					<Skeleton variant="text-block" lines={4} />
				</div>
			</div>

			<div class="view-title">
				<span class="view-item-title">Reports</span>
			</div>
			<Skeleton variant="rect" height="3.5rem" />
			<Skeleton variant="rect" height="3.5rem" />

			<div class="view-title"><span class="view-item-title">Media</span></div>
			<div class="media-list">
				<Skeleton variant="rect" height="6rem" />
			</div>
		</div>

		<!-- Sidebar skeleton -->
		<div class="sidebar-container">
			<div class="sidebar-top">
				<div class="sidebar-header-2">
					<p>
						<Skeleton variant="text" width="60%" height="1rem" />
					</p>
				</div>
				<div class="sidebar-pic">
					<Skeleton variant="circle" width="180px" height="180px" />
				</div>
				<div class="sidebar-content">
					<Skeleton variant="text" width="40%" />
					<div class="sidebar-status">
						<Skeleton variant="badge" width="6rem" height="1.5rem" />
					</div>
					<Skeleton variant="text-block" lines={6} />
				</div>
			</div>
			<div class="meta-card">
				<div class="meta-card-header"><p>Details</p></div>
				<div class="meta-card-body">
					<Skeleton variant="text-block" lines={3} />
				</div>
			</div>
		</div>
	</div>
{:else if error}
	<div class="error-state" role="alert">
		<p class="error-state-message">Could not load this case: {error}</p>
		<button type="button" class="btn btn-secondary" onclick={loadPerson}>Retry</button>
	</div>
{:else if person}
	<div class="view-container">
		<!-- Main content (reports, media) -->
		<div class="victim-item-container">
			{#if person.summary_narrative}
				<div class="view-title">
					<span class="view-item-title">Summary</span>
				</div>
				<div class="summary-card">
					<div class="summary-card-body">
						<div class="summary-narrative">
							{#each paragraphs(person.summary_narrative) as para, i (i)}
								<p>
									{#each scanNarrativeDates(para) as part, j (j)}
										{#if part.kind === 'date'}
											<strong class="summary-date">{part.value}</strong>
										{:else}
											{part.value}
										{/if}
									{/each}
								</p>
							{/each}
						</div>
					</div>
					{#if person.authoritative_source}
						<div class="summary-footer">
							<span>Source:</span>
							{#if person.authoritative_url}
								<a
									href={person.authoritative_url}
									target="_blank"
									rel="noopener noreferrer"
									class="summary-footer-link"
								>
									<span>{person.authoritative_source}</span>
									<span class="summary-footer-icon" aria-hidden="true">↗</span>
								</a>
							{:else}
								<span>{person.authoritative_source}</span>
							{/if}
						</div>
					{/if}
				</div>
			{/if}

			<div class="view-title">
				<span class="view-item-title">Reports ({person.reports?.length || 0})</span>
				{#if isVolunteer(currentUser)}
					<a
						href="{base}/persons/{person.id}/report"
						class="btn"
						style="padding:5px 10px;font-size:0.8rem;">Add Report</a
					>
				{/if}
			</div>
			{#if person.reports && person.reports.length > 0}
				{#each person.reports as report (report.id)}
					{@const open = expandedId === report.id}
					{@const title = report.source_attribution || sourceTypeLabels[report.source_type] || 'Report'}
					<div class="incident-container">
						<div class="report-card-header">
							<button
								type="button"
								class="report-card-toggle"
								aria-expanded={open}
								aria-controls="report-body-{report.id}"
								onclick={() => (expandedId = open ? null : report.id)}
							>
								<span class="badge badge-source-{report.source_type}">
									{sourceTypeLabels[report.source_type] || report.source_type}
								</span>
								<span class="report-card-title">{title}</span>
								<span class="report-card-date small muted">
									{#if report.date_start}
										{report.date_start}{#if report.date_end} — {report.date_end}{/if}
									{:else}
										{new Date(report.created_at).toLocaleDateString()}
									{/if}
								</span>
								<span class="report-card-chevron" class:open aria-hidden="true">▸</span>
							</button>
							{#if isVolunteer(currentUser)}
								<div class="report-card-actions" role="group" aria-label="Report actions">
									<a
										href="{base}/persons/{person.id}/report?id={report.id}"
										class="row-action"
										aria-label="Edit report: {title}"
										title="Edit"
									>
										<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
											<path
												fill="currentColor"
												d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"
											/>
										</svg>
									</a>
									<button
										type="button"
										class="row-action row-action-danger"
										aria-label="Delete report: {title}"
										title="Delete"
										onclick={() => startReportDelete(report)}
									>
										<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
											<path
												fill="currentColor"
												d="M6 19a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"
											/>
										</svg>
									</button>
								</div>
							{/if}
						</div>
						{#if open}
							<div id="report-body-{report.id}" class="report-card-body">
								{#if report.rough_location}
									<p class="small muted">Location: {report.rough_location}</p>
								{/if}
								<p class="report-card-narrative">
									{#each scanNarrative(report.narrative) as part, i (i)}
										{#if part.kind === 'url'}
											<a
												href={normalizeUrl(part.value)}
												target="_blank"
												rel="noopener noreferrer"
												class="report-link-btn"
												title={part.value}
											>
												<span>{domainOf(part.value)}</span>
												<span class="report-link-icon" aria-hidden="true">↗</span>
											</a>
										{:else}
											{part.value}
										{/if}
									{/each}
								</p>
								{#if report.suspected_reason}
									<p class="mt-1"><strong>Suspected reason:</strong> {report.suspected_reason}</p>
								{/if}
								{#if report.official_reason}
									<p class="mt-1"><strong>Official reason:</strong> {report.official_reason}</p>
								{/if}
								{#if report.media_files && report.media_files.length > 0}
									<div class="report-card-media">
										{#each report.media_files as media (media.id)}
											{#if media.url}
												<a
													href={media.url}
													target="_blank"
													rel="noopener noreferrer"
													class="report-link-btn"
													title={media.description || media.url}
												>
													<span>{domainOf(media.url)}</span>
													<span class="report-link-icon" aria-hidden="true">↗</span>
												</a>
											{/if}
										{/each}
									</div>
								{/if}
							</div>
						{/if}
					</div>
				{/each}
			{:else}
				<p class="muted mt-1">No reports yet.</p>
			{/if}

			<div class="view-title media-section-header">
				<div class="media-section-header-text">
					<svg class="media-section-icon" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
						<path
							fill="currentColor"
							d="M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6zm2 0v.4l1.6-.9 2.4 1.6 4.8-3 3.2 2V6H6zm12 2.7-3.2-2-4.8 3-2.4-1.6L6 9.4V18h12V8.7zM10 13a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z"
						/>
					</svg>
					<span class="view-item-title">Media</span>
					{#if mediaList.length > 0}
						<span class="media-section-count" aria-label="{mediaList.length} items">
							{mediaList.length}
						</span>
					{/if}
				</div>
				{#if isVolunteer(currentUser) && person}
					<button
						type="button"
						class="btn btn-secondary btn-sm media-add-btn"
						onclick={openUpload}
					>
						<svg class="media-add-btn-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
							<path fill="currentColor" d="M8 2a.5.5 0 0 1 .5.5v5h5a.5.5 0 0 1 0 1h-5v5a.5.5 0 0 1-1 0v-5h-5a.5.5 0 0 1 0-1h5v-5A.5.5 0 0 1 8 2z" />
						</svg>
						Add media
					</button>
				{/if}
			</div>

			{#if loadingMedia}
				<div class="media-skeleton">
					<Skeleton variant="card" />
					<Skeleton variant="card" />
				</div>
			{:else if mediaError}
				<div class="media-error" role="alert">
					<p>{mediaError}</p>
					<button type="button" class="btn btn-secondary btn-sm" onclick={() => loadMedia()}>Retry</button>
				</div>
			{:else if mediaList.length === 0}
				<div class="media-empty">
					<p class="muted">
						{isVolunteer(currentUser)
							? 'No media attached yet. Click "+ Add media" to upload a file or link an external source.'
							: 'No media attached yet.'}
					</p>
				</div>
			{:else}
				<div class="media-list fade-in-stagger">
					{#each mediaList as media (media.id)}
						<div class="media-item-card">
							{#if media.media_type === 'photo' && media.file}
								<img
									src={media.file}
									alt={media.description || 'Photo'}
									class="media-item-thumb"
								/>
							{/if}
							<div class="media-item-body">
								<div class="media-item-meta">
									<span class="media-item-type media-type-{media.media_type}">
										{mediaTypeLabels[media.media_type] || media.media_type}
									</span>
									<span class="media-item-visibility visibility-{media.visibility}">
										{visibilityLabels[media.visibility] || media.visibility}
									</span>
								</div>
								{#if media.description}
									<p class="media-item-description">{media.description}</p>
								{/if}
								{#if media.url}
									<a
										href={media.url}
										target="_blank"
										rel="noopener noreferrer"
										class="media-item-action"
									>
										<span>View source</span>
										<span class="media-item-action-icon" aria-hidden="true">↗</span>
									</a>
								{/if}
								{#if isVolunteer(currentUser)}
									<div class="media-item-actions">
										<button
											type="button"
											class="row-action"
											aria-label="Edit {media.description || mediaTypeLabels[media.media_type]}"
											title="Edit"
											onclick={() => openEdit(media)}
										>
											<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
												<path
													fill="currentColor"
													d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"
												/>
											</svg>
										</button>
										<button
											type="button"
											class="row-action row-action-danger"
											aria-label="Delete {media.description || mediaTypeLabels[media.media_type]}"
											title="Delete"
											onclick={() => startDelete(media)}
										>
											<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
												<path
													fill="currentColor"
													d="M6 19a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"
												/>
											</svg>
										</button>
									</div>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Sidebar -->
		<div class="sidebar-container">
			{#if isVolunteer(currentUser)}
				<!--
					Action group: Edit and Delete are siblings inside a flex
					container — never nest a <button> inside an <a> (HTML
					forbids interactive descendants, and it triggers an a11y
					warning under Svelte's a11y rules). This mirrors the
					sibling pattern in `.report-card-header` above.
				-->
				<div class="mb-1 sidebar-actions">
					<a
						href="{base}/persons/{person.id}/edit"
						class="btn btn-primary sidebar-actions-edit">Edit Case</a
					>
					<button
						type="button"
						class="btn btn-danger sidebar-actions-delete"
						onclick={startPersonDelete}
					>Delete Case</button>
				</div>
			{/if}
			<div class="sidebar-top">
				<div class="sidebar-header-2">
					<p><strong>{person.name}</strong></p>
				</div>
				<div class="sidebar-pic">
					{#if person.profile_image_url}
						<img
							src={person.profile_image_url}
							alt={person.name}
							class="profile-photo"
						/>
					{:else}
						<div class="profile-photo-placeholder"></div>
					{/if}
				</div>
				<div class="sidebar-content">
					{#if person.legal_name}
						<p class="small muted">Legal name: {person.legal_name}</p>
					{/if}
					{#if person.aliases}
						<p class="sidebar-aliases">{person.aliases}</p>
					{/if}
					<div class="sidebar-status">
						<StatusBadge status={person.current_status} />
					</div>
					<dl class="sidebar-fields">
						<div class="sidebar-field">
							<dt>Country</dt>
							<dd>{person.country}</dd>
						</div>
						{#if person.rough_location}
							<div class="sidebar-field">
								<dt>Location</dt>
								<dd>{person.rough_location}</dd>
							</div>
						{/if}
						{#if person.last_known_date}
							<div class="sidebar-field">
								<dt>Last known</dt>
								<dd>{person.last_known_date}</dd>
							</div>
						{/if}
						{#if person.ethnicity}
							<div class="sidebar-field">
								<dt>Ethnicity</dt>
								<dd>{person.ethnicity}</dd>
							</div>
						{/if}
						{#if person.gender}
							<div class="sidebar-field">
								<dt>Gender</dt>
								<dd>{person.gender}</dd>
							</div>
						{/if}
						{#if person.date_of_birth}
							<div class="sidebar-field">
								<dt>DOB</dt>
								<dd>{person.date_of_birth}</dd>
							</div>
						{/if}
						{#if medicalLabels[person.medical_status] !== 'Deceased'}
							<div class="sidebar-field">
								<dt>Medical</dt>
								<dd>{medicalLabels[person.medical_status] || person.medical_status}</dd>
							</div>
						{/if}
					</dl>
					{#if person.authoritative_source}
						<div class="sidebar-source">
							<span class="sidebar-source-label">Source</span>
							{#if person.authoritative_url}
								<a
									href={person.authoritative_url}
									target="_blank"
									rel="noopener noreferrer"
									class="sidebar-source-link"
								>
									<span>{person.authoritative_source}</span>
									<span class="sidebar-source-icon" aria-hidden="true">↗</span>
								</a>
							{:else}
								<span>{person.authoritative_source}</span>
							{/if}
						</div>
					{/if}
				</div>
			</div>

			{#if person.categories && person.categories.length > 0}
				<div class="meta-card">
					<div class="meta-card-body">
						<h3 class="meta-section-title">Categories</h3>
						<ul class="meta-list">
							{#each person.categories as cat (cat.id)}
								<li>{cat.name}</li>
							{/each}
						</ul>
					</div>
				</div>
			{/if}

			{#if person.quality_tier}
				<div class="meta-card">
					<div class="meta-card-body">
						<h3 class="meta-section-title">Evidence Tier</h3>
						<p class="meta-tier">{person.quality_tier}</p>
					</div>
				</div>
			{/if}

			{#if loadingRelationships || relationships.length > 0 || isVolunteer(currentUser)}
				<div class="meta-card">
					<div class="meta-card-body">
						<div class="family-header">
							<h3 class="meta-section-title">Family</h3>
							{#if isVolunteer(currentUser)}
								<button
									type="button"
									class="row-action row-action-add"
									aria-label="Add family relationship"
									title="Add family relationship"
									onclick={startRelCreate}
								>
									<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
										<path fill="currentColor" d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" />
									</svg>
								</button>
							{/if}
						</div>
						{#if relationshipError}
							<div class="form-error" role="alert">
								<span class="form-error-icon" aria-hidden="true">!</span>
								<span>{relationshipError}</span>
							</div>
						{/if}
						{#if loadingRelationships}
							<Skeleton variant="text" width="80%" />
							<Skeleton variant="text" width="60%" />
						{:else if relationships.length === 0}
							<p class="muted meta-empty">No family links yet.</p>
						{:else}
							<ul class="meta-family-list">
								{#each relationships as rel (rel.id)}
									{@const other = otherPerson(rel)}
									<li class="meta-family-row">
										<a href="{base}/persons/{other.id}" class="meta-family-name">
											{other.name}
										</a>
										<span class="muted meta-family-type">
											{RELATIONSHIP_TYPE_LABELS[rel.relationship_type] ?? rel.relationship_type}
										</span>
										{#if isVolunteer(currentUser)}
											<span class="meta-family-actions" role="group" aria-label="Relationship actions">
												<button
													type="button"
													class="row-action"
													aria-label="Edit relationship with {other.name}"
													title="Edit"
													onclick={() => startRelEdit(rel)}
												>
													<svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true">
														<path
															fill="currentColor"
															d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"
														/>
													</svg>
												</button>
												<button
													type="button"
													class="row-action row-action-danger"
													aria-label="Delete relationship with {other.name}"
													title="Delete"
													onclick={() => startRelDelete(rel)}
												>
													<svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true">
														<path
															fill="currentColor"
															d="M6 19a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"
														/>
													</svg>
												</button>
											</span>
										{/if}
									</li>
								{/each}
							</ul>
						{/if}
					</div>
				</div>
			{/if}

			<div class="meta-card">
				<div class="meta-card-body">
					<div class="meta-row">
						<span class="meta-label">Created</span>
						<span class="meta-value">{new Date(person.created_at).toLocaleDateString()}</span>
					</div>
					<div class="meta-row">
						<span class="meta-label">Updated</span>
						<span class="meta-value">{new Date(person.updated_at).toLocaleDateString()}</span>
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}

<!-- Media upload / edit modal -->
<MediaUploadModal
	open={uploadOpen}
	media={editTarget}
	personId={person?.id}
	hidePerson={true}
	canMarkSensitive={canMarkSensitive}
	onSaved={onMediaSaved}
	onClose={() => (uploadOpen = false)}
/>

<!-- Delete media confirm dialog -->
{#if deleteTarget}
	{@const mediaTarget = deleteTarget}
	<ConfirmModal
		open
		stage={deleting ? 'pending' : 'confirming'}
		title="Delete media?"
		body=""
		destructive
		onConfirm={confirmDelete}
		onCancel={cancelDelete}
	>
		{#snippet bodyContent()}
			<div class="confirm-rich-body">
				{#if deleteError}
					<div class="form-error" role="alert">
						<span class="form-error-icon" aria-hidden="true">!</span>
						<span>{deleteError}</span>
					</div>
				{/if}
				<p>
					This will permanently delete
					<strong>{mediaTarget.description || mediaTypeLabels[mediaTarget.media_type] || 'this media item'}</strong>.
					It cannot be recovered.
				</p>
			</div>
		{/snippet}
	</ConfirmModal>
{/if}

<!-- Delete report confirm dialog — mirrors the media dialog but warns
     about the Media FK cascade (cases/models.py: Media.report CASCADE). -->
{#if reportDeleteTarget}
	{@const reportTarget = reportDeleteTarget}
	<ConfirmModal
		open
		stage={reportDeleting ? 'pending' : 'confirming'}
		title="Delete report?"
		body=""
		destructive
		onConfirm={confirmReportDelete}
		onCancel={cancelReportDelete}
	>
		{#snippet bodyContent()}
			<div class="confirm-rich-body">
				{#if reportDeleteError}
					<div class="form-error" role="alert">
						<span class="form-error-icon" aria-hidden="true">!</span>
						<span>{reportDeleteError}</span>
					</div>
				{/if}
				<p>
					This will permanently delete
					<strong>{reportTarget.source_attribution || sourceTypeLabels[reportTarget.source_type] || 'this report'}</strong>
					<strong>and any media attached to it</strong>. It cannot be recovered.
				</p>
			</div>
		{/snippet}
	</ConfirmModal>
{/if}

<!-- Delete case confirm dialog — sibling to the report / media dialogs.
     Warns the volunteer that the entire case (reports, media, family
     links) will be cascaded away. On success we redirect to the catalog
     with `?deleted=1`, which surfaces a transient banner there. -->
{#if personDeleteOpen && person}
	{@const targetPerson = person}
	<ConfirmModal
		open
		stage={personDeleting ? 'pending' : 'confirming'}
		title="Delete case?"
		body=""
		destructive
		onConfirm={confirmPersonDelete}
		onCancel={cancelPersonDelete}
	>
		{#snippet bodyContent()}
			<div class="confirm-rich-body">
				{#if personDeleteError}
					<div class="form-error" role="alert">
						<span class="form-error-icon" aria-hidden="true">!</span>
						<span>{personDeleteError}</span>
					</div>
				{/if}
				<p>
					This will permanently delete
					<strong>{targetPerson.name}</strong>
					and <strong>every report, piece of media, and family link</strong>
					attached to this case. It cannot be recovered.
				</p>
			</div>
		{/snippet}
	</ConfirmModal>
{/if}

<!-- Family relationship create / edit modal -->
{#if relationshipFormOpen && person}
	<div class="modal-overlay" onclick={cancelRelForm} role="presentation"></div>
	<div class="modal" role="dialog" aria-modal="true" aria-labelledby="rel-form-title">
		<header class="modal-header">
			<h2 id="rel-form-title">
				{editingRel ? 'Edit family link' : 'Add family link'}
			</h2>
			<button
				type="button"
				class="modal-close"
				aria-label="Close"
				onclick={cancelRelForm}
				disabled={relationshipSaving}
			>×</button>
		</header>
		<div class="modal-body">
			{#if relationshipFormError}
				<div class="form-error" role="alert">
					<span class="form-error-icon" aria-hidden="true">!</span>
					<span>{relationshipFormError}</span>
				</div>
			{/if}
			<p class="muted small">
				Linking <strong>{person.name}</strong>
				{#if editingRel}
					{@const other = otherPerson(editingRel)}
					to <strong>{other.name}</strong>.
				{:else}
					to another person on the platform.
				{/if}
			</p>
			{#if !editingRel}
				<label class="form-field" for="rel-other">
					<span class="form-label">Person</span>
					<select
						id="rel-other"
						class="form-select"
						bind:value={relationshipFormOtherId}
						disabled={relationshipSaving}
					>
						<option value="" disabled>Pick a person…</option>
						{#each relationshipPickerList as p (p.id)}
							{#if p.id !== person.id}
								<option value={p.id}>{p.name} — {p.country}</option>
							{/if}
						{/each}
					</select>
				</label>
			{/if}
			<label class="form-field" for="rel-type">
				<span class="form-label">Relationship</span>
				<select
					id="rel-type"
					class="form-select"
					bind:value={relationshipFormType}
					disabled={relationshipSaving}
				>
					{#each Object.entries(RELATIONSHIP_TYPE_LABELS) as [value, label] (value)}
						<option {value}>{label}</option>
					{/each}
				</select>
			</label>
			<label class="form-field" for="rel-notes">
				<span class="form-label">Notes <span class="muted">(optional)</span></span>
				<textarea
					id="rel-notes"
					class="form-textarea"
					bind:value={relationshipFormNotes}
					rows="2"
					disabled={relationshipSaving}
				></textarea>
			</label>
			<div class="modal-actions">
				<button type="button" class="btn btn-secondary" onclick={cancelRelForm} disabled={relationshipSaving}>
					Cancel
				</button>
				<button type="button" class="btn btn-primary" onclick={submitRelForm} disabled={relationshipSaving}>
					{relationshipSaving ? 'Saving…' : (editingRel ? 'Save' : 'Add')}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Family relationship delete confirm dialog -->
{#if relationshipDelTarget && person}
	{@const other = otherPerson(relationshipDelTarget)}
	{@const anchorPerson = person}
	<ConfirmModal
		open
		stage={relationshipDeleting ? 'pending' : 'confirming'}
		title="Remove family link?"
		body=""
		confirmLabel="Remove"
		cancelLabel="Cancel"
		destructive
		onConfirm={confirmRelDelete}
		onCancel={cancelRelDelete}
	>
		{#snippet bodyContent()}
			<div class="confirm-rich-body">
				{#if relationshipDeleteError}
					<div class="form-error" role="alert">
						<span class="form-error-icon" aria-hidden="true">!</span>
						<span>{relationshipDeleteError}</span>
					</div>
				{/if}
				<p>
					Remove the link between
					<strong>{anchorPerson.name}</strong> and
					<strong>{other.name}</strong>?
					It cannot be recovered.
				</p>
			</div>
		{/snippet}
	</ConfirmModal>
{/if}

<style>
	/* Responsive grid: 1 column on mobile (sidebar first so the profile card is
	   immediately scannable), 2-column 2:1 split at >=50em. minmax(0, …) tracks
	   are the canonical fix for grid/flex overflow — without them, a long URL,
	   country name, or fixed-width child can push the column past the viewport
	   and produce a horizontal scrollbar. */
	.view-container {
		margin-top: 15px;
		margin-bottom: 15px;
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: 1.5rem;
		overflow-x: clip;
	}
	@media (min-width: 50em) {
		.view-container {
			grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
		}
	}
	.victim-item-container,
	.sidebar-container {
		min-width: 0; /* allow grid item to shrink below its content size */
	}
	.sidebar-top {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		box-shadow: var(--shadow-card);
		position: relative;
		padding-bottom: 10px;
		overflow: hidden; /* clip children to rounded corners */
		min-width: 0;
	}
	.sidebar-bot {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		box-shadow: var(--shadow-card);
		margin-top: 15px;
		overflow: hidden;
		min-width: 0;
	}
	.sidebar-header-2 {
		background-color: var(--color-primary);
		text-align: center;
		padding: 5px;
	}
	.sidebar-header-2 p {
		color: var(--color-text-light);
		margin: 0;
	}
	.sidebar-pic {
		text-align: center;
		padding: 10px;
	}
	.sidebar-content {
		margin-left: 10px;
		margin-right: 10px;
		padding-bottom: 5px;
	}
	.photo-placeholder-sidebar {
		width: 200px;
		height: 200px;
		background: var(--color-bg);
		margin: 0 auto;
		border-radius: 4px;
	}

	/* Profile photo — responsive: capped at 180px on wide screens,
	   shrinks fluidly on narrow viewports so the sidebar never overflows.
	   aspect-ratio keeps the photo square without a fixed pixel height. */
	.profile-photo {
		display: block;
		width: 100%;
		max-width: 180px;
		aspect-ratio: 1 / 1;
		height: auto;
		object-fit: cover;
		margin: 0 auto;
		border-radius: var(--radius-card);
		border: 1px solid var(--color-border-light);
		box-shadow: var(--shadow-card);
	}
	.profile-photo-placeholder {
		width: 100%;
		max-width: 180px;
		aspect-ratio: 1 / 1;
		height: auto;
		background: var(--color-bg);
		margin: 0 auto;
		border-radius: var(--radius-card);
		border: 1px dashed var(--color-border-light);
		box-shadow: var(--shadow-card);
	}

	/* Aliases — differentiated from legal name */
	.sidebar-aliases {
		font-size: 0.75rem;
		font-style: italic;
		color: var(--color-text-muted);
		margin: 0.15rem 0 0 0;
	}

	/* Status badge wrapper — small breathing room */
	.sidebar-status {
		margin: 0.75rem 0 1rem 0;
	}

	/* Field rows — semantic label/value pairs */
	.sidebar-fields {
		margin: 0;
		padding: 0;
	}
	.sidebar-field {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: 0.75rem;
		padding: 0.4rem 0;
		border-bottom: 1px solid var(--color-border-light);
		font-size: 0.88rem;
	}
	.sidebar-field:last-child {
		border-bottom: none;
	}
	.sidebar-field dt {
		font-size: 0.72rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--color-text-muted);
		flex: 0 0 auto;
		min-width: 4.5rem;
	}
	.sidebar-field dd {
		margin: 0;
		text-align: right;
		color: var(--color-text);
		flex: 1 1 auto;
		word-break: break-word;
	}

	/* Source footer — subtle separation from the metadata fields */
	.sidebar-source {
		margin-top: 0.75rem;
		padding-top: 0.6rem;
		border-top: 1px solid var(--color-border-light);
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
		font-size: 0.8rem;
		color: var(--color-text-muted);
	}
	.sidebar-source-label {
		font-size: 0.72rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}
	.sidebar-source-link {
		color: var(--color-primary);
		text-decoration: none;
		display: inline-flex;
		align-items: center;
		gap: 0.2rem;
	}
	.sidebar-source-link:hover {
		text-decoration: underline;
	}
	.sidebar-source-icon {
		font-size: 0.7rem;
		opacity: 0.7;
	}
	/* Media list — vertical stack of polished cards (replaces old grid + .media-card) */
	.media-list {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		margin-top: 10px;
	}
	.media-item-card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		box-shadow: var(--shadow-card);
		padding: var(--card-padding);
		display: flex;
		align-items: flex-start;
		gap: 1.25rem;
		color: var(--color-text);
	}
	.media-item-thumb {
		width: 120px;
		height: 120px;
		object-fit: cover;
		border-radius: 4px;
		flex-shrink: 0;
		border: 1px solid var(--color-border-light);
	}
	.media-item-body {
		flex: 1 1 auto;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		line-height: 1.6;
	}
	.media-item-meta {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
	}
	.media-item-type {
		font-size: 0.72rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--color-text-muted);
	}
	.media-item-visibility {
		font-size: 0.68rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		padding: 0.1rem 0.45rem;
		border-radius: 3px;
		background: var(--color-bg);
		color: var(--color-text-muted);
	}
	.media-item-description {
		margin: 0;
		font-size: 0.92rem;
		color: var(--color-text);
		line-height: 1.6;
		word-break: break-word;
	}
	.media-item-action {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.4rem 0.95rem;
		margin-top: 0.25rem;
		border: 1px solid var(--color-primary);
		border-radius: 999px;
		background: var(--color-primary);
		color: var(--color-text-light);
		font-size: 0.8rem;
		font-weight: 600;
		text-decoration: none;
		align-self: flex-start;
		transition:
			background 0.15s ease,
			border-color 0.15s ease;
	}
	.media-item-action:hover {
		background: var(--color-primary-light);
		border-color: var(--color-primary-light);
	}
	.media-item-action-icon {
		font-size: 0.75rem;
	}

	/* Metadata cards — refined versions of .sidebar-bot for Categories, Evidence Tier, dates */
	.meta-card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		box-shadow: var(--shadow-card);
		margin-top: 15px;
		overflow: hidden;
	}
	.meta-card-header {
		background-color: var(--color-primary);
		color: var(--color-text-light);
		text-align: center;
		padding: 0.55rem 1rem;
		font-size: 0.85rem;
		font-weight: 600;
		letter-spacing: 0.04em;
		text-transform: uppercase;
	}
	.meta-card-header p {
		margin: 0;
	}
	.meta-card-body {
		padding: var(--card-padding);
		color: var(--color-text);
		font-size: 0.92rem;
		line-height: 1.65;
	}
	.meta-card-body p {
		margin: 0;
	}
	.meta-section-title {
		font-size: 0.72rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.05rem;
		color: var(--color-text-muted);
		margin: 0 0 0.6rem 0;
	}
	.meta-list {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.meta-list li {
		padding: 0.4rem 0;
		border-bottom: 1px solid var(--color-border-light);
	}
	.meta-list li:last-child {
		border-bottom: none;
	}
	.meta-tier {
		font-size: 1rem;
		font-weight: 600;
		color: var(--color-primary);
	}
	.meta-family-row {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.35rem 0;
		border-bottom: 1px solid var(--color-border-subtle);
		font-size: 0.88rem;
	}
	.meta-family-row:last-child {
		border-bottom: none;
	}
	.meta-family-name {
		flex: 1 1 auto;
		min-width: 0;
		font-weight: 600;
		color: var(--color-primary);
		text-decoration: none;
	}
	.meta-family-name:hover {
		text-decoration: underline;
	}
	.meta-family-type {
		flex: 0 0 auto;
		font-size: 0.78rem;
	}
	.meta-family-actions {
		flex: 0 0 auto;
		display: inline-flex;
		gap: 0.3rem;
	}
	.meta-family-list {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.meta-empty {
		margin: 0.3rem 0 0 0;
		font-size: 0.86rem;
	}
	.family-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
	}
	.row-action-add {
		color: var(--color-primary);
	}
	/* Form fields inside the relationship modal — reusable label/input
	   pair styling consistent with other modals in the app. */
	.form-field {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}
	.form-label {
		font-size: 0.72rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		color: var(--color-text-muted);
	}
	.form-select,
	.form-textarea {
		font: inherit;
		padding: 0.5rem 0.65rem;
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		background: var(--color-bg-white);
		color: var(--color-text);
		width: 100%;
		box-sizing: border-box;
	}
	.form-select:focus-visible,
	.form-textarea:focus-visible {
		outline: 2px solid var(--color-primary);
		outline-offset: 1px;
		border-color: var(--color-primary);
	}
	.form-textarea {
		resize: vertical;
		min-height: 3rem;
	}
	.meta-row {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: 0.75rem;
		padding: 0.4rem 0;
		border-bottom: 1px solid var(--color-border-light);
		font-size: 0.88rem;
	}
	.meta-row:last-child {
		border-bottom: none;
	}
	.meta-row .meta-label {
		font-size: 0.72rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--color-text-muted);
		flex: 0 0 auto;
		min-width: 4.5rem;
	}
	.meta-row .meta-value {
		text-align: right;
		color: var(--color-text);
		flex: 1 1 auto;
		word-break: break-word;
	}

	.error-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
		padding: 3rem 1rem;
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-left: 3px solid var(--color-danger);
		border-radius: var(--radius-card);
		text-align: center;
		max-width: var(--max-w-prose);
		margin: 2rem auto;
	}
	.error-state-message {
		margin: 0;
		color: var(--color-text-muted);
	}

	/* === Reports: collapsible card with edit / delete row actions ===
	   The header is a flex container holding a full-width toggle button
	   (left) and a small action group (right). Restructured from a
	   single <button> to a div+button so we can nest anchor/button
	   siblings without violating the "no nested interactive elements"
	   rule. The .incident-container provides the card chrome. */
	.report-card-header {
		display: flex;
		align-items: stretch;
		gap: 0.25rem;
	}
	.report-card-toggle {
		flex: 1 1 auto;
		min-width: 0;
		display: flex;
		align-items: center;
		gap: 0.6rem;
		padding: 0;
		background: transparent;
		border: none;
		text-align: left;
		cursor: pointer;
		color: inherit;
		font: inherit;
	}
	.report-card-toggle:focus-visible {
		outline: 2px solid var(--color-primary);
		outline-offset: 2px;
		border-radius: var(--radius-card);
	}
	.report-card-actions {
		display: flex;
		gap: 0.4rem;
		align-items: center;
		flex: 0 0 auto;
		padding-left: 0.5rem;
	}
	.report-card-chevron {
		display: inline-block;
		font-size: 0.85rem;
		color: var(--color-text-muted);
		transition: transform 0.15s ease;
	}
	.report-card-chevron.open {
		transform: rotate(90deg);
	}

	/* === Media section: interactive gallery with edit / delete === */
	.media-section-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.85rem;
		/* Override .view-title's `border-bottom: 1px solid black` (legacy bug)
		   so the header bar reads as one continuous primary surface. */
		border-bottom: 1px solid var(--color-primary-light);
		padding: 0.55rem 0.85rem;
	}
	.media-section-header-text {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
	}
	.media-section-icon {
		color: var(--color-text-light);
		opacity: 0.92;
		flex-shrink: 0;
	}
	.media-section-count {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 22px;
		height: 22px;
		padding: 0 0.5rem;
		border-radius: 999px;
		background: var(--color-text-light);
		color: var(--color-primary);
		font-size: 0.74rem;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		line-height: 1;
	}

	/* Add media button — secondary on the dark header surface. Subtle hover
	   lift + icon scale for tactile feedback. */
	.media-add-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		transition:
			transform 0.15s ease,
			box-shadow 0.15s ease,
			background 0.15s ease,
			border-color 0.15s ease;
	}
	.media-add-btn:hover {
		transform: translateY(-1px);
		box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
	}
	.media-add-btn:active {
		transform: translateY(0);
	}
	.media-add-btn-icon {
		transition: transform 0.15s ease;
	}
	.media-add-btn:hover .media-add-btn-icon {
		transform: scale(1.15);
	}

	.media-skeleton {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	.media-empty {
		padding: 0.5rem 0;
	}
	.media-empty .muted {
		font-size: 0.9rem;
		margin: 0;
	}
	.media-error {
		padding: 0.6rem 0.85rem;
		background: #fed7d7;
		color: #c53030;
		border: 1px solid #feb2b2;
		border-radius: var(--radius-card);
		font-size: 0.88rem;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	.media-error p { margin: 0; flex: 1 1 auto; }

	/* Type + visibility pills inside the existing media-item-card layout */
	.media-item-type {
		display: inline-flex;
		align-items: center;
		padding: 0.15rem 0.55rem;
		border-radius: 999px;
		background: var(--color-surface);
		color: var(--color-primary);
		border: 1px solid var(--color-border-light);
		font-weight: 700;
		text-transform: capitalize;
		letter-spacing: 0.06rem;
		line-height: 1.2;
		box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.04);
	}
	.media-item-visibility {
		padding: 0.2rem 0.6rem;
		border-radius: 999px;
		font-size: 0.72rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		line-height: 1.2;
		box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.04);
	}
	.media-item-visibility.visibility-public {
		background: #c6f6d5;
		color: #22543d;
	}
	.media-item-visibility.visibility-restricted {
		background: #fefcbf;
		color: #744210;
	}
	.media-item-visibility.visibility-sensitive {
		background: #fed7d7;
		color: #742a2a;
	}

	/* Card hover — subtle lift to invite interaction */
	.media-item-card {
		transition:
			box-shadow 0.15s ease,
			border-color 0.15s ease;
	}
	.media-item-card:hover {
		box-shadow: var(--shadow-card-hover);
		border-color: var(--color-primary-light);
	}

	/* Action group — soft top divider gives the buttons visual weight */
	.media-item-actions {
		display: flex;
		gap: 0.5rem;
		margin-top: 0.6rem;
		padding-top: 0.6rem;
		border-top: 1px solid var(--color-border-subtle);
		justify-content: flex-end;
	}

	/* Row actions (Edit / Delete) — `.row-action` is scoped to /contacts/+page.svelte
	   so we re-define it here for this page. Always-visible subtle surface;
	   primary tint on hover; distinct danger variant for delete. */
	.row-action {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		border-radius: var(--radius-card);
		background: var(--color-surface);
		border: 1px solid var(--color-border-light);
		color: var(--color-primary);
		cursor: pointer;
		padding: 0;
		transition:
			background 0.15s ease,
			color 0.15s ease,
			border-color 0.15s ease,
			box-shadow 0.15s ease;
	}
	.row-action:hover {
		background: var(--color-primary-tint);
		color: var(--color-primary);
		border-color: var(--color-primary-light);
		box-shadow: var(--focus-ring);
	}
	.row-action:focus-visible {
		outline: 2px solid var(--color-primary);
		outline-offset: 2px;
	}
	.row-action-danger {
		color: var(--color-danger);
	}
	.row-action-danger:hover {
		background: rgba(217, 22, 22, 0.12);
		color: var(--color-danger);
		border-color: var(--color-danger);
		box-shadow: 0 0 0 3px rgba(217, 22, 22, 0.18);
	}

	@media (prefers-reduced-motion: reduce) {
		.media-item-card,
		.media-add-btn,
		.row-action,
		.media-add-btn-icon {
			transition: none;
		}
	}

	/* Sidebar action group — Edit (anchor) + Delete (button) as siblings
	   inside a flex column. Edit keeps its full-width primary look;
	   Delete sits below as a secondary-feeling danger action (smaller
	   padding) so the two don't compete visually. */
	.sidebar-actions {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	.sidebar-actions-edit {
		display: block;
		text-align: center;
		width: 100%;
	}
	.sidebar-actions-delete {
		width: 100%;
		font-size: 0.88rem;
		padding: 0.55rem 0.85rem;
	}

	/* Modal — shared styles used by both MediaUploadModal (mounted) and
	   the inline delete-confirm dialog. Lives in this page's scope because
	   the modal is only used here today; if a second page starts using
	   modals, lift these to app.css. */
	.modal-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.45);
		backdrop-filter: blur(2px);
		-webkit-backdrop-filter: blur(2px);
		z-index: 80;
	}
	.modal {
		position: fixed;
		top: 1.25rem;
		left: 50%;
		transform: translateX(-50%);
		width: calc(100% - 2rem);
		max-width: 540px;
		max-height: calc(100vh - 2.5rem);
		overflow-y: auto;
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-left: 3px solid var(--color-danger);
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-card-lg);
		z-index: 90;
		display: flex;
		flex-direction: column;
	}
	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1rem 1.25rem;
		border-bottom: 1px solid var(--color-border-subtle);
	}
	.modal-header h2 {
		margin: 0;
		font-size: 1.1rem;
		font-weight: 700;
		color: var(--color-text);
	}
	.modal-close {
		background: transparent;
		border: none;
		color: var(--color-text-muted);
		font-size: 1.4rem;
		line-height: 1;
		padding: 0 0.25rem;
		cursor: pointer;
	}
	.modal-close:hover { color: var(--color-text); }
	.modal-close:disabled { opacity: 0.5; cursor: not-allowed; }

	.modal-body {
		padding: 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 0.85rem;
	}

	.modal-actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.75rem;
		padding-top: 0.5rem;
		border-top: 1px solid var(--color-border-subtle);
	}
	.modal-actions .btn { min-width: 120px; }
	.modal-actions .btn:disabled { opacity: 0.6; cursor: not-allowed; }

	.form-error {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.6rem 0.85rem;
		background: #fed7d7;
		color: #c53030;
		border: 1px solid #feb2b2;
		border-radius: var(--radius-card);
		font-size: 0.88rem;
	}
	.form-error-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 20px;
		height: 20px;
		border-radius: 50%;
		background: rgba(197, 48, 48, 0.2);
		font-weight: 700;
		font-size: 0.85rem;
	}

	.btn-sm {
		padding: 0.4rem 0.85rem;
		font-size: 0.82rem;
	}
	.btn-danger {
		background: var(--color-danger);
		color: var(--color-text-light);
	}
	.btn-danger:hover { background: #b71212; color: var(--color-text-light); }
</style>
