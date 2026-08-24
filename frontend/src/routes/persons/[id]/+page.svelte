<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { getPerson } from '$lib/api';
	import { user, isVolunteer } from '$lib/session';
	import StatusBadge from '$lib/StatusBadge.svelte';

	// Source-type display labels (mirror backend Report.SourceType.choices)
	const sourceTypeLabels: Record<string, string> = {
		firsthand: 'Firsthand',
		secondhand: 'Secondhand',
		news: 'News',
		document: 'Document',
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
		'gi'
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

	let person: any = $state(null);
	let loading = $state(true);
	let error = $state('');
	let expandedId: number | null = $state(null);
	let currentUser = $derived($user);

	const medicalLabels: Record<string, string> = {
		unknown: 'Unknown',
		healthy: 'Healthy',
		health_concerns: 'Health Concerns',
		critical: 'Critical',
		deceased: 'Deceased',
	};

	onMount(async () => {
		try {
			person = await getPerson(page.params.id);
		} catch (e: any) {
			error = e.message;
		}
		loading = false;
	});
</script>

<svelte:head>
	<title>{person ? person.name : 'Loading...'} — Testimonies.world</title>
</svelte:head>

{#if loading}
	<p class="muted">Loading...</p>
{:else if error}
	<p class="muted">Error: {error}</p>
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
					<a href="{base}/persons/{person.id}/report" class="btn" style="padding:5px 10px;font-size:0.8rem;">Add Report</a>
				{/if}
			</div>
			{#if person.reports?.length > 0}
				{#each person.reports as report (report.id)}
					{@const open = expandedId === report.id}
					{@const title = report.source_attribution || sourceTypeLabels[report.source_type] || 'Report'}
					<div class="incident-container">
						<button
							type="button"
							class="report-card-header"
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
								{#if report.media_files?.length > 0}
									<div class="report-card-media">
										{#each report.media_files as media}
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

			{#if person.media_files?.length > 0}
				<div class="view-title">
					<span class="view-item-title">Media</span>
				</div>
				<div class="media-grid mt-1">
					{#each person.media_files as media}
						<div class="incident-container">
							{#if media.media_type === 'photo' && media.file}
								<img src={media.file} alt={media.description || 'Photo'} class="photo" />
							{:else if media.url}
								<a href={media.url} target="_blank" rel="noopener">{media.description || media.url}</a>
							{/if}
							{#if media.description}
								<p class="small muted mt-1">{media.description}</p>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Sidebar -->
		<div class="sidebar-container">
			{#if isVolunteer(currentUser)}
				<div class="mb-1">
					<a href="{base}/persons/{person.id}/edit" class="btn btn-primary" style="width:100%;text-align:center;display:block;">Edit Case</a>
				</div>
			{/if}
			<div class="sidebar-top">
				<div class="sidebar-header-2">
					<p><strong>{person.name}</strong></p>
				</div>
				<div class="sidebar-pic">
					{#if person.profile_image_url}
						<img src={person.profile_image_url} alt={person.name} class="profile-photo" />
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
								<a href={person.authoritative_url} target="_blank" rel="noopener noreferrer" class="sidebar-source-link">
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

			{#if person.categories?.length > 0}
				<div class="meta-card">
					<div class="meta-card-header">
						<p>Categories</p>
					</div>
					<div class="meta-card-body">
						<ul class="meta-list">
							{#each person.categories as cat}
								<li>{cat.name}</li>
							{/each}
						</ul>
					</div>
				</div>
			{/if}

			{#if person.quality_tier}
				<div class="meta-card">
					<div class="meta-card-header">
						<p>Evidence Tier</p>
					</div>
					<div class="meta-card-body">
						<p class="meta-tier">{person.quality_tier}</p>
					</div>
				</div>
			{/if}

			{#if person.family?.length > 0}
				<div class="sidebar-bot">
					<div class="sidebar-header-2">
						<p><strong>Family</strong></p>
					</div>
					<div class="sidebar-content">
						{#each person.family as rel}
							<p class="small">
								<a href="{base}/persons/{rel.person_id}">{rel.person_name}</a>
								<span class="muted">({rel.relationship})</span>
							</p>
						{/each}
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

<style>
	.view-container {
		margin-top: 15px;
		margin-bottom: 15px;
		display: flex;
		flex-direction: column-reverse;
		justify-content: space-around;
	}
	@media all and (min-width: 50em) {
		.view-container {
			flex-direction: row;
		}
	}
	.victim-item-container {
		flex-basis: 60%;
		margin-right: 1em;
	}
	.sidebar-container {
		flex-basis: 30%;
	}
	.sidebar-top {
		border: thin solid black;
		border-radius: 4px;
		position: relative;
		padding-bottom: 10px;
	}
	.sidebar-bot {
		border: thin solid black;
		border-radius: 4px;
		margin-top: 15px;
	}
	.sidebar-header-2 {
		background-color: #25646a;
		text-align: center;
		padding: 5px;
	}
	.sidebar-header-2 p {
		color: #fafafa;
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

	/* Profile photo */
	.profile-photo {
		display: block;
		width: 180px;
		height: 180px;
		object-fit: cover;
		margin: 0 auto;
		border-radius: 8px;
		border: 1px solid var(--color-border-light);
	}
	.profile-photo-placeholder {
		width: 180px;
		height: 180px;
		background: var(--color-bg);
		margin: 0 auto;
		border-radius: 8px;
		border: 1px dashed var(--color-border-light);
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
		min-width: 5.5rem;
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
	.media-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
		gap: 1rem;
	}

	/* Metadata cards — refined versions of .sidebar-bot for Categories, Evidence Tier, dates */
	.meta-card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: 6px;
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
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
		padding: 1.25rem 1.5rem;
		color: var(--color-text);
		font-size: 0.92rem;
		line-height: 1.65;
	}
	.meta-card-body p {
		margin: 0;
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
		min-width: 5.5rem;
	}
	.meta-row .meta-value {
		text-align: right;
		color: var(--color-text);
		flex: 1 1 auto;
		word-break: break-word;
	}
</style>
