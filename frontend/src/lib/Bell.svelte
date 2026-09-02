<script lang="ts">
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { user, isAdvocate } from '$lib/session';
	import {
		getUnreadCount,
		getNotifications,
		markOneRead,
		markAllRead,
		type Notification,
	} from '$lib/notification';

	let unread = $state(0);
	let items = $state<Notification[]>([]);
	let open = $state(false);
	let loading = $state(false);
	let panelRef = $state<HTMLElement | null>(null);

	async function refresh() {
		if (!$user.authenticated) {
			unread = 0;
			items = [];
			return;
		}
		try {
			const c = await getUnreadCount();
			unread = c.count;
		} catch {
			unread = 0;
		}
		try {
			const r = await getNotifications({});
			items = Array.isArray(r) ? (r as Notification[]) : (r.results ?? []);
		} catch {
			items = [];
		}
	}

	onMount(() => {
		refresh();
		// Re-poll every 60s while mounted — cheap, keeps the bell roughly
	// fresh without websockets.
		const id = setInterval(refresh, 60_000);
		return () => clearInterval(id);
	});

	function onDocClick(e: MouseEvent) {
		if (!panelRef) return;
		if (open && !panelRef.contains(e.target as Node)) {
			open = false;
		}
	}

	$effect(() => {
		if (!open) return;
		document.addEventListener('mousedown', onDocClick);
		return () => document.removeEventListener('mousedown', onDocClick);
	});

	async function toggle() {
		open = !open;
		if (open && unread > 0) {
			// Refresh so the latest items appear at the top.
			loading = true;
			await refresh();
			loading = false;
		}
	}

	async function onItemClick(n: Notification) {
		if (!n.is_read) {
			try {
				await markOneRead(n.id);
				n.is_read = true;
				unread = Math.max(0, unread - 1);
			} catch {
				/* silent — they can mark from the page */
			}
		}
		open = false;
		if (n.casework) {
			goto(`${base}/casework/?id=${n.casework}`);
		}
	}

	async function onMarkAll(e: MouseEvent) {
		e.stopPropagation();
		try {
			await markAllRead();
			unread = 0;
			items = items.map((n) => ({ ...n, is_read: true }));
		} catch {
			/* ignore */
		}
	}

	function summary(n: Notification): string {
		const actor = n.actor_name || 'Someone';
		const persons = (n.casework_persons && n.casework_persons.length > 0)
			? n.casework_persons.slice(0, 2).join(', ')
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

	function timeAgo(iso: string): string {
		try {
			const d = new Date(iso);
			const diff = (Date.now() - d.getTime()) / 1000;
			if (diff < 60) return 'just now';
			if (diff < 3600) return `${Math.floor(diff / 60)}m`;
			if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
			return `${Math.floor(diff / 86400)}d`;
		} catch {
			return '';
		}
	}
</script>

{#if isAdvocate($user)}
	<div class="bell-wrap" bind:this={panelRef}>
		<button
			type="button"
			class="bell-btn"
			aria-label="Notifications"
			aria-expanded={open}
			onclick={toggle}
		>
			<span class="bell-icon" aria-hidden="true">◔</span>
			{#if unread > 0}
				<span class="bell-badge" aria-label="{unread} unread">{unread}</span>
			{/if}
		</button>

		{#if open}
			<div class="bell-panel" role="dialog" aria-label="Notifications">
				<header class="bell-header">
					<span>Notifications</span>
					{#if unread > 0}
						<button type="button" class="bell-link" onclick={onMarkAll}>Mark all read</button>
					{/if}
				</header>
				<div class="bell-body">
					{#if loading}
						<p class="bell-empty">Loading…</p>
					{:else if items.length === 0}
						<p class="bell-empty">No notifications yet.</p>
					{:else}
						<ul class="bell-list">
							{#each items.slice(0, 5) as n (n.id)}
								<li>
									<button
										type="button"
										class="bell-item"
										class:bell-item-unread={!n.is_read}
										onclick={() => onItemClick(n)}
									>
										<span class="bell-item-text">{summary(n)}</span>
										<span class="bell-item-time">{timeAgo(n.created_at)}</span>
									</button>
								</li>
							{/each}
						</ul>
						<footer class="bell-footer">
							<a href="{base}/notifications" onclick={() => (open = false)}>View all</a>
						</footer>
					{/if}
				</div>
			</div>
		{/if}
	</div>
{/if}

<style>
	.bell-wrap {
		position: relative;
		display: inline-flex;
		align-items: center;
		margin: 0 4px;
	}
	.bell-btn {
		position: relative;
		background: rgba(0, 0, 0, 0.18);
		border: 0;
		color: var(--color-text-light);
		font-size: 1.1rem;
		width: 38px;
		height: 38px;
		border-radius: 50%;
		cursor: pointer;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		transition: background 0.15s ease;
	}
	.bell-btn:hover {
		background: rgba(0, 0, 0, 0.32);
	}
	.bell-icon {
		font-family: 'Georgia', serif;
		font-size: 1.1rem;
		line-height: 1;
	}
	.bell-badge {
		position: absolute;
		top: -2px;
		right: -2px;
		min-width: 18px;
		height: 18px;
		padding: 0 4px;
		border-radius: 9px;
		background: var(--color-danger);
		color: white;
		font-size: 0.7rem;
		font-weight: 700;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		font-variant-numeric: tabular-nums;
	}
	.bell-panel {
		position: absolute;
		top: calc(100% + 8px);
		right: 0;
		min-width: 320px;
		max-width: 380px;
		background: var(--color-bg-white);
		color: var(--color-text);
		border: 1px solid var(--color-border-subtle);
		border-radius: var(--radius-card-lg);
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
		z-index: 100;
	}
	.bell-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.7rem 0.9rem;
		border-bottom: 1px solid var(--color-border-subtle);
		font-weight: 600;
		font-size: 0.9rem;
	}
	.bell-link {
		background: transparent;
		border: 0;
		color: var(--color-primary-light);
		font-size: 0.78rem;
		font-weight: 500;
		cursor: pointer;
		text-decoration: underline;
		text-underline-offset: 2px;
	}
	.bell-link:hover {
		color: var(--color-primary);
	}
	.bell-body {
		max-height: 360px;
		overflow-y: auto;
	}
	.bell-empty {
		margin: 0;
		padding: 1rem 0.9rem;
		color: var(--color-text-muted);
		font-size: 0.88rem;
	}
	.bell-list {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.bell-item {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
		width: 100%;
		text-align: left;
		background: transparent;
		border: 0;
		border-top: 1px solid var(--color-border-subtle);
		padding: 0.7rem 0.9rem;
		cursor: pointer;
		font: inherit;
		color: inherit;
	}
	.bell-item:hover {
		background: var(--color-surface);
	}
	.bell-item-unread {
		background: var(--color-primary-tint);
	}
	.bell-item-unread:hover {
		background: var(--color-primary-tint);
		filter: brightness(0.97);
	}
	.bell-item-text {
		font-size: 0.85rem;
		line-height: 1.4;
		color: var(--color-text);
	}
	.bell-item-time {
		font-size: 0.72rem;
		color: var(--color-text-muted);
	}
	.bell-footer {
		padding: 0.55rem 0.9rem;
		text-align: center;
		border-top: 1px solid var(--color-border-subtle);
	}
	.bell-footer a {
		font-size: 0.82rem;
		color: var(--color-primary-light);
		text-decoration: underline;
		text-underline-offset: 2px;
	}
	.bell-footer a:hover {
		color: var(--color-primary);
	}
</style>