<script lang="ts">
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { user, isAdvocate } from '$lib/session';
	import { createContact, getContact, updateContact, ApiError } from '$lib/api';
	import type { Contact, ContactRole } from '$lib/types';

	let currentUser = $derived($user);
	let saving = $state(false);
	let loading = $state(true);
	let loadError = $state('');
	let formError = $state('');
	let errors = $state<Record<string, string>>({});

	// Edit mode: when ?id=X is present, we PATCH instead of POST.
	// Reactive so Back/Forward between ?id=5 and ?id=7 re-hydrates the form.
	let contactId: number | null = $derived.by(() => {
		const raw = $page.url.searchParams.get('id');
		if (!raw) return null;
		const n = Number(raw);
		return Number.isFinite(n) && n > 0 ? n : null;
	});
	const isEdit = $derived(contactId !== null);

	// Form fields. Match the backend Contact model:
	//   name (required), role (required), email, phone, signal, whatsapp, notes
	let name = $state('');
	let role = $state<ContactRole>('other');
	let email = $state('');
	let phone = $state('');
	let signal = $state('');
	let whatsapp = $state('');
	let notes = $state('');

	const roleLabels: Record<string, string> = {
		family: 'Family member',
		advocate: 'Advocate',
		lawyer: 'Lawyer',
		official: 'Government official',
		journalist: 'Journalist',
		reporter: 'Reporter / witness',
		other: 'Other',
	};
	const roleOptions = Object.entries(roleLabels);

	const MAX_FIELD = 1000;

	// Refetch-guard token: Back/Forward between ?id=5 and ?id=7 must not
	// let a slow response for 5 clobber the form populated for 7.
	let loadToken = 0;

	async function load() {
		const token = ++loadToken;
		loadError = '';
		if (contactId === null) {
			// Switching edit → create: clear stale fields.
			name = '';
			role = 'other';
			email = '';
			phone = '';
			signal = '';
			whatsapp = '';
			notes = '';
			loading = false;
			return;
		}
		loading = true;
		try {
			const c = await getContact(contactId);
			if (token !== loadToken) return;
			name = c.name ?? '';
			role = c.role ?? 'other';
			email = c.email ?? '';
			phone = c.phone ?? '';
			signal = c.signal ?? '';
			whatsapp = c.whatsapp ?? '';
			notes = c.notes ?? '';
		} catch (e: unknown) {
			if (token !== loadToken) return;
			if (e instanceof ApiError && e.status === 404) {
				loadError = 'That contact no longer exists.';
			} else if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
				loadError = "You don't have permission to edit this contact.";
			} else {
				loadError =
					e instanceof Error ? e.message : "Couldn't load this contact.";
			}
		} finally {
			if (token === loadToken) loading = false;
		}
	}

	// Re-fetch whenever the route or its ?id= param changes. $effect
	// dedupes unchanged deps, so first-mount + reactive on subsequent nav.
	$effect(() => {
		void contactId;
		void load();
	});

	function validate(): boolean {
		const e: Record<string, string> = {};
		const trimmedName = name.trim();
		if (!trimmedName) {
			e.name = 'Name is required.';
		} else if (trimmedName.length > 255) {
			e.name = 'Name is too long (max 255 characters).';
		}
		if (!role || !roleLabels[role]) {
			e.role = 'Pick a role.';
		}
		if (email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
			e.email = 'Enter a valid email address, or leave it blank.';
		}
		errors = e;
		return Object.keys(e).length === 0;
	}

	async function save() {
		if (!validate()) return;
		formError = '';
		saving = true;
		try {
			const payload: Partial<Contact> = {
				name: name.trim(),
				role,
				email: email.trim(),
				phone: phone.trim(),
				signal: signal.trim(),
				whatsapp: whatsapp.trim(),
				notes: notes.trim(),
			};
			if (isEdit && contactId !== null) {
				await updateContact(contactId, payload);
				await goto(`${base}/contacts?saved=1`, { replaceState: true });
			} else {
				await createContact(payload);
				await goto(`${base}/contacts?saved=1`, { replaceState: true });
			}
		} catch (e: unknown) {
			if (e instanceof ApiError) {
				if (e.fieldErrors && Object.keys(e.fieldErrors).length) {
					// fieldErrors is Record<string, string[]> from Django.
					// Flatten to the first message per field for display.
					const flat: Record<string, string> = {};
					for (const [k, v] of Object.entries(e.fieldErrors)) {
						flat[k] = Array.isArray(v) ? v[0] ?? '' : String(v);
					}
					errors = { ...flat, ...errors };
					formError = 'Please correct the highlighted fields.';
				} else {
					formError = e.message;
				}
			} else {
				formError = e instanceof Error ? e.message : 'Something went wrong.';
			}
			saving = false;
		}
	}

	function cancel() {
		goto(`${base}/contacts`);
	}
</script>

<svelte:head>
	<title>{isEdit ? 'Edit contact' : 'New contact'} — Testimonies.world</title>
</svelte:head>

<div class="contacts-page">
	{#if !isAdvocate(currentUser)}
		<p class="muted">
			You must be logged in as an advocate to manage contacts.
			<a href="{base}/api/auth/login/?next={base}/contacts">Login</a>
		</p>
	{:else if loading}
		<p class="muted">Loading…</p>
	{:else if loadError}
		<section class="form-card form-card-error">
			<header class="error-header">
				<span class="error-icon" aria-hidden="true">⚠</span>
				<h2>Could not load</h2>
			</header>
			<p class="error-message">{loadError}</p>
			<a class="btn btn-secondary" href="{base}/contacts">Back to contacts</a>
		</section>
	{:else}
		<header class="contacts-header">
			<h1>{isEdit ? 'Edit contact' : 'New contact'}</h1>
			<p class="contacts-intro">
				{#if isEdit}
					Update this contact's details. Edits are logged.
				{:else}
					People involved in cases — advocates, lawyers, journalists, family
					members, and officials. Always private; visible only to advocates.
				{/if}
			</p>
		</header>

		<form class="form-card" onsubmit={(e) => { e.preventDefault(); save(); }} novalidate>
			{#if formError}
				<div class="form-error" role="alert">
					<span class="form-error-icon" aria-hidden="true">!</span>
					<span>{formError}</span>
				</div>
			{/if}

			<div class="form-grid">
				<!-- Name — full width, primary field -->
				<div class="field field-full">
					<label for="contact-name">Name</label>
					<input
						id="contact-name"
						type="text"
						class="input--search"
						class:has-error={!!errors.name}
						bind:value={name}
						autocomplete="off"
						required
						maxlength={255}
						placeholder="e.g. Layla Hassan"
					/>
					{#if errors.name}
						<p class="field-error">{errors.name}</p>
					{/if}
				</div>

				<!-- Role -->
				<div class="field">
					<label for="contact-role">Role</label>
					<select
						id="contact-role"
						class="select--filter"
						class:has-error={!!errors.role}
						bind:value={role}
					>
						{#each roleOptions as [value, label] (value)}
							<option {value}>{label}</option>
						{/each}
					</select>
					{#if errors.role}
						<p class="field-error">{errors.role}</p>
					{/if}
				</div>

				<!-- Email -->
				<div class="field">
					<label for="contact-email">Email</label>
					<input
						id="contact-email"
						type="email"
						class="input--search"
						class:has-error={!!errors.email}
						bind:value={email}
						autocomplete="off"
						maxlength={255}
						placeholder="name@example.org"
					/>
					{#if errors.email}
						<p class="field-error">{errors.email}</p>
					{/if}
				</div>

				<!-- Phone -->
				<div class="field">
					<label for="contact-phone">Phone</label>
					<input
						id="contact-phone"
						type="tel"
						class="input--search"
						bind:value={phone}
						autocomplete="off"
						maxlength={50}
						placeholder="+1 555 0100"
					/>
				</div>

				<!-- Signal -->
				<div class="field">
					<label for="contact-signal">Signal handle</label>
					<input
						id="contact-signal"
						type="text"
						class="input--search"
						bind:value={signal}
						autocomplete="off"
						maxlength={50}
						placeholder="@username"
					/>
				</div>

				<!-- WhatsApp -->
				<div class="field">
					<label for="contact-whatsapp">WhatsApp</label>
					<input
						id="contact-whatsapp"
						type="text"
						class="input--search"
						bind:value={whatsapp}
						autocomplete="off"
						maxlength={50}
						placeholder="+1 555 0100"
					/>
				</div>

				<!-- Notes — full width, textarea -->
				<div class="field field-full">
					<label for="contact-notes">Notes</label>
					<textarea
						id="contact-notes"
						class="input--search"
						bind:value={notes}
						maxlength={MAX_FIELD}
						placeholder="Background, context, how you connected — anything that helps the team."
					></textarea>
					<div class="field-counter" aria-live="polite">
						{notes.length} / {MAX_FIELD}
					</div>
				</div>
			</div>

			<div class="form-actions">
				<button
					type="button"
					class="btn btn-secondary"
					onclick={cancel}
					disabled={saving}
				>Cancel</button>
				<button
					type="submit"
					class="btn btn-primary"
					disabled={saving}
				>{saving ? 'Saving…' : isEdit ? 'Save changes' : 'Create contact'}</button>
			</div>
		</form>
	{/if}
</div>

<style>
	.contacts-page {
		width: 100%;
		max-width: var(--max-w-prose);
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	/* === Header (matches /contacts list) === */
	.contacts-header h1 {
		margin: 0 0 0.4rem 0;
		color: var(--color-primary);
		font-size: 1.85rem;
		font-weight: 700;
		letter-spacing: -0.01em;
	}
	.contacts-intro {
		margin: 0;
		color: var(--color-text);
		font-size: 1rem;
		line-height: 1.6;
	}

	/* === Form card === */
	.form-card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-subtle);
		border-left: 3px solid var(--color-primary);
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-card);
		padding: 1.75rem;
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	/* Error-only card variant */
	.form-card-error {
		border-left-color: var(--color-danger);
	}

	/* === Form-level error banner === */
	.form-error {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.65rem 0.9rem;
		background: #fed7d7;
		color: #c53030;
		border: 1px solid #feb2b2;
		border-radius: var(--radius-card);
		font-size: 0.9rem;
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

	/* === Grid layout — name + notes span full width === */
	.form-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 1rem 1.25rem;
	}
	.field-full {
		grid-column: 1 / -1;
	}

	.field {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
		min-width: 0; /* prevent overflow inside grid */
	}
	.field label {
		font-size: 0.85rem;
		font-weight: 600;
		color: var(--color-text);
		margin: 0;
	}

	/* Override global input/textarea defaults to use design-system
	   tokens. The .input--search class (defined in app.css) is reused
	   here for consistency with the floating filter toolbar. */
	.field .input--search {
		font-size: 0.95rem;
		padding: 0.55rem 0.85rem;
	}
	.field textarea.input--search {
		min-height: 110px;
		resize: vertical;
		font-family: inherit;
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
	.input--search.has-error,
	.select--filter.has-error {
		border-color: var(--color-danger);
	}
	.input--search.has-error:focus,
	.select--filter.has-error:focus {
		box-shadow: 0 0 0 3px rgba(217, 22, 22, 0.15);
	}

	/* === Actions === */
	.form-actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.75rem;
		padding-top: 0.5rem;
		border-top: 1px solid var(--color-border-subtle);
	}
	.form-actions .btn {
		min-width: 140px;
	}
	.form-actions .btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	/* === Error header === */
	.error-header {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		margin-bottom: 0.6rem;
		color: var(--color-danger);
	}
	.error-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		border-radius: 50%;
		background: rgba(217, 22, 22, 0.12);
		color: var(--color-danger);
		font-weight: 700;
		font-size: 1rem;
	}
	.error-header h2 {
		margin: 0;
		font-size: 1.05rem;
		font-weight: 700;
		color: var(--color-text);
	}
	.error-message {
		margin: 0 0 1rem 0;
		color: var(--color-text-muted);
		font-size: 0.92rem;
	}

	/* === Responsive === */
	@media (max-width: 600px) {
		.form-grid {
			grid-template-columns: 1fr;
		}
		.form-actions {
			flex-direction: column-reverse;
		}
		.form-actions .btn {
			width: 100%;
		}
	}
</style>