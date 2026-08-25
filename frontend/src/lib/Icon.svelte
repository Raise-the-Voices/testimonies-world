<script lang="ts" module>
	/**
	 * Module-level: export the IconName type so other components can type
	 * their `icon` prop without duplicating the union.
	 */
	export type IconName =
		| 'cases'
		| 'globe'
		| 'lock'
		| 'help'
		| 'pencil'
		| 'refresh'
		| 'megaphone'
		| 'newspaper'
		| 'arrow-right'
		| 'chart-bar';

	// All icons share the same 24×24 viewBox + the same stroke style so
	// they read as a coherent family regardless of where they're used.
	export const iconPaths: Record<IconName, string> = {
		cases: `<path d="M20 7h-3a2 2 0 0 1-2-2V2"/><path d="M9 18a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v3z"/><path d="M14 2H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2z"/><path d="M22 18a2 2 0 0 1-2 2h-3a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v3z"/>`,
		globe: `<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>`,
		lock: `<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>`,
		help: `<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>`,
		pencil: `<path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>`,
		refresh: `<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>`,
		megaphone: `<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>`,
		newspaper: `<path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8"/><path d="M15 18h-5"/><path d="M10 6h8v4h-8V6z"/>`,
		'arrow-right': `<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>`,
		'chart-bar': `<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>`,
	};
</script>

<script lang="ts">
	/**
	 * Icon — centralized icon registry for the app.
	 *
	 * Usage:
	 *   <Icon name="cases" size={20} />
	 *   <Icon name="globe" />          <!-- uses default size -->
	 *
	 * To add a new icon, add an entry to `iconPaths` in the module block
	 * above. All icons share the same viewBox (24×24) and stroke
	 * conventions so they read as one family.
	 */

	let {
		name,
		size = 18,
		strokeWidth = 2,
		ariaHidden = true,
		ariaLabel = '',
	}: {
		name: IconName;
		size?: number;
		strokeWidth?: number;
		ariaHidden?: boolean;
		ariaLabel?: string;
	} = $props();
</script>

<svg
	xmlns="http://www.w3.org/2000/svg"
	viewBox="0 0 24 24"
	width={size}
	height={size}
	fill="none"
	stroke="currentColor"
	stroke-width={strokeWidth}
	stroke-linecap="round"
	stroke-linejoin="round"
	aria-hidden={ariaHidden ? 'true' : undefined}
	aria-label={ariaHidden ? undefined : ariaLabel || name}
	role={ariaHidden ? undefined : 'img'}
>{@html iconPaths[name]}</svg>