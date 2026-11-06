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
		// Documentation Form Section D added these to the backend enum
		// (Person.Status). They are absent from STATUS_VALUES — the
		// /persons filter dropdown still offers only the original 8 —
		// but a case can carry one, so the label map covers all 13
		// the backend accepts (see schemas/personForm.ts).
		ongoing_enforced_disappearance: 'Ongoing enforced disappearance',
		found_alive: 'Found alive',
		found_dead: 'Found dead',
		case_closed: 'Case closed',
		other: 'Other',
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
