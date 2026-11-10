/**
 * Stub for `$app/navigation`.
 *
 * See `app-paths.ts` for why these stubs exist.
 *
 * `goto` records where the app asked to go, so a test can assert the
 * end of a journey ("save the case → land back on the case page")
 * instead of only the request that was sent.
 */
export const navigationCalls: string[] = [];

export async function goto(url: string): Promise<void> {
	navigationCalls.push(url);
}

export async function invalidate(): Promise<void> {}
export async function invalidateAll(): Promise<void> {}
export async function preloadData(): Promise<void> {}
export function beforeNavigate(): void {}
export function afterNavigate(): void {}
export function pushState(): void {}
export function replaceState(): void {}
