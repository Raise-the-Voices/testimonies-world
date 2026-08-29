import { base } from '$app/paths';
import type {
	CaseworkRecord,
	Contact,
	Paginated,
	Person,
	PersonCategory,
	Report,
	Statistics,
	User,
} from './types';

const API_BASE = `${base}/api`;

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
	const url = `${API_BASE}${path}`;
	const res = await fetch(url, {
		credentials: 'include',
		headers: {
			'Content-Type': 'application/json',
			...options.headers,
		},
		...options,
	});
	if (!res.ok) {
		throw new Error(`API error: ${res.status} ${res.statusText}`);
	}
	return res.json() as Promise<T>;
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

export async function createPerson(data: Record<string, unknown>): Promise<Person> {
	return request<Person>('/persons/', {
		method: 'POST',
		body: JSON.stringify(data),
	});
}

export async function updatePerson(
	id: number | string,
	data: Record<string, unknown>,
): Promise<Person> {
	return request<Person>(`/persons/${id}/`, {
		method: 'PATCH',
		body: JSON.stringify(data),
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

export async function getContacts(
	params: Record<string, string> = {},
): Promise<Paginated<Contact> | Contact[]> {
	const qs = new URLSearchParams(params).toString();
	return request<Paginated<Contact> | Contact[]>(`/contacts/${qs ? '?' + qs : ''}`);
}
