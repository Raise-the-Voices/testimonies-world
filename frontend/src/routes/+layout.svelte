<script lang="ts">
	import { base } from '$app/paths';
	import { user, ready, loadSession, isVolunteer, isAdvocate } from '$lib/session';
	import { clearDraft } from '$lib/submitDraft';
	import Bell from '$lib/Bell.svelte';
	import Skeleton from '$lib/Skeleton.svelte';
	import '../app.css';
	import { page } from '$app/stores';
	import type { LayoutData } from './$types';

	let { children, data }: { children: any; data: LayoutData } = $props();

	// Seed the session store from the universal load BEFORE any child
	// effect runs. `$effect.pre` is Svelte 5's "before DOM update"
	// effect — it runs ahead of `$effect` and `$derived` re-evaluation,
	// so children that read `$user` in their own `$effect` see the
	// hydrated value. The previous `onMount(loadSession)` ran AFTER
	// children mounted, causing protected pages to flash their
	// "must be logged in" or "couldn't load" error state on hard
	// refresh.
	$effect.pre(() => {
		if (data.user) user.set(data.user);
		ready.set(true);
	});

	let currentUser = $derived($user);
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
</script>

<header class="header-container">
	<div class="main-header">
		<a href="{base}/" class="logo">
			<p>Raise the Voices</p>
			<p>Cases</p>
		</a>
		<nav class="main-navigation">
			<ul>
				{#if currentUser.authenticated}
					<li><a href="{base}/dashboard" class:active={$page.url.pathname.startsWith(`${base}/dashboard`)}>Dashboard</a></li>
				{/if}
				<li><a href="{base}/persons" class:active={$page.url.pathname.startsWith(`${base}/persons`)}>Cases</a></li>
				<li><a href="{base}/statistics" class:active={$page.url.pathname.startsWith(`${base}/statistics`)}>Statistics</a></li>
				{#if isVolunteer(currentUser)}
					<li><a href="{base}/submit" class:active={$page.url.pathname.startsWith(`${base}/submit`)}>Submit</a></li>
					<li><a href="{base}/reports" class:active={$page.url.pathname.startsWith(`${base}/reports`)}>Reports</a></li>
					<li><a href="{base}/watchdog" class:active={$page.url.pathname.startsWith(`${base}/watchdog`)}>Watchdog</a></li>
				{/if}
				{#if isAdvocate(currentUser)}
					<li><a href="{base}/casework" class:active={$page.url.pathname.startsWith(`${base}/casework`)}>Casework</a></li>
					<li><a href="{base}/contacts" class:active={$page.url.pathname.startsWith(`${base}/contacts`)}>Contacts</a></li>
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

<main class="page">
	<div class="wrapper">
		{#if $ready}
			{@render children()}
		{:else}
			<!-- Auth-hydration skeleton: renders while the universal
			     load is in flight (server-side first paint during SSR
			     hydration; client-side when re-fetching after a
			     cross-tab logout). Without this gate, protected pages
			     see `$user` as the default `{ authenticated: false }`
			     and flash their "must be logged in" or "couldn't
			     load (HTTP 0)" state on hard refresh. -->
			<div class="auth-hydrating" aria-busy="true" aria-live="polite">
				<Skeleton variant="rect" width="100%" height="12rem" />
				<Skeleton variant="text-block" lines={4} />
			</div>
		{/if}
	</div>
</main>

<footer>
	<div class="container">
		<p class="muted small"><a href="https://raisethevoices.org">RaisetheVoices.org</a> — Every person matters.</p>
	</div>
</footer>

<style>
	.header-container {
		background: var(--color-primary);
	}
	.main-header {
		height: 100px;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 90%;
		max-width: 1140px;
		margin: 0 auto;
		letter-spacing: 0.08rem;
	}
	.logo {
		flex: 1 0 200px;
		max-width: 200px;
		color: var(--color-text-light);
		font-size: 1.2em;
		line-height: 1.4;
		background: rgba(0, 0, 0, 0.55);
		text-align: center;
		text-transform: uppercase;
		align-self: stretch;
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
	.main-navigation {
		flex: 4;
	}
	.main-navigation ul {
		display: flex;
		align-items: center;
		justify-content: flex-end;
	}
	.main-navigation li {
		font-size: 0.95em;
	}
	.main-navigation a {
		display: block;
		padding: 20px;
		font-weight: bold;
		text-decoration: none;
		text-transform: uppercase;
		color: var(--color-text-light);
		border-radius: 4px;
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

	.nav-user {
		padding: 20px;
		color: rgba(250, 250, 250, 0.7);
		font-size: 0.85em;
	}
	.nav-bell {
		display: inline-flex;
		align-items: center;
	}
	.nav-avatar {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 36px;
		height: 36px;
		border-radius: 50%;
		background: rgba(0, 0, 0, 0.35);
		color: var(--color-text-light);
		font-weight: bold;
		font-size: 1rem;
		margin: 0 20px;
		cursor: default;
	}
	main.page {
		padding: 40px 0;
		min-height: calc(100vh - 160px);
	}
	.wrapper {
		width: 85%;
		max-width: 1140px;
		margin: 0 auto;
	}
	footer {
		border-top: 1px solid var(--color-border-light);
		padding: 1rem 0;
		margin-top: 2rem;
	}

	/* Auth-hydration skeleton: matches the visual weight of a real
	   page so the swap from skeleton to content doesn't reflow. */
	.auth-hydrating {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		min-height: 18rem;
	}

	@media (max-width: 800px) {
		.main-header {
			flex-direction: column;
			height: auto;
			padding: 10px 0;
		}
		.logo {
			max-width: none;
			width: 100%;
			padding: 10px;
		}
		.main-navigation ul {
			flex-wrap: wrap;
			justify-content: center;
		}
		.main-navigation a {
			padding: 10px 12px;
			font-size: 0.85em;
		}
	}
</style>
