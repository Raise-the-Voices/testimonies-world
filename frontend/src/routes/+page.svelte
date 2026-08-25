<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { getStatistics } from '$lib/api';

	let stats: any = $state(null);

	onMount(async () => {
		try {
			stats = await getStatistics();
		} catch {
			/* empty db is fine */
		}
	});
</script>

<svelte:head>
	<title>Cases — RaisetheVoices.org</title>
</svelte:head>

<div class="home">
	{#if stats && stats.total > 0}
		<!-- 1. Stats counters — unified floating bar -->
		<section class="stats-bar" aria-label="Platform statistics">
			<div class="stat-item">
				<span class="stat-icon" aria-hidden="true">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
						><path d="M20 7h-3a2 2 0 0 1-2-2V2" /><path
							d="M9 18a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v3z"
						/><path d="M14 2H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2z" /><path
							d="M22 18a2 2 0 0 1-2 2h-3a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v3z"
						/></svg
					>
				</span>
				<span class="stat-text">
					<span class="stat-number">{stats.total}</span>
					<span class="stat-label">Cases</span>
				</span>
			</div>

			<div class="stat-item">
				<span class="stat-icon" aria-hidden="true">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
						><circle cx="12" cy="12" r="10" /><line
							x1="2"
							y1="12"
							x2="22"
							y2="12"
						/><path
							d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"
						/></svg
					>
				</span>
				<span class="stat-text">
					<span class="stat-number">{Object.keys(stats.by_country).length}</span>
					<span class="stat-label">Countries</span>
				</span>
			</div>

			<div class="stat-item">
				<span class="stat-icon" aria-hidden="true">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
						><rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path
							d="M7 11V7a5 5 0 0 1 10 0v4"
						/></svg
					>
				</span>
				<span class="stat-text">
					<span class="stat-number">{stats.by_status?.detained || 0}</span>
					<span class="stat-label">Detained</span>
				</span>
			</div>

			<div class="stat-item">
				<span class="stat-icon" aria-hidden="true">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
						><circle cx="12" cy="12" r="10" /><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" /><line
							x1="12"
							y1="17"
							x2="12.01"
							y2="17"
						/></svg
					>
				</span>
				<span class="stat-text">
					<span class="stat-number">{stats.by_status?.disappeared || 0}</span>
					<span class="stat-label">Disappeared</span>
				</span>
			</div>
		</section>
	{/if}

	<!-- 2. Hero card — centered intro + actions -->
	<section class="hero-card">
		<div class="hero-text">
			<p>
				Documenting cases of people facing oppression — enforced disappearances, arbitrary
				detention, restricted rights, statelessness, and other situations where people cannot
				turn to their own government for protection.
			</p>
			<p>
				We anchor reports, track cases, and coordinate advocacy so that no one is forgotten.
				Reports can be entered even in uncertain or incomplete form — the goal is to create a
				record that can grow over time as more information becomes available.
			</p>
			<p>
				Based on the principle that freedom and due process are universal human rights,
				regardless of birthplace, race, religion, gender, or language.
			</p>
		</div>
		<div class="actions">
			<a href="{base}/persons" class="btn btn-primary btn-lg">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					aria-hidden="true"
					><path d="M20 7h-3a2 2 0 0 1-2-2V2" /><path
						d="M9 18a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v3z"
					/><path d="M14 2H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2z" /><path
						d="M22 18a2 2 0 0 1-2 2h-3a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v3z"
					/></svg
				>
				Browse Cases
				<svg
					class="btn-arrow"
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					aria-hidden="true"><line x1="5" y1="12" x2="19" y2="12" /><polyline
						points="12 5 19 12 12 19"
					/></svg
				>
			</a>
			<a href="{base}/statistics" class="btn btn-secondary btn-lg">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					aria-hidden="true"
					><line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line
						x1="6"
						y1="20"
						x2="6"
						y2="14"
					/></svg
				>
				View Statistics
			</a>
		</div>
	</section>

	<!-- 3. How to help — feature card grid -->
	<section class="help-section">
		<header class="section-header">
			<h2 class="section-title">How to help</h2>
			<p class="section-subtitle">
				Four ways to contribute to the record of human rights documentation.
			</p>
		</header>
		<div class="help-grid">
			<div class="help-card">
				<span class="help-icon" aria-hidden="true">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
						><path d="M12 20h9" /><path
							d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"
						/></svg
					>
				</span>
				<h3>Submit a case</h3>
				<p>If you know of someone facing oppression, log in and submit their story.</p>
			</div>

			<div class="help-card">
				<span class="help-icon" aria-hidden="true">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
						><polyline points="23 4 23 10 17 10" /><polyline
							points="1 20 1 14 7 14"
						/><path
							d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"
						/></svg
					>
				</span>
				<h3>Update existing cases</h3>
				<p>Add new reports with updated information as situations evolve.</p>
			</div>

			<div class="help-card">
				<span class="help-icon" aria-hidden="true">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
						><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" /><path
							d="M15.54 8.46a5 5 0 0 1 0 7.07"
						/><path d="M19.07 4.93a10 10 0 0 1 0 14.14" /></svg
					>
				</span>
				<h3>Advocate</h3>
				<p>Contact us to join as a casework volunteer and amplify documented cases.</p>
			</div>

			<div class="help-card">
				<span class="help-icon" aria-hidden="true">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
						><path
							d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"
						/><path d="M18 14h-8" /><path d="M15 18h-5" /><path
							d="M10 6h8v4h-8V6z"
						/></svg
					>
				</span>
				<h3>Journalists and NGOs</h3>
				<p>Data exports available upon request for reporting and analysis.</p>
			</div>
		</div>
	</section>
</div>

<style>
	.home {
		width: 100%;
		max-width: 1100px;
		margin: 0 auto;
		display: flex;
		flex-direction: column;
		gap: 2rem;
	}

	/* === 1. Stats counters — unified floating bar === */
	.stats-bar {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		box-shadow: var(--shadow-card);
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 1rem;
		padding: 1.25rem 1.5rem;
		animation: fadeSlideUp 0.4s ease both;
	}
	.stat-item {
		display: grid;
		grid-template-columns: auto 1fr;
		grid-template-rows: auto auto;
		column-gap: 0.85rem;
		row-gap: 0.15rem;
		align-items: center;
		padding: 0.6rem 0.7rem;
		border-radius: var(--radius-card);
		transition:
			box-shadow var(--transition-card),
			transform var(--transition-card),
			background var(--transition-card);
	}
	.stat-item:hover {
		box-shadow: var(--shadow-card-hover);
		transform: translateY(-2px);
		background: var(--color-bg);
	}
	.stat-icon {
		grid-row: 1 / span 2;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 40px;
		height: 40px;
		border-radius: 50%;
		background: rgba(37, 100, 106, 0.08);
		color: var(--color-primary);
		flex: 0 0 auto;
	}
	.stat-icon :global(svg) {
		width: 20px;
		height: 20px;
	}
	.stat-text {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}
	.stat-number {
		font-size: 1.35rem;
		font-weight: 700;
		color: var(--color-primary);
		line-height: 1.1;
	}
	.stat-label {
		font-size: 0.78rem;
		color: var(--color-text-muted);
		text-transform: uppercase;
		letter-spacing: 0.06rem;
		margin-top: 0.1rem;
	}

	/* === 2. Hero card === */
	.hero-card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		box-shadow: var(--shadow-card);
		padding: 2.25rem 2rem;
		text-align: center;
		animation: fadeSlideUp 0.4s ease both;
		animation-delay: 0.05s;
	}
	.hero-text {
		max-width: 720px;
		margin: 0 auto;
	}
	.hero-text p {
		font-size: 1.05rem;
		line-height: 1.7;
		margin: 0 0 1rem 0;
		color: var(--color-text);
	}
	.hero-text p:last-child {
		margin-bottom: 0;
	}

	.actions {
		display: flex;
		gap: 0.75rem;
		justify-content: center;
		flex-wrap: wrap;
		margin-top: 1.5rem;
	}
	.btn-lg {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.7rem 1.4rem;
		font-size: 0.95rem;
		font-weight: 600;
		border-radius: var(--radius-card);
		min-height: 44px;
		transition:
			background var(--transition-card),
			color var(--transition-card),
			border-color var(--transition-card),
			transform var(--transition-card),
			box-shadow var(--transition-card);
	}
	.btn-lg :global(svg) {
		width: 18px;
		height: 18px;
	}
	.btn-lg:hover {
		transform: translateY(-1px);
		box-shadow: var(--shadow-card-hover);
	}
	.btn-arrow {
		transition: transform var(--transition-card);
	}
	.btn-lg:hover .btn-arrow {
		transform: translateX(3px);
	}

	/* === 3. How to help grid === */
	.section-header {
		text-align: center;
		margin-bottom: 1.25rem;
	}
	.section-title {
		font-size: 1.4rem;
		font-weight: 700;
		margin: 0 0 0.35rem 0;
		color: var(--color-text);
	}
	.section-subtitle {
		color: var(--color-text-muted);
		margin: 0;
		font-size: 0.95rem;
	}
	.help-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 1rem;
	}
	.help-card {
		background: var(--color-bg-white);
		border: 1px solid var(--color-border-light);
		border-radius: var(--radius-card);
		box-shadow: var(--shadow-card);
		padding: 1.5rem;
		transition:
			box-shadow var(--transition-card),
			transform var(--transition-card),
			border-color var(--transition-card);
		animation: fadeSlideUp 0.4s ease both;
	}
	.help-card:hover {
		box-shadow: var(--shadow-card-hover);
		transform: translateY(-3px);
		border-color: var(--color-primary-light);
	}
	.help-card:nth-child(1) {
		animation-delay: 0.1s;
	}
	.help-card:nth-child(2) {
		animation-delay: 0.15s;
	}
	.help-card:nth-child(3) {
		animation-delay: 0.2s;
	}
	.help-card:nth-child(4) {
		animation-delay: 0.25s;
	}
	.help-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 44px;
		height: 44px;
		border-radius: 10px;
		background: rgba(37, 100, 106, 0.08);
		color: var(--color-primary);
		margin-bottom: 0.85rem;
	}
	.help-icon :global(svg) {
		width: 22px;
		height: 22px;
	}
	.help-card h3 {
		font-size: 1.05rem;
		font-weight: 700;
		margin: 0 0 0.5rem 0;
		color: var(--color-text);
	}
	.help-card p {
		font-size: 0.9rem;
		line-height: 1.55;
		color: var(--color-text-muted);
		margin: 0;
	}

	/* Responsive */
	@media (max-width: 900px) {
		.stats-bar {
			grid-template-columns: repeat(2, 1fr);
		}
		.help-grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}
	@media (max-width: 560px) {
		.stats-bar {
			grid-template-columns: 1fr;
		}
		.help-grid {
			grid-template-columns: 1fr;
		}
		.hero-card {
			padding: 1.5rem 1.25rem;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.stats-bar,
		.hero-card,
		.help-card {
			animation: none;
		}
		.stat-item:hover,
		.help-card:hover,
		.btn-lg:hover {
			transform: none;
		}
	}
</style>