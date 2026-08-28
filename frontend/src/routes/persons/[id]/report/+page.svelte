<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { user, isVolunteer } from '$lib/session';
	import { getPerson, createReport } from '$lib/api';

	let currentUser = $derived($user);
	let person: any = $state(null);
	let loading = $state(true);
	let saving = $state(false);
	let errorMsg = $state('');

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

	onMount(async () => {
		try {
			person = await getPerson(page.params.id!);
		} catch (e: any) {
			errorMsg = e.message;
		}
		loading = false;
	});

	async function handleSubmit() {
		if (!narrative) {
			errorMsg = 'Narrative is required.';
			return;
		}
		saving = true;
		errorMsg = '';
		try {
			await createReport({
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
			});
			goto(`${base}/persons/${person.id}`);
		} catch (e: any) {
			errorMsg = e.message || 'Failed to save.';
		}
		saving = false;
	}
</script>

<svelte:head>
	<title>Add Report — {person?.name || 'Loading...'} — Testimonies.world</title>
</svelte:head>

{#if loading}
	<p class="muted">Loading...</p>
{:else if !isVolunteer(currentUser)}
	<p class="muted">You must be logged in as a volunteer to add reports. <a href="{base}/api/auth/login/?next={base}/persons/{page.params.id}/report">Login</a></p>
{:else if person}
	<h1>Add Report</h1>
	<p class="muted mb-2">Adding a report for <a href="{base}/persons/{person.id}">{person.name}</a></p>

	{#if errorMsg}
		<div class="error-banner mb-2">{errorMsg}</div>
	{/if}

	<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
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
				<label for="source_attr">Source Attribution (public)</label>
				<input id="source_attr" bind:value={sourceAttribution} placeholder='e.g. "family member", "BBC article"' />
			</div>
			<div class="field">
				<label for="reporter_name">Reporter Name (private)</label>
				<input id="reporter_name" bind:value={reporterName} placeholder="Not shown publicly" />
			</div>
			<div class="field">
				<label for="reporter_contact">Reporter Contact (private)</label>
				<input id="reporter_contact" bind:value={reporterContact} placeholder="Email, phone, Signal" />
			</div>
			<div class="field">
				<label for="date_start">Date of Event (start)</label>
				<input id="date_start" type="date" bind:value={dateStart} />
			</div>
			<div class="field">
				<label for="date_end">Date of Event (end, if range)</label>
				<input id="date_end" type="date" bind:value={dateEnd} />
			</div>
			<div class="field">
				<label for="location">Location</label>
				<input id="location" bind:value={roughLocation} />
			</div>
		</div>

		<div class="field">
			<label for="narrative">Narrative *</label>
			<textarea id="narrative" bind:value={narrative} required placeholder="What happened? What is known?"></textarea>
		</div>

		<div class="form-grid">
			<div class="field">
				<label for="suspected_reason">Suspected Reason</label>
				<textarea id="suspected_reason" bind:value={suspectedReason} placeholder="What do sources believe is the reason?"></textarea>
			</div>
			<div class="field">
				<label for="official_reason">Official Reason</label>
				<textarea id="official_reason" bind:value={officialReason} placeholder="What did the state officially charge?"></textarea>
			</div>
		</div>

		<div class="mt-2">
			<button type="submit" class="btn" disabled={saving}>
				{saving ? 'Saving...' : 'Add Report'}
			</button>
			<a href="{base}/persons/{person.id}" class="btn btn-secondary" style="margin-left:0.5rem;">Cancel</a>
		</div>
	</form>
{/if}

<style>
	form {
		width: 75%;
		margin: 0 auto;
	}
	.form-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
		gap: 0 1rem;
	}
	@media (max-width: 800px) {
		form {
			width: 90%;
		}
	}
</style>
