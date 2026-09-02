<script lang="ts">
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import {
		getNotifications,
		markOneRead,
		markAllRead,
		type Notification,
	} from '$lib/notification';
	import Skeleton from '$lib/Skeleton.svelte';

	let filter = $state<'all' | 'unread'>('all');
	let loading = $state(true);
	let error = $state('');
	let items = $state<Notification[]>([]);

	async function load() {
		loading = true;
		error = '';
		try {
			const r = await getNotifications({ unread: filter === 'unread' });
			items = Array.isArray(r) ? (r as Notification[]) : (r.results ?? []);
		} catch (e: any) {
			error = e?.message ?? "Couldn't load notifications.";
			items = [];
		} finally {
			loading = false;
		}
	}

	onMount(load);
	$effect(() => {
		filter;
		load();
	});

	async function onItem(n: Notification) {
		if (!n.is_read) {
			try {
				await markOneRead(n.id);
				n.is_read = true;
			} catch {
				/* ignore */
			}
		}
		if (n.casework) goto(`${base}/casework/?id=${n.casework}`);
	}

	async function onMarkAll() {
		try {
			await markAllRead();
			items = items.map((n) => ({ ...n, is_read: true }));
		} catch {
			/* ignore */
		}
	}

	function summary(n: Notification): string {
		const actor = n.actor_name || 'Someone';
		const persons = (n.casework_persons && n.casework_persons.length > 0)
			? n.casework_persons.slice(0, 3).join(', ')
			: 'a case';
		switch (n.kind) {
		case 'record_created':
			return `${actor} logged a new ${n.casework_action_type ?? 'record'} on ${persons}`;
		case 'status_done':
			return `${actor} marked a record done for ${persons}`;
		case 'record_seen':
			return `${actor} opened your casework record`;
		default:
			return `${actor} updated casework on ${persons}`;
		}
	}

	function formatTime(iso: string): string {
		try {
			return new Date(iso).toLocaleString(undefined, {
				year: 'numeric',
				month: 'short',
				day: 'numeric',
				hour: '2-digit',
				minute: '2-digit',
			});
		} catch {
			return iso;
		}
	}

	const hasUnread = $derived(items.some((n) => !n.is_read));
</script>

<svelte:head>
	<title>Notifications — Testimonies.world</title>
</svelte:head>

<div class="container">
	<header class="page-header">
		<h1 class="page-title">Notifications</h1>
		{#if hasUnread}
			<button type="button" class="btn btn-secondary" onclick={onMarkAll}>
				Mark all read
			</button>
		{/if}
	</header>

	<div class="filters" role="tablist" aria-label="Filter notifications">
		<button
			type="button"
			class="filter-tab"
			class:filter-tab-active={filter === 'all'}
			role="tab"
			aria-selected={filter === 'all'}
			onclick={() => (filter = 'all')}
		>All</button>
		<button
			type="button"
			class="filter-tab"
			class:filter-tab-active={filter === 'unread'}
			role="tab"
			aria-selected={filter === 'unread'}
			onclick={() => (filter = 'unread')}
		>Unread</button>
	</div>

	{#if loading}
		<div class="notif-skeleton" aria-busy="true" aria-label="Loading notifications">
			<Skeleton variant="rect" height="3.2rem" />
			<Skeleton variant="rect" height="3.2rem" />
			<Skeleton variant="rect" height="3.2rem" />
		</div>
	{:else if error}
		<div class="state-card state-error" role="alert">
			<div class="state-icon state-icon-error" aria-hidden="true">!</div>
			<h2 class="state-title">Couldn't load notifications</h2>
			<p class="state-body">{error}</p>
			<button type="button" class="btn btn-primary" onclick={load}>Try again</button>
		</div>
	{:else if items.length === 0}
		<div class="state-card state-empty">
			<div class="state-icon state-icon-empty" aria-hidden="true">✓</div>
			<h2 class="state-title">
				{filter === 'unread' ? 'Nothing unread' : 'No notifications yet'}
			</h2>
			<p class="state-body">
				{filter === 'unread'
					? 'You are caught up. New casework activity will appear here.'
					: 'New casework activity from your teammates will appear here.'}
			</p>
		</div>
	{:else}
		<section class="list" aria-label="Notifications">
			{#each items as n (n.id)}
				<article class="row" class:row-unread={!n.is_read}>
					<button
						type="button"
						class="row-body"
						onclick={() => onItem(n)}
						aria-label={summary(n)}
					>
						<span class="row-text">{summary(n)}</span>
						<time class="row-time" datetime={n.created_at}>{formatTime(n.created_at)}</time>
					</button>
				</article>
			{/each}
		</section>
	{/if}
</div>

<style>
	.page-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		margin-bottom: 1.5rem;
		flex-wrap: wrap;
	}
	.page-title {
		margin: 0;
		color: var(--color-primary);
		font-size: 1.85rem;
		font-weight: 700;
		letter-spacing: -0.01em;
	}
	.filters {
		display: flex;
		gap: 0.4rem;
		margin-bottom: 1.25rem;
		border-bottom: 1px solid var(--color-border-subtle);
	}
	.filter-tab {
		background: transparent;
		border: 0;
		padding: 0.5rem 0.9rem;
		font: inherit;
		font-size: 0.9rem;
		color: var(--color-text-muted);
		cursor: pointer;
		border-bottom: 2px solid transparent;
	}
	.filter-tab:hover {
		color: var(--color-text);
	}
	.filter-tab-active {
		color: var(--color-primary);
		border-bottom-color: var(--color-primary);
		font-weight: 600;
	}
	.notif-skeleton {
		display: flex;
		flex-direction: column;
		gap: 0.6rem;
	}
	.list {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}
	.row {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-subtle);
		border-left: 4px solid transparent;
		border-radius: var(--radius-card-lg);
		box-shadow: var(--shadow-card);
	}
	.row-unread {
		border-left-color: var(--color-primary);
		background: var(--color-primary-tint);
	}
	.row-body {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
		width: 100%;
		text-align: left;
		background: transparent;
		border: 0;
		padding: 0.85rem 1rem;
		cursor: pointer;
		font: inherit;
		color: inherit;
		border-radius: inherit;
	}
	.row-body:hover {
		filter: brightness(0.97);
	}
	.row-text {
		font-size: 0.93rem;
		line-height: 1.45;
		color: var(--color-text);
	}
	.row-time {
		font-size: 0.78rem;
		color: var(--color-text-muted);
	}
	.state-card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-subtle);
		border-radius: var(--radius-card-lg);
		padding: 2.5rem 2rem;
		text-align: center;
		box-shadow: var(--shadow-card);
		max-width: 540px;
		margin: 1.5rem auto;
	}
	.state-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 48px;
		height: 48px;
		border-radius: 50%;
		font-family: 'Georgia', serif;
		font-style: italic;
		font-weight: 700;
		font-size: 1.4rem;
		color: white;
		margin-bottom: 1rem;
	}
	.state-icon-empty { background: var(--color-success); }
	.state-icon-error { background: var(--color-danger); }
	.state-title {
		margin: 0 0 0.5rem 0;
		color: var(--color-text);
		font-size: 1.15rem;
		font-weight: 700;
	}
	.state-body {
		margin: 0;
		color: var(--color-text-muted);
		font-size: 0.95rem;
		line-height: 1.55;
	}
	@media (prefers-reduced-motion: reduce) {
		.row-body { transition: none; }
	}
</style>