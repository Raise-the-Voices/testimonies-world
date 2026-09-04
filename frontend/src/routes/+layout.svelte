<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { user, loadSession, isVolunteer, isAdvocate } from '$lib/session';
	import Bell from '$lib/Bell.svelte';
	import '../app.css';
	import { page } from '$app/stores';

	let { children } = $props();
	let currentUser = $derived($user);

	onMount(() => {
		loadSession();
	});
</script>

<header class="header-container">
	<div class="main-header">
		<a href="{base}/" class="logo">
			<p>Raise the Voices</p>
			<p>Cases</p>
		</a>
		<nav class="main-navigation">
			<ul>
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
		{@render children()}
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
