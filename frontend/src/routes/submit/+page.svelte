<script lang="ts">
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { user, isVolunteer } from '$lib/session';
	import { createPerson, createReport, getCategories } from '$lib/api';

	let currentUser = $derived($user);
	let categories: any[] = $state([]);
	let saving = $state(false);
	let errorMsg = $state('');

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
		const data = await getCategories();
		categories = data.results || data;
	});

	function toggleCategory(id: number) {
		if (selectedCategories.includes(id)) {
			selectedCategories = selectedCategories.filter(c => c !== id);
		} else {
			selectedCategories = [...selectedCategories, id];
		}
	}

	async function handleSubmit() {
		if (!name || !country) {
			errorMsg = 'Name and country are required.';
			return;
		}
		if (!narrative) {
			errorMsg = 'Please provide a narrative for the initial report.';
			return;
		}

		saving = true;
		errorMsg = '';

		try {
			const personData: any = {
				name,
				country,
				current_status: currentStatus,
				medical_status: medicalStatus,
				rough_location: roughLocation,
				precise_location: preciseLocation,
				summary_narrative: summaryNarrative,
				ethnicity,
				gender: gender || undefined,
				category_ids: selectedCategories,
			};
			if (lastKnownDate) personData.last_known_date = lastKnownDate;
			if (dateOfBirth) personData.date_of_birth = dateOfBirth;

			const person = await createPerson(personData);

			await createReport({
				person: person.id,
				source_type: sourceType,
				source_attribution: sourceAttribution,
				reporter_name: reporterName,
				reporter_contact: reporterContact,
				date_start: reportDateStart || null,
				rough_location: reportRoughLocation,
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
	<title>Submit Case — Testimonies.world</title>
</svelte:head>

<div class="container">
	{#if !isVolunteer(currentUser)}
		<p class="muted">You must be logged in as a volunteer to submit cases. <a href="{base}/api/auth/login/?next={base}/submit">Login</a></p>
	{:else}
		<h1>Submit a Case</h1>
		<p class="muted mb-2">Enter information about a person facing oppression. All fields except name, country, and narrative are optional.</p>

		{#if errorMsg}
			<div class="error-banner mb-2">{errorMsg}</div>
		{/if}

		<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
			<h2>Person Information</h2>
			<div class="form-grid">
				<div class="field">
					<label for="name">Name *</label>
					<input id="name" bind:value={name} required />
				</div>
				<div class="field">
					<label for="country">Country *</label>
					<input id="country" bind:value={country} required />
				</div>
				<div class="field">
					<label for="status">Current Status</label>
					<select id="status" bind:value={currentStatus}>
						<option value="detained">Detained</option>
						<option value="disappeared">Disappeared</option>
						<option value="restricted_movement">Restricted Movement</option>
						<option value="released">Released</option>
						<option value="deceased">Deceased</option>
						<option value="unknown">Unknown</option>
						<option value="stateless">Stateless</option>
						<option value="rights_restricted">Rights Restricted</option>
					</select>
				</div>
				<div class="field">
					<label for="medical">Medical Status</label>
					<select id="medical" bind:value={medicalStatus}>
						<option value="unknown">Unknown</option>
						<option value="healthy">Healthy</option>
						<option value="health_concerns">Health Concerns</option>
						<option value="critical">Critical</option>
						<option value="deceased">Deceased</option>
					</select>
				</div>
				<div class="field">
					<label for="rough_location">Location (public — region/city)</label>
					<input id="rough_location" bind:value={roughLocation} />
				</div>
				<div class="field">
					<label for="precise_location">Precise Location (private)</label>
					<input id="precise_location" bind:value={preciseLocation} placeholder="Not shown publicly" />
				</div>
				<div class="field">
					<label for="last_known_date">Last Known Date</label>
					<input id="last_known_date" type="date" bind:value={lastKnownDate} />
				</div>
				<div class="field">
					<label for="ethnicity">Ethnicity</label>
					<input id="ethnicity" bind:value={ethnicity} />
				</div>
				<div class="field">
					<label for="gender">Gender</label>
					<select id="gender" bind:value={gender}>
						<option value="">—</option>
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

			<div class="field">
				<label for="summary">Summary Narrative</label>
				<textarea id="summary" bind:value={summaryNarrative} placeholder="Brief overview of this person's situation"></textarea>
			</div>

			<div class="field">
				<label>Categories</label>
				<div class="categories-select">
					{#each categories as cat}
						<label class="cat-option">
							<input type="checkbox" checked={selectedCategories.includes(cat.id)} onchange={() => toggleCategory(cat.id)} />
							{cat.name}
						</label>
					{/each}
				</div>
			</div>

			<h2 class="mt-3">Initial Report</h2>
			<p class="muted mb-1 small">The first testimony or report about this person.</p>

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
					<label for="report_date">Date of Event</label>
					<input id="report_date" type="date" bind:value={reportDateStart} />
				</div>
				<div class="field">
					<label for="report_location">Location</label>
					<input id="report_location" bind:value={reportRoughLocation} />
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
				<button type="submit" class="btn btn-primary" disabled={saving}>
					{saving ? 'Saving...' : 'Submit Case'}
				</button>
			</div>
		</form>
	{/if}
</div>

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
	.categories-select {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
	}
	.cat-option {
		display: flex;
		align-items: center;
		gap: 0.3rem;
		font-weight: normal;
		font-size: 0.9rem;
	}
	.cat-option input[type="checkbox"] {
		width: auto;
	}
	@media (max-width: 800px) {
		form {
			width: 90%;
		}
	}
</style>
