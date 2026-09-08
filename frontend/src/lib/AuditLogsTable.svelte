<!--
  AuditLogsTable — staff-only audit log table.

  Renders the paginated rows from `auditLogsList`. Sticky header, hover
  row, action-colored chips matching the activity-feed style on the
  dashboard "Recent activity" widget so the two surfaces look like
  one product.

  Click on the row's `target_type #target_id` cell navigates to the
  entity if we know its URL pattern (currently: person → /persons/<id>).
  Other target_types fall back to a no-link span.
-->
<script lang="ts">
	import type { AuditLog } from './api/generated/endpoints.schemas';

	interface Props {
		rows: AuditLog[];
	}

	let { rows }: Props = $props();

	function formatWhen(iso: string): string {
		const then = new Date(iso).getTime();
		if (Number.isNaN(then)) return iso;
		const diffMs = Date.now() - then;
		const mins = Math.floor(diffMs / 60000);
		if (mins < 1) return 'just now';
		if (mins < 60) return `${mins}m ago`;
		const hours = Math.floor(mins / 60);
		if (hours < 24) return `${hours}h ago`;
		const days = Math.floor(hours / 24);
		if (days < 30) return `${days}d ago`;
		return new Date(iso).toLocaleString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit',
		});
	}

	function targetHref(targetType: string, targetId: number): string | null {
		// Only person has a known URL pattern today. Other target_types
		// (report, media, contact, casework, etc.) don't have a
		// dedicated detail page yet, so the cell stays a static span
		// instead of a dead link.
		if (targetType === 'person') return `/persons/${targetId}`;
		return null;
	}
</script>

<div class="table-wrap">
	<table class="audit-table" aria-label="Audit log">
		<thead>
			<tr>
				<th scope="col">When</th>
				<th scope="col">User</th>
				<th scope="col">Action</th>
				<th scope="col">Target</th>
				<th scope="col">Details</th>
				<th scope="col">IP</th>
			</tr>
		</thead>
		<tbody>
			{#each rows as row (row.id)}
				{@const href = targetHref(row.target_type, row.target_id)}
				<tr>
					<td class="cell-when" title={row.timestamp}>
						{formatWhen(row.timestamp)}
					</td>
					<td class="cell-user">{#if row.user}{row.user}{:else}—{/if}</td>
					<td>
						<span class="chip chip-{row.action}">{row.action}</span>
					</td>
					<td class="cell-target">
						{#if href}
							<a href={href} class="target-link">
								{row.target_type} <span class="target-id">#{row.target_id}</span>
							</a>
						{:else}
							<span class="target-static">
								{row.target_type} <span class="target-id">#{row.target_id}</span>
							</span>
						{/if}
					</td>
					<td class="cell-details" title={row.details}>
						{row.details || '—'}
					</td>
					<td class="cell-ip">{row.ip_address ?? '—'}</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>

<style>
	.table-wrap {
		overflow-x: auto;
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		background: var(--color-bg-white);
	}
	.audit-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.88rem;
	}
	.audit-table thead {
		background: var(--color-surface);
	}
	.audit-table th {
		text-align: left;
		padding: 0.65rem 0.85rem;
		font-size: 0.72rem;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		color: var(--color-text-muted);
		border-bottom: 1px solid var(--color-border-light);
		position: sticky;
		top: 0;
		background: var(--color-surface);
	}
	.audit-table td {
		padding: 0.55rem 0.85rem;
		border-bottom: 1px solid var(--color-border-subtle);
		vertical-align: middle;
		color: var(--color-text);
	}
	.audit-table tbody tr:last-child td {
		border-bottom: none;
	}
	.audit-table tbody tr {
		transition: background 0.15s ease;
	}
	.audit-table tbody tr:hover {
		background: var(--color-surface);
	}
	.cell-when {
		color: var(--color-text-muted);
		white-space: nowrap;
		font-size: 0.82rem;
	}
	.cell-user {
		font-weight: 700;
		font-family: ui-monospace, 'SF Mono', Menlo, monospace;
		font-size: 0.82rem;
	}
	.chip {
		display: inline-block;
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		padding: 0.15rem 0.5rem;
		border-radius: 4px;
		background: var(--color-bg);
		color: var(--color-text-muted);
	}
	.chip-viewed {
		background: var(--color-primary-tint);
		color: var(--color-primary);
	}
	.chip-edited {
		background: rgba(217, 119, 6, 0.15);
		color: #b45309;
	}
	.chip-deleted {
		background: rgba(217, 22, 22, 0.15);
		color: var(--color-danger);
	}
	.chip-downloaded {
		background: rgba(47, 133, 90, 0.15);
		color: var(--color-success);
	}
	.cell-target {
		white-space: nowrap;
	}
	.target-link,
	.target-static {
		font-family: ui-monospace, 'SF Mono', Menlo, monospace;
		font-size: 0.82rem;
		color: var(--color-text);
		text-decoration: none;
	}
	.target-link:hover {
		color: var(--color-primary);
		text-decoration: underline;
	}
	.target-id {
		color: var(--color-text-muted);
	}
	.cell-details {
		max-width: 28ch;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		color: var(--color-text-muted);
		font-size: 0.82rem;
	}
	.cell-ip {
		font-family: ui-monospace, 'SF Mono', Menlo, monospace;
		font-size: 0.78rem;
		color: var(--color-text-muted);
		white-space: nowrap;
	}
	@media (max-width: 720px) {
		.cell-details,
		.cell-ip {
			display: none;
		}
	}
</style>
