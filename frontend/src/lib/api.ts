import { base } from '$app/paths';

const API_BASE = `${base}/api`;

async function request(path: string, options: RequestInit = {}) {
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
	return res.json();
}

export async function getSession() {
	return request('/session/');
}

export async function getPersons(params: Record<string, string> = {}) {
	const qs = new URLSearchParams(params).toString();
	return request(`/persons/${qs ? '?' + qs : ''}`);
}

export async function getPerson(id: number | string) {
	return request(`/persons/${id}/`);
}

export async function getWatchdog() {
	return request('/persons/watchdog/');
}

export async function getStatistics() {
	return request('/persons/statistics/');
}

export async function getCountries() {
	return request('/persons/countries/');
}

export async function getCategories() {
	return request('/categories/');
}

export async function createPerson(data: Record<string, unknown>) {
	return request('/persons/', {
		method: 'POST',
		body: JSON.stringify(data),
	});
}

export async function updatePerson(id: number | string, data: Record<string, unknown>) {
	return request(`/persons/${id}/`, {
		method: 'PATCH',
		body: JSON.stringify(data),
	});
}

export async function createReport(data: Record<string, unknown>) {
	return request('/reports/', {
		method: 'POST',
		body: JSON.stringify(data),
	});
}

export async function getCasework(params: Record<string, string> = {}) {
	const qs = new URLSearchParams(params).toString();
	return request(`/casework/${qs ? '?' + qs : ''}`);
}

export async function createCasework(data: Record<string, unknown>) {
	return request('/casework/', {
		method: 'POST',
		body: JSON.stringify(data),
	});
}

export async function getContacts(params: Record<string, string> = {}) {
	const qs = new URLSearchParams(params).toString();
	return request(`/contacts/${qs ? '?' + qs : ''}`);
}
