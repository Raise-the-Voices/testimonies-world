<script lang="ts">
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { user, isAdvocate } from '$lib/session';
	import { createCasework, getPersons } from '$lib/api';

	let currentUser = $derived($user);
	let saving = $state(false);
	let errorMsg = $state('');
	let persons: any[] = $state([]);
	let selectedPersons: number[] = $state([]);

	let actionType = $state('outreach');
	let description = $state('');
	let date = $state(new Date().toISOString().split('T')[0]);
	let status = $state('open');
	let nextSteps = $state('');
	let notes = $state('');

	const actionLabels: Record<string, string> = {
		outreach: 'Outreach',
		legal_filing: 'Legal Filing',
		media: 'Media',
		advocacy: 'Advocacy',
		investigation: 'Investigation',
		other: 'Other',
	};

	onMount(async () => {
		try {
			const data = await getPersons({ page_size: '1000' });
			persons = data.results || [];
		} catch (e) {
			console.error(e);
		}
	});

	function togglePerson(id: number) {
		if (selectedPersons.includes(id)) {
			selectedPersons = selectedPersons.filter(p => p !== id);
		} else {
			selectedPersons = [...selectedPersons, id];
		}
	}

	async function handleSubmit() {
		if (!description) {
			errorMsg = 'Description is required.';
			return;
		}
		saving = true;
		errorMsg = '';
		try {
			await createCasework({
				action_type: actionType,
				description,
				date,
				status,
				next_steps: nextSteps,
				notes,
				persons: selectedPersons,
			});
			goto(`${base}/casework`);
		} catch (e: any) {
			errorMsg = e.message || 'Failed to save.';
		}
		saving = false;
	}
</script>

<svelte:head>
	<title>New Casework Record — Testimonies.world</title>
</svelte:head>

{#if !isAdvocate(currentUser)}
	<p class="muted">You must be logged in as an advocate to create casework records. <a href="{base}/api/auth/login/?next={base}/casework/new">Login</a></p>
{:else}
	<h1>New Casework Record</h1>

	{#if errorMsg}
		<div class="error-banner mb-2">{errorMsg}</div>
	{/if}

	<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
		<div class="form-grid">
			<div class="field">
				<label for="action_type">Action Type</label>
				<select id="action_type" bind:value={actionType}>
					{#each Object.entries(actionLabels) as [value, label]}
						<option {value}>{label}</option>
					{/each}
				</select>
			</div>
			<div class="field">
				<label for="date">Date</label>
				<input id="date" type="date" bind:value={date} />
			</div>
			<div class="field">
				<label for="status">Status</label>
				<select id="status" bind:value={status}>
					<option value="open">Open</option>
					<option value="in_progress">In Progress</option>
					<option value="done">Done</option>
				</select>
			</div>
		</div>

		<div class="field">
			<label for="description">Description *</label>
			<textarea id="description" bind:value={description} required placeholder="What action was taken or needs to be taken?"></textarea>
		</div>

		<div class="field">
			<label for="next_steps">Next Steps</label>
			<textarea id="next_steps" bind:value={nextSteps} placeholder="What should happen next?"></textarea>
		</div>

		<div class="field">
			<label for="notes">Notes</label>
			<textarea id="notes" bind:value={notes} placeholder="Internal notes"></textarea>
		</div>

		{#if persons.length > 0}
			<div class="field">
				<label>Linked Persons</label>
				<div class="persons-select">
					{#each persons as person}
						<label class="person-option">
							<input type="checkbox" checked={selectedPersons.includes(person.id)} onchange={() => togglePerson(person.id)} />
							{person.name} ({person.country})
						</label>
					{/each}
				</div>
			</div>
		{/if}

		<div class="mt-2">
			<button type="submit" class="btn" disabled={saving}>
				{saving ? 'Saving...' : 'Create Record'}
			</button>
			<a href="{base}/casework" class="btn btn-secondary" style="margin-left:0.5rem;">Cancel</a>
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
	.persons-select {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		max-height: 200px;
		overflow-y: auto;
		border: 1px solid var(--color-border);
		padding: 10px;
		border-radius: 4px;
	}
	.person-option {
		display: flex;
		align-items: center;
		gap: 0.3rem;
		font-weight: normal;
		font-size: 0.9rem;
	}
	.person-option input[type="checkbox"] {
		width: auto;
	}
	@media (max-width: 800px) {
		form {
			width: 90%;
		}
	}
</style>
