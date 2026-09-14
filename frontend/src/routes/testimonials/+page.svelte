<script lang="ts">
	import { afterNavigate } from '$app/navigation';
	import { base } from '$app/paths';
	import { testimonialsList } from '$lib/api/generated/endpoints';
	import {
		TestimonialsListStatus,
		type TestimonialPublic,
	} from '$lib/api/generated/endpoints.schemas';
	import { isAdvocate, user } from '$lib/session';
	import Skeleton from '$lib/Skeleton.svelte';
	import TestimonialCard from '$lib/TestimonialCard.svelte';
	import type { Paginated } from '$lib/types';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// SSR-hydrated auth — see +layout.svelte for the full rationale.
	let currentUser = $derived(data.user ?? $user);
	let canReview = $derived(isAdvocate(currentUser));

	/* ---------------------------------------------------------------------------
	   Tab model

	   Each tab is one row in `CLIENT_TABS`. The config carries everything the
	   template needs to render it (visibility, copy, status filter, empty-state
	   CTA) so the markup can be a single {#each} / state-machine render rather
	   than a cascade of per-tab branches. Adding a fourth tab is one row.

	   The `published` tab is special: its data is SSR-baked into `data.testimonials`
	   and so it doesn't share the client-tab state machine — it has its own
	   short render branch.
	   --------------------------------------------------------------------------- */
	type TabKey = 'published' | 'mine' | 'review' | 'rejected';
	type ClientTabKey = Exclude<TabKey, 'published'>;
	type ClientTabStatus =
		| typeof TestimonialsListStatus.draft
		| typeof TestimonialsListStatus.under_review
		| typeof TestimonialsListStatus.rejected;

	type TestimonialWithWorkflow = TestimonialPublic & {
		readonly review_notes?: string;
		readonly reviewed_at?: string | null;
	};

	type EmptyAction = { label: string; href: string };

	type ClientTab = {
		key: ClientTabKey;
		label: string;
		status: ClientTabStatus;
		visible: boolean;
		errorMessage: string;
		emptyMessage: string;
		emptyAction?: EmptyAction;
	};

	const CLIENT_TABS = $derived<ClientTab[]>([
		{
			key: 'mine',
			label: 'My drafts',
			status: TestimonialsListStatus.draft,
			visible: currentUser.authenticated,
			errorMessage: 'Could not load your drafts',
			emptyMessage: "You don't have any drafts yet.",
			emptyAction: { label: 'Start one', href: `${base}/testimonials/new` },
		},
		{
			key: 'review',
			label: 'Review queue',
			status: TestimonialsListStatus.under_review,
			visible: canReview,
			errorMessage: 'Could not load the review queue',
			emptyMessage: 'The queue is empty. Nothing pending review.',
		},
		{
			key: 'rejected',
			label: 'Rejected',
			status: TestimonialsListStatus.rejected,
			visible: currentUser.authenticated,
			errorMessage: 'Could not load rejected testimonials',
			emptyMessage: 'Nothing has been rejected yet.',
		},
	]);

	let activeTab = $state<TabKey>('published');

	/* ---------------------------------------------------------------------------
	   Per-tab fetch state

	   One state record replaces three sets of (list / loading / error / attempted)
       state. Svelte 5 makes nested `$state` properties reactive, so
       `tabState.mine.loading = true` propagates to badge counts and the render
       branch without explicit invalidation.

       The `attempted` sentinel gates re-fetches: the first call flips it true,
       subsequent calls become no-ops. `afterNavigate` re-arms it on cross-route
       nav so badges re-sync after, e.g., creating a new draft and returning.
	   --------------------------------------------------------------------------- */
	type TabState = {
		list: TestimonialWithWorkflow[];
		loading: boolean;
		error: string | null;
		attempted: boolean;
	};
	const newTabState = (): TabState => ({
		list: [],
		loading: false,
		error: null,
		attempted: false,
	});
	let tabState = $state<Record<ClientTabKey, TabState>>({
		mine: newTabState(),
		review: newTabState(),
		rejected: newTabState(),
	});

	async function loadTab(key: ClientTabKey): Promise<void> {
		const tab = CLIENT_TABS.find((t) => t.key === key);
		if (!tab?.visible) return;
		const s = tabState[key];
		s.loading = true;
		s.error = null;
		try {
			// orval-vs-DRF shape mismatch: `testimonialsList()` is typed as
			// returning {data, status, headers} but DRF sends the paginated
			// body directly. Reading `res.data` is always undefined; treat
			// the response as the paginated body. Same pattern in
			// testimonials/new and [id]/+page.svelte.
			const res = await testimonialsList({ status: tab.status });
			const body =
				(res as unknown as Paginated<TestimonialWithWorkflow>).results ?? [];
			s.list = body;
		} catch (e) {
			s.error = e instanceof Error ? e.message : `${tab.errorMessage}.`;
		} finally {
			s.loading = false;
		}
	}

	/* ---------------------------------------------------------------------------
	   Fetch orchestration

	   Eagerly kick off fetchers for every visible client-tab as soon as auth
	   is known so badge counts populate before the user ever clicks a tab.
	   On logout, reset state so a fresh login refetches.
	   --------------------------------------------------------------------------- */
	$effect(() => {
		void currentUser.authenticated;

		if (!currentUser.authenticated) {
			for (const key of Object.keys(tabState) as ClientTabKey[]) {
				const s = tabState[key];
				s.list = [];
				s.error = null;
				s.attempted = false;
			}
			return;
		}

		for (const tab of CLIENT_TABS) {
			if (!tab.visible) continue;
			const s = tabState[tab.key];
			if (s.attempted || s.loading) continue;
			s.attempted = true;
			loadTab(tab.key);
		}
	});

	// Re-arm the one-shot sentinels on cross-route nav so cache refetches
	// after, e.g., creating a new draft. Defense-in-depth: SvelteKit usually
	// re-mounts +page.svelte on cross-route nav.
	afterNavigate(({ from, to }) => {
		if (from?.url.pathname !== to?.url.pathname) {
			for (const key of Object.keys(tabState) as ClientTabKey[]) {
				tabState[key].attempted = false;
			}
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

{#snippet cardGrid(items: TestimonialPublic[], showStatus: boolean)}
	<div class="testimonials-grid">
		{#each items as t (t.id)}
			<TestimonialCard testimonial={t} {showStatus} />
		{/each}
	</div>
{/snippet}

{#snippet rejectedCard(t: TestimonialWithWorkflow)}
	<div class="rejected-card-wrap">
		<TestimonialCard testimonial={t} showStatus />
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
{/snippet}

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
			<a
				class="btn btn-secondary page-header-action"
				href="{base}/accounts/google/login/?next={base}/testimonials"
			>
				Sign in to submit
			</a>
		{/if}
	</header>

	<nav class="testimonials-tabs" aria-label="Testimonials sections">
		{#each CLIENT_TABS as tab (tab.key)}
			{#if tab.visible}
				<button
					type="button"
					class="testimonials-tab"
					class:testimonials-tab-active={activeTab === tab.key}
					role="tab"
					aria-selected={activeTab === tab.key}
					aria-controls="testimonials-panel"
					id="testimonials-tab-{tab.key}"
					onclick={() => (activeTab = tab.key)}
				>
					{tab.label}
					<span class="testimonials-tab-count">{tabState[tab.key].list.length}</span>
				</button>
			{/if}
		{/each}

		<button
			type="button"
			class="testimonials-tab"
			class:testimonials-tab-active={activeTab === 'published'}
			role="tab"
			aria-selected={activeTab === 'published'}
			aria-controls="testimonials-panel"
			id="testimonials-tab-published"
			onclick={() => (activeTab = 'published')}
		>
			Published
			<span class="testimonials-tab-count">{data.count ?? data.testimonials.length}</span>
		</button>
	</nav>

	<div
		class="testimonials-panel"
		role="tabpanel"
		id="testimonials-panel"
		aria-labelledby={`testimonials-tab-${activeTab}`}
	>
	{#if activeTab === 'published'}
		{#if data.error}
			<div class="error-state" role="alert">
				<p>Could not load testimonials: {data.error}</p>
			</div>
		{:else if data.testimonials.length === 0}
			<div class="empty-state">
				<p>No published testimonials yet.</p>
				{#if currentUser.authenticated}
					<a class="btn btn-primary" href="{base}/testimonials/new">
						Submit the first testimonial →
					</a>
				{:else}
					<a class="btn btn-primary" href="{base}/accounts/google/login/?next={base}/testimonials/new">
						Sign in to contribute
					</a>
				{/if}
			</div>
		{:else}
			{@render cardGrid(data.testimonials, false)}
		{/if}
	{:else}
		{@const tab = CLIENT_TABS.find((t) => t.key === activeTab)}
		{#if !tab || !tab.visible}
			<div class="empty-state">
				<p>This section isn't available for your role.</p>
			</div>
		{:else}
			{@const state = tabState[tab.key]}
			{#if state.loading}
				<div class="testimonials-grid" aria-busy="true">
					<Skeleton variant="card" />
					<Skeleton variant="card" />
					<Skeleton variant="card" />
				</div>
			{:else if state.error}
				<div class="error-state" role="alert">
					<p>{tab.errorMessage}: {state.error}</p>
					<button
						type="button"
						class="btn btn-secondary"
						onclick={() => {
							state.attempted = false;
							loadTab(tab.key);
						}}
					>
						Retry
					</button>
				</div>
			{:else if state.list.length === 0}
				<div class="empty-state">
					<p>{tab.emptyMessage}</p>
					{#if tab.emptyAction}
						<a class="btn btn-primary" href={tab.emptyAction.href}>{tab.emptyAction.label}</a>
					{/if}
				</div>
			{:else}
				<div class="testimonials-grid">
					{#each state.list as t (t.id)}
						{#if tab.key === 'rejected'}
							{@render rejectedCard(t)}
						{:else}
							<TestimonialCard testimonial={t} showStatus />
						{/if}
					{/each}
				</div>
			{/if}
		{/if}
	{/if}
	</div>
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
		overflow-x: auto;
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