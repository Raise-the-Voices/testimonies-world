<script lang="ts">
	import { base } from '$app/paths';
	import { user, ready, loadSession, isVolunteer, isAdvocate } from '$lib/session';
	import { clearDraft } from '$lib/submitDraft';
	import Bell from '$lib/Bell.svelte';
	import '../app.css';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import type { LayoutData } from './$types';

	let { children, data }: { children: any; data: LayoutData } = $props();

	// SSR-hydrated auth state. `data.user` is populated by the root
	// +layout.ts on every navigation (server and client), so the
	// SSR HTML and post-hydration HTML render against the SAME auth
	// state — no flicker on hard refresh of /dashboard, /casework,
	// /submit, etc.
	//
	// Why not just `$user`? Because `$user` is a module-level writable
	// that defaults to `{ authenticated: false }` during SSR. Reading
	// from it on the server would render the unauthenticated chrome
	// ("you must be logged in", no Dashboard nav link, ...) and the
	// client hydration would then snap to the authenticated state —
	// the exact flicker we're trying to eliminate.
	//
	// `?? $user` is the fallback for client-side reactivity (logout,
	// cross-tab session expiry, etc.) where the store changes without
	// a fresh +layout.ts run.
	let currentUser = $derived(data.user ?? $user);

	// Seed the global session store from the SSR data on the client.
	// `$effect.pre` is client-only — it runs before child `$effect`s
	// fire on hydration, so any child that subscribes to `$user`
	// (e.g. the Bell's reactive isAdvocate check) sees the hydrated
	// value on first render. The store itself is not the SSR source
	// of truth — `data.user` is — this just keeps the global store
	// in sync for client-side mutations.
	$effect.pre(() => {
		if (data.user) user.set(data.user);
		ready.set(true);
	});
	let prevAuthenticated = $state<boolean | null>(null);

	// --- Logout cleanup -------------------------------------------------
	// When the user transitions from authenticated → unauthenticated
	// (e.g. clicks Logout, session expires, or another tab logs them
	// out), wipe any submit-form drafts they had on this browser.
	// This protects sensitive human-rights data on shared/public
	// browsers — the same reason the rest of the platform
	// audit-logs sensitive access. Drafts are keyed by userId, so
	// account A logging out doesn't touch account B's draft.
	$effect(() => {
		const authed = currentUser.authenticated;
		if (prevAuthenticated === null) {
			prevAuthenticated = authed;
			return;
		}
		if (prevAuthenticated && !authed && currentUser.username) {
			clearDraft(currentUser.username);
		}
		prevAuthenticated = authed;
	});

	// Cross-tab logout: when another tab logs the user out, the
	// 'storage' event fires here. The session cookie is shared — a
	// logout in tab A invalidates the session in tab B too. We
	// re-read /api/session/ via the client-side path, which doesn't
	// need cookie forwarding (cookies travel with every fetch via
	// `credentials: 'include'`).
	if (typeof window !== 'undefined') {
		window.addEventListener('storage', (e) => {
			if (e.key === null || e.key === 'sessionid') {
				loadSession();
			}
		});
	}

	// --- Mobile nav drawer ---------------------------------------------
	// Hamburger button is visible <768px; tapping it opens a slide-in
	// drawer with the same nav items as the desktop nav. The drawer
	// auto-closes on route change (any nav click inside the drawer
	// triggers $page.url update → reactive `closeDrawer()`).
	let drawerOpen = $state(false);

	function closeDrawer() {
		drawerOpen = false;
	}

	// Auto-close on route change — clicking a nav link should land
	// the user on the new page with the drawer collapsed, not still
	// hanging open over the destination.
	$effect(() => {
		// Touch $page.url so this effect re-runs on every navigation.
		void $page.url;
		closeDrawer();
	});

	// Lock body scroll while the drawer is open (mobile only — desktop
	// never opens the drawer, so this is a no-op there).
	$effect(() => {
		if (typeof document === 'undefined') return;
		if (drawerOpen) {
			document.body.style.overflow = 'hidden';
		} else {
			document.body.style.overflow = '';
		}
	});

	// Close drawer on Escape.
	onMount(() => {
		const onKey = (e: KeyboardEvent) => {
			if (e.key === 'Escape' && drawerOpen) closeDrawer();
		};
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});
</script>

<!-- Site-wide SEO defaults. Per-page <svelte:head> blocks emit
     <title>, og:description, og:type — those override or extend
     these. canonical + og:title are derived from the current URL
     so each page gets a unique shareable link. -->
<svelte:head>
	<link rel="canonical" href="{$page.url.origin}{$page.url.pathname}" />
	<meta property="og:title" content={`${$page.url.pathname === '/' ? 'Testimonies.world' : $page.url.pathname.replace(/^\//, '').replace(/\/$/, '').replace(/^./, (c) => c.toUpperCase())} — Testimonies.world`} />
	<meta property="og:url" content="{$page.url.origin}{$page.url.pathname}" />
</svelte:head>

<!-- Skip-to-content link (WCAG 2.4.1). Visually hidden until the user
     tabs to it; jumps focus past the header / nav drawer to the
     main content. -->
<a href="#main-content" class="skip-link">Skip to main content</a>

<header class="header-container">
	<div class="main-header container-app">
		<a href="{base}/" class="logo">
			<p>Raise the Voices</p>
			<p>Cases</p>
		</a>

		<!-- Hamburger — visible <768px only. Toggles the drawer. -->
		<button
			type="button"
			class="nav-toggle"
			aria-label={drawerOpen ? 'Close navigation' : 'Open navigation'}
			aria-expanded={drawerOpen}
			aria-controls="primary-nav-drawer"
			onclick={() => (drawerOpen = !drawerOpen)}
		>
			<span class="nav-toggle-bar" aria-hidden="true"></span>
			<span class="nav-toggle-bar" aria-hidden="true"></span>
			<span class="nav-toggle-bar" aria-hidden="true"></span>
		</button>

		<!-- Desktop nav — visible >=768px only. Same items as the
		     drawer; the drawer is the mobile mirror. -->
		<nav class="main-navigation" aria-label="Primary">
			<ul>
				{#if currentUser.authenticated}
					<li><a href="{base}/dashboard" class:active={$page.url.pathname.startsWith(`${base}/dashboard`)} aria-current={$page.url.pathname.startsWith(`${base}/dashboard`) ? "page" : undefined}>Dashboard</a></li>
				{/if}
				<li><a href="{base}/persons" class:active={$page.url.pathname.startsWith(`${base}/persons`)} aria-current={$page.url.pathname.startsWith(`${base}/persons`) ? "page" : undefined}>Cases</a></li>
				<li><a href="{base}/statistics" class:active={$page.url.pathname.startsWith(`${base}/statistics`)} aria-current={$page.url.pathname.startsWith(`${base}/statistics`) ? "page" : undefined}>Statistics</a></li>
				{#if isVolunteer(currentUser)}
					<li><a href="{base}/submit" class:active={$page.url.pathname.startsWith(`${base}/submit`)} aria-current={$page.url.pathname.startsWith(`${base}/submit`) ? "page" : undefined}>Submit</a></li>
					<li><a href="{base}/reports" class:active={$page.url.pathname.startsWith(`${base}/reports`)} aria-current={$page.url.pathname.startsWith(`${base}/reports`) ? "page" : undefined}>Reports</a></li>
					<li><a href="{base}/watchdog" class:active={$page.url.pathname.startsWith(`${base}/watchdog`)} aria-current={$page.url.pathname.startsWith(`${base}/watchdog`) ? "page" : undefined}>Watchdog</a></li>
				{/if}
				{#if isAdvocate(currentUser)}
					<li><a href="{base}/casework" class:active={$page.url.pathname.startsWith(`${base}/casework`)} aria-current={$page.url.pathname.startsWith(`${base}/casework`) ? "page" : undefined}>Casework</a></li>
					<li><a href="{base}/contacts" class:active={$page.url.pathname.startsWith(`${base}/contacts`)} aria-current={$page.url.pathname.startsWith(`${base}/contacts`) ? "page" : undefined}>Contacts</a></li>
				{/if}
				{#if currentUser.authenticated}
					<li class="nav-bell"><Bell /></li>
					<li><span class="nav-avatar" title={currentUser.username}>{currentUser.username?.charAt(0).toUpperCase()}</span></li>
				{:else}
					<li><a href="{base}/accounts/google/login/?next={base}/">Login</a></li>
				{/if}
			</ul>
		</nav>
	</div>
</header>

<!-- Mobile drawer — same nav items as the desktop nav, but in a
     slide-in panel. Hidden by default, slides in from the right
     when the hamburger is tapped. A scrim covers the rest of the
     viewport so tapping outside closes it. -->
{#if drawerOpen}
	<button
		type="button"
		class="nav-scrim"
		aria-label="Close navigation"
		onclick={closeDrawer}
	></button>
{/if}
<nav
	id="primary-nav-drawer"
	class="nav-drawer"
	class:nav-drawer-open={drawerOpen}
	aria-label="Primary"
	aria-hidden={!drawerOpen}
	inert={!drawerOpen}
>
	<ul>
		{#if currentUser.authenticated}
			<li><a href="{base}/dashboard" class:active={$page.url.pathname.startsWith(`${base}/dashboard`)} aria-current={$page.url.pathname.startsWith(`${base}/dashboard`) ? "page" : undefined} onclick={closeDrawer}>Dashboard</a></li>
		{/if}
		<li><a href="{base}/persons" class:active={$page.url.pathname.startsWith(`${base}/persons`)} aria-current={$page.url.pathname.startsWith(`${base}/persons`) ? "page" : undefined} onclick={closeDrawer}>Cases</a></li>
		<li><a href="{base}/statistics" class:active={$page.url.pathname.startsWith(`${base}/statistics`)} aria-current={$page.url.pathname.startsWith(`${base}/statistics`) ? "page" : undefined} onclick={closeDrawer}>Statistics</a></li>
		{#if isVolunteer(currentUser)}
			<li><a href="{base}/submit" class:active={$page.url.pathname.startsWith(`${base}/submit`)} aria-current={$page.url.pathname.startsWith(`${base}/submit`) ? "page" : undefined} onclick={closeDrawer}>Submit</a></li>
			<li><a href="{base}/reports" class:active={$page.url.pathname.startsWith(`${base}/reports`)} aria-current={$page.url.pathname.startsWith(`${base}/reports`) ? "page" : undefined} onclick={closeDrawer}>Reports</a></li>
			<li><a href="{base}/watchdog" class:active={$page.url.pathname.startsWith(`${base}/watchdog`)} aria-current={$page.url.pathname.startsWith(`${base}/watchdog`) ? "page" : undefined} onclick={closeDrawer}>Watchdog</a></li>
		{/if}
		{#if isAdvocate(currentUser)}
			<li><a href="{base}/casework" class:active={$page.url.pathname.startsWith(`${base}/casework`)} aria-current={$page.url.pathname.startsWith(`${base}/casework`) ? "page" : undefined} onclick={closeDrawer}>Casework</a></li>
			<li><a href="{base}/contacts" class:active={$page.url.pathname.startsWith(`${base}/contacts`)} aria-current={$page.url.pathname.startsWith(`${base}/contacts`) ? "page" : undefined} onclick={closeDrawer}>Contacts</a></li>
		{/if}
		{#if currentUser.authenticated}
			<li class="nav-bell"><Bell /></li>
			<li><span class="nav-avatar" title={currentUser.username}>{currentUser.username?.charAt(0).toUpperCase()}</span></li>
		{:else}
			<li><a href="{base}/accounts/google/login/?next={base}/" onclick={closeDrawer}>Login</a></li>
		{/if}
	</ul>
</nav>

<main id="main-content" class="page" tabindex="-1">
	<div class="container-app">
		{@render children()}
	</div>
</main>

<footer>
	<div class="container-app">
		<p class="muted small"><a href="https://raisethevoices.org">RaisetheVoices.org</a> — Every person matters.</p>
	</div>
</footer>

<style>
	.header-container {
		background: var(--color-primary);
	}
	/* Header grid: logo (left) + hamburger (right) on mobile; logo
	   (left) + nav (right) on desktop. The nav uses `margin-left: auto`
	   so it sits at the right end without forcing an artificial gap
	   between logo and first link — the gap is owned by the parent
	   flex container and the inner <ul>'s gap property. */
	.main-header {
		min-height: 80px;
		display: flex;
		align-items: center;
		gap: 1.5rem;
		padding-block: 0.75rem;
		letter-spacing: 0.08rem;
	}
	/* Tighten the header height on phones — saves vertical real estate. */
	@media (max-width: 767px) {
		.main-header {
			min-height: 60px;
			gap: 0.75rem;
		}
	}

	.logo {
		flex: 0 0 auto;
		min-width: 140px;
		max-width: 200px;
		color: var(--color-text-light);
		font-size: 1.05em;
		line-height: 1.2;
		background: rgba(0, 0, 0, 0.55);
		text-align: center;
		text-transform: uppercase;
		padding: 0.6rem 1rem;
		border-radius: 4px;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		text-decoration: none;
	}
	.logo:hover {
		text-decoration: none;
		color: var(--color-text-light);
	}
	.logo p {
		margin: 0;
		padding: 0;
	}
	/* Make the logo block a touch smaller on phones — the full-width
	   black band ate too much of the header at narrow widths. */
	@media (max-width: 767px) {
		.logo {
			min-width: 0;
			font-size: 0.95em;
			padding: 0.45rem 0.75rem;
		}
	}

	/* === Hamburger button ===
	   Hidden on desktop (>=768px); the inline nav handles desktop.
	   Visible on mobile; toggles the slide-in drawer. */
	.nav-toggle {
		display: none;
		flex-direction: column;
		justify-content: space-between;
		width: 38px;
		height: 32px;
		padding: 6px 4px;
		background: rgba(0, 0, 0, 0.18);
		border: 0;
		border-radius: 6px;
		cursor: pointer;
		flex: 0 0 auto;
	}
	.nav-toggle:hover {
		background: rgba(0, 0, 0, 0.32);
	}
	.nav-toggle-bar {
		display: block;
		width: 100%;
		height: 3px;
		background: var(--color-text-light);
		border-radius: 2px;
		transition: transform 0.2s ease, opacity 0.2s ease;
	}
	.nav-toggle[aria-expanded='true'] .nav-toggle-bar:nth-child(1) {
		transform: translateY(7px) rotate(45deg);
	}
	.nav-toggle[aria-expanded='true'] .nav-toggle-bar:nth-child(2) {
		opacity: 0;
	}
	.nav-toggle[aria-expanded='true'] .nav-toggle-bar:nth-child(3) {
		transform: translateY(-7px) rotate(-45deg);
	}
	@media (max-width: 767px) {
		.nav-toggle {
			display: flex;
		}
	}

	/* === Desktop nav ===
	   Visible >=768px. Hidden on mobile — the drawer takes over.
	   `margin-left: auto` pushes the nav to the right end of the
	   header without forcing an artificial gap between logo and
	   first link; `flex: 0 1 auto` lets the nav shrink on narrow
	   desktop widths so items wrap inside the <ul> instead of
	   overflowing the header. */
	.main-navigation {
		margin-left: auto;
		flex: 0 1 auto;
		min-width: 0;
	}
	.main-navigation ul {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 0.5rem;
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.main-navigation li {
		display: flex;
		align-items: center;
		font-size: 0.95em;
	}
	/* All nav items (text link, bell, avatar) sit on the same
	   baseline via inline-flex + align-items: center. The link's
	   padding keeps the tap target generous (44px+). */
	.main-navigation a {
		display: inline-flex;
		align-items: center;
		padding: 0.7rem 0.85rem;
		font-weight: bold;
		text-decoration: none;
		text-transform: uppercase;
		color: var(--color-text-light);
		border-radius: 4px;
		white-space: nowrap;
		transition: background 0.15s ease;
	}
	.main-navigation a:hover {
		background: rgba(0, 0, 0, 0.16);
		color: var(--color-text-light);
	}

	.main-navigation a:hover,
	.main-navigation a.active {
		background: rgba(0, 0, 0, 0.25);
		color: var(--color-bg-white);
		border-bottom: 3px solid var(--color-bg-white);
	}

	.main-navigation a.active {
		cursor: default;
	}

	@media (max-width: 767px) {
		.main-navigation {
			display: none;
		}
	}

	/* === Mobile drawer ===
	   Off-canvas panel that slides in from the right when the
	   hamburger is tapped. Same nav items as the desktop nav;
	   the drawer is the mobile mirror. */
	.nav-drawer {
		position: fixed;
		top: 0;
		right: 0;
		bottom: 0;
		width: min(82vw, 320px);
		background: var(--color-primary);
		color: var(--color-text-light);
		padding: 1.25rem 0;
		transform: translateX(100%);
		transition: transform 0.25s ease;
		z-index: 60;
		box-shadow: -8px 0 24px rgba(0, 0, 0, 0.18);
		overflow-y: auto;
		-webkit-overflow-scrolling: touch;
	}
	.nav-drawer-open {
		transform: translateX(0);
	}
	.nav-drawer ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
	}
	.nav-drawer li {
		margin: 0;
	}
	.nav-drawer a {
		display: block;
		padding: 0.9rem 1.25rem;
		font-weight: 700;
		text-transform: uppercase;
		text-decoration: none;
		color: var(--color-text-light);
		font-size: 0.95rem;
	}
	.nav-drawer a:hover {
		background: rgba(0, 0, 0, 0.25);
	}
	.nav-drawer a.active {
		background: rgba(0, 0, 0, 0.32);
		border-left: 3px solid var(--color-bg-white);
	}
	.nav-drawer .nav-bell {
		padding: 0.5rem 1.25rem;
	}
	.nav-drawer .nav-avatar {
		margin: 0.5rem 1.25rem;
	}

	/* Drawer is mobile-only; on desktop it's hidden outright. */
	@media (min-width: 768px) {
		.nav-drawer {
			display: none;
		}
	}

	/* Scrim — covers the rest of the viewport while the drawer is
	   open. Tapping the scrim closes the drawer (it's a button). */
	.nav-scrim {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.4);
		z-index: 55;
		border: 0;
		padding: 0;
		cursor: pointer;
		animation: scrim-fade-in 0.2s ease;
	}
	@keyframes scrim-fade-in {
		from { opacity: 0; }
		to { opacity: 1; }
	}
	@media (min-width: 768px) {
		.nav-scrim {
			display: none;
		}
	}

	.nav-user {
		padding: 20px;
		color: rgba(250, 250, 250, 0.7);
		font-size: 0.85em;
	}
	/* Bell: lift the inline margin Bell.svelte puts on its wrap so
	   the parent <ul> gap controls spacing consistently. */
	.nav-bell {
		display: inline-flex;
		align-items: center;
	}
	:global(.main-navigation .nav-bell .bell-wrap),
	:global(.main-navigation .nav-bell .bell-btn) {
		margin: 0;
	}
	/* Avatar: same diameter as the bell (38px), no horizontal margin
	   so the parent <ul> gap controls spacing. */
	.nav-avatar {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 38px;
		height: 38px;
		border-radius: 50%;
		background: rgba(0, 0, 0, 0.35);
		color: var(--color-text-light);
		font-weight: 700;
		font-size: 1rem;
		cursor: default;
	}

	main.page {
		padding: clamp(1.25rem, 4vw, 2.5rem) 0;
		min-height: calc(100vh - 200px);
	}
	footer {
		border-top: 1px solid var(--color-border-light);
		padding: 1rem 0;
		margin-top: 2rem;
	}

	@media (prefers-reduced-motion: reduce) {
		.nav-drawer,
		.nav-toggle-bar,
		.nav-scrim {
			transition: none !important;
			animation: none !important;
		}
	}
</style>
