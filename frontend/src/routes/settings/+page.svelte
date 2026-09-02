<script lang="ts">
	import { onMount } from 'svelte';
	import { user } from '$lib/session';
	import { getPreferences, updatePreferences, type UserPreferences } from '$lib/notification';

	let prefs = $state<UserPreferences>({ notify_email: true, notify_inapp: true });
	let original = $state<UserPreferences>({ notify_email: true, notify_inapp: true });
	let loading = $state(true);
	let saving = $state(false);
	let savedAt = $state<string | null>(null);
	let error = $state('');

	onMount(async () => {
		try {
			const p = await getPreferences();
			prefs = { ...p };
			original = { ...p };
		} catch (e: any) {
			error = e?.message ?? "Couldn't load preferences.";
		} finally {
			loading = false;
		}
	});

	async function save() {
		saving = true;
		savedAt = null;
		error = '';
		try {
			const next = await updatePreferences(prefs);
			prefs = { ...next };
			original = { ...next };
			savedAt = new Date().toLocaleTimeString();
		} catch (e: any) {
			error = e?.message ?? "Couldn't save preferences.";
		} finally {
			saving = false;
		}
	}

	const dirty = $derived(
		prefs.notify_email !== original.notify_email ||
			prefs.notify_inapp !== original.notify_inapp,
	);
</script>

<svelte:head>
	<title>Settings — Testimonies.world</title>
</svelte:head>

<div class="container">
	<header class="page-header">
		<h1 class="page-title">Notification settings</h1>
	</header>

	{#if !$user.authenticated}
		<p class="muted">Please <a href="/accounts/google/login/?next=/settings">log in</a> to manage settings.</p>
	{:else if loading}
		<p class="muted">Loading…</p>
	{:else}
		<section class="card" aria-label="Notification preferences">
			<div class="row">
				<div class="row-text">
					<div class="row-title">Email notifications</div>
					<p class="row-help">
						Receive an email when a teammate logs or updates casework you should know about.
						We suppress repeat emails within 24 hours, and we never email about deletions.
					</p>
				</div>
				<label class="switch">
					<input
						type="checkbox"
						bind:checked={prefs.notify_email}
					/>
					<span class="switch-track" aria-hidden="true"><span class="switch-thumb"></span></span>
				</label>
			</div>

			<div class="row">
				<div class="row-text">
					<div class="row-title">In-app notifications</div>
					<p class="row-help">
						Show a bell badge and feed of new casework activity. You can still open the
						notification page even if this is off.
					</p>
				</div>
				<label class="switch">
					<input
						type="checkbox"
						bind:checked={prefs.notify_inapp}
					/>
					<span class="switch-track" aria-hidden="true"><span class="switch-thumb"></span></span>
				</label>
			</div>

			{#if error}
				<div class="error" role="alert">{error}</div>
			{/if}

			<footer class="actions">
				{#if savedAt}
					<span class="saved">Saved at {savedAt}.</span>
				{/if}
				<button
					type="button"
					class="btn btn-primary"
					disabled={!dirty || saving}
					onclick={save}
				>{saving ? 'Saving…' : 'Save changes'}</button>
			</footer>
		</section>
	{/if}
</div>

<style>
	.page-header {
		margin-bottom: 1.5rem;
	}
	.page-title {
		margin: 0;
		color: var(--color-primary);
		font-size: 1.85rem;
		font-weight: 700;
		letter-spacing: -0.01em;
	}
	.card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-subtle);
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-card);
		padding: 0.5rem 0;
	}
	.row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1.5rem;
		padding: 1rem 1.25rem;
		border-top: 1px solid var(--color-border-subtle);
	}
	.row:first-child { border-top: 0; }
	.row-text { flex: 1 1 auto; min-width: 0; }
	.row-title {
		font-weight: 600;
		color: var(--color-text);
		margin-bottom: 0.25rem;
	}
	.row-help {
		margin: 0;
		color: var(--color-text-muted);
		font-size: 0.88rem;
		line-height: 1.5;
	}
	.switch {
		display: inline-flex;
		align-items: center;
		cursor: pointer;
		flex: 0 0 auto;
	}
	.switch input {
		position: absolute;
		opacity: 0;
		width: 0;
		height: 0;
	}
	.switch-track {
		width: 38px;
		height: 22px;
		background: var(--color-border-light);
		border-radius: 11px;
		position: relative;
		transition: background 0.15s ease;
	}
	.switch-thumb {
		position: absolute;
		top: 2px;
		left: 2px;
		width: 18px;
		height: 18px;
		background: white;
		border-radius: 50%;
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.18);
		transition: transform 0.15s ease;
	}
	.switch input:checked + .switch-track {
		background: var(--color-primary);
	}
	.switch input:checked + .switch-track .switch-thumb {
		transform: translateX(16px);
	}
	.switch input:focus-visible + .switch-track {
		box-shadow: 0 0 0 3px var(--color-primary-tint);
	}
	.actions {
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: 1rem;
		padding: 0.85rem 1.25rem;
		border-top: 1px solid var(--color-border-subtle);
	}
	.saved {
		color: var(--color-success);
		font-size: 0.85rem;
	}
	.error {
		margin: 0 1.25rem 0.75rem;
		padding: 0.6rem 0.8rem;
		background: var(--color-danger);
		color: var(--color-text-light);
		border-radius: var(--radius-input);
		font-size: 0.88rem;
	}
</style>