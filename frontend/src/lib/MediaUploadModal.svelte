<script lang="ts">
	import { fly, fade } from 'svelte/transition';
	import { uploadMedia, updateMedia, ApiError } from '$lib/api';
	import type { Media, MediaType, Visibility } from '$lib/types';

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

	const mediaTypeLabels: Record<MediaType, string> = {
		photo: 'Photo',
		video: 'Video',
		document: 'Document',
		link: 'External link',
	};
	const mediaTypes: MediaType[] = ['photo', 'video', 'document', 'link'];
	const visibilityLabels: Record<Visibility, string> = {
		public: 'Public — anyone can see',
		restricted: 'Restricted — volunteers and above',
		sensitive: 'Sensitive — advocates and admins only',
	};
	// Reactive: hide 'sensitive' if the user can't mark it. `$derived`
	// re-evaluates when the prop changes (e.g. session refresh upgrades
	// role).
	const visibilities = $derived<Visibility[]>(
		canMarkSensitive
			? ['public', 'restricted', 'sensitive']
			: ['public', 'restricted'],
	);

	let mediaType = $state<MediaType>('photo');
	let visibility = $state<Visibility>('public');
	let description = $state('');
	let urlValue = $state('');
	let fileValue = $state<File | null>(null);
	let fileInputEl: HTMLInputElement | null = $state(null);
	let saving = $state(false);
	let formError = $state('');
	let errors = $state<Record<string, string>>({});
	let isDragging = $state(false);

	const MAX_FILE_BYTES = 25 * 1024 * 1024; // 25 MB
	const MAX_DESC = 500;

	// Initialize fields when opening.
	$effect(() => {
		if (!open) return;
		if (media) {
			mediaType = media.media_type;
			visibility = media.visibility;
			description = media.description ?? '';
			urlValue = media.url ?? '';
			fileValue = null;
		} else {
			mediaType = 'photo';
			visibility = 'public';
			description = '';
			urlValue = '';
			fileValue = null;
		}
		formError = '';
		errors = {};
	});

	// Escape closes the modal.
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
		if (saving) return; // don't close mid-save
		onClose();
	}

	function onFileChange(e: Event) {
		const input = e.currentTarget as HTMLInputElement;
		fileValue = input.files && input.files.length > 0 ? input.files[0] : null;
	}

	function onDrop(e: DragEvent) {
		e.preventDefault();
		isDragging = false;
		if (!e.dataTransfer) return;
		const file = e.dataTransfer.files?.[0];
		if (file) {
			fileValue = file;
			if (fileInputEl) fileInputEl.value = '';
		}
	}

	function onDragOver(e: DragEvent) {
		e.preventDefault();
		isDragging = true;
	}

	function onDragLeave(e: DragEvent) {
		e.preventDefault();
		isDragging = false;
	}

	function validate(): boolean {
		const e: Record<string, string> = {};
		if (!mediaType) e.media_type = 'Pick a media type.';
		if (!visibility) e.visibility = 'Pick a visibility level.';

		if (isEdit) {
			// On edit, file and url are optional (keep what's there).
			if (fileValue) {
				if (fileValue.size > MAX_FILE_BYTES) {
					e.file = `File too large (${(fileValue.size / 1024 / 1024).toFixed(1)} MB). Max 25 MB.`;
				}
			}
		} else {
			// On create, exactly one of file or url is required, never both.
			if (!fileValue && !urlValue.trim()) {
				e.file = 'Pick a file or paste a URL.';
				e.url = '';
			}
			if (fileValue && urlValue.trim()) {
				e.file = 'Pick a file OR a URL, not both.';
				e.url = '';
			}
			if (fileValue && fileValue.size > MAX_FILE_BYTES) {
				e.file = `File too large (${(fileValue.size / 1024 / 1024).toFixed(1)} MB). Max 25 MB.`;
			}
			if (!fileValue && urlValue.trim() && !/^https?:\/\//i.test(urlValue.trim())) {
				e.url = 'URL must start with http:// or https://';
			}
		}

		if (description.length > MAX_DESC) {
			e.description = `Description too long (max ${MAX_DESC} characters).`;
		}

		if (mediaType === 'link' && !urlValue.trim() && !fileValue) {
			e.url = 'External links require a URL.';
		}

		errors = e;
		return Object.keys(e).length === 0;
	}

	function filePreviewUrl(file: File): string | null {
		if (!file.type.startsWith('image/')) return null;
		try {
			return URL.createObjectURL(file);
		} catch {
			return null;
		}
	}
	const previewUrl = $derived(fileValue ? filePreviewUrl(fileValue) : null);

	async function save() {
		if (!validate()) return;
		formError = '';
		saving = true;

		try {
			const fd = new FormData();
			fd.append('media_type', mediaType);
			fd.append('visibility', visibility);
			if (description.trim()) fd.append('description', description.trim());

			if (fileValue) {
				fd.append('file', fileValue);
			}
			if (urlValue.trim()) {
				fd.append('url', urlValue.trim());
			}
			// Attach person only on create (and when not hidden).
			if (!isEdit && !hidePerson && personId !== undefined) {
				fd.append('person', String(personId));
			}

			const result = isEdit && media
				? await updateMedia(media.id, fd)
				: await uploadMedia(fd);
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
			saving = false;
		}
	}
</script>

{#if open}
	<!-- Backdrop -->
	<div class="modal-overlay" onclick={close} role="presentation" transition:fade={{ duration: 150 }}></div>

	<!-- Dialog -->
	<div
		class="modal"
		role="dialog"
		aria-modal="true"
		aria-labelledby="media-modal-title"
		transition:fly={{ y: -16, duration: 200, opacity: 0 }}
	>
		<header class="modal-header">
			<h2 id="media-modal-title">{isEdit ? 'Edit media' : 'Upload media'}</h2>
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

			<!-- Media type -->
			<div class="field">
				<label for="media-type">Type</label>
				<select
					id="media-type"
					class="select--filter"
					class:has-error={!!errors.media_type}
					bind:value={mediaType}
				>
					{#each mediaTypes as t (t)}
						<option value={t}>{mediaTypeLabels[t]}</option>
					{/each}
				</select>
				{#if errors.media_type}
					<p class="field-error">{errors.media_type}</p>
				{/if}
			</div>

			<!-- Source: file or URL -->
			<fieldset class="field source-fieldset">
				<legend>Source</legend>
				<p class="field-hint">
					{#if isEdit}
						Leave blank to keep the existing file / URL. Upload a new file to replace it,
						or paste a URL to switch to an external link.
					{:else}
						Pick a file to upload, or paste an external URL. Exactly one of the two.
					{/if}
				</p>

				<!-- Drop zone + file input -->
				<div
					class="dropzone"
					class:is-dragging={isDragging}
					class:has-error={!!errors.file}
					role="button"
					tabindex="0"
					onclick={() => fileInputEl?.click()}
					onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInputEl?.click(); } }}
					ondrop={onDrop}
					ondragover={onDragOver}
					ondragleave={onDragLeave}
				>
					<input
						bind:this={fileInputEl}
						type="file"
						class="visually-hidden"
						onchange={onFileChange}
						accept="image/*,video/*,application/pdf"
					/>
					{#if previewUrl}
						<img src={previewUrl} alt="" class="dropzone-preview" />
					{:else if fileValue}
						<div class="dropzone-filename">
							<span class="dropzone-fileicon" aria-hidden="true">📄</span>
							<span>{fileValue.name}</span>
						</div>
					{:else}
						<div class="dropzone-prompt">
							<span class="dropzone-icon" aria-hidden="true">↑</span>
							<span class="dropzone-text">
								<strong>Click to choose</strong> or drag a file here
							</span>
							<span class="dropzone-hint">Images, video, PDF — up to 25 MB</span>
						</div>
					{/if}
				</div>
				{#if errors.file}
					<p class="field-error">{errors.file}</p>
				{/if}

				<!-- OR URL -->
				<div class="or-divider"><span>or</span></div>

				<input
					type="url"
					class="input--search"
					class:has-error={!!errors.url}
					bind:value={urlValue}
					placeholder="https://example.org/document.pdf"
					autocomplete="off"
				/>
				{#if errors.url}
					<p class="field-error">{errors.url}</p>
				{/if}
			</fieldset>

			<!-- Description -->
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
					placeholder="What's in this file? Any context that matters."
				/>
				<div class="field-counter" aria-live="polite">
					{description.length} / {MAX_DESC}
				</div>
				{#if errors.description}
					<p class="field-error">{errors.description}</p>
				{/if}
			</div>

			<!-- Visibility -->
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
				>{saving ? 'Saving…' : isEdit ? 'Save changes' : 'Upload'}</button>
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

	/* === Form-level error === */
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
	.source-fieldset {
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		padding: 0.85rem 1rem 1rem 1rem;
		margin: 0;
	}
	.source-fieldset legend {
		font-size: 0.85rem;
		font-weight: 600;
		color: var(--color-text);
		padding: 0 0.35rem;
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

	/* === Drop zone === */
	.dropzone {
		position: relative;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 130px;
		padding: 1.25rem;
		border: 2px dashed var(--color-border-light);
		border-radius: var(--radius-card);
		background: var(--color-surface);
		cursor: pointer;
		transition: border-color 0.15s ease, background 0.15s ease;
	}
	.dropzone:hover,
	.dropzone:focus-visible {
		border-color: var(--color-primary);
		background: var(--color-primary-tint);
		outline: none;
	}
	.dropzone.is-dragging {
		border-color: var(--color-primary);
		background: var(--color-primary-tint);
	}
	.dropzone.has-error {
		border-color: var(--color-danger);
	}
	.visually-hidden {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
		border: 0;
	}

	.dropzone-prompt {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.4rem;
		text-align: center;
		color: var(--color-text-muted);
	}
	.dropzone-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 36px;
		height: 36px;
		border-radius: 50%;
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		color: var(--color-primary);
		font-weight: 700;
		font-size: 1.1rem;
	}
	.dropzone-text { font-size: 0.92rem; }
	.dropzone-text strong { color: var(--color-text); font-weight: 600; }
	.dropzone-hint { font-size: 0.78rem; }

	.dropzone-preview {
		max-width: 100%;
		max-height: 200px;
		border-radius: var(--radius-card);
		object-fit: contain;
	}
	.dropzone-filename {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.9rem;
		color: var(--color-text);
	}
	.dropzone-fileicon {
		font-size: 1.4rem;
	}

	.or-divider {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin: 0.6rem 0 0.4rem 0;
		color: var(--color-text-muted);
		font-size: 0.78rem;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
	}
	.or-divider::before,
	.or-divider::after {
		content: '';
		flex: 1 1 auto;
		height: 1px;
		background: var(--color-border-light);
	}

	/* === Actions === */
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
		.dropzone,
		.modal,
		.modal-overlay {
			transition: none;
		}
	}
</style>