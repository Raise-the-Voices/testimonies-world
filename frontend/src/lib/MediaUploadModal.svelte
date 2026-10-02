<!--
  MediaUploadModal — link-only media entry form.

  Per the 2026-10-02 product decision, the volunteer-facing surface
  accepts external URLs only. No file/binary uploads, no storage,
  no nginx serving — the media row stores `url` and the browser
  fetches the destination directly. This sidesteps the upload-
  pipeline complexity that was making fills flicker behind a 403/404
  nginx path on the dev VM.

  Backend still accepts the `file` column for any future admin /
  import path, but the volunteer form never sets it.
-->
<script lang="ts">
	import { fly, fade } from 'svelte/transition';
	import { uploadMediaJson, updateMediaJson, ApiError } from '$lib/api';
	import type { Media, Visibility } from '$lib/types';

	interface Props {
		open: boolean;
		/** Optional existing media to edit; omit for create. */
		media?: Media | null;
		/** Required for create; ignored on edit (the row already has a person). */
		personId?: number;
		/** Hide the person field entirely (e.g. when uploading from a person page). */
		hidePerson?: boolean;
		/** Disable the 'sensitive' visibility option for non-advocate users. */
		canMarkSensitive: boolean;
		onSaved: (m: Media) => void;
		onClose: () => void;
	}

	let {
		open,
		media = null,
		personId,
		hidePerson = false,
		canMarkSensitive,
		onSaved,
		onClose,
	}: Props = $props();

	const isEdit = $derived(!!media);

	const visibilityLabels: Record<Visibility, string> = {
		public: 'Public — anyone can see',
		restricted: 'Restricted — volunteers and above',
		sensitive: 'Sensitive — advocates and admins only',
	};
	const visibilities = $derived<Visibility[]>(
		canMarkSensitive
			? ['public', 'restricted', 'sensitive']
			: ['public', 'restricted'],
	);

	// Link-only — the modal never lets the volunteer pick a type.
	const mediaType = 'link';
	let visibility = $state<Visibility>('public');
	let urlValue = $state('');
	let description = $state('');
	let saving = $state(false);
	let formError = $state('');
	let errors = $state<Record<string, string>>({});

	const MAX_DESC = 500;

	$effect(() => {
		if (!open) return;
		if (media) {
			visibility = media.visibility ?? 'public';
			description = media.description ?? '';
			urlValue = media.url ?? '';
		} else {
			visibility = 'public';
			description = '';
			urlValue = '';
		}
		formError = '';
		errors = {};
	});

	$effect(() => {
		if (!open) return;
		const handler = (e: KeyboardEvent) => {
			if (e.key === 'Escape' && open) {
				e.preventDefault();
				close();
			}
		};
		document.addEventListener('keydown', handler);
		return () => document.removeEventListener('keydown', handler);
	});

	function close() {
		if (saving) return;
		onClose();
	}

	function validate(): boolean {
		const e: Record<string, string> = {};
		const trimmed = urlValue.trim();
		if (!trimmed) {
			e.url = 'A URL is required.';
		} else if (!/^https?:\/\//i.test(trimmed)) {
			e.url = 'URL must start with http:// or https://';
		}
		if (description.length > MAX_DESC) {
			e.description = `Description too long (max ${MAX_DESC} characters).`;
		}
		errors = e;
		return Object.keys(e).length === 0;
	}

	async function save() {
		if (!validate()) return;
		formError = '';
		saving = true;

		try {
			const payload: Parameters<typeof uploadMediaJson>[0] = {
				media_type: mediaType,
				visibility,
				description: description.trim(),
				url: urlValue.trim(),
			};
			// Attach person when personId is set on a non-edit. `hidePerson`
			// only controls whether the picker UI is rendered — it must
			// not skip the binding, otherwise /persons/[id]/ would create
			// orphan rows with person_id=NULL.
			if (!isEdit && personId !== undefined) {
				payload.person = personId;
			}

			const result = isEdit && media
				? await updateMediaJson(media.id, payload)
				: await uploadMediaJson(payload);
			onSaved(result);
			onClose();
		} catch (e: unknown) {
			if (e instanceof ApiError) {
				if (e.fieldErrors && Object.keys(e.fieldErrors).length) {
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
		} finally {
			saving = false;
		}
	}
</script>

{#if open}
	<div class="modal-overlay" onclick={close} role="presentation" transition:fade={{ duration: 150 }}></div>

	<div
		class="modal"
		role="dialog"
		aria-modal="true"
		aria-labelledby="media-modal-title"
		transition:fly={{ y: -16, duration: 200, opacity: 0 }}
	>
		<header class="modal-header">
			<h2 id="media-modal-title">{isEdit ? 'Edit media link' : 'Add a media link'}</h2>
			<button
				type="button"
				class="modal-close"
				aria-label="Close"
				onclick={close}
				disabled={saving}
			>×</button>
		</header>

		<form class="modal-body" onsubmit={(e) => { e.preventDefault(); save(); }} novalidate>
			{#if formError}
				<div class="form-error" role="alert">
					<span class="form-error-icon" aria-hidden="true">!</span>
					<span>{formError}</span>
				</div>
			{/if}

			<p class="field-hint">
				Paste a URL to an external article, document, video, or image. The link is stored
				on the case; no file is uploaded.
			</p>

			<div class="field">
				<label for="media-url">URL</label>
				<input
					id="media-url"
					type="url"
					class="input--search"
					class:has-error={!!errors.url}
					bind:value={urlValue}
					placeholder="https://example.org/document.pdf"
					autocomplete="off"
					required
				/>
				{#if errors.url}
					<p class="field-error">{errors.url}</p>
				{/if}
			</div>

			<div class="field">
				<label for="media-description">Description</label>
				<input
					id="media-description"
					type="text"
					class="input--search"
					class:has-error={!!errors.description}
					bind:value={description}
					autocomplete="off"
					maxlength={MAX_DESC}
					placeholder="What is this link? Any context that matters."
				/>
				<div class="field-counter" aria-live="polite">
					{description.length} / {MAX_DESC}
				</div>
				{#if errors.description}
					<p class="field-error">{errors.description}</p>
				{/if}
			</div>

			<div class="field">
				<label for="media-visibility">Visibility</label>
				<select
					id="media-visibility"
					class="select--filter"
					class:has-error={!!errors.visibility}
					bind:value={visibility}
				>
					{#each visibilities as v (v)}
						<option value={v}>{visibilityLabels[v]}</option>
					{/each}
				</select>
				{#if errors.visibility}
					<p class="field-error">{errors.visibility}</p>
				{/if}
			</div>

			<div class="modal-actions">
				<button
					type="button"
					class="btn btn-secondary"
					onclick={close}
					disabled={saving}
				>Cancel</button>
				<button
					type="submit"
					class="btn btn-primary"
					disabled={saving}
				>{saving ? 'Saving…' : isEdit ? 'Save changes' : 'Add'}</button>
			</div>
		</form>
	</div>
{/if}

<style>
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
		border-left: 3px solid var(--color-primary);
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
		gap: 1rem;
	}

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

	.field {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
		min-width: 0;
	}
	.field label {
		font-size: 0.85rem;
		font-weight: 600;
		color: var(--color-text);
		margin: 0;
	}
	.field-hint {
		margin: 0;
		font-size: 0.82rem;
		color: var(--color-text-muted);
		line-height: 1.45;
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

	.modal-actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.75rem;
		padding-top: 0.5rem;
		border-top: 1px solid var(--color-border-subtle);
	}
	.modal-actions .btn {
		min-width: 120px;
	}
	.modal-actions .btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	@media (max-width: 600px) {
		.modal-actions {
			flex-direction: column-reverse;
		}
		.modal-actions .btn {
			width: 100%;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.modal,
		.modal-overlay {
			transition: none;
		}
	}
</style>