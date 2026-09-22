<!--
  StatusHistoryTimeline — newest-first list of auto-captured status
  changes for a Person.

  Drives the "Status history" feed on /persons/{id}. Each row is one
  `CaseEvent` row written by `PersonViewSet.perform_update`
  (backend/cases/views.py) when one of the status-ish fields
  (`current_status`, `medical_status`, `current_status_date`,
  `current_status_source`, `current_status_verification`) changes.

  Data shape (from CaseEventSerializer, backend/cases/serializers.py:581):
  {
    id: number,
    event_date: string (ISO date),
    event_kind: 'status_change' | ...,
    description: string (e.g. "current_status: detained → released"),
    source: string,
    verification: string,
    created_by: { username: string } | null,
    created_at: string (ISO datetime),
  }

  Status labels come from `StatusBadge.statusLabels` — the canonical
  Person-status label map, reused for the old → new display so the
  timeline stays in sync with the badge on the same page.
-->
<script lang="ts">
	import StatusBadge, { statusLabels } from '$lib/StatusBadge.svelte';

	export interface StatusHistoryEntry {
		id: number;
		event_date: string | null;
		event_kind: string;
		description: string;
		source: string;
		verification?: string;
		created_by: number | null;
		created_by_username: string | null;
		created_at?: string;
	}

	interface Props {
		events: StatusHistoryEntry[];
	}
	let { events }: Props = $props();

	// The backend's default CaseEvent ordering is `event_date asc,
	// created_at asc` (models.py Meta.ordering on CaseEvent). For a
	// "history" feed the user expects newest-first, so reverse the
	// list defensively — covers the case where the queryset returns
	// a different order in a future migration.
	const sortedEvents = $derived(
		[...events].sort((a, b) => {
			const aTime = a.created_at ?? a.event_date ?? '';
			const bTime = b.created_at ?? b.event_date ?? '';
			return bTime.localeCompare(aTime);
		}),
	);

	/** Parse a row description ("current_status: detained → released")
	 *  into a typed { field, prev, current } tuple when the shape
	 *  matches the backend's auto-format. Falls back to a flat
	 *  description for any row that doesn't match (legacy or hand-
	 *  written rows). */
	interface ParsedChange {
		field: string;
		prev: string;
		current: string;
	}
	function parseChange(description: string): ParsedChange | null {
		// Match "<field>: <prev> → <current>" — em-dash U+2192 with
		// optional surrounding whitespace.
		const m = description.match(/^([^:]+):\s*(.+?)\s*→\s*(.+)$/);
		if (!m) return null;
		return { field: m[1].trim(), prev: m[2].trim(), current: m[3].trim() };
	}

	/** Display label for the actor. Falls back to "system" when the
	 *  creating user is NULL (e.g. an automated import or a deleted
	 *  user account) — never render the raw null. */
	function actorLabel(entry: StatusHistoryEntry): string {
		return entry.created_by_username ?? 'system';
	}

	/** Format the event date for display. The backend sends
	 *  `event_date` as an ISO date (YYYY-MM-DD). */
	function formatEventDate(iso: string | null): string {
		if (!iso) return '—';
		const d = new Date(iso);
		if (Number.isNaN(d.getTime())) return iso;
		return d.toLocaleDateString(undefined, {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
		});
	}
</script>

<section class="status-history" aria-labelledby="status-history-heading">
	<h3 id="status-history-heading" class="status-history-heading">
		Status history
	</h3>

	{#if sortedEvents.length === 0}
		<p class="status-history-empty">
			No status changes yet — the initial state was recorded when
			the case was created.
		</p>
	{:else}
		<ol class="status-history-list">
			{#each sortedEvents as event (event.id)}
				{@const parsed = parseChange(event.description)}
				<li class="status-history-row">
					<div class="status-history-row-meta">
						<time class="status-history-date" datetime={event.event_date ?? ''}>
							{formatEventDate(event.event_date)}
						</time>
						<span class="status-history-actor">by {actorLabel(event)}</span>
					</div>

					{#if parsed && (parsed.field === 'current_status' || parsed.field === 'medical_status')}
						<!-- Status flip → render as old → new badges so the
						     row reads like a status badge pair. -->
						<div class="status-history-change">
							<StatusBadge status={parsed.prev} />
							<span class="status-history-arrow" aria-hidden="true">→</span>
							<StatusBadge status={parsed.current} />
						</div>
					{:else if parsed}
						<!-- Other status-ish fields (current_status_date,
						     current_status_source, current_status_verification):
						     show the raw "field: prev → current" text so the
						     volunteer sees what specifically changed. -->
						<div class="status-history-text">
							<span class="status-history-field">{parsed.field}</span>:
							<code class="status-history-value">{parsed.prev}</code>
							<span class="status-history-arrow" aria-hidden="true">→</span>
							<code class="status-history-value">{parsed.current}</code>
						</div>
					{:else}
						<!-- Unparseable description (legacy / hand-written row) —
						     fall back to the raw description verbatim. -->
						<div class="status-history-text">
							{event.description}
						</div>
					{/if}
				</li>
			{/each}
		</ol>
	{/if}
</section>

<style>
	.status-history {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		margin-top: 1rem;
	}
	.status-history-heading {
		margin: 0;
		font-size: 0.95rem;
		font-weight: 700;
		color: var(--color-text);
	}
	.status-history-empty {
		margin: 0;
		padding: 0.85rem 1rem;
		background: var(--color-surface, #f8fafb);
		border: 1px dashed var(--color-border-light, #e2e8f0);
		border-radius: var(--radius-input, 10px);
		font-size: 0.88rem;
		color: var(--color-text-muted, #666);
		line-height: 1.45;
	}
	.status-history-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 0.6rem;
	}
	.status-history-row {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
		padding: 0.7rem 0.9rem;
		background: var(--color-bg-white, #fff);
		border: 1px solid var(--color-border-subtle, #eef2f5);
		border-left: 3px solid var(--color-primary, #25646a);
		border-radius: var(--radius-card, 8px);
	}
	.status-history-row-meta {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 0.75rem;
		flex-wrap: wrap;
	}
	.status-history-date {
		font-size: 0.82rem;
		font-weight: 600;
		color: var(--color-text-muted, #666);
	}
	.status-history-actor {
		font-size: 0.78rem;
		color: var(--color-text-muted, #666);
		font-style: italic;
	}
	.status-history-change {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
	}
	.status-history-text {
		font-size: 0.88rem;
		color: var(--color-text, #1a1a1a);
		line-height: 1.45;
		word-break: break-word;
	}
	.status-history-field {
		font-weight: 600;
		color: var(--color-text, #1a1a1a);
	}
	.status-history-value {
		font-family: ui-monospace, 'SF Mono', 'Cascadia Mono', Menlo, Consolas, monospace;
		font-size: 0.85rem;
		background: var(--color-surface, #f8fafb);
		padding: 0.05rem 0.35rem;
		border-radius: 4px;
		border: 1px solid var(--color-border-subtle, #eef2f5);
		color: var(--color-text, #1a1a1a);
	}
	.status-history-arrow {
		color: var(--color-text-muted, #666);
		font-size: 1rem;
		margin: 0 0.15rem;
	}

	@media (max-width: 480px) {
		.status-history-row-meta {
			flex-direction: column;
			align-items: flex-start;
			gap: 0.15rem;
		}
	}
</style>
