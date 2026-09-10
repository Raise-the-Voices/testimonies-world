<!--
  /dashboard - the operator command center.

  Layout (desktop, single column at all breakpoints - the dashboard
  reads top-to-bottom so the user can track which card they're on
  without their eyes jumping between columns):

    +-------------------------------------------------+
    | Header: title + scope badge + Refresh btn       |
    +-------------------------------------------------+
    | 4-tile summary row (open / my work / notifs / stale)
    +-------------------------------------------------+
    | Quick actions                                   |
    +-------------------------------------------------+
    | Recent activity                                 |
    +-------------------------------------------------+
    | Status breakdown                                |
    +-------------------------------------------------+
    | Recently updated cases                          |
    +-------------------------------------------------+
    | My recent casework (Advocate/Admin only)        |
    +-------------------------------------------------+

  Anti-flicker design
  -------------------
  - Each section is independently wrapped with a fixed `min-height`
    so swapping skeleton → content never reflows the page.
  - Skeleton → content transitions use `transition:fade` (220 ms) so
    the swap is a soft crossfade, not a hard cut.
  - Auth state derives from `data.user` (SSR-hydrated by +layout.ts)
    instead of the global `$user` store. Without this, the SSR HTML
    would render the unauthenticated chrome and the client hydration
    would snap to the authenticated state — the classic "you must be
    logged in" flash on hard refresh.
  - Skeletons render only when data is genuinely loading (initial
    soft-nav load, manual refresh). Hard refresh with SSR success
    renders real content directly — no skeleton at all.
-->
<script lang="ts">
	import { base } from '$app/paths';
	import { invalidateAll } from '$app/navigation';
	import { fade } from 'svelte/transition';
	import Icon from '$lib/Icon.svelte';
	import DashboardCard from '$lib/DashboardCard.svelte';
	import StatTile from '$lib/StatTile.svelte';
	import QuickActions from '$lib/QuickActions.svelte';
	import StatusBreakdownChart from '$lib/StatusBreakdownChart.svelte';
	import { isAdvocate, isAdmin, isVolunteer } from '$lib/session';
	import Skeleton from '$lib/Skeleton.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let refreshing = $state(false);
	async function refresh() {
		refreshing = true;
		try {
			await invalidateAll();
		} finally {
			refreshing = false;
		}
	}

	// Per-section loading state. Hard refresh with successful SSR
	// renders real content directly (data.data is hydrated). Skeletons
	// only show on initial soft-nav load OR while `refreshing` is true.
	const loading = $derived(!data.data || refreshing);

	// SSR-hydrated auth. See +layout.svelte for the full rationale —
	// in short, reading from `data.user` instead of `$user` keeps the
	// SSR HTML and post-hydration HTML identical, killing the flicker.
	const currentUser = $derived(data.user);

	const scopeLabel = $derived(data.data?.scope ?? null);
	const showCaseworkSection = $derived(isAdvocate(currentUser) || isAdmin(currentUser));

	// Role-aware quick action list. Each entry uses the role gate from
	// $lib/session at render time so the set adapts to the user.
	type QuickAction = {
		label: string;
		description: string;
		href: string;
		visible: boolean;
	};
	const allActions: QuickAction[] = $derived([
		{
			label: 'Submit a case',
			description: 'Document someone new facing oppression.',
			href: '/submit',
			visible: isVolunteer(currentUser),
		},
		{
			label: 'Browse cases',
			description: 'Search and filter the full case catalog.',
			href: '/persons',
			visible: true,
		},
		{
			label: 'Open watchdog',
			description: 'Cases needing fresh reporting.',
			href: '/watchdog',
			visible: isVolunteer(currentUser),
		},
		{
			label: 'Review reports',
			description: 'Latest report submissions across cases.',
			href: '/reports',
			visible: isVolunteer(currentUser),
		},
		{
			label: 'Open casework',
			description: 'Track advocacy actions and follow-ups.',
			href: '/casework',
			visible: isAdvocate(currentUser),
		},
		{
			label: 'Open contacts',
			description: 'Always-private contacts registry.',
			href: '/contacts',
			visible: isAdvocate(currentUser),
		},
		{
			label: 'Audit log',
			description: 'Full system activity (admin).',
			href: '/admin/cases/auditlog/',
			visible: isAdmin(currentUser),
		},
	]);
	const visibleActions = $derived(allActions.filter((a) => a.visible));

	function formatRelative(iso: string | null | undefined): string {
		if (!iso) return '';
		const then = new Date(iso).getTime();
		if (Number.isNaN(then)) return '';
		const diffMs = Date.now() - then;
		const mins = Math.floor(diffMs / 60000);
		if (mins < 1) return 'just now';
		if (mins < 60) return `${mins}m ago`;
		const hours = Math.floor(mins / 60);
		if (hours < 24) return `${hours}h ago`;
		const days = Math.floor(hours / 24);
		if (days < 30) return `${days}d ago`;
		return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
	}

	function personHref(id: number): string {
		return `${base}/persons/${id}`;
	}

	function caseworkHref(id: number): string {
		return `${base}/casework/${id}`;
	}
</script>

<svelte:head>
	<title>Dashboard - Testimonies.world</title>
</svelte:head>

<div class="dashboard-page">
	<header class="page-header">
		<div>
			<h1>Dashboard</h1>
			<p class="page-subtitle">
				What's happening, what needs attention, and one click to the right place.
			</p>
		</div>
		<div class="header-actions">
			{#if scopeLabel}
				<span class="scope-badge scope-{scopeLabel}" title="Your access scope">
					{scopeLabel === 'staff' ? 'Admin' : scopeLabel === 'advocate' ? 'Advocate' : 'Volunteer'}
				</span>
			{/if}
			<button
				type="button"
				class="btn btn-secondary refresh-btn"
				onclick={refresh}
				disabled={refreshing}
				aria-label="Refresh dashboard"
			>
				<Icon name="refresh" size={16} />
				<span>{refreshing ? 'Refreshing...' : 'Refresh'}</span>
			</button>
		</div>
	</header>

	{#if data.error}
		<DashboardCard variant="error" title="Couldn't load the dashboard">
			<p>{data.error}</p>
			<button type="button" class="btn btn-secondary" onclick={refresh}>
				Try again
			</button>
		</DashboardCard>
	{:else}
		<!-- === SECTION: Summary row (4 tiles) ===
		     min-height matches the real StatTile geometry so the swap
		     doesn't reflow. -->
		<div class="dashboard-section summary-section">
			{#if loading}
				<div class="section-inner" transition:fade={{ duration: 220 }}>
					<div class="summary-row" aria-hidden="true">
						{#each Array(4) as _, i (i)}
							<Skeleton variant="rect" height="6rem" />
						{/each}
					</div>
				</div>
			{:else if data.data}
				<div class="section-inner" transition:fade={{ duration: 220 }}>
					<section class="summary-row" aria-label="Platform summary">
						<StatTile
							label="Open cases"
							value={data.data.summary.open_cases}
							hint="Published persons, any status."
							href="{base}/persons"
						/>
						<StatTile
							label="Stale cases"
							value={data.data.summary.stale_cases}
							hint="Not released, not deceased."
							href="{base}/watchdog"
						/>
						{#if isAdvocate(currentUser) || isAdmin(currentUser)}
							<StatTile
								label="My open casework"
								value={data.data.summary.my_open_casework}
								hint="Open + in-progress."
								href="{base}/casework"
							/>
						{:else}
							<StatTile
								label="My reports"
								value={data.data.recent_reports.length}
								hint="Most recent across all cases."
								href="{base}/reports"
							/>
						{/if}
						<StatTile
							label="Unread notifications"
							value={data.data.summary.unread_notifications}
							hint={isAdvocate(currentUser) ? 'Advocate in-app alerts.' : 'Account-level alerts.'}
						/>
					</section>
				</div>
			{/if}
		</div>

		<!-- === SECTION: Quick actions ===
		     min-height matches the QuickActions grid (2 rows × ~3.5rem
		     action tiles + card chrome). -->
		<div class="dashboard-section quick-actions-section">
			{#if loading}
				<div class="section-inner" transition:fade={{ duration: 220 }}>
					<DashboardCard title="Quick actions" subtitle="One click to the right place.">
						<div class="quick-actions" aria-hidden="true">
							{#each Array(6) as _, i (i)}
								<Skeleton variant="rect" height="3.5rem" />
							{/each}
						</div>
					</DashboardCard>
				</div>
			{:else if data.data}
				<div class="section-inner" transition:fade={{ duration: 220 }}>
					<DashboardCard title="Quick actions" subtitle="One click to the right place.">
						{#if visibleActions.length === 0}
							<p class="empty-state">No actions available for your role.</p>
						{:else}
							<QuickActions actions={visibleActions} />
						{/if}
					</DashboardCard>
				</div>
			{/if}
		</div>

		<!-- === SECTION: Recent activity ===
		     min-height matches ~5 activity rows + card chrome. -->
		<div class="dashboard-section activity-section">
			{#if loading}
				<div class="section-inner" transition:fade={{ duration: 220 }}>
					<DashboardCard title="Recent activity" subtitle="Your activity across the platform.">
						<div class="feed-skel" aria-hidden="true">
							{#each Array(5) as _, i (i)}
								<Skeleton variant="rect" height="2.6rem" />
							{/each}
						</div>
					</DashboardCard>
				</div>
			{:else if data.data}
				<div class="section-inner" transition:fade={{ duration: 220 }}>
					<DashboardCard
						title="Recent activity"
						subtitle={scopeLabel === 'staff'
							? 'System-wide audit log.'
							: scopeLabel === 'advocate'
								? 'Your activity plus casework events.'
								: 'Your activity across the platform.'}
					>
						{#snippet trailing()}
							{#if isAdmin(currentUser)}
								<a href="{base}/dashboard/audit-logs" class="view-all-link">
									View all <Icon name="arrow-right" size={14} />
								</a>
							{/if}
						{/snippet}
						{#if data.data.activity.length === 0}
							<p class="empty-state">No recent activity.</p>
						{:else}
							<ul class="activity-feed">
								{#each data.data.activity as a (a.id)}
									<li class="activity-item">
										<span class="activity-meta">
											<span class="activity-user">{a.user ?? '-'}</span>
											<span class="activity-action activity-action-{a.action}">{a.action}</span>
											<span class="activity-target">{a.target_type} #{a.target_id}</span>
										</span>
										<span class="activity-when">{formatRelative(a.timestamp)}</span>
									</li>
								{/each}
							</ul>
						{/if}
					</DashboardCard>
				</div>
			{/if}
		</div>

		<!-- === SECTION: Status breakdown ===
		     min-height matches the chart bar + legend grid. -->
		<div class="dashboard-section status-section">
			{#if loading}
				<div class="section-inner" transition:fade={{ duration: 220 }}>
					<DashboardCard title="Status breakdown" subtitle="Open cases by current status.">
						<div class="status-skel" aria-hidden="true">
							<Skeleton variant="rect" height="0.75rem" width="100%" />
							<div class="status-legend-skel">
								{#each Array(6) as _, i (i)}
									<Skeleton variant="rect" height="1rem" width="60%" />
								{/each}
							</div>
						</div>
					</DashboardCard>
				</div>
			{:else if data.data}
				<div class="section-inner" transition:fade={{ duration: 220 }}>
					<DashboardCard title="Status breakdown" subtitle="Open cases by current status.">
						<StatusBreakdownChart counts={data.data.by_status} />
					</DashboardCard>
				</div>
			{/if}
		</div>

		<!-- === SECTION: Recently updated cases ===
		     min-height matches ~5 person rows + card chrome. -->
		<div class="dashboard-section recent-persons-section">
			{#if loading}
				<div class="section-inner" transition:fade={{ duration: 220 }}>
					<DashboardCard title="Recently updated cases" subtitle="Latest five published cases.">
						<div class="feed-skel" aria-hidden="true">
							{#each Array(5) as _, i (i)}
								<Skeleton variant="rect" height="3rem" />
							{/each}
						</div>
					</DashboardCard>
				</div>
			{:else if data.data}
				<div class="section-inner" transition:fade={{ duration: 220 }}>
					<DashboardCard title="Recently updated cases" subtitle="Latest five published cases.">
						{#snippet trailing()}
							<a href="{base}/persons" class="view-all-link">
								Browse all <Icon name="arrow-right" size={14} />
							</a>
						{/snippet}
						{#if data.data.recent_persons.length === 0}
							<p class="empty-state">No published cases yet.</p>
						{:else}
							<ul class="person-list">
								{#each data.data.recent_persons as p (p.id)}
									<li class="person-row">
										<a href={personHref(p.id)}>
											<span class="person-name">{p.name}</span>
											<span class="person-country">{p.country}</span>
											<span class="person-status status-{p.current_status}">{p.current_status.replace(/_/g, ' ')}</span>
											<span class="person-when">{formatRelative(p.updated_at)}</span>
										</a>
									</li>
								{/each}
							</ul>
						{/if}
					</DashboardCard>
				</div>
			{/if}
		</div>

		<!-- === SECTION: Recent casework (Advocate / Admin only) ===
		     Role gate reads from `currentUser` which is SSR-hydrated
		     (data.user), so this section is server-rendered with the
		     correct visibility — no flash on hard refresh. -->
		{#if showCaseworkSection}
			<div class="dashboard-section recent-casework-section">
				{#if loading}
					<div class="section-inner" transition:fade={{ duration: 220 }}>
						<DashboardCard title="My recent casework" subtitle="Latest five advocacy actions.">
							<div class="feed-skel" aria-hidden="true">
								{#each Array(5) as _, i (i)}
									<Skeleton variant="rect" height="3rem" />
								{/each}
							</div>
						</DashboardCard>
					</div>
				{:else if data.data}
					<div class="section-inner" transition:fade={{ duration: 220 }}>
						<DashboardCard
							title={isAdmin(currentUser) ? 'Recent casework' : 'My recent casework'}
							subtitle="Latest five advocacy actions."
						>
							{#snippet trailing()}
								<a href="{base}/casework" class="view-all-link">
									View all <Icon name="arrow-right" size={14} />
								</a>
							{/snippet}
							{#if data.data.recent_casework.length === 0}
								<p class="empty-state">No recent casework records.</p>
							{:else}
								<ul class="casework-list">
									{#each data.data.recent_casework as cw (cw.id)}
										<li class="casework-row">
											<a href={caseworkHref(cw.id)}>
												<span class="cw-desc">{cw.description}</span>
												<span class="cw-pills">
													<span class="cw-action">{cw.action_type.replace(/_/g, ' ')}</span>
													<span class="cw-status cw-status-{cw.status}">{cw.status.replace(/_/g, ' ')}</span>
												</span>
												<span class="cw-meta">
													<span>{cw.date}</span>
													{#if cw.performed_by_name}
														<span>* {cw.performed_by_name}</span>
													{/if}
												</span>
											</a>
										</li>
									{/each}
								</ul>
							{/if}
						</DashboardCard>
					</div>
				{/if}
			</div>
		{/if}
	{/if}
</div>

<style>
	.dashboard-page {
		width: 100%;
		max-width: var(--max-w-page);
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	/* Each section gets a fixed min-height matching its real content.
	   This is the load-bearing piece of the no-shift design: when
	   skeleton → content swaps, the section's box doesn't move. */
	.dashboard-section {
		display: block;
	}
	.summary-section { min-height: 6rem; }
	.quick-actions-section { min-height: 11rem; }
	.activity-section { min-height: 17rem; }
	.status-section { min-height: 16rem; }
	.recent-persons-section { min-height: 17rem; }
	.recent-casework-section { min-height: 18rem; }

	/* Inner wrapper holds the transitioning content. Its own height is
	   driven by the children; the outer .dashboard-section's min-height
	   keeps the slot the right size. */
	.section-inner {
		display: block;
		width: 100%;
	}

	/* === Summary row === */
	.summary-row {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: var(--gap-card);
	}
	@media (min-width: 720px) {
		.summary-row {
			grid-template-columns: repeat(4, minmax(0, 1fr));
		}
	}

	/* === Feed skeletons (activity, recent persons, recent casework) ===
	   All three share the same vertical list geometry; reuse the same
	   skeleton so the swap pattern stays consistent across sections. */
	.feed-skel {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	/* === Status breakdown skeleton ===
	   Mirrors the chart bar + auto-fill legend grid. */
	.status-skel {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
	.status-legend-skel {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
		gap: 0.4rem 1rem;
	}

	/* === Quick actions skeleton ===
	   Same grid geometry as QuickActions so the layout matches. */
	.quick-actions {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 0.75rem;
	}
	@media (min-width: 720px) {
		.quick-actions {
			grid-template-columns: repeat(3, minmax(0, 1fr));
		}
	}

	/* === Page header === */
	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-end;
		gap: 1rem;
		flex-wrap: wrap;
		padding-bottom: 0.75rem;
		border-bottom: 1px solid var(--color-border-light);
	}
	.page-header h1 {
		margin: 0 0 0.25rem 0;
		font-size: 1.5rem;
		color: var(--color-primary);
	}
	.page-subtitle {
		margin: 0;
		font-size: 0.95rem;
		color: var(--color-text-muted);
		max-width: var(--max-w-prose);
	}

	.header-actions {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}
	.scope-badge {
		display: inline-flex;
		align-items: center;
		padding: 0.25rem 0.65rem;
		border-radius: 999px;
		font-size: 0.78rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		background: var(--color-primary-tint);
		color: var(--color-primary);
		white-space: nowrap;
	}
	.scope-badge.scope-staff {
		background: rgba(217, 22, 22, 0.1);
		color: var(--color-danger);
	}
	.scope-badge.scope-advocate {
		background: var(--color-primary-tint);
		color: var(--color-primary);
	}
	.scope-badge.scope-volunteer {
		background: var(--color-bg);
		color: var(--color-text-muted);
	}
	.refresh-btn {
		min-height: 36px;
		padding: 0.4rem 0.85rem;
		font-size: 0.85rem;
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
	}

	.view-all-link {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		text-decoration: none;
		color: var(--color-primary);
		font-size: 0.85rem;
		font-weight: 600;
	}
	.view-all-link:hover {
		text-decoration: underline;
	}

	.empty-state {
		margin: 0;
		padding: 1rem 0 0.25rem 0;
		text-align: center;
		color: var(--color-text-muted);
		font-size: 0.9rem;
	}

	/* === Activity feed === */
	.activity-feed {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	.activity-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 0.75rem;
		padding: 0.55rem 0.75rem;
		background: var(--color-surface);
		border-radius: var(--radius-input);
		font-size: 0.85rem;
	}
	.activity-meta {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		min-width: 0;
		flex-wrap: wrap;
	}
	.activity-user {
		font-weight: 700;
		color: var(--color-text);
	}
	.activity-action {
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		padding: 0.1rem 0.45rem;
		border-radius: 4px;
		background: var(--color-bg);
		color: var(--color-text-muted);
	}
	.activity-action-viewed {
		background: var(--color-primary-tint);
		color: var(--color-primary);
	}
	.activity-action-edited {
		background: rgba(217, 119, 6, 0.15);
		color: #b45309;
	}
	.activity-action-deleted {
		background: rgba(217, 22, 22, 0.15);
		color: var(--color-danger);
	}
	.activity-target {
		color: var(--color-text-muted);
		font-family: ui-monospace, 'SF Mono', Menlo, monospace;
		font-size: 0.8rem;
	}
	.activity-when {
		color: var(--color-text-muted);
		font-size: 0.78rem;
		white-space: nowrap;
	}

	/* === Person list === */
	.person-list,
	.casework-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}
	.person-row a {
		display: grid;
		grid-template-columns: 1fr auto auto auto;
		align-items: center;
		gap: 0.75rem;
		padding: 0.55rem 0.75rem;
		background: var(--color-surface);
		border-radius: var(--radius-input);
		text-decoration: none;
		color: var(--color-text);
		font-size: 0.88rem;
		transition: background 0.15s ease;
	}
	@media (max-width: 600px) {
		.person-row a {
			grid-template-columns: 1fr auto;
		}
		.person-row .person-status {
			grid-column: 2;
		}
		.person-row .person-when {
			grid-column: 1 / -1;
			justify-self: end;
		}
	}
	.person-row a:hover {
		background: var(--color-bg);
	}
	.person-name {
		font-weight: 700;
		color: var(--color-text);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.person-country {
		color: var(--color-text-muted);
		font-size: 0.82rem;
	}
	.person-status,
	.cw-status {
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		padding: 0.15rem 0.5rem;
		border-radius: 4px;
		background: var(--color-bg);
		color: var(--color-text-muted);
		white-space: nowrap;
	}
	.person-when {
		color: var(--color-text-muted);
		font-size: 0.78rem;
		white-space: nowrap;
	}

	/* === Casework list - LTR English reading order === */
	.casework-row a {
		display: grid;
		grid-template-columns: 1fr auto auto;
		align-items: center;
		gap: 0.6rem 0.85rem;
		padding: 0.55rem 0.75rem;
		background: var(--color-surface);
		border-radius: var(--radius-input);
		text-decoration: none;
		color: var(--color-text);
		font-size: 0.88rem;
		transition: background 0.15s ease;
	}
	@media (max-width: 600px) {
		.casework-row a {
			grid-template-columns: 1fr auto;
		}
		.casework-row .cw-pills {
			grid-column: 2;
			justify-self: end;
		}
		.casework-row .cw-meta {
			grid-column: 1 / -1;
			justify-self: end;
		}
	}
	.casework-row a:hover {
		background: var(--color-bg);
	}
	.cw-desc {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		min-width: 0;
	}
	.cw-pills {
		display: inline-flex;
		gap: 0.4rem;
		align-items: center;
		flex-shrink: 0;
	}
	.cw-action {
		font-size: 0.78rem;
		color: var(--color-text-muted);
		white-space: nowrap;
	}
	.cw-meta {
		display: inline-flex;
		gap: 0.35rem;
		color: var(--color-text-muted);
		font-size: 0.78rem;
		white-space: nowrap;
		flex-shrink: 0;
	}

	@media (prefers-reduced-motion: reduce) {
		.dashboard-page *,
		.dashboard-page *::before,
		.dashboard-page *::after {
			animation-duration: 0s !important;
			transition-duration: 0s !important;
		}
	}
</style>
