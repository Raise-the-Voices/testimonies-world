<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import { user, isVolunteer, isAdvocate } from '$lib/session';
	import { testimonialsList } from '$lib/api/generated/endpoints';
	import TestimonialCard from '$lib/TestimonialCard.svelte';
	import Skeleton from '$lib/Skeleton.svelte';
	import type { Paginated } from '$lib/types';
	import type { TestimonialPublic } from '$lib/api/generated/endpoints.schemas';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// SSR-hydrated auth — see +layout.svelte for the full rationale.
	let currentUser = $derived(data.user ?? $user);
	let canReview = $derived(isAdvocate(currentUser));

	/* Tab state. The default `published` tab always shows the public
	   list (SSR-baked in `data.testimonials`). The `mine` and `review`
	   tabs require an authenticated request and so are client-fetched.

	   Hash routing instead of query-string so the back button stays
	   sensible and the URL stays clean for the public. */
	type Tab = 'published' | 'mine' | 'review' | 'rejected';
	let activeTab = $state<Tab>('published');

	/* Auth-gated tabs only render for authenticated users. Volunteers
	   can have `mine` (their own drafts). Review tab is Advocate-only
	   because drafts/under_review queue is staff territory. The
	   Rejected tab is open to every authenticated user — a Volunteer
	   sees their own rejected rows (the rejection reason is their
	   actionable feedback), and an Advocate sees the full rejection
	   backlog (useful for periodic re-review and archival planning). */
	const showMineTab = $derived(currentUser.authenticated);
	const showReviewTab = $derived(canReview);
	const showRejectedTab = $derived(currentUser.authenticated);

	/* Wire-shape extends TestimonialPublic with the workflow metadata
	   fields returned by `TestimonialInternalSerializer` (the
	   serializer authed GETs receive). The public serializer is what
	   anonymous users get and doesn't include `review_notes`; the
	   rejected tab is auth-only, so widening the type here is safe.
	   Same widening pattern used in [id]/+page.svelte and the
	   WorkflowActions card. */
	type TestimonialWithWorkflow = TestimonialPublic & {
		readonly review_notes?: string;
		readonly reviewed_at?: string | null;
	};

	/* Mine-tab client-side state — fetched lazily on tab activation.
	   The Internal serializer omits `created_by_username` for the
	   canonical record (the OpenAPI spec doesn't include it), so we
	   keep the same shape across all three lists and use the published
	   tab as the canonical "what's visible publicly" surface. */
	let mineList: TestimonialWithWorkflow[] = $state([]);
	let mineLoading = $state(false);
	let mineError = $state<string | null>(null);

	/* Rejected-tab state. Same auth-gated lazy-fetch pattern as the
	   mine + review tabs — the one-shot sentinel stops the loading
	   state from looping on empty result sets. */
	let rejectedList: TestimonialWithWorkflow[] = $state([]);
	let rejectedLoading = $state(false);
	let rejectedError = $state<string | null>(null);
	let rejectedAttempted = $state(false);

	// `mineAttempted` / `reviewAttempted` / `rejectedAttempted` are
	// one-shot sentinels that gate the lazy fetch. The earlier
	// pattern used `$effect` with `length === 0` as the trigger,
	// which re-fired infinitely when the backend returned an empty
	// list — keeping the loading state on forever. The sentinel
	// flips to true once a fetch has been kicked off for the
	// current auth session.
	let mineAttempted = $state(false);
	let reviewAttempted = $state(false);

	async function loadMine() {
		if (!currentUser.authenticated) return;
		mineLoading = true;
		mineError = null;
		try {
			// Narrow to the requester's own drafts on the server. The
			// backend's `?status=draft` filter intersects with role-
			// based scoping (Volunteer → own rows at that status;
			// Advocate+ → all rows at that status). Without this
			// param the page would receive `(own drafts ∪ all
			// PUBLISHED)` — the published rows are noise in the
			// "My drafts" tab.
			const res = await testimonialsList({ status: 'draft' });
			// Response-shape note: orval's type says `testimonialsList()`
			// returns {data, status, headers}, but the actual DRF
			// response body IS the paginated list directly. Reading
			// `res.data` always yields `undefined` on a real response
			// and the "My drafts" tab silently shows empty. Treat the
			// response as the paginated body — same pattern I applied
			// in the create form (9b11b51) and detail page (e3c8527).
			const body = (res as unknown as Paginated<TestimonialWithWorkflow>).results ?? [];
			mineList = body;
			// For an Advocate, `mine` would otherwise overlap with
			// the review queue (they see everything). Empty it for
			// staff so the tab isn't a duplicate of "Review queue"
			// until the backend exposes a created_by_username filter.
			if (canReview) mineList = [];
		} catch (e) {
			mineError = e instanceof Error ? e.message : 'Failed to load your drafts.';
		} finally {
			mineLoading = false;
		}
	}

	/* Review-queue client-side state. Only fetched when the review tab
	   is active AND user is Advocate+. The queue shows everything not
	   currently `published` or `archived` so reviewers can see what
	   needs attention. */
	let reviewList: TestimonialPublic[] = $state([]);
	let reviewLoading = $state(false);
	let reviewError = $state<string | null>(null);

	async function loadReview() {
		if (!canReview) return;
		reviewLoading = true;
		reviewError = null;
		try {
			// Narrow to under_review rows on the server. Without
			// this filter the Advocate would receive every status
			// (draft + approved + published + archived + rejected)
			// and the "Review queue" tab would have to bucket-
			// filter client-side — wasteful and slow on a busy queue.
			const res = await testimonialsList({ status: 'under_review' });
			// Response-shape note: same orval-vs-DRF mismatch as
			// loadMine — read the response as the paginated body.
			const body = (res as unknown as Paginated<TestimonialPublic>).results ?? [];
			reviewList = body;
		} catch (e) {
			reviewError = e instanceof Error ? e.message : 'Failed to load review queue.';
		} finally {
			reviewLoading = false;
		}
	}

	/* Rejected-tab loader. Visible to every authenticated user; the
	   backend's `?status=rejected` filter intersects with role-based
	   scoping (Volunteer → own rejected rows; Advocate+ → every
	   rejected row). Same one-shot sentinel pattern as loadMine. */
	async function loadRejected() {
		if (!currentUser.authenticated) return;
		rejectedLoading = true;
		rejectedError = null;
		try {
			const res = await testimonialsList({ status: 'rejected' });
			const body =
				(res as unknown as Paginated<TestimonialWithWorkflow>).results ?? [];
			rejectedList = body;
		} catch (e) {
			rejectedError =
				e instanceof Error ? e.message : 'Failed to load rejected testimonials.';
		} finally {
			rejectedLoading = false;
		}
	}

	$effect(() => {
		// Re-fires when auth changes OR tab changes; we only want the
		// fetch to happen on a real signal (tab activation, not
		// reactive emptiness), so we read the values but use the
		// per-tab attempted sentinel as the gate.
		void currentUser.authenticated;
		void activeTab;

		// Reset on auth changes so a fresh login refetches. The
		// 'activeTab' dependency already triggers a re-run when the
		// user clicks a tab, so resetting only on auth flips is the
		// minimum needed.
		if (!currentUser.authenticated) {
			mineAttempted = false;
			reviewAttempted = false;
			rejectedAttempted = false;
			return;
		}

		if (
			activeTab === 'mine' &&
			showMineTab &&
			!mineAttempted &&
			!mineLoading
		) {
			mineAttempted = true;
			loadMine();
		}
		if (
			activeTab === 'review' &&
			showReviewTab &&
			!reviewAttempted &&
			!reviewLoading
		) {
			reviewAttempted = true;
			loadReview();
		}
		if (
			activeTab === 'rejected' &&
			showRejectedTab &&
			!rejectedAttempted &&
			!rejectedLoading
		) {
			rejectedAttempted = true;
			loadRejected();
		}
	});
</script>

<svelte:head>
	<title>Testimonials — Testimonies.world</title>
	<meta
		name="description"
		content="Published testimonial accounts — human rights cases documented for the public record."
	/>
	<meta property="og:type" content="website" />
</svelte:head>

<div class="testimonials-page">
	<header class="page-header">
		<div class="page-header-text">
			<h1>Testimonials</h1>
			<p class="page-subtitle">
				Published accounts of cases documented through the platform. Sensitive source
				identities are protected; only roles that need to verify sources can read them.
			</p>
		</div>
		{#if currentUser.authenticated}
			<a class="btn btn-primary page-header-action" href="{base}/testimonials/new">
				New testimonial
			</a>
		{:else}
			<a class="btn btn-secondary page-header-action" href="{base}/accounts/google/login/?next={base}/testimonials">
				Sign in to submit
			</a>
		{/if}
	</header>

	<nav class="testimonials-tabs" aria-label="Testimonials sections">
		<button
			type="button"
			class="testimonials-tab"
			class:testimonials-tab-active={activeTab === 'published'}
			aria-current={activeTab === 'published' ? 'page' : undefined}
			onclick={() => (activeTab = 'published')}
		>
			Published
			<span class="testimonials-tab-count">{data.count ?? data.testimonials.length}</span>
		</button>

		{#if showMineTab}
			<button
				type="button"
				class="testimonials-tab"
				class:testimonials-tab-active={activeTab === 'mine'}
				aria-current={activeTab === 'mine' ? 'page' : undefined}
				onclick={() => (activeTab = 'mine')}
			>
				My drafts
				{#if mineList.length > 0}<span class="testimonials-tab-count">{mineList.length}</span>{/if}
			</button>
		{/if}

		{#if showReviewTab}
			<button
				type="button"
				class="testimonials-tab"
				class:testimonials-tab-active={activeTab === 'review'}
				aria-current={activeTab === 'review' ? 'page' : undefined}
				onclick={() => (activeTab = 'review')}
			>
				Review queue
				{#if reviewList.length > 0}<span class="testimonials-tab-count">{reviewList.length}</span>{/if}
			</button>
		{/if}

		{#if showRejectedTab}
			<button
				type="button"
				class="testimonials-tab"
				class:testimonials-tab-active={activeTab === 'rejected'}
				aria-current={activeTab === 'rejected' ? 'page' : undefined}
				onclick={() => (activeTab = 'rejected')}
			>
				Rejected
				{#if rejectedList.length > 0}<span class="testimonials-tab-count">{rejectedList.length}</span>{/if}
			</button>
		{/if}
	</nav>

	{#if activeTab === 'published'}
		{#if data.error}
			<div class="error-state" role="alert">
				<p>Could not load testimonials: {data.error}</p>
			</div>
		{:else if data.testimonials.length === 0}
			<div class="empty-state">
				<p>No published testimonials yet.</p>
			</div>
		{:else}
			<div class="testimonials-grid">
				{#each data.testimonials as t (t.id)}
					<TestimonialCard testimonial={t} />
				{/each}
			</div>
		{/if}
	{:else if activeTab === 'mine'}
		{#if !currentUser.authenticated}
			<div class="empty-state">
				<p>Sign in to see your drafts.</p>
			</div>
		{:else if mineLoading}
			<div class="testimonials-grid" aria-busy="true">
				<Skeleton variant="card" />
				<Skeleton variant="card" />
				<Skeleton variant="card" />
			</div>
		{:else if mineError}
			<div class="error-state" role="alert">
				<p>Could not load your drafts: {mineError}</p>
			</div>
		{:else if mineList.length === 0}
			<div class="empty-state">
				<p>You don't have any drafts yet.</p>
				<a class="btn btn-primary" href="{base}/testimonials/new">Start one</a>
			</div>
		{:else}
			<div class="testimonials-grid">
				{#each mineList as t (t.id)}
					<TestimonialCard testimonial={t} showStatus />
				{/each}
			</div>
		{/if}
	{:else if activeTab === 'review'}
		{#if !canReview}
			<div class="empty-state">
				<p>The review queue is reserved for Advocate and Admin roles.</p>
			</div>
		{:else if reviewLoading}
			<div class="testimonials-grid" aria-busy="true">
				<Skeleton variant="card" />
				<Skeleton variant="card" />
				<Skeleton variant="card" />
			</div>
		{:else if reviewError}
			<div class="error-state" role="alert">
				<p>Could not load the review queue: {reviewError}</p>
			</div>
		{:else if reviewList.length === 0}
			<div class="empty-state">
				<p>The queue is empty. Nothing pending review.</p>
			</div>
		{:else}
			<div class="testimonials-grid">
				{#each reviewList as t (t.id)}
					<TestimonialCard testimonial={t} showStatus />
				{/each}
			</div>
		{/if}
	{:else if activeTab === 'rejected'}
		{#if !currentUser.authenticated}
			<div class="empty-state">
				<p>Sign in to see rejected testimonials.</p>
			</div>
		{:else if rejectedLoading}
			<div class="testimonials-grid" aria-busy="true">
				<Skeleton variant="card" />
				<Skeleton variant="card" />
				<Skeleton variant="card" />
			</div>
		{:else if rejectedError}
			<div class="error-state" role="alert">
				<p>Could not load rejected testimonials: {rejectedError}</p>
			</div>
		{:else if rejectedList.length === 0}
			<div class="empty-state">
				<p>Nothing has been rejected yet.</p>
			</div>
		{:else}
			<div class="testimonials-grid">
				{#each rejectedList as t (t.id)}
					<div class="rejected-card-wrap">
						<TestimonialCard testimonial={t} showStatus />
						<!-- The rejection reason is the actionable
						     signal for the submitter (Volunteer sees
						     their own feedback) and the audit trail
						     for reviewers. Backend requires
						     `review_notes` non-empty at reject time
						     (TestimonialViewSet.reject), so a
						     missing reason here is a real bug
						     worth surfacing. -->
						{#if t.review_notes}
							<aside class="rejection-reason" aria-label="Rejection reason">
								<header class="rejection-reason-header">
									<span class="rejection-reason-label">Rejection reason</span>
									{#if t.reviewed_at}
										<time class="rejection-reason-date" datetime={t.reviewed_at}>
											{new Date(t.reviewed_at).toLocaleDateString(undefined, {
												year: 'numeric',
												month: 'short',
												day: 'numeric',
											})}
										</time>
									{/if}
								</header>
								<p class="rejection-reason-text">{t.review_notes}</p>
							</aside>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	{/if}
</div>

<style>
	.testimonials-page {
		width: 100%;
		max-width: var(--max-w-page);
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-end;
		gap: 1rem;
		flex-wrap: wrap;
		padding-bottom: 0.75rem;
		border-bottom: 1px solid var(--color-border-light);
	}
	.page-header-text {
		flex: 1 1 320px;
		min-width: 0;
	}
	.page-header h1 {
		margin: 0 0 0.25rem 0;
		color: var(--color-primary);
	}
	.page-subtitle {
		margin: 0;
		color: var(--color-text-muted);
		font-size: 0.95rem;
		max-width: var(--max-w-prose);
		line-height: 1.55;
	}
	.page-header-action {
		flex: 0 0 auto;
		white-space: nowrap;
	}

	/* Tab nav: same segmented-control pattern used on /persons.
	   `role="tablist"` semantics live on the parent <nav>; per-button
	   aria-current="page" tells AT users which tab is active. */
	.testimonials-tabs {
		display: flex;
		gap: 0.4rem;
		flex-wrap: wrap;
		border-bottom: 1px solid var(--color-border-light);
		padding-bottom: 0.4rem;
	}
	.testimonials-tab {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 0.85rem;
		background: transparent;
		border: 1px solid transparent;
		border-radius: var(--radius-card);
		font-size: 0.88rem;
		font-weight: 700;
		color: var(--color-text-muted);
		cursor: pointer;
	}
	.testimonials-tab:hover {
		background: var(--color-section-bg);
	}
	.testimonials-tab-active {
		background: var(--color-bg-white);
		border-color: var(--color-primary-light);
		color: var(--color-primary);
	}
	.testimonials-tab-count {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 1.25rem;
		padding: 0 0.4rem;
		height: 1.25rem;
		background: var(--color-section-bg);
		color: var(--color-primary);
		border-radius: 999px;
		font-size: 0.72rem;
	}
	.testimonials-tab-active .testimonials-tab-count {
		background: var(--color-primary);
		color: var(--color-text-light);
	}

	/* Grid: 1 column on mobile (cards are already self-contained,
	   no row alignment pressure), 2 columns >=700px, 3 columns >=1100px. */
	.testimonials-grid {
		display: grid;
		grid-template-columns: 1fr;
		gap: 1.25rem;
	}
	@media (min-width: 700px) {
		.testimonials-grid {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	@media (min-width: 1100px) {
		.testimonials-grid {
			grid-template-columns: repeat(3, minmax(0, 1fr));
		}
	}

	.empty-state,
	.error-state {
		padding: 2.5rem 1.25rem;
		text-align: center;
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		color: var(--color-text-muted);
	}
	.empty-state .btn {
		margin-top: 0.75rem;
	}
	.error-state {
		border-left: 3px solid var(--color-danger);
		text-align: left;
	}

	/* Rejected tab — each card is wrapped so the rejection reason
	   sits flush against its card and reads as a continuation of
	   the same record rather than a separate row. */
	.rejected-card-wrap {
		display: flex;
		flex-direction: column;
		gap: 0;
	}

	.rejection-reason {
		margin-top: -1px; /* tuck under the card's border-radius edge */
		padding: 0.85rem 1rem 0.95rem;
		background: #fef2f2;
		border: 1px solid var(--color-danger);
		border-top: 0;
		border-radius: 0 0 var(--radius-card) var(--radius-card);
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}

	.rejection-reason-header {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.rejection-reason-label {
		font-size: 0.72rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		color: var(--color-danger);
	}

	.rejection-reason-date {
		font-size: 0.72rem;
		color: #9b2c2c;
		font-variant-numeric: tabular-nums;
	}

	.rejection-reason-text {
		margin: 0;
		font-size: 0.92rem;
		line-height: 1.5;
		color: #7b1f1f;
		white-space: pre-line;
	}
</style>
