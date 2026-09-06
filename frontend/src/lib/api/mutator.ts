/**
 * orval mutator — every generated endpoint converges here.
 *
 * Responsibilities:
 *   - Forward credentials (session cookies) on every request.
 *   - Forward CSRF token on state-changing methods.
 *   - Throw `ApiError` on non-2xx responses (the existing error type
 *     from the codebase; see `src/lib/api.ts`).
 *   - Defer raw JSON parsing to the caller — generated code passes a
 *     `Response`, we return the `Response` so orval handles JSON.parse
 *     for the simple cases and Step 3's Zod layer can intercept where
 *     it matters (Date, Decimal, branded types).
 *
 * Step 3 wraps this mutator so that `fetcher<T>` becomes
 * `fetcher<T>(url, schema)` returning `z.infer<T>`. The orval-generated
 * client functions are typed at the boundary by the OpenAPI types;
 * after the Zod parse, runtime values are richer than those types claim.
 */
import type { ApiError } from '../api';

type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' | 'HEAD' | 'OPTIONS';

function csrfToken(): string {
	if (typeof document === 'undefined') return '';
	const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
	return m ? decodeURIComponent(m[1]) : '';
}

export async function fetcher<T>(url: string, options: RequestInit = {}): Promise<T> {
	const method = ((options.method ?? 'GET') as string).toUpperCase() as Method;
	const stateChanging = method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS';

	const headers: Record<string, string> = {
		Accept: 'application/json',
		...((options.headers as Record<string, string> | undefined) ?? {}),
	};
	if (stateChanging) {
		const t = csrfToken();
		if (t) headers['X-CSRFToken'] = t;
		// Only set Content-Type for non-FormData bodies.
		if (
			options.body &&
			typeof FormData === 'undefined' ||
			(!(options.body instanceof FormData) && !('Content-Type' in headers))
		) {
			headers['Content-Type'] = 'application/json';
		}
	}

	let res: Response;
	try {
		res = await fetch(url, {
			credentials: 'include',
			...options,
			headers,
			method,
		});
	} catch (e) {
		throw new Error("Couldn't reach the server. Check your connection.");
	}

	if (!res.ok) {
		let body: unknown = null;
		try {
			body = await res.json();
		} catch {
			/* not JSON */
		}
		const message =
			(body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string')
				? body.detail
				: `Request failed (${res.status} ${res.statusText})`;
		const fieldErrors: Record<string, string[]> = {};
		if (body && typeof body === 'object') {
			for (const [k, v] of Object.entries(body as Record<string, unknown>)) {
				if (Array.isArray(v) && v.every((x) => typeof x === 'string')) {
					fieldErrors[k] = v as string[];
				}
			}
		}
		// Lazy import to avoid circular dep at module load time.
		const mod = await import('../api');
		throw new mod.ApiError(message, res.status, res.statusText, fieldErrors, body);
	}

	// 204 No Content — orval types this as `void` in generated clients.
	if (res.status === 204) {
		return undefined as unknown as T;
	}
	return (await res.json()) as T;
}