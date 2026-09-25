import { base } from '$app/paths';
import type {
	CaseworkRecord,
	Contact,
	DashboardData,
	FamilyRelationshipRow,
	Media,
	Paginated,
	Person,
	PersonCategory,
	Report,
	Statistics,
	User,
} from './types';

export type {
	CaseworkRecord,
	Contact,
	DashboardData,
	FamilyRelationshipRow,
	Person,
	PersonCategory,
	Report,
	User,
	Paginated,
} from './types';

const API_BASE = `${base}/api`;

/**
 * Default per-request timeout. Prevents a hung server from hanging
 * the UI indefinitely — every form's 4-way catch maps `status: 0` to
 * a friendly network / server error message, so a timeout shows up
 * to the user as "The server took too long to respond…" rather than
 * a frozen spinner.
 *
 * 30s is generous enough for slow connections / large payloads
 * (media uploads typically complete in 5-15s; we expect <5s for JSON
 * CRUD). Long-running uploads can override per-call via
 * `request(path, { timeoutMs: 0 })` to disable.
 */
const DEFAULT_REQUEST_TIMEOUT_MS = 30_000;

// Error parsing is pure and SvelteKit-free — it lives in `api/errors.ts`
// so vitest can import it in node mode and the orval `fetcher()` in
// `api/mutator.ts` can share it. Re-exported here for callers that
// import `ApiError` from `$lib/api` directly (every existing call site
// does — don't break that).
export {
	ApiError,
	STATUS_FALLBACK,
	parseApiErrorBody,
	readErrorBody,
	collectMessages,
	extractFieldErrors,
	type FieldErrors,
} from './api/errors';

import {
	ApiError,
	parseApiErrorBody,
	readErrorBody,
	type FieldErrors,
} from './api/errors';

/**
 * Read Django's `csrftoken` cookie. Django sets it on the first safe
 * request (e.g. /api/session/) and expects it back as `X-CSRFToken`
 * on POST / PUT / PATCH / DELETE when using SessionAuthentication.
 *
 * Without this, every state-changing request fails Django's CSRF
 * check and returns 403 — even for fully-authenticated users.
 */
function getCsrfToken(): string {
	if (typeof document === 'undefined') return '';
	const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
	return match ? decodeURIComponent(match[1]) : '';
}

export async function request<T>(
	path: string,
	options: RequestInit & {
		fetch?: typeof globalThis.fetch;
		/**
		 * Hard timeout in milliseconds. If the server doesn't respond
		 * within this window the request is aborted and an `ApiError`
		 * with `status: 0`, `statusText: 'timeout'` is thrown — caught
		 * by the existing 4-way switch in every form as a network /
		 * server failure.
		 *
		 * Default: `DEFAULT_REQUEST_TIMEOUT_MS` (30s). Pass `0` to
		 * disable the timeout for long-running uploads.
		 */
		timeoutMs?: number;
	} = {},
): Promise<T> {
	const url = `${API_BASE}${path}`;

	const method = (options.method ?? 'GET').toUpperCase();
	const stateChanging = method === 'POST' || method === 'PUT' || method === 'PATCH' || method === 'DELETE';

// For FormData uploads we MUST NOT set Content-Type ourselves — the
	// browser needs to add the multipart boundary header itself, and a
	// caller-supplied Content-Type without a boundary would silently
	// drop the file on the floor. Detect FormData and skip the default.
	const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;

	const headers: Record<string, string> = isFormData
		? { ...(options.headers as Record<string, string> | undefined) }
		: {
				'Content-Type': 'application/json',
				...(options.headers as Record<string, string> | undefined),
			};
	if (stateChanging) {
		const csrf = getCsrfToken();
		if (csrf) headers['X-CSRFToken'] = csrf;
	}

	// SvelteKit's load functions pass a wrapped `fetch` that forwards
	// cookies during SSR — the global fetch does NOT. Use the injected
	// fetch when present (root +layout.ts is the only caller today);
	// fall back to the global fetch for client-side calls where
	// `credentials: 'include'` already handles cookies.
	const doFetch = options.fetch ?? globalThis.fetch.bind(globalThis);

	// Timeout: race the fetch against a setTimeout. Aborting causes
	// doFetch to reject with an AbortError, which we re-throw as a
	// timeout ApiError below. `timeoutMs === 0` disables (used for
	// long-running uploads where 30s isn't enough).
	const timeoutMs = options.timeoutMs ?? DEFAULT_REQUEST_TIMEOUT_MS;
	const timeoutController =
		timeoutMs > 0 ? new AbortController() : null;
	const timeoutId = timeoutController
		? setTimeout(() => timeoutController.abort(), timeoutMs)
		: null;

	let res: Response;
	try {
		res = await doFetch(url, {
			credentials: 'include',
			headers,
			...options,
			signal: timeoutController?.signal,
		});
	} catch (e) {
		if (timeoutId) clearTimeout(timeoutId);
		// Timeout aborts land here as DOMException('AbortError').
		// Distinguish from a caller-supplied AbortSignal: if the
		// timeout fired, surface as a friendly timeout message;
		// otherwise (e.g. unmount-time abort) re-throw a generic
		// network error.
		const isTimeout =
			timeoutController !== null &&
			timeoutController.signal.aborted &&
			e instanceof DOMException &&
			e.name === 'AbortError';
		if (isTimeout) {
			throw new ApiError(
				`The server took too long to respond (over ${Math.round(timeoutMs / 1000)}s). Please try again.`,
				0,
				'timeout',
				{},
				null,
				[],
				'',
			);
		}
		// Network / CORS / offline
		throw new ApiError(
			"Couldn't reach the server — check your connection and try again.",
			0,
			'network',
			{},
			null,
			[],
			'',
		);
	}
	if (timeoutId) clearTimeout(timeoutId);

	if (res.ok) {
		// DELETE responses are usually 204 No Content (empty body). Calling
		// res.json() on an empty string throws "Unexpected end of JSON input"
		// and the caller sees a fake ApiError even though the server processed
		// the request. Read as text first; only parse if there's a body.
		const text = await res.text();
		return (text ? JSON.parse(text) : undefined) as T;
	}

	const { body, contentType } = await readErrorBody(res);
	const { message, fieldErrors, messages } = parseApiErrorBody(body, res.status, res.statusText);
	throw new ApiError(
		message,
		res.status,
		res.statusText,
		fieldErrors,
		body,
		messages,
		contentType,
	);
}

export async function getSession(
	injectedFetch?: typeof globalThis.fetch,
): Promise<User> {
	return request<User>('/session/', { fetch: injectedFetch });
}

export async function getPersons(
	params: Record<string, string> = {},
	opts: { signal?: AbortSignal } = {},
): Promise<Paginated<Person>> {
	const qs = new URLSearchParams(params).toString();
	return request<Paginated<Person>>(`/persons/${qs ? '?' + qs : ''}`, { signal: opts.signal });
}

export async function getPerson(
	id: number | string,
	opts: { signal?: AbortSignal } = {},
): Promise<Person> {
	// Parsed through Zod schema: dates become `Date` (not ISO strings),
	// nullables are validated, drift in the wire shape is caught by
	// `WireFormatError` at this boundary. See `src/lib/schemas/overlays.ts`.
	const raw = await request<unknown>(`/persons/${id}/`, { signal: opts.signal });
	const { PersonDetailSchema } = await import('./schemas/overlays');
	const parsed = PersonDetailSchema.safeParse(raw);
	if (!parsed.success) {
		const { WireFormatError } = await import('./api/parser');
		throw new WireFormatError(`/persons/${id}/`, parsed.error);
	}
	return parsed.data as unknown as Person;
}

export async function getWatchdog(): Promise<Person[]> {
	return request<Person[]>('/persons/watchdog/');
}

/**
 * `injectedFetch` mirrors the `getDashboard()` pattern: SvelteKit's
 * universal load functions pass a wrapped `fetch` that forwards cookies
 * during SSR. The global fetch does NOT. Pass it explicitly from
 * `+page.ts` so the SSR call to `/persons/statistics/` is authenticated
 * when the user has a session cookie set.
 */
export async function getStatistics(
	injectedFetch?: typeof globalThis.fetch,
): Promise<Statistics> {
	return request<Statistics>('/persons/statistics/', { fetch: injectedFetch });
}

/**
 * Dashboard aggregator — the SvelteKit /dashboard page consumes this
 * as a single cohesive payload (no parallel fetches, no client-side
 * composition). The backend scopes the response by role (see
 * backend/cases/dashboard.py for the scoping rules).
 *
 * Accepts an optional `injectedFetch` so the SvelteKit universal load
 * can pass its wrapped `fetch` — the global fetch does NOT forward
 * cookies during SSR, so without this, /dashboard SSR fails on hard
 * refresh with an anonymous call to a 401-protected endpoint.
 */
export async function getDashboard(
	injectedFetch?: typeof globalThis.fetch,
): Promise<DashboardData> {
	return request<DashboardData>('/dashboard/', { fetch: injectedFetch });
}

export async function getCountries(
	params: Record<string, string> = {},
): Promise<Array<{ country: string; count: number }>> {
	const qs = new URLSearchParams(params).toString();
	return request<Array<{ country: string; count: number }>>(
		`/persons/countries/${qs ? '?' + qs : ''}`,
	);
}

export async function getCategories(): Promise<Paginated<PersonCategory> | PersonCategory[]> {
	return request<Paginated<PersonCategory> | PersonCategory[]>('/categories/');
}

export async function createPerson(data: Record<string, unknown> | FormData): Promise<Person> {
	return request<Person>('/persons/', {
		method: 'POST',
		body: data instanceof FormData ? data : JSON.stringify(data),
	});
}

export async function updatePerson(
	id: number | string,
	data: Record<string, unknown> | FormData,
): Promise<Person> {
	return request<Person>(`/persons/${id}/`, {
		method: 'PATCH',
		body: data instanceof FormData ? data : JSON.stringify(data),
	});
}

export async function deletePerson(id: number | string): Promise<void> {
	await request<null>(`/persons/${id}/`, {
		method: 'DELETE',
	});
}

/* --- Family Relationships ------------------------------------------------
   The CRUD UI on the person-detail page reads/writes through
   `/api/relationships/`. The endpoint accepts `?person=X` to filter by
   either side (see FamilyRelationshipFilter in cases/views.py), and
   returns rows with `person_a_name` / `person_b_name` already denormalised.
*/

export async function getRelationships(
	params: { person?: string } = {},
	opts: { signal?: AbortSignal } = {},
): Promise<Paginated<FamilyRelationshipRow> | FamilyRelationshipRow[]> {
	const qs = new URLSearchParams(params).toString();
	return request<Paginated<FamilyRelationshipRow> | FamilyRelationshipRow[]>(
		`/relationships/${qs ? '?' + qs : ''}`,
		{ signal: opts.signal },
	);
}

export async function createRelationship(
	data: Partial<FamilyRelationshipRow>,
): Promise<FamilyRelationshipRow> {
	return request<FamilyRelationshipRow>('/relationships/', {
		method: 'POST',
		body: JSON.stringify(data),
	});
}

export async function updateRelationship(
	id: number,
	data: Partial<FamilyRelationshipRow>,
): Promise<FamilyRelationshipRow> {
	return request<FamilyRelationshipRow>(`/relationships/${id}/`, {
		method: 'PATCH',
		body: JSON.stringify(data),
	});
}

export async function deleteRelationship(id: number): Promise<void> {
	await request<null>(`/relationships/${id}/`, {
		method: 'DELETE',
	});
}

export async function createReport(data: Record<string, unknown>): Promise<Report> {
	return request<Report>('/reports/', {
		method: 'POST',
		body: JSON.stringify(data),
	});
}

export async function getReports(
	params: Record<string, string> = {},
): Promise<Paginated<Report> | Report[]> {
	const qs = new URLSearchParams(params).toString();
	return request<Paginated<Report> | Report[]>(`/reports/${qs ? '?' + qs : ''}`);
}

export async function getReport(id: number | string): Promise<Report> {
	return request<Report>(`/reports/${id}/`);
}

export async function updateReport(
	id: number | string,
	data: Record<string, unknown>,
): Promise<Report> {
	return request<Report>(`/reports/${id}/`, {
		method: 'PATCH',
		body: JSON.stringify(data),
	});
}

export async function deleteReport(id: number | string): Promise<void> {
	await request<null>(`/reports/${id}/`, {
		method: 'DELETE',
	});
}

export async function getCasework(
	params: Record<string, string> = {},
): Promise<Paginated<CaseworkRecord> | CaseworkRecord[]> {
	const qs = new URLSearchParams(params).toString();
	return request<Paginated<CaseworkRecord> | CaseworkRecord[]>(
		`/casework/${qs ? '?' + qs : ''}`,
	);
}

export async function createCasework(data: Record<string, unknown>): Promise<CaseworkRecord> {
	return request<CaseworkRecord>('/casework/', {
		method: 'POST',
		body: JSON.stringify(data),
	});
}

export async function getCaseworkRecord(id: number | string): Promise<CaseworkRecord> {
	return request<CaseworkRecord>(`/casework/${id}/`);
}

export async function updateCasework(
	id: number | string,
	data: Record<string, unknown>,
): Promise<CaseworkRecord> {
	return request<CaseworkRecord>(`/casework/${id}/`, {
		method: 'PATCH',
		body: JSON.stringify(data),
	});
}

export async function deleteCasework(id: number | string): Promise<void> {
	await request<null>(`/casework/${id}/`, {
		method: 'DELETE',
	});
}

export async function getContacts(
	params: Record<string, string> = {},
): Promise<Paginated<Contact> | Contact[]> {
	const qs = new URLSearchParams(params).toString();
	return request<Paginated<Contact> | Contact[]>(`/contacts/${qs ? '?' + qs : ''}`);
}

export async function getContact(id: number | string): Promise<Contact> {
	return request<Contact>(`/contacts/${id}/`);
}

export async function createContact(data: Partial<Contact>): Promise<Contact> {
	return request<Contact>('/contacts/', {
		method: 'POST',
		body: JSON.stringify(data),
	});
}

export async function updateContact(
	id: number | string,
	data: Partial<Contact>,
): Promise<Contact> {
	return request<Contact>(`/contacts/${id}/`, {
		method: 'PATCH',
		body: JSON.stringify(data),
	});
}

export async function deleteContact(id: number | string): Promise<void> {
	await request<null>(`/contacts/${id}/`, {
		method: 'DELETE',
	});
}

/* --- Media -----------------------------------------------------------------
   File uploads use multipart/form-data so the browser sets the boundary
   correctly — we deliberately do NOT set Content-Type ourselves on these.
   The generic request() helper detects FormData and strips its
   Content-Type so the browser can supply the right multipart boundary.
*/

export async function getMedia(
	params: Record<string, string> = {},
	opts: { signal?: AbortSignal } = {},
): Promise<Paginated<Media> | Media[]> {
	const qs = new URLSearchParams(params).toString();
	return request<Paginated<Media> | Media[]>(`/media/${qs ? '?' + qs : ''}`, { signal: opts.signal });
}

export async function getMediaItem(id: number | string): Promise<Media> {
	return request<Media>(`/media/${id}/`);
}

export async function uploadMedia(formData: FormData): Promise<Media> {
	return request<Media>('/media/', {
		method: 'POST',
		body: formData,
	});
}

export async function updateMedia(id: number | string, formData: FormData): Promise<Media> {
	return request<Media>(`/media/${id}/`, {
		method: 'PATCH',
		body: formData,
	});
}

export async function deleteMedia(id: number | string): Promise<void> {
	await request<null>(`/media/${id}/`, {
		method: 'DELETE',
	});
}
