<!--
  StatusBreakdownChart — horizontal stacked-bar visualization of the
  platform's case status counts.

  Pure SVG, no animation beyond the parent card entrance (per the
  "human-first & practical" brief — the data is the story, not the
  motion). Each segment is a <rect> with a <title> for screen-reader
  text; the whole chart has role="img" + aria-label so AT users get
  a single label describing what's shown.
-->
<script lang="ts">
	import { STATUS_VALUES, type StatusValue } from './StatusBadge.svelte';

	interface Props {
		/** Map of status → count. Missing keys are treated as 0. */
		counts: Partial<Record<StatusValue, number>>;
	}

	let { counts }: Props = $props();

	// Order + labels + colors. Locked order so the bar reads
	// consistently across reloads. Colors are token-aligned; if a
	// status isn't covered by a token, fall back to muted.
	// `unknown` is intentionally last — it's the catch-all bucket and
	// not the story an advocate wants told first.
	const SEGMENTS: Array<{
		key: StatusValue;
		label: string;
		color: string;
	}> = [
		{ key: 'detained', label: 'Detained', color: 'var(--color-primary)' },
		{ key: 'disappeared', label: 'Disappeared', color: 'var(--color-danger)' },
		{ key: 'restricted_movement', label: 'Restricted movement', color: '#d97706' },
		{ key: 'rights_restricted', label: 'Rights restricted', color: '#b45309' },
		{ key: 'stateless', label: 'Stateless', color: 'var(--color-primary-light)' },
		{ key: 'released', label: 'Released', color: 'var(--color-success)' },
		{ key: 'deceased', label: 'Deceased', color: 'var(--color-text-muted)' },
		{ key: 'unknown', label: 'Unknown', color: 'var(--color-border)' },
	];
	// Silence the "unused import" lint for STATUS_VALUES — we use it as
	// a type-source via StatusValue, but the explicit reference keeps
	// the dependency honest if anyone reorders the segments list.
	void STATUS_VALUES;

	const total = $derived(
		Object.values(counts).reduce<number>((sum, n) => sum + (n ?? 0), 0),
	);

	// Each segment width is (count / total) * 100, expressed as a
	// percentage of the bar's full viewBox width (100 units).
	type SegmentLayout = { key: StatusValue; label: string; color: string; count: number; width: number; offset: number };
	const segments = $derived.by<SegmentLayout[]>(() => {
		if (total === 0) return [];
		let offset = 0;
		const layout: SegmentLayout[] = [];
		for (const seg of SEGMENTS) {
			const count = counts[seg.key] ?? 0;
			if (count === 0) continue;
			const width = (count / total) * 100;
			layout.push({ ...seg, count, width, offset });
			offset += width;
		}
		return layout;
	});
</script>

{#if total === 0}
	<p class="chart-empty">No published cases yet.</p>
{:else}
	<div class="chart-wrap" role="img" aria-label="Case status breakdown: {total} total cases">
		<svg
			class="chart-svg"
			viewBox="0 0 100 12"
			preserveAspectRatio="none"
			xmlns="http://www.w3.org/2000/svg"
		>
			{#each segments as seg (seg.key)}
				<rect
					x={seg.offset}
					y="0"
					width={seg.width}
					height="12"
					fill={seg.color}
				>
					<title>{seg.count} {seg.label.toLowerCase()} ({Math.round(seg.width)}%)</title>
				</rect>
			{/each}
		</svg>

		<ul class="chart-legend">
			{#each segments as seg (seg.key)}
				<li class="legend-item">
					<span class="legend-swatch" style="background: {seg.color}" aria-hidden="true"></span>
					<span class="legend-label">{seg.label}</span>
					<span class="legend-count">{seg.count}</span>
				</li>
			{/each}
		</ul>
	</div>
{/if}

<style>
	.chart-wrap {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}
	.chart-svg {
		width: 100%;
		height: 12px;
		display: block;
		border-radius: 4px;
		overflow: hidden;
		background: var(--color-bg);
	}
	.chart-empty {
		margin: 0;
		padding: 0.75rem 0;
		color: var(--color-text-muted);
		text-align: center;
		font-size: 0.9rem;
	}
	.chart-legend {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
		gap: 0.4rem 1rem;
	}
	.legend-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.82rem;
		color: var(--color-text);
	}
	.legend-swatch {
		display: inline-block;
		flex-shrink: 0;
		width: 12px;
		height: 12px;
		border-radius: 3px;
	}
	.legend-label {
		flex: 1;
		min-width: 0;
	}
	.legend-count {
		font-variant-numeric: tabular-nums;
		font-weight: 700;
		color: var(--color-text);
	}
</style>
