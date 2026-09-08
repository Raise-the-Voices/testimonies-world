<!--
  AuditLogsFilters — filter bar for /dashboard/audit-logs.

  The parent owns the URL search-params state and passes the current
  values via bind:. The component emits an `oncommit` callback on blur
  / change events (not on every keystroke) so the parent can call
  goto() with merged params — this keeps the URL the source of truth
  and avoids hammering the server while typing.
-->
<script lang="ts">
	interface Props {
		username: string;
		action: string;
		targetType: string;
		timestampAfter: string;
		timestampBefore: string;
		search: string;
		oncommit: () => void;
		onclear: () => void;
	}

	let {
		username = $bindable(''),
		action = $bindable(''),
		targetType = $bindable(''),
		timestampAfter = $bindable(''),
		timestampBefore = $bindable(''),
		search = $bindable(''),
		oncommit,
		onclear,
	}: Props = $props();

	// Action + target_type enums. Must match backend AuditLog.Action
	// and the strings used by _audit() helpers in viewsets — adding
	// a new action on the backend means adding it here too.
	const ACTIONS = ['viewed', 'edited', 'deleted', 'downloaded'] as const;
	// Common target_type values. We don't enumerate exhaustively because
	// the underlying audit_log.target_type is a free-form CharField;
	// any new model that emits audit rows will appear here as a new
	// option, surfaced via the dropdown (the backend filters on
	// exact match, so unknown values still work via the search field).
	const TARGET_TYPES = [
		'person',
		'report',
		'media',
		'casework',
		'contact',
		'relationship',
		'category',
	] as const;
</script>

<div class="filters" aria-label="Audit log filters">
	<div class="filter-grid">
		<label class="field">
			<span class="field-label">User</span>
			<input
				type="text"
				class="input"
				placeholder="username"
				bind:value={username}
				onblur={oncommit}
				onkeydown={(e) => e.key === 'Enter' && oncommit()}
				autocomplete="off"
			/>
		</label>
		<label class="field">
			<span class="field-label">Action</span>
			<select class="select" bind:value={action} onchange={oncommit}>
				<option value="">Any</option>
				{#each ACTIONS as a (a)}
					<option value={a}>{a}</option>
				{/each}
			</select>
		</label>
		<label class="field">
			<span class="field-label">Target type</span>
			<select class="select" bind:value={targetType} onchange={oncommit}>
				<option value="">Any</option>
				{#each TARGET_TYPES as t (t)}
					<option value={t}>{t}</option>
				{/each}
			</select>
		</label>
		<label class="field">
			<span class="field-label">Search</span>
			<input
				type="text"
				class="input"
				placeholder="details, IP, username…"
				bind:value={search}
				onblur={oncommit}
				onkeydown={(e) => e.key === 'Enter' && oncommit()}
				autocomplete="off"
			/>
		</label>
		<label class="field">
			<span class="field-label">From</span>
			<input
				type="datetime-local"
				class="input"
				bind:value={timestampAfter}
				onchange={oncommit}
			/>
		</label>
		<label class="field">
			<span class="field-label">To</span>
			<input
				type="datetime-local"
				class="input"
				bind:value={timestampBefore}
				onchange={oncommit}
			/>
		</label>
	</div>
	{#if username || action || targetType || search || timestampAfter || timestampBefore}
		<div class="filter-actions">
			<button type="button" class="btn btn-secondary" onclick={onclear}>
				Clear filters
			</button>
		</div>
	{/if}
</div>

<style>
	.filters {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}
	.filter-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 0.75rem;
	}
	@media (min-width: 900px) {
		.filter-grid {
			grid-template-columns: repeat(3, minmax(0, 1fr));
		}
	}
	@media (min-width: 1200px) {
		.filter-grid {
			grid-template-columns: repeat(6, minmax(0, 1fr));
		}
	}
	.field {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		min-width: 0;
	}
	.field-label {
		font-size: 0.72rem;
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		color: var(--color-text-muted);
	}
	.input,
	.select {
		font: inherit;
		padding: 0.45rem 0.6rem;
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-input);
		background: var(--color-bg-white);
		color: var(--color-text);
		min-width: 0;
	}
	.input:focus-visible,
	.select:focus-visible {
		outline: none;
		box-shadow: 0 0 0 3px var(--color-primary-tint);
		border-color: var(--color-primary);
	}
	.filter-actions {
		display: flex;
		justify-content: flex-end;
	}
</style>
