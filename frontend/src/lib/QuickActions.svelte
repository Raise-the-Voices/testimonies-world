<!--
  QuickActions - 2x3 (or smaller, on narrow screens) grid of shortcut
  tiles that jump straight into the right CRUD workflow.

  Each tile is a real <a> so it's keyboard-focusable, middle-clickable,
  and gets the same underline-on-hover treatment as any nav link.

  Role gating: each action declares which role gates it. The page that
  embeds this component is responsible for passing the role-aware list;
  this component is intentionally dumb and just renders what it's given.
-->
<script lang="ts">
	import { base } from '$app/paths';

	interface Action {
		label: string;
		description: string;
		href: string;
	}

	interface Props {
		actions: Action[];
	}

	let { actions }: Props = $props();
</script>

<div class="quick-actions">
	{#each actions as action (action.href)}
		<a class="quick-action" href="{base}{action.href}">
			<span class="qa-text">
				<span class="qa-label">{action.label}</span>
				<span class="qa-desc">{action.description}</span>
			</span>
		</a>
	{/each}
</div>

<style>
	.quick-actions {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 0.75rem;
	}
	@media (min-width: 720px) {
		.quick-actions {
			grid-template-columns: repeat(3, minmax(0, 1fr));
		}
	}
	.quick-action {
		display: block;
		padding: 0.9rem 1rem;
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		background: var(--color-bg-white);
		text-decoration: none;
		color: var(--color-text);
		transition:
			box-shadow var(--transition-card),
			border-color var(--transition-card),
			background var(--transition-card);
	}
	.quick-action:hover {
		box-shadow: var(--shadow-card-hover);
		border-color: var(--color-primary-light);
	}
	.quick-action:focus-visible {
		outline: none;
		box-shadow: 0 0 0 3px var(--color-primary-tint);
	}
	.qa-text {
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
		min-width: 0;
	}
	.qa-label {
		font-weight: 700;
		font-size: 0.95rem;
		color: var(--color-text);
		line-height: 1.3;
	}
	.qa-desc {
		font-size: 0.78rem;
		color: var(--color-text-muted);
		line-height: 1.4;
	}
	@media (prefers-reduced-motion: reduce) {
		.quick-action,
		.quick-action:hover {
			transition: none;
		}
	}
</style>
