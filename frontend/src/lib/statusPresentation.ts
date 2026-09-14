/**
 * Status presentation — single source of truth for testimonial
 * status labels and color tokens.
 *
 * The audit found the same six-state color set duplicated in two
 * places (TestimonialCard.svelte and WorkflowActions.svelte). When
 * a new status is added (or an existing one is renamed), both had
 * to be updated in lock-step — a regression waiting to happen.
 *
 * This module centralises:
 *   - STATUS_LABEL  : human-readable label keyed by status slug
 *   - STATUS_PILL   : CSS class tokens (status-{slug}) keyed by slug
 *                     so consumers can compose `class="status-pill {STATUS_PILL.draft}"`
 *
 * Adding a new status: add a row here + a matching CSS rule in
 * `app.css` (using the same `.testimonial-card-status-{slug}` /
 * `.status-pill-{slug}` selectors).
 */

export const STATUS_LABEL: Record<string, string> = {
	draft: 'Draft',
	under_review: 'Under review',
	published: 'Published',
	rejected: 'Rejected',
	archived: 'Archived',
};

/**
 * Inline-friendly human label for compact rendering (cards, table
 * cells, etc.). Falls back to `slug.replace('_', ' ')` so an
 * unrecognised status doesn't render as a raw enum value.
 */
export function statusLabel(status: string): string {
	return STATUS_LABEL[status] ?? status.replace(/_/g, ' ');
}

/**
 * CSS modifier token for the pill / badge background. Pair with a
 * base `.status-pill` or `.testimonial-card-status` rule.
 */
export function statusPillClass(status: string): string {
	return `status-pill-${status}`;
}