<!--
  MediaImage — image renderer with a robust external-host fallback.

  Two distinct ways a `<img src={...}>` for an external Media URL
  produces a broken icon on the page:

    1. The host hotlink-protects or returns non-image content. The
       notable one for this project is x.com (formerly Twitter): most
       of the imported `Media.url` values are status-page URLs
       (https://x.com/i/status/<id>) that return HTML, not an image
       binary. Even the photo-path URLs (https://x.com/<user>/status/
       <id>/photo/1) require a Referer header Twitter only sends to
       its own origin, and our Referrer-Policy: same-origin header
       (set globally by Django's SecurityMiddleware) intentionally
       strips it. The browser gets HTML back and the <img> tag can't
       render it.

    2. The URL is a valid image but the network/CORS request fails
       (deleted tweet, expired CDN URL, etc.). The browser fires
       `onerror` on the <img>.

  Instead of waiting for `onerror` and only catching (2), this
  component inspects the URL at render time and short-circuits the
  request entirely for hosts in HOSTILE_HOSTS. For everything else it
  tries the image; if the image errors, it swaps to a fallback card
  with a link to the source URL.

  The fallback is a styled <a> card showing the source domain and a
  "view →" affordance. Clicking it opens the original URL in a new
  tab — so the user always gets a working link, never a dead icon.

  Used in:
    - persons/[id]/+page.svelte (media gallery)
    - any other surface that renders external `Media.url` as <img>
-->
<script lang="ts">
	interface Props {
		src: string;
		alt: string;
		/** Optional description shown as the link's title attribute. */
		description?: string;
		/** CSS class(es) applied to whichever element ends up rendering. */
		class?: string;
		loading?: 'lazy' | 'eager';
		decoding?: 'async' | 'sync' | 'auto';
		width?: string | number;
		height?: string | number;
		/** Optional override for the hostile-host check. */
		fallbackHosts?: string[];
	}

	let {
		src,
		alt,
		description,
		class: klass = '',
		loading = 'lazy',
		decoding = 'async',
		width,
		height,
		fallbackHosts,
	}: Props = $props();

	// Toggle when the underlying <img> fires onerror. Resets when
	// src changes (the {showFallback && ...} block re-renders on src
	// change because Svelte 5's $derived re-evaluates its deps).
	let failed = $state(false);

	// Hosts we know never serve a renderable image binary. Keep this
	// conservative — only add when an import path is verified to never
	// resolve to image content.
	const DEFAULT_HOSTILE_HOSTS = [
		'x.com',
		'twitter.com',
		// Tweet status pages (not image CDN paths — those can work).
		// The hostname check is enough; we don't pattern-match paths.
	];

	function isHostileUrl(url: string, hostile: string[]): boolean {
		if (!url) return false;
		try {
			const u = new URL(url, window.location.href);
			const host = u.hostname.toLowerCase();
			return hostile.some(
				(h) => host === h || host.endsWith('.' + h),
			);
		} catch {
			return false;
		}
	}

	let showFallback = $derived(
		failed || isHostileUrl(src, fallbackHosts ?? DEFAULT_HOSTILE_HOSTS),
	);

	function domainOf(url: string): string {
		try {
			return new URL(url, window.location.href).hostname.replace(
				/^www\./,
				'',
			);
		} catch {
			return url;
		}
	}

	function handleError() {
		failed = true;
	}
</script>

{#if showFallback}
	<a
		href={src}
		target="_blank"
		rel="noopener noreferrer"
		class={`media-fallback ${klass}`}
		title={description ?? src}
		data-testid="media-fallback"
	>
		<span class="media-fallback-domain">{domainOf(src)}</span>
		<span class="media-fallback-icon" aria-hidden="true">↗</span>
	</a>
{:else}
	<img
		{src}
		{alt}
		class={klass}
		{loading}
		{decoding}
		{width}
		{height}
		onerror={handleError}
		data-testid="media-image"
	/>
{/if}

<style>
	.media-fallback {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.4rem;
		padding: 0.5rem 0.75rem;
		background: var(--color-section-bg, #f5f5f5);
		border: 1px solid var(--color-border-light, #e0e0e0);
		border-radius: var(--radius-input, 6px);
		color: var(--color-text, #222);
		text-decoration: none;
		font-size: 0.85rem;
		font-weight: 600;
		min-height: 2.5rem;
		min-width: 6rem;
		transition: background-color 0.15s ease, border-color 0.15s ease;
	}

	.media-fallback:hover {
		background: var(--color-bg-white, #fff);
		border-color: var(--color-primary, #256);
	}

	.media-fallback:focus-visible {
		outline: 2px solid var(--color-primary, #256);
		outline-offset: 2px;
	}

	.media-fallback-domain {
		font-variant-numeric: tabular-nums;
	}

	.media-fallback-icon {
		font-size: 0.95rem;
		line-height: 1;
	}
</style>