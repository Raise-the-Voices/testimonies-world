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
				<div class="incident-container">
					<p class="white-space-pre-line">{person.summary_narrative}</p>
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
						<img src={person.profile_image_url} alt={person.name} class="photo" />
					{:else}
						<div class="photo-placeholder-sidebar"></div>
					{/if}
				</div>
				<div class="sidebar-content">
					{#if person.legal_name}
						<p class="small muted">Legal name: {person.legal_name}</p>
					{/if}
					{#if person.aliases}
						<p class="small muted">Aliases: {person.aliases}</p>
					{/if}
					<div class="mt-1">
						<StatusBadge status={person.current_status} />
					</div>
					<p class="small mt-1"><strong>Country:</strong> {person.country}</p>
					{#if person.rough_location}
						<p class="small"><strong>Location:</strong> {person.rough_location}</p>
					{/if}
					{#if person.last_known_date}
						<p class="small"><strong>Last known:</strong> {person.last_known_date}</p>
					{/if}
					{#if person.ethnicity}
						<p class="small"><strong>Ethnicity:</strong> {person.ethnicity}</p>
					{/if}
					{#if person.gender}
						<p class="small"><strong>Gender:</strong> {person.gender}</p>
					{/if}
					{#if person.date_of_birth}
						<p class="small"><strong>DOB:</strong> {person.date_of_birth}</p>
					{/if}
					<p class="small mt-1"><strong>Medical:</strong> {medicalLabels[person.medical_status] || person.medical_status}</p>
					{#if person.authoritative_source}
						<p class="small mt-1"><strong>Source:</strong>
							{#if person.authoritative_url}
								<a href={person.authoritative_url} target="_blank" rel="noopener">{person.authoritative_source}</a>
							{:else}
								{person.authoritative_source}
							{/if}
						</p>
					{/if}
				</div>
			</div>

			{#if person.categories?.length > 0}
				<div class="sidebar-bot">
					<div class="sidebar-header-2">
						<p><strong>Categories</strong></p>
					</div>
					<div class="sidebar-content">
						{#each person.categories as cat}
							<p class="small">{cat.name}</p>
						{/each}
					</div>
				</div>
			{/if}

			{#if person.quality_tier}
				<div class="sidebar-bot">
					<div class="sidebar-header-2">
						<p><strong>Evidence Tier</strong></p>
					</div>
					<div class="sidebar-content">
						<p class="small">{person.quality_tier}</p>
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

			<div class="sidebar-bot">
				<div class="sidebar-content">
					<p class="small muted mt-1">Created: {new Date(person.created_at).toLocaleDateString()}</p>
					<p class="small muted">Updated: {new Date(person.updated_at).toLocaleDateString()}</p>
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
	.media-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
		gap: 1rem;
	}
</style>
