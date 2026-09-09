<!--
  /dashboard - the operator command center.

  Layout (desktop):
    +-------------------------------------------------+
    | Header: title + scope badge + Refresh btn       |
    +-------------------------------------------------+
    | 4-tile summary row (open / my work / notifs / stale)
    +----------------------+--------------------------+
    | Quick actions        | Recent activity          |
    +----------------------+--------------------------+
    | Status breakdown     | Recent published cases   |
    +----------------------+--------------------------+
    | My open casework (Advocate/Staff only)          |
    +-------------------------------------------------+

  Mobile (<= 700px): single column.

  Sections are conditionally rendered based on role via the helpers
  in $lib/session. The data itself is already role-scoped on the
  server (see backend/cases/dashboard.py); the UI gating here just
  hides widgets that wouldn't be useful for the role.
-->
<script lang="ts">
	import { base } from '$app/paths';
	import { invalidateAll } from '$app/navigation';
	import Icon from '$lib/Icon.svelte';
	import DashboardCard from '$lib/DashboardCard.svelte';
	import StatTile from '$lib/StatTile.svelte';
	import QuickActions from '$lib/QuickActions.svelte';
	import StatusBreakdownChart from '$lib/StatusBreakdownChart.svelte';
	import { isAdvocate, isAdmin, isVolunteer, user } from '$lib/session';
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

	const scopeLabel = $derived(data.data?.scope ?? null);

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
			visible: isVolunteer($user),
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
			visible: isVolunteer($user),
		},
		{
			label: 'Review reports',
			description: 'Latest report submissions across cases.',
			href: '/reports',
			visible: isVolunteer($user),
		},
		{
			label: 'Open casework',
			description: 'Track advocacy actions and follow-ups.',
			href: '/casework',
			visible: isAdvocate($user),
		},
		{
			label: 'Open contacts',
			description: 'Always-private contacts registry.',
			href: '/contacts',
			visible: isAdvocate($user),
		},
		{
			label: 'Audit log',
			description: 'Full system activity (admin).',
			href: '/admin/cases/auditlog/',
			visible: isAdmin($user),
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
	{:else if data.data}
		<!-- Summary row (4 tiles) -->
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
			{#if isAdvocate($user) || isAdmin($user)}
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
				hint={isAdvocate($user) ? 'Advocate in-app alerts.' : 'Account-level alerts.'}
			/>
		</section>

		<!-- All cards stack single-column. Previously this section was
		     a 2-col grid (Quick actions | Recent activity and Status
		     breakdown | Recently updated cases) which made the page
		     feel busy and hard to scan. Single column reads top-to-bottom. -->
		<DashboardCard title="Quick actions" subtitle="One click to the right place.">
			{#if visibleActions.length === 0}
				<p class="empty-state">No actions available for your role.</p>
			{:else}
				<QuickActions actions={visibleActions} />
			{/if}
		</DashboardCard>

		<DashboardCard
			title="Recent activity"
			subtitle={scopeLabel === 'staff'
				? 'System-wide audit log.'
				: scopeLabel === 'advocate'
					? 'Your activity plus casework events.'
					: 'Your activity across the platform.'}
		>
			{#snippet trailing()}
				{#if isAdmin($user)}
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

		<DashboardCard title="Status breakdown" subtitle="Open cases by current status.">
			<StatusBreakdownChart counts={data.data.by_status} />
		</DashboardCard>

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

		<!-- Recent casework - only for Advocate / Admin. The row
		     column order is description -> action -> status -> meta
		     (LTR English reading order: what's happening, then
		     the type + state, then when/who). -->
		{#if isAdvocate($user) || isAdmin($user)}
			<DashboardCard
				title={isAdmin($user) ? 'Recent casework' : 'My recent casework'}
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

	/* Summary row */
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

	/* Section grid - single column on all viewports. The dashboard
	   reads top-to-bottom so the user can track which card they're
	   on without their eyes jumping between columns. */

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

	/* Activity feed */
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

	/* Person list */
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

	/* Casework - LTR English reading order. The main content
	   (the description) is on the LEFT so the row reads as a
	   sentence. Action + status pills are grouped next; date
	   and the author are at the far right. */
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
