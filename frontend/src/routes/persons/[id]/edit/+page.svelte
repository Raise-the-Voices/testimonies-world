<script lang="ts">
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { user, isVolunteer } from '$lib/session';
	import { getPerson, updatePerson, getCategories } from '$lib/api';

	let currentUser = $derived($user);
	let categories: any[] = $state([]);
	let saving = $state(false);
	let loading = $state(true);
	let errorMsg = $state('');
	let personId = $derived(page.params.id!);

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

	onMount(async () => {
		try {
			const [person, catData] = await Promise.all([
				getPerson(personId),
				getCategories(),
			]);

			categories = Array.isArray(catData) ? catData : catData.results ?? [];

			// Populate form fields from existing person data
			name = person.name || '';
			country = person.country || '';
			currentStatus = person.current_status || 'unknown';
			medicalStatus = person.medical_status || 'unknown';
			roughLocation = person.rough_location || '';
			preciseLocation = person.precise_location || '';
			lastKnownDate = person.last_known_date || '';
			summaryNarrative = person.summary_narrative || '';
			ethnicity = person.ethnicity || '';
			gender = person.gender || '';
			dateOfBirth = person.date_of_birth || '';
			selectedCategories = (person.categories || []).map((c: any) => c.id);
		} catch (e: any) {
			errorMsg = e.message || 'Failed to load case data.';
		}
		loading = false;
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
				gender: gender || '',
				category_ids: selectedCategories,
			};
			if (lastKnownDate) personData.last_known_date = lastKnownDate;
			else personData.last_known_date = null;
			if (dateOfBirth) personData.date_of_birth = dateOfBirth;
			else personData.date_of_birth = null;

			await updatePerson(personId, personData);
			goto(`${base}/persons/${personId}`);
		} catch (e: any) {
			errorMsg = e.message || 'Failed to save.';
		}
		saving = false;
	}
</script>

<svelte:head>
	<title>Edit Case — Testimonies.world</title>
</svelte:head>

<div class="container">
	{#if loading}
		<p class="muted">Loading...</p>
	{:else if !isVolunteer(currentUser)}
		<p class="muted">You must be logged in as a volunteer to edit cases. <a href="{base}/api/auth/login/?next={base}/persons/{personId}/edit">Login</a></p>
	{:else}
		<h1>Edit Case</h1>
		<p class="muted mb-2">Update information for this person. Fields marked * are required.</p>

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

			<div class="mt-2 form-actions">
				<button type="submit" class="btn btn-primary" disabled={saving}>
					{saving ? 'Saving...' : 'Save Changes'}
				</button>
				<a href="{base}/persons/{personId}" class="btn">Cancel</a>
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
	.form-actions {
		display: flex;
		gap: 1rem;
		align-items: center;
	}
	@media (max-width: 800px) {
		form {
			width: 90%;
		}
	}
</style>
