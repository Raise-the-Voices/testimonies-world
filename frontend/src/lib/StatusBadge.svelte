<script lang="ts" module>
	/**
	 * Module-level exports — the canonical 8 statuses and their display
	 * labels. Consumers (e.g. /persons filter dropdown, /statistics page)
	 * should import these rather than redeclaring them, so adding a new
	 * status only needs to be done in one place.
	 */
	export const STATUS_VALUES = [
		'detained',
		'disappeared',
		'restricted_movement',
		'released',
		'deceased',
		'unknown',
		'stateless',
		'rights_restricted',
	] as const;
	export type StatusValue = (typeof STATUS_VALUES)[number];

	export const statusLabels: Record<string, string> = {
		detained: 'Detained',
		disappeared: 'Disappeared',
		restricted_movement: 'Restricted Movement',
		released: 'Released',
		deceased: 'Deceased',
		unknown: 'Unknown',
		stateless: 'Stateless',
		rights_restricted: 'Rights Restricted',
	};
</script>

<script lang="ts">
	/**
	 * StatusBadge — semantic pill for Person.current_status.
	 *
	 * Usage:
	 *   <StatusBadge status={person.current_status} />
	 *   <StatusBadge status="deceased" variant="overlay" />
	 *
	 * The `overlay` variant applies `.badge--overlay` from app.css — a
	 * floating pill with backdrop blur, intended for use over image cards.
	 * Default `variant="default"` is a flat pill that matches the legacy
	 * Marturia styling.
	 */

	let {
		status,
		label,
		variant = 'default',
	}: {
		status: string;
		label?: string;
		variant?: 'default' | 'overlay';
	} = $props();
</script>

<span
	class="badge badge-{status}"
	class:badge--overlay={variant === 'overlay'}
>{label || statusLabels[status] || status}</span>
