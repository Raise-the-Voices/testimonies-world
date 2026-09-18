<!--
  /persons/{id}/report — Per-case "Add Report" page.

  Wraps the shared ReportForm component (same one used by the
  /reports modal). The page's only jobs are:
    - load the Person from the URL (passed into ReportForm via `person` prop)
    - derive edit-mode ?id= (passed into ReportForm via `reportId` prop)
    - after a successful save, redirect to the case page (replaceState
      so Back doesn't return to a stale form)
    - gate access to volunteers+
    - show auth-gate / loading skeleton / form-error states that
      ReportForm can't know about (it expects to be rendered as part
      of a parent that's already authorized)

  All form fields, validation, sources/media repeating, and submit
  logic lives in ReportForm.svelte.
-->
<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { fly } from 'svelte/transition';
	import { onMount, untrack } from 'svelte';
	import { user, isVolunteer } from '$lib/session';
	import { getPerson, ApiError } from '$lib/api';
	import ReportForm from '$lib/ReportForm.svelte';
	import Skeleton from '$lib/Skeleton.svelte';
	import { showToast } from '$lib/toast';
	import type { Report } from '$lib/types';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// SSR-hydrated auth (see +layout.svelte for the full rationale).
	let currentUser = $derived(data.user ?? $user);

	// Person is loaded from the URL param. Refetch-guard token so a
	// slow response for /persons/X can't be clobbered by a faster one
	// for /persons/Y after navigation.
	let person = $state<{ id: number; name: string } | null>(null);
	let loadingPerson = $state(true);
	let personError = $state('');

	let loadToken = 0;
	async function load() {
		const token = ++loadToken;
		loadingPerson = true;
		personError = '';
		try {
			const p = await getPerson(page.params.id!);
			if (token !== loadToken) return;
			person = { id: p.id, name: p.name };
		} catch (e: unknown) {
			if (token !== loadToken) return;
			personError = e instanceof Error ? e.message : "Couldn't load this case.";
		} finally {
			if (token === loadToken) loadingPerson = false;
		}
	}

	$effect(() => {
		void page.params.id;
		void load();
	});

	// `?id=` in the URL → edit mode. Reactive so Back/Forward between
	// ?id=5 and ?id=7 re-hydrates the form with the right report.
	let reportId: number | null = $derived.by(() => {
		const raw = page.url.searchParams.get('id');
		if (!raw) return null;
		const n = Number(raw);
		return Number.isFinite(n) ? n : null;
	});
	let isEdit = $derived(reportId !== null);

	function onSuccess(detail: { report: Report; mediaFailures: string[] }) {
		// Fire the success toast BEFORE the navigation. The toast
		// store lives in module scope (see $lib/toast.ts) so it
		// persists across SvelteKit's goto() and renders on the
		// destination page. The toast carries the full server response
		// so the operator sees the new id + case FK + created_at — the
		// JSON viewer button reveals the full payload for debugging.
		showToast(
			isEdit ? 'Report updated.' : 'Report saved.',
			{
				variant: 'success',
				details: detail.report as unknown as Record<string, unknown>,
			},
		);
		// replaceState so Back from the case page doesn't return to a
		// stale form with the report we just saved. We surface the
		// media-partial-failures via a query param so the destination
		// page can show a banner (the page itself doesn't read query
		// state today, but we leave the option open without forcing a
		// re-render of the form).
		const q = detail.mediaFailures.length > 0 ? '?media_warnings=1' : '';
		void goto(`${base}/persons/${detail.report.person}${q}`, { replaceState: true });
	}
	function onCancel() {
		if (person === null) {
			void goto(`${base}/persons`);
			return;
		}
		void goto(`${base}/persons/${person.id}`);
	}
</script>

<svelte:head>
	<title>{isEdit ? 'Edit Report' : 'Add Report'} — {person?.name ?? 'Testimonies.world'} — Testimonies.world</title>
	<meta name="description" content="{isEdit ? 'Edit a report' : 'Add a new report'} on this case — incident, observation, or update." />
	<meta property="og:description" content="{isEdit ? 'Edit a report' : 'Add a new report'} on this case — incident, observation, or update." />
	<meta property="og:type" content="website" />
	<meta name="twitter:description" content="{isEdit ? 'Edit a report' : 'Add a new report'} on this case — incident, observation, or update." />
</svelte:head>

{#if loadingPerson}
	<div class="report-page-skeleton" aria-label="Loading case">
		<Skeleton variant="rect" width="60%" height="2rem" />
		<Skeleton variant="rect" width="40%" height="1rem" />
		<div class="report-page-skeleton-form">
			<Skeleton variant="rect" width="100%" height="2.5rem" />
			<Skeleton variant="rect" width="100%" height="2.5rem" />
			<Skeleton variant="rect" width="100%" height="8rem" />
		</div>
	</div>
{:else if personError}
	<div class="form-error form-error-server" role="alert" transition:fly={{ y: -8, duration: 200 }}>
		<span class="form-error-icon" aria-hidden="true">!</span>
		<span>{personError}</span>
	</div>
{:else if !isVolunteer(currentUser)}
	<p class="muted">
		You must be logged in as a volunteer to add reports.
		<a href="{base}/api/auth/login/?next={base}/persons/{page.params.id}/report">Login</a>
	</p>
{:else if person}
	<header class="report-page-header">
		<p class="breadcrumb">
			<a href="{base}/persons/{person.id}">{person.name}</a>
			<span class="breadcrumb-sep" aria-hidden="true">›</span>
			<span>{isEdit ? 'Edit report' : 'Add report'}</span>
		</p>
		<h1>{isEdit ? 'Edit report' : 'Add a report'}</h1>
		<p class="muted">
			{isEdit
				? 'Update the report below. Only the author, an advocate, or staff can edit a report.'
				: 'Reports are chronological updates — what happened, when, and where. The more detail, the stronger the case. Required fields are marked with'}
			{#if !isEdit}
				<span class="required-mark" aria-hidden="true">*</span>.
			{/if}
		</p>
	</header>

	<ReportForm
		{person}
		{reportId}
		{onSuccess}
		{onCancel}
	/>
{/if}

<style>
	/* === Page-level chrome (header / breadcrumb / errors) ===
	   The form chrome itself lives in ReportForm.svelte. */
	.report-page-header {
		width: 100%;
		max-width: 880px;
		margin: 0 auto 1.25rem auto;
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}
	.report-page-header h1 {
		margin: 0;
		color: var(--color-primary);
		font-size: 1.85rem;
		font-weight: 700;
		letter-spacing: -0.01em;
	}
	.breadcrumb {
		margin: 0;
		font-size: 0.88rem;
		color: var(--color-text-muted);
	}
	.breadcrumb a {
		color: var(--color-text-muted);
		text-decoration: underline;
		text-decoration-color: var(--color-border-light);
		text-underline-offset: 2px;
	}
	.breadcrumb a:hover { color: var(--color-primary); }
	.breadcrumb-sep {
		margin: 0 0.4rem;
		color: var(--color-text-muted);
	}

	.required-mark { color: var(--color-danger); font-weight: 700; }

	/* Page-level error (Person failed to load — distinct from
	   ReportForm's own per-field errors). */
	.form-error {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem 0.85rem;
		padding: 0.7rem 0.95rem;
		background: #fed7d7;
		color: #c53030;
		border: 1px solid #feb2b2;
		border-radius: var(--radius-card);
		font-size: 0.9rem;
		max-width: 880px;
		margin: 1rem auto;
	}
	.form-error-server { background: #fed7d7; color: #c53030; border-color: #feb2b2; }
	.form-error-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 22px;
		height: 22px;
		border-radius: 50%;
		background: rgba(197, 48, 48, 0.2);
		font-weight: 700;
		font-size: 0.85rem;
	}

	.report-page-skeleton {
		display: flex;
		flex-direction: column;
		gap: 0.8rem;
		width: 100%;
		max-width: 880px;
		margin: 0 auto;
	}
	.report-page-skeleton-form {
		display: flex;
		flex-direction: column;
		gap: 0.8rem;
		margin-top: 1rem;
	}
</style>
