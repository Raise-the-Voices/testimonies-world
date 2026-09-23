<script lang="ts" module>
	/**
	 * Module-level: export the IconName type so other components can type
	 * their `icon` prop without duplicating the union.
	 *
	 * Two glyph styles live in one registry:
	 *   - stroke style (lucide-like): fill="none" stroke="currentColor".
	 *     Default mode; honors the `strokeWidth` prop.
	 *   - filled style (Material-like): fill="currentColor", no stroke.
	 *     Set `filled` on the component. Used by row-action buttons
	 *     (pencil, trash) and "private" badges (lock) where the heavier
	 *     filled glyph reads better at 11–16px.
	 *
	 * `*-fill` names map to filled glyphs; their paths are authored in
	 * the same 24×24 viewBox as the stroke family except where noted.
	 * `lock-fill` keeps its native 16×16 viewBox via the per-entry
	 * override (shifting coordinates would change stroke weight).
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
		| 'chart-bar'
		| 'search'
		| 'pin'
		| 'clock'
		| 'layout-grid'
		| 'list'
		| 'chevron-down'
		| 'x'
		| 'envelope'
		| 'dashboard'
		| 'plus'
		| 'people'
		| 'eye'
		| 'book'
		| 'pencil-fill'
		| 'trash-fill'
		| 'lock-fill';

	interface IconPath {
		/** Inner SVG markup. Becomes the <svg> body. */
		path: string;
		/** Override the default 24×24 viewBox. lock-fill uses 16×16. */
		viewBox?: string;
	}

	// All icons share the same 24×24 viewBox + the same stroke style so
	// they read as a coherent family regardless of where they're used.
	export const iconPaths: Record<IconName, IconPath> = {
		cases: { path: `<path d="M20 7h-3a2 2 0 0 1-2-2V2"/><path d="M9 18a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v3z"/><path d="M14 2H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2z"/><path d="M22 18a2 2 0 0 1-2 2h-3a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v3z"/>` },
		globe: { path: `<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>` },
		lock: { path: `<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>` },
		help: { path: `<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>` },
		pencil: { path: `<path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>` },
		refresh: { path: `<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>` },
		megaphone: { path: `<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>` },
		newspaper: { path: `<path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8"/><path d="M15 18h-5"/><path d="M10 6h8v4h-8V6z"/>` },
		'arrow-right': { path: `<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>` },
		'chart-bar': { path: `<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>` },
		search: { path: `<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>` },
		pin: { path: `<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>` },
		clock: { path: `<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>` },
		'layout-grid': { path: `<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>` },
		list: { path: `<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>` },
		'chevron-down': { path: `<polyline points="6 9 12 15 18 9"/>` },
		x: { path: `<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>` },
		// Real-feeling envelope: outer rounded rectangle with the classic
		// fold line dipping into the body. Stroke-only so it inherits
		// color and stacks cleanly on the dark header.
		envelope: { path: `<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3.5 6.5 12 13l8.5-6.5"/>` },
		// 4-square dashboard glyph: read as "overview tiles."
		dashboard: { path: `<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>` },
		// Plus: used on QuickActions "Submit a case" tile.
		plus: { path: `<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>` },
		// People: two overlapping circles for the contacts/casework tiles.
		people: { path: `<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>` },
		// Eye: used on the "Audit log" tile for Admin.
		eye: { path: `<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>` },
		// Open book: used on "Reports" tile.
		book: { path: `<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>` },
		// --- Filled glyphs (Material-style). Used by row-action buttons
		// and "private" badges where the heavier silhouette reads better
		// than the stroke style at 11–16px. ---
		'pencil-fill': { path: `<path fill="currentColor" d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>` },
		'trash-fill': { path: `<path fill="currentColor" d="M6 19a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>` },
		// Bootstrap-icons `lock-fill`. Native 16×16 viewBox — the path
		// is hand-tuned to that canvas and would visibly shrink if we
		// forced it into 24×24.
		'lock-fill': { path: `<path fill="currentColor" d="M4 7V5a4 4 0 1 1 8 0v2h1a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1h1zm2 0h4V5a2 2 0 1 0-4 0v2z"/>`, viewBox: '0 0 16 16' },
	};
</script>

<script lang="ts">
	/**
	 * Icon — centralized icon registry for the app.
	 *
	 * Usage:
	 *   <Icon name="cases" size={20} />
	 *   <Icon name="globe" />          <!-- uses default size -->
	 *   <Icon name="pencil-fill" size={14} filled />
	 *
	 * To add a new icon, add an entry to `iconPaths` in the module block
	 * above. All icons share the same viewBox (24×24) and stroke
	 * conventions so they read as one family — except `lock-fill`,
	 * which keeps its native 16×16 geometry.
	 */

	let {
		name,
		size = 18,
		strokeWidth = 2,
		filled = false,
		viewBox,
		ariaHidden = true,
		ariaLabel = '',
	}: {
		name: IconName;
		size?: number;
		strokeWidth?: number;
		/**
		 * Render in filled Material style (fill="currentColor", no stroke)
		 * instead of the default stroke style. strokeWidth is ignored
		 * when filled.
		 */
		filled?: boolean;
		/** Override the default 24×24 viewBox. */
		viewBox?: string;
		ariaHidden?: boolean;
		ariaLabel?: string;
	} = $props();

	const entry = $derived(iconPaths[name]);
	const resolvedViewBox = $derived(viewBox ?? entry.viewBox ?? '0 0 24 24');
</script>

<svg
	xmlns="http://www.w3.org/2000/svg"
	viewBox={resolvedViewBox}
	width={size}
	height={size}
	fill={filled ? 'currentColor' : 'none'}
	stroke={filled ? 'none' : 'currentColor'}
	stroke-width={filled ? undefined : strokeWidth}
	stroke-linecap="round"
	stroke-linejoin="round"
	aria-hidden={ariaHidden ? 'true' : undefined}
	aria-label={ariaHidden ? undefined : ariaLabel || name}
	role={ariaHidden ? undefined : 'img'}
>{@html entry.path}</svg>