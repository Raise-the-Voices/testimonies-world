/**
 * Case card export — turning the poster into a file.
 *
 * The poster is a DOM node. `html-to-image` clones it into an SVG
 * `foreignObject`, inlines the computed styles, the webfont and the
 * photograph, and hands back a PNG blob. The library is ~20 KB, so
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
 * Capture a node as a PNG blob.
 *
 * `pixelRatio: 2` doubles the poster's 1080px to 2160px — the size a
 * poster needs to stay sharp when a platform re-scales it. The paper
 * tone comes from the token the card is printed on, so the file's
 * background matches the sheet rather than being a white rectangle.
 *
 * The file is a blob, not a data URL, and that is load-bearing. The
 * production CSP is `connect-src 'self'`, and `fetch()` on a `data:`
 * URL is a connect-src request: the browser refuses it, and a poster
 * that renders perfectly still fails to download. The blob comes
 * straight off the canvas and never touches the network.
 */
export async function renderPosterBlob(node: HTMLElement): Promise<Blob> {
	await imagesSettled(node);
	const { toBlob } = await import('html-to-image');
	// Nothing inside the sheet may be moving when it is cloned.
	freezeMotion(node);
	const blob = await toBlob(node, {
		pixelRatio: 2,
		backgroundColor: paperColour(),
		cacheBust: true,
		// The font file and the photograph are fetched to be inlined;
		// cookies come along so a session-gated asset still resolves.
		fetchRequestInit: { credentials: 'include' },
	});
	if (!blob) {
		// `canvas.toBlob` resolves with null when the canvas is tainted
		// or empty. Either way there is no file to hand over.
		throw new Error('The poster could not be rendered.');
	}
	return blob;
}

/**
 * Finish every animation that is running inside the sheet.
 *
 * `html-to-image` inlines the *computed* style of everything it
 * clones, so an animation caught mid-flight ships inside the poster:
 * the same case exported twice can produce two different files. The
 * stylesheet already switches CSS motion off inside the export copy
 * (`.case-card--export`), but a Svelte transition is a Web Animations
 * animation and no CSS rule can stop it.
 *
 * `finish()` is the right verb, not `cancel()`. It resolves the
 * animation, so a Svelte transition ends the way it was meant to and
 * the element is left in its settled state — the state a poster wants.
 * `cancel()` would drop the animation's promise and leave the element
 * wherever the transition had put it.
 *
 * The sweep repeats: a transition in its delay phase is a dummy
 * animation, and finishing that is what starts the real one.
 */
export function freezeMotion(node: HTMLElement): void {
	for (let pass = 0; pass < 3; pass += 1) {
		const running = node.getAnimations({ subtree: true });
		if (running.length === 0) return;
		for (const animation of running) {
			try {
				animation.finish();
			} catch {
				// An animation with no effect left, a zero playback rate
				// or an already-detached node cannot be finished. There
				// is nothing left to freeze.
			}
		}
	}
}

/**
 * Wait for the sheet's images to settle before it is captured.
 *
 * The export copy of the card mounts off-screen and its photograph
 * starts loading at that moment. Capturing before the photograph has
 * arrived ships a poster with an empty frame — the one element a case
 * card cannot be missing.
 *
 * A photograph that fails to load is not waited on forever: the card
 * swaps in its placeholder, and the capture is taken once that swap
 * has been rendered, so the file shows the same thing the screen does.
 */
async function imagesSettled(node: HTMLElement): Promise<void> {
	const images = Array.from(node.querySelectorAll('img'));
	await Promise.all(
		images.map(
			(image) =>
				image.complete
					? Promise.resolve()
					: new Promise<void>((resolve) => {
							const done = () => resolve();
							image.addEventListener('load', done, { once: true });
							image.addEventListener('error', done, { once: true });
						}),
		),
	);
	// Two frames: one for the browser to lay the photograph out, one
	// for the card to swap in its placeholder if it did not arrive.
	await new Promise<void>((resolve) =>
		requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
	);
}

/**
 * Hand the PNG to the browser as a download.
 *
 * An object URL is what `a[download]` expects — a multi-megabyte data
 * URL in an `href` is refused by some browsers. The URL is revoked a
 * moment later; the download has already started by then.
 */
export function downloadPoster(blob: Blob, filename: string): void {
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
