<!--
  StatusTransitionBanner — prominent banner on /persons/{id} showing the
  most recent `current_status` flip.

  Reads the same `status_history` array that StatusHistoryTimeline
  consumes. The timeline is the full chronological feed; this banner
  is the headline — a single, prominent row that answers "what
  changed?" without scrolling.

  Sibling component to StatusHistoryTimeline. Splitting them keeps the
  banner's markup small (it only ever renders 0 or 1 row) while the
  timeline handles the unbounded list.

  Empty state: the banner does NOT render when there's no current_status
  history. The StatusHistoryTimeline still shows medical_status / date /
  source / verification changes (with the empty-state copy if there's
  nothing at all). This is intentional — we don't want a "no status
  changes yet" banner for the entire detail page.
-->
<script lang="ts">
	import StatusBadge, { statusLabels } from '$lib/StatusBadge.svelte';
	import type { StatusHistoryEntry } from '$lib/types';

	interface Props {
		events: StatusHistoryEntry[];
	}
	let { events }: Props = $props();

	/** Same parser the timeline uses. We only care about rows that
	 *  match the "<field>: <prev> → <current>" shape AND where the
	 *  field is `current_status` (the headline field volunteers
	 *  scan for). Medical_status etc. live in the timeline. */
	interface ParsedChange {
		field: string;
		prev: string;
		current: string;
	}
	function parseChange(description: string): ParsedChange | null {
		const m = description.match(/^([^:]+):\s*(.+?)\s*→\s*(.+)$/);
		if (!m) return null;
		return { field: m[1].trim(), prev: m[2].trim(), current: m[3].trim() };
	}

	/** Find the most recent `current_status` flip. `events` is the
	 *  raw array from the backend (already newest-first by the
	 *  status_history prefetch + filter, but we re-sort defensively
	 *  in case a future migration changes the ordering). */
	const latestStatusFlip = $derived.by(() => {
		const sorted = [...events].sort((a, b) => {
			const aTime = a.created_at ?? a.event_date ?? '';
			const bTime = b.created_at ?? b.event_date ?? '';
			return bTime.localeCompare(aTime);
		});
		for (const event of sorted) {
			const parsed = parseChange(event.description);
			if (parsed && parsed.field === 'current_status') {
				return { event, parsed };
			}
		}
		return null;
	});

	function formatEventDate(iso: string | null): string {
		if (!iso) return '';
		const d = new Date(iso);
		if (Number.isNaN(d.getTime())) return iso;
		return d.toLocaleDateString(undefined, {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
		});
	}

	/** Human label for a status slug. Falls back to the slug with
	 *  underscores replaced (matches StatusBadge.statusLabels behavior). */
	function labelFor(status: string): string {
		return statusLabels[status] ?? status.replace(/_/g, ' ');
	}
</script>

{#if latestStatusFlip}
	{@const { event, parsed } = latestStatusFlip}
	<aside class="status-transition-banner" role="status" aria-live="polite">
		<div class="status-transition-headline">
			<span class="status-transition-prefix">Status changed from</span>
			<StatusBadge status={parsed.prev} />
			<span class="status-transition-arrow" aria-hidden="true">➔</span>
			<StatusBadge status={parsed.current} />
		</div>
		<div class="status-transition-meta">
			{#if event.event_date}
				<time datetime={event.event_date}>{formatEventDate(event.event_date)}</time>
			{/if}
			{#if event.created_by_username}
				<span class="status-transition-actor">by {event.created_by_username}</span>
			{/if}
		</div>
	</aside>
{/if}

<style>
	.status-transition-banner {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-top: 0.85rem;
		padding: 0.9rem 1rem;
		background: linear-gradient(
			180deg,
			rgba(37, 100, 106, 0.06),
			var(--color-bg-white, #fff) 70%
		);
		border: 1px solid var(--color-primary-light, #477c81);
		border-left: 4px solid var(--color-primary, #25646a);
		border-radius: var(--radius-card, 8px);
		box-shadow: var(--shadow-card, 0 1px 2px rgba(0, 0, 0, 0.04));
	}
	.status-transition-headline {
		display: flex;
		align-items: center;
		gap: 0.55rem;
		flex-wrap: wrap;
		font-size: 0.95rem;
		line-height: 1.4;
	}
	.status-transition-prefix {
		font-weight: 700;
		color: var(--color-text, #1a1a1a);
	}
	.status-transition-arrow {
		font-size: 1.1rem;
		color: var(--color-primary, #25646a);
		font-weight: 700;
		margin: 0 0.15rem;
	}
	.status-transition-meta {
		display: flex;
		align-items: baseline;
		gap: 0.6rem;
		flex-wrap: wrap;
		font-size: 0.82rem;
		color: var(--color-text-muted, #666);
	}
	.status-transition-actor {
		font-style: italic;
	}

	@media (max-width: 480px) {
		.status-transition-headline {
			font-size: 0.9rem;
		}
		.status-transition-arrow {
			font-size: 1rem;
		}
	}
</style>
