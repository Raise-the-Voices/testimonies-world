import { base } from '$app/paths';
import type {
	CaseworkRecord,
	Contact,
	Media,
	Paginated,
	Person,
	PersonCategory,
	Report,
	Statistics,
	User,
} from './types';

export type { CaseworkRecord, Contact, Person, PersonCategory, Report, User, Paginated } from './types';

const API_BASE = `${base}/api`;

/**
 * Error thrown by `request()` when the API returns a non-2xx response.
 * Carries enough context for callers to map server errors back to fields
 * (DRF sends `{ field: ["msg", ...] }` for 400s) and to write copy
 * tailored to auth failures.
 */
export class ApiError extends Error {
	status: number;
	statusText: string;
	fieldErrors: Record<string, string[]>;
	body: unknown;

	constructor(
		message: string,
		status: number,
		statusText: string,
		fieldErrors: Record<string, string[]> = {},
		body: unknown = null,
	) {
		super(message);
		this.name = 'ApiError';
		this.status = status;
		this.statusText = statusText;
		this.fieldErrors = fieldErrors;
		this.body = body;
	}

	get isUnauthorized(): boolean {
		return this.status === 401 || this.status === 403;
	}
	get isServer(): boolean {
		return this.status >= 500;
	}
	get isValidation(): boolean {
		return this.status === 400 || this.status === 422;
	}
}

/**
 * Pick the first human-readable message from a DRF error body.
 * Falls back to a status-based message if the body isn't shaped like a
 * `{ field: [strings] }` or `{ detail: string }` object.
 */
function flattenDrfError(body: unknown, status: number, statusText: string): {
	message: string;
	fieldErrors: Record<string, string[]>;
} {
	const fieldErrors: Record<string, string[]> = {};
	if (body && typeof body === 'object') {
		const obj = body as Record<string, unknown>;
		for (const [key, value] of Object.entries(obj)) {
			if (Array.isArray(value) && value.every((v) => typeof v === 'string')) {
				fieldErrors[key] = value as string[];
			} else if (typeof value === 'string') {
				fieldErrors[key] = [value];
			}
		}
	}

	if (Object.keys(fieldErrors).length > 0) {
		const firstField = Object.keys(fieldErrors)[0];
		const firstMsg = fieldErrors[firstField][0];
		return { message: `${firstField}: ${firstMsg}`, fieldErrors };
	}
	if (body && typeof body === 'object' && 'detail' in body && typeof (body as any).detail === 'string') {
		return { message: (body as any).detail as string, fieldErrors };
	}

	const fallback: Record<number, string> = {
		400: 'Some fields look off — please review and try again.',
		401: 'You need to log in to do that.',
		403: "You don't have permission to do that.",
		404: "We couldn't find what you were looking for.",
		500: 'The server hit a snag. Please try again in a moment.',
		502: 'The server is temporarily unreachable. Please try again.',
		503: 'The server is temporarily unreachable. Please try again.',
		504: 'The server took too long to respond. Please try again.',
	};
	return {
		message: fallback[status] ?? `Request failed (${status} ${statusText}).`,
		fieldErrors,
	};
}

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

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
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

	let res: Response;
	try {
		res = await fetch(url, {
			credentials: 'include',
			headers,
			...options,
		});
	} catch (e) {
		// Network / CORS / offline
		throw new ApiError(
			"Couldn't reach the server — check your connection and try again.",
			0,
			'network',
			{},
			null,
		);
	}

	if (res.ok) {
		// DELETE responses are usually 204 No Content (empty body). Calling
		// res.json() on an empty string throws "Unexpected end of JSON input"
		// and the caller sees a fake ApiError even though the server processed
		// the request. Read as text first; only parse if there's a body.
		const text = await res.text();
		return (text ? JSON.parse(text) : undefined) as T;
	}

	let body: unknown = null;
	try {
		body = await res.json();
	} catch {
		// body wasn't JSON
	}

	const { message, fieldErrors } = flattenDrfError(body, res.status, res.statusText);
	throw new ApiError(message, res.status, res.statusText, fieldErrors, body);
}

export async function getSession(): Promise<User> {
	return request<User>('/session/');
}

export async function getPersons(
	params: Record<string, string> = {},
): Promise<Paginated<Person>> {
	const qs = new URLSearchParams(params).toString();
	return request<Paginated<Person>>(`/persons/${qs ? '?' + qs : ''}`);
}

export async function getPerson(id: number | string): Promise<Person> {
	return request<Person>(`/persons/${id}/`);
}

export async function getWatchdog(): Promise<Person[]> {
	return request<Person[]>('/persons/watchdog/');
}

export async function getStatistics(): Promise<Statistics> {
	return request<Statistics>('/persons/statistics/');
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

export async function createReport(data: Record<string, unknown>): Promise<Report> {
	return request<Report>('/reports/', {
		method: 'POST',
		body: JSON.stringify(data),
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
): Promise<Paginated<Media> | Media[]> {
	const qs = new URLSearchParams(params).toString();
	return request<Paginated<Media> | Media[]>(`/media/${qs ? '?' + qs : ''}`);
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
