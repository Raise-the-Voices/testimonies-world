<script lang="ts">
	import { base } from '$app/paths';
	import { user, isAdvocate } from '$lib/session';
	import {
		testimonialsList,
		testimonialsApproveCreate,
		testimonialsRejectCreate,
		testimonialsPublishCreate,
		testimonialsArchiveCreate,
		testimonialsSubmitCreate,
	} from '$lib/api/generated/endpoints';
	import type { Paginated } from '$lib/types';
	import type { TestimonialPublic } from '$lib/api/generated/endpoints.schemas';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let currentUser = $derived(data.user ?? $user);
	let canReview = $derived(isAdvocate(currentUser));

	let rows: TestimonialPublic[] = $state([]);
	let loading = $state(false);
	let error = $state<string | null>(null);

	// One-shot sentinel: fetch the queue ONCE per mount (or per auth
	// change), not on every $effect re-run. Without this, the
	// `rows.length === 0` check below re-fired infinitely whenever
	// the backend returned an empty list — driving the
	// "Loading queue…" UI in an endless cycle. `didAttempt` flips
	// to true the first time we kick off loadAll(); the refresh
	// button below resets it.
	let didAttempt = $state(false);

	// Per-row action state. `busyId` ensures only one transition is in
	// flight at a time and that the row is visually marked as
	// "in-flight" so the reviewer doesn't double-click.
	let busyId = $state<number | null>(null);
	let actionError = $state<string | null>(null);

	// The reject dialog (review_notes required per the backend
	// transition rule) lives inline rather than as a separate modal —
	// keeps the surface area low for v1.
	let rejectTarget = $state<number | null>(null);
	let rejectNotes = $state('');
	let rejectSaving = $state(false);

	async function loadAll() {
		loading = true;
		error = null;
		// Hard ceiling on how long the loading state can be shown for
		// a single fetch. Without this, a server-side hang (DB
		// connection pool exhausted, broker timeout) leaves the UI
		// stuck on 'Loading queue…' indefinitely. 10s is short
		// enough to be obvious, long enough that a slow response
		// from the API doesn't false-positive.
		const TIMEOUT_MS = 10_000;
		let timedOut = false;
		const timer = setTimeout(() => {
			timedOut = true;
			error = 'The queue did not load in time. Please retry.';
			loading = false;
		}, TIMEOUT_MS);
		try {
			const res = await testimonialsList();
			if (timedOut) return; // timer already settled state
			clearTimeout(timer);
			const body = (res as { data?: Paginated<TestimonialPublic> }).data;
			rows = body?.results ?? [];
		} catch (e) {
			if (timedOut) return;
			clearTimeout(timer);
			error = e instanceof Error ? e.message : 'Failed to load the queue.';
		} finally {
			if (!timedOut) loading = false;
		}
	}

	async function runAction(
		id: number,
		action: 'submit' | 'approve' | 'publish' | 'archive',
		notes?: string
	) {
		if (busyId !== null) return;
		busyId = id;
		actionError = null;
		try {
			switch (action) {
				case 'submit':
					await testimonialsSubmitCreate(id, {});
					break;
				case 'approve':
					await testimonialsApproveCreate(id, {});
					break;
				case 'publish':
					await testimonialsPublishCreate(id, {});
					break;
				case 'archive':
					await testimonialsArchiveCreate(id, {});
					break;
			}
			await loadAll();
		} catch (e) {
			actionError =
				e instanceof Error
					? `Action ${action} failed: ${e.message}`
					: `Action ${action} failed.`;
		} finally {
			busyId = null;
		}
	}

	async function submitReject() {
		if (rejectTarget === null) return;
		const notes = rejectNotes.trim();
		if (!notes) return;
		rejectSaving = true;
		actionError = null;
		try {
			// orval didn't generate a typed body param for the @action
			// endpoint (it falls back to RequestInit). Review_notes is
			// the backend's required field per the transition contract.
			await testimonialsRejectCreate(rejectTarget, {
				method: 'POST',
				body: JSON.stringify({ review_notes: notes }),
				headers: { 'Content-Type': 'application/json' },
			});
			rejectTarget = null;
			rejectNotes = '';
			await loadAll();
		} catch (e) {
			actionError =
				e instanceof Error ? `Reject failed: ${e.message}` : 'Reject failed.';
		} finally {
			rejectSaving = false;
		}
	}

	$effect(() => {
		void canReview;
		// Reset on auth change so a fresh login re-fetches (the user
		// may now see rows they couldn't before, and a fresh review
		// queue fetch reflects the new session's permissions).
		if (!canReview) {
			didAttempt = false;
			return;
		}
		// The `didAttempt` sentinel is the infinite-loading fix —
		// don't re-run loadAll() while rows is empty. Manual
		// refresh below resets didAttempt to retry.
		if (didAttempt) return;
		if (loading) return;
		didAttempt = true;
		loadAll();
	});

	// Buckets for the reviewer. `draft` and `under_review` are the
	// actionable work; `approved` is publish-ready; `published` and
	// `archived` are visible for context.
	const buckets = $derived(
		{
			draft: rows.filter((t) => t.status === 'draft'),
			under_review: rows.filter((t) => t.status === 'under_review'),
			approved: rows.filter((t) => t.status === 'approved'),
			published: rows.filter((t) => t.status === 'published'),
			rejected: rows.filter((t) => t.status === 'rejected'),
			archived: rows.filter((t) => t.status === 'archived'),
		} as Record<string, TestimonialPublic[]>
	);

	function formatDate(iso: string | null | undefined): string {
		if (!iso) return '';
		return new Date(iso).toLocaleDateString(undefined, {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
		});
	}
</script>

<svelte:head>
	<title>Review queue — Testimonies.world</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="review-page">
	<header class="page-header">
		<a href="{base}/testimonials" class="back-link">← Back to testimonials</a>
		<h1>Review queue</h1>
		<p class="page-subtitle">
			{#if !canReview}
				This page is reserved for Advocate and Admin roles.
				Volunteers can create drafts at
				<a href="{base}/testimonials/new">/testimonials/new</a> and track their
				status from <em>My drafts</em> on the testimonials index.
			{:else}
				Bucket rows by status. Approve / reject at the
				<strong>under_review</strong> stage; publish at <strong>approved</strong>;
				archive once a published row should be retired.
			{/if}
		</p>
	</header>

	{#if !canReview}
		<div class="empty-state">
			<p>You don't have permission to access the review queue.</p>
		</div>
	{:else if loading}
		<div class="loading" aria-busy="true">Loading queue…</div>
	{:else if error}
		<div class="error-state" role="alert">
			<p>{error}</p>
			<button type="button" class="btn btn-secondary" onclick={loadAll}>Retry</button>
		</div>
	{:else}
		{#if actionError}
			<div class="action-error" role="alert">{actionError}</div>
		{/if}

		<section class="bucket">
			<h2>Under review ({buckets.under_review.length})</h2>
			{#if buckets.under_review.length === 0}
				<p class="bucket-empty">No rows awaiting review.</p>
			{:else}
				{#each buckets.under_review as t (t.id)}
					<article class="row" class:row-busy={busyId === t.id}>
						<header class="row-header">
							<h3>
								<a href="{base}/testimonials/{t.id}">
									{t.title || 'Untitled testimonial'}
								</a>
							</h3>
							<span class="status-pill status-pill-under_review">
								{t.status.replace('_', ' ')}
							</span>
						</header>
						{#if t.summary}<p class="row-summary">{t.summary}</p>{/if}
						<dl class="row-meta">
							{#if t.country}<dt>Country</dt><dd>{t.country}{#if t.region}, {t.region}{/if}</dd>{/if}
							{#if t.incident_date}<dt>Incident</dt><dd>{formatDate(t.incident_date)}</dd>{/if}
							{#if t.source_visible && t.public_source_label}<dt>Source</dt><dd>{t.public_source_label}</dd>{/if}
						</dl>
						<div class="row-actions">
							<button
								type="button"
								class="btn btn-primary"
								disabled={busyId !== null}
								onclick={() => runAction(t.id, 'approve')}
							>
								{busyId === t.id ? 'Working…' : 'Approve'}
							</button>
							<button
								type="button"
								class="btn btn-danger"
								disabled={busyId !== null}
								onclick={() => {
									rejectTarget = t.id;
									rejectNotes = '';
								}}
							>
								Reject…
							</button>
						</div>
					</article>
				{/each}
			{/if}
		</section>

		<section class="bucket">
			<h2>Drafts ({buckets.draft.length})</h2>
			{#if buckets.draft.length === 0}
				<p class="bucket-empty">No drafts.</p>
			{:else}
				{#each buckets.draft as t (t.id)}
					<article class="row" class:row-busy={busyId === t.id}>
						<header class="row-header">
							<h3>
								<a href="{base}/testimonials/{t.id}">
									{t.title || 'Untitled testimonial'}
								</a>
							</h3>
							<span class="status-pill status-pill-draft">
								{t.status}
							</span>
						</header>
						{#if t.summary}<p class="row-summary">{t.summary}</p>{/if}
						<div class="row-actions">
							<button
								type="button"
								class="btn btn-secondary"
								disabled={busyId !== null}
								onclick={() => runAction(t.id, 'submit')}
							>
								Submit to review
							</button>
						</div>
					</article>
				{/each}
			{/if}
		</section>

		<section class="bucket">
			<h2>Approved &amp; ready to publish ({buckets.approved.length})</h2>
			{#if buckets.approved.length === 0}
				<p class="bucket-empty">No rows awaiting publish.</p>
			{:else}
				{#each buckets.approved as t (t.id)}
					<article class="row" class:row-busy={busyId === t.id}>
						<header class="row-header">
							<h3>
								<a href="{base}/testimonials/{t.id}">
									{t.title || 'Untitled testimonial'}
								</a>
							</h3>
							<span class="status-pill status-pill-approved">
								{t.status}
							</span>
						</header>
						<div class="row-actions">
							<button
								type="button"
								class="btn btn-primary"
								disabled={busyId !== null}
								onclick={() => runAction(t.id, 'publish')}
							>
								Publish
							</button>
						</div>
					</article>
				{/each}
			{/if}
		</section>

		<section class="bucket">
			<h2>Published ({buckets.published.length})</h2>
			{#if buckets.published.length === 0}
				<p class="bucket-empty">No published rows.</p>
			{:else}
				{#each buckets.published as t (t.id)}
					<article class="row">
						<header class="row-header">
							<h3>
								<a href="{base}/testimonials/{t.id}">
									{t.title || 'Untitled testimonial'}
								</a>
							</h3>
							<span class="status-pill status-pill-published">
								{t.status}
							</span>
						</header>
						<div class="row-actions">
							<a class="btn btn-secondary" href="{base}/testimonials/{t.id}">View public page</a>
							<button
								type="button"
								class="btn btn-secondary"
								disabled={busyId !== null}
								onclick={() => runAction(t.id, 'archive')}
							>
								Archive
							</button>
						</div>
					</article>
				{/each}
			{/if}
		</section>

		{#if buckets.rejected.length > 0 || buckets.archived.length > 0}
			<section class="bucket">
				<h2>Recent rejections &amp; archives</h2>
				{#each buckets.rejected.concat(buckets.archived) as t (t.id)}
					<article class="row row-muted">
						<header class="row-header">
							<h3>
								<a href="{base}/testimonials/{t.id}">
									{t.title || 'Untitled testimonial'}
								</a>
							</h3>
							<span class="status-pill status-pill-{t.status === 'rejected' ? 'rejected' : 'archived'}">
								{t.status}
							</span>
						</header>
					</article>
				{/each}
			</section>
		{/if}

		<section class="refresh-row">
			<button
				type="button"
				class="btn btn-secondary"
				onclick={() => {
					didAttempt = false;
					loadAll();
				}}
				disabled={loading}
			>
				Refresh
			</button>
		</section>
	{/if}
</div>

{#if rejectTarget !== null}
	<div
		class="modal-backdrop"
		role="dialog"
		aria-modal="true"
		aria-labelledby="reject-title"
	>
		<div class="modal">
			<h2 id="reject-title">Reject testimonial #{rejectTarget}</h2>
			<p>
				Rejection requires a reason. The submitter will see this note on their
				draft.
			</p>
			<label class="modal-label" for="reject-notes">Reason</label>
			<textarea
				id="reject-notes"
				rows="4"
				bind:value={rejectNotes}
				placeholder="e.g. Source unreliable; needs re-verification."
			></textarea>
			<div class="modal-actions">
				<button
					type="button"
					class="btn btn-secondary"
					onclick={() => {
						rejectTarget = null;
						rejectNotes = '';
					}}
				>
					Cancel
				</button>
				<button
					type="button"
					class="btn btn-danger"
					disabled={!rejectNotes.trim() || rejectSaving}
					onclick={submitReject}
				>
					{rejectSaving ? 'Rejecting…' : 'Reject'}
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.review-page {
		max-width: var(--max-w-page);
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	.page-header h1 {
		margin: 0.25rem 0 0.5rem 0;
		color: var(--color-primary);
	}
	.page-subtitle {
		margin: 0;
		color: var(--color-text-muted);
		max-width: var(--max-w-prose);
		line-height: 1.55;
	}
	.back-link {
		color: var(--color-primary);
		text-decoration: none;
		font-size: 0.9rem;
	}
	.back-link:hover {
		text-decoration: underline;
	}

	.loading,
	.empty-state,
	.error-state,
	.action-error {
		padding: 1.25rem;
		text-align: center;
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		color: var(--color-text-muted);
	}
	.action-error {
		border-left: 3px solid var(--color-danger);
		color: var(--color-danger);
		background: #fef2f2;
		text-align: left;
	}
	.error-state {
		border-left: 3px solid var(--color-danger);
		text-align: left;
	}

	.bucket {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}
	.bucket h2 {
		margin: 0;
		font-size: 0.85rem;
		text-transform: uppercase;
		letter-spacing: 0.08rem;
		color: var(--color-text-muted);
		padding-bottom: 0.4rem;
		border-bottom: 1px solid var(--color-border-light);
	}
	.bucket-empty {
		margin: 0;
		padding: 0.75rem 1rem;
		font-size: 0.9rem;
		color: var(--color-text-muted);
	}

	.row {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		padding: 1rem 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		transition: opacity 0.15s ease;
	}
	.row-busy {
		opacity: 0.6;
		pointer-events: none;
	}
	.row-muted {
		opacity: 0.7;
	}

	.row-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
		flex-wrap: wrap;
	}
	.row-header h3 {
		margin: 0;
		font-size: 1.05rem;
	}
	.row-header a {
		color: var(--color-primary);
		text-decoration: none;
	}
	.row-header a:hover {
		text-decoration: underline;
	}
	.row-summary {
		margin: 0;
		font-size: 0.92rem;
		color: var(--color-text);
		line-height: 1.5;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
	.row-meta {
		display: grid;
		grid-template-columns: max-content 1fr;
		gap: 0.2rem 0.6rem;
		font-size: 0.82rem;
		margin: 0;
	}
	.row-meta dt {
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.04rem;
		font-size: 0.7rem;
		font-weight: 700;
	}
	.row-meta dd {
		margin: 0;
	}
	.row-actions {
		display: flex;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.status-pill {
		display: inline-block;
		padding: 0.15rem 0.55rem;
		border-radius: 999px;
		font-size: 0.72rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.04rem;
	}
	.status-pill-draft {
		background: #f1f5f9;
		color: #475569;
	}
	.status-pill-under_review {
		background: #fef3c7;
		color: #92400e;
	}
	.status-pill-approved {
		background: #dcfce7;
		color: #15803d;
	}
	.status-pill-published {
		background: var(--color-primary);
		color: var(--color-text-light);
	}
	.status-pill-rejected {
		background: #fee2e2;
		color: #b91c1c;
	}
	.status-pill-archived {
		background: #e5e7eb;
		color: #4b5563;
	}

	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.4);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
		padding: 1rem;
	}
	.modal {
		background: var(--color-bg-white);
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-card-lg);
		padding: 1.5rem;
		max-width: 32rem;
		width: 100%;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}
	.modal h2 {
		margin: 0;
		font-size: 1.1rem;
		color: var(--color-primary);
	}
	.modal p {
		margin: 0;
		color: var(--color-text-muted);
		font-size: 0.92rem;
	}
	.modal-label {
		font-size: 0.85rem;
		font-weight: 700;
	}
	.modal textarea {
		font: inherit;
		padding: 0.5rem 0.65rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-input);
		resize: vertical;
		min-height: 5em;
	}
	.modal-actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.5rem;
	}

	.refresh-row {
		display: flex;
		justify-content: flex-end;
		margin-top: 0.5rem;
	}
</style>
