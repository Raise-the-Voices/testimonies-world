/**
 * Case card export — turning the poster into a file.
 *
 * The poster is a DOM node. `html-to-image` clones it into an SVG
 * `foreignObject`, inlines the computed styles, the webfont and the
 * photograph, and hands back a PNG data URL. The library is ~20 KB, so
 * it is loaded through a dynamic `import()`: it never enters the main
 * bundle and is only fetched when someone actually downloads a poster.
 *
 * Why client-side and not a server-side renderer: the deployment is a
 * SvelteKit app behind nginx and a Django API. Adding a headless
 * browser to the VM to draw one card is disproportionate, and it would
 * mean drawing the poster twice — once in CSS for the screen and once
 * in Python for the file. One component, one layout, one output.
 *
 * The design plan for this lives in `docs/case-info-card-architecture.md`
 * §3.1–§3.7.
 */

/**
 * The name of the downloaded file.
 *
 * The case reference is the only citable identifier a poster has, so it
 * is the file's name: `ED-2026-0042` → `case-ED-2026-0042.png`. A case
 * with no reference yet still downloads, under a neutral name.
 */
export function posterFilename(reference: string | null | undefined): string {
	const slug = (reference ?? '')
		.trim()
		.replace(/[^A-Za-z0-9]+/g, '-')
		.replace(/^-+|-+$/g, '');
	return slug ? `case-${slug}.png` : 'case-card.png';
}

/**
 * Rewrite a media URL onto the page's own origin.
 *
 * The photograph has to be same-origin for the export to work at all:
 * `html-to-image` reads the image's pixels into a canvas, and a canvas
 * that has drawn a cross-origin image without CORS headers is tainted —
 * `toDataURL()` then throws "Tainted canvases may not be exported".
 * The app's CSP (`connect-src 'self'`) blocks the cross-origin fetch
 * before the taint even arrives.
 *
 * The server builds media URLs from `settings.SITE_URL`, which is a
 * different origin from the app in development and behind a proxy in
 * production. The fix is the same in both: keep the path, drop the
 * origin, re-apply the app's base path.
 *
 * Only the app's own public media is rewritten. A photograph hosted
 * somewhere else is left alone — pointing it at the app's host would
 * turn a working image into a 404.
 *
 * @param url       The URL as the API returned it.
 * @param origin    The origin of the page, e.g. `https://cases.raisethevoices.org`.
 * @param basePath  The app's base path, e.g. `/testimonies`.
 */
export function sameOriginMediaUrl(url: string, origin: string, basePath: string): string {
	if (!url) return url;

	let parsed: URL;
	try {
		parsed = new URL(url, origin);
	} catch {
		// Not a URL we can reason about — leave it exactly as it came.
		return url;
	}

	// Already on this origin: nothing to do.
	if (parsed.origin === origin) return url;

	const base = basePath.replace(/\/+$/, '');
	const path = parsed.pathname;
	const hasBase = base !== '' && path.startsWith(`${base}/`);
	const withoutBase = hasBase ? path.slice(base.length) : path;

	if (!withoutBase.startsWith('/public-media/')) return url;

	return `${base}${withoutBase}${parsed.search}`;
}

/**
 * Capture a node as a PNG data URL.
 *
 * `pixelRatio: 2` doubles the poster's 1080px to 2160px — the size a
 * poster needs to stay sharp when a platform re-scales it. The paper
 * tone comes from the token the card is printed on, so the file's
 * background matches the sheet rather than being a white rectangle.
 */
export async function renderPosterPng(node: HTMLElement): Promise<string> {
	const { toPng } = await import('html-to-image');
	return toPng(node, {
		pixelRatio: 2,
		backgroundColor: paperColour(),
		cacheBust: true,
		// The font file and the photograph are fetched to be inlined;
		// cookies come along so a session-gated asset still resolves.
		fetchRequestInit: { credentials: 'include' },
	});
}

/**
 * Hand the PNG to the browser as a download.
 *
 * The data URL is turned into a blob first: a multi-megabyte data URL
 * in an `href` is refused by some browsers, and an object URL is what
 * `a[download]` expects. The URL is revoked a moment later — the
 * download has already started by then.
 */
export async function downloadPoster(dataUrl: string, filename: string): Promise<void> {
	const blob = await (await fetch(dataUrl)).blob();
	const url = URL.createObjectURL(blob);
	const link = document.createElement('a');
	link.href = url;
	link.download = filename;
	link.rel = 'noopener';
	document.body.appendChild(link);
	link.click();
	link.remove();
	setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

/** The paper tone the poster is printed on, read from the token. */
function paperColour(): string {
	if (typeof document === 'undefined') return '#ffffff';
	const value = getComputedStyle(document.documentElement)
		.getPropertyValue('--color-card-paper')
		.trim();
	return value || '#ffffff';
}
