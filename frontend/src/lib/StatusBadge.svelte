<script lang="ts">
	let { status, label }: { status: string; label?: string } = $props();

	const labels: Record<string, string> = {
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

<span class="badge badge-{status}">{label || labels[status] || status}</span>
