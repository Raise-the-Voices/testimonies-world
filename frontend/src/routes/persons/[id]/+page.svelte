<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { getPerson } from '$lib/api';
	import { user, isVolunteer } from '$lib/session';
	import StatusBadge from '$lib/StatusBadge.svelte';

	let person: any = $state(null);
	let loading = $state(true);
	let error = $state('');
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
				{#each person.reports as report}
					<div class="incident-container">
						<div class="incident-top">
							<span class="badge">{report.source_type}</span>
							{#if report.source_attribution}
								<span class="muted small"> — {report.source_attribution}</span>
							{/if}
							<span class="small muted" style="float:right;">
								{#if report.date_start}
									{report.date_start}{#if report.date_end} — {report.date_end}{/if}
								{:else}
									{new Date(report.created_at).toLocaleDateString()}
								{/if}
							</span>
						</div>
						{#if report.rough_location}
							<p class="small muted mt-1">Location: {report.rough_location}</p>
						{/if}
						<p class="mt-1 white-space-pre-line">{report.narrative}</p>
						{#if report.suspected_reason}
							<p class="mt-1"><strong>Suspected reason:</strong> {report.suspected_reason}</p>
						{/if}
						{#if report.official_reason}
							<p class="mt-1"><strong>Official reason:</strong> {report.official_reason}</p>
						{/if}
						{#if report.media_files?.length > 0}
							<div class="mt-1">
								{#each report.media_files as media}
									{#if media.url}
										<a href={media.url} target="_blank" rel="noopener" class="small">{media.description || media.url}</a>
									{/if}
								{/each}
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
