<!--
  ActivityItem - one row in an activity-feed list.

  Matches the dashboard's "Recent activity" widget geometry:
    [user] [action chip] [target] ........ [when]

  Used by:
    - /dashboard - the 5-row "Recent activity" widget (no target link,
      no secondary line).
    - /dashboard/audit-logs - the full audit log list, where each
      entry has a clickable target (when the URL pattern is known)
      and a secondary line showing details + IP.

  Lives outside any .dashboard-page scope so both surfaces pick up
  the same styling. The component owns the .activity-item /
  .activity-feed styles so callers don't have to redefine them.

  Action chip variants: viewed, edited, deleted, downloaded. Adding
  a new action means adding a `.activity-action-<name>` rule here
  AND in the backend AuditLog.Action enum.
-->
<script lang="ts">
	interface Props {
		/** Username (or user-id when the API only exposes the FK).
		 *  Accepts string OR number so both surfaces — the dashboard
		 *  (where /api/dashboard/ joins users) and the audit log
		 *  (where /api/audit-logs/ returns the raw FK) — can use the
		 *  same component without coercion. */
		user: string | number | null;
		/** Action key — drives the chip color. */
		action: string;
		/** Audit target type, e.g. "person", "report", "media". */
		targetType: string;
		/** Audit target id (numeric). */
		targetId: number;
		/** When set, the target renders as a link to this URL.
		 *  When null/undefined, target is a plain span. */
		targetHref?: string | null;
		/** Pre-formatted "when" string (e.g. "5m ago"). The caller
		 *  owns formatting so the component stays render-only. */
		when: string;
		/** Optional secondary line below the primary meta — used by
		 *  the audit log to surface details + IP. */
		secondary?: string | null;
	}

	let {
		user,
		action,
		targetType,
		targetId,
		targetHref = null,
		when,
		secondary = null,
	}: Props = $props();
</script>

<li class="activity-item">
	<div class="activity-main">
		<span class="activity-meta">
			<span class="activity-user">{user ?? '—'}</span>
			<span class="activity-action activity-action-{action}">{action}</span>
			{#if targetHref}
				<a href={targetHref} class="activity-target activity-target-link">
					{targetType} <span class="target-id">#{targetId}</span>
				</a>
			{:else}
				<span class="activity-target">
					{targetType} <span class="target-id">#{targetId}</span>
				</span>
			{/if}
		</span>
		{#if secondary}
			<span class="activity-secondary" title={secondary}>{secondary}</span>
		{/if}
	</div>
	<span class="activity-when">{when}</span>
</li>

<style>
	/* Same geometry + tokens as the dashboard's recent-activity widget.
	   Re-extracted here so any caller (dashboard, audit log, future
	   surfaces) renders the same shape without inheriting styles from
	   a scoped .dashboard-page ancestor. */
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
	.activity-main {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
		min-width: 0;
		flex: 1 1 auto;
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
		flex-shrink: 0;
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
	.activity-action-downloaded {
		background: rgba(47, 133, 90, 0.15);
		color: var(--color-success);
	}
	.activity-target {
		color: var(--color-text-muted);
		font-family: ui-monospace, 'SF Mono', Menlo, monospace;
		font-size: 0.8rem;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.activity-target-link {
		text-decoration: none;
		color: var(--color-text-muted);
		transition: color 0.15s ease;
	}
	.activity-target-link:hover {
		color: var(--color-primary);
		text-decoration: underline;
	}
	.target-id {
		color: var(--color-text-muted);
	}
	.activity-secondary {
		font-size: 0.78rem;
		color: var(--color-text-muted);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		max-width: 100%;
	}
	.activity-when {
		color: var(--color-text-muted);
		font-size: 0.78rem;
		white-space: nowrap;
		flex-shrink: 0;
	}
</style>
