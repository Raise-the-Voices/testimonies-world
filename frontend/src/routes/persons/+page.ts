// Universal load for the /persons catalog. Reads URL searchParams to
// drive the initial fetch so deep-linked filters (e.g. /persons?country=USA)
// render with results on first paint instead of a skeleton. The page
// component still owns filter UI state and uses getPersons() for
// subsequent client-side refetches when the user changes filters.
import { base } from '$app/paths';
import type { Paginated, Person, PersonCategory } from '$lib/types';

export async function load({ url, fetch }) {
    const searchParams = url.searchParams;
    const params: Record<string, string> = {};
    // Mirror the filter keys consumed by persons/+page.svelte so the
    // server-side fetch matches what the client would request.
    for (const key of ['search', 'country', 'current_status', 'category', 'ordering', 'page']) {
        const value = searchParams.get(key);
        if (value) params[key] = value;
    }

    try {
        const qs = new URLSearchParams(params).toString();
        const [personsRes, countriesRes, categoriesRes] = await Promise.all([
            fetch(`${base}/api/persons/${qs ? '?' + qs : ''}`),
            // Countries dropdown mirrors the same filters minus `country`
            // so the dropdown shows every country with the matching
            // per-country counts (see persons/+page.svelte's
            // currentCountryParams()).
            fetch(
                `${base}/api/persons/countries/${buildCountriesQs(params)}`,
            ),
            fetch(`${base}/api/categories/`),
        ]);

        const persons = personsRes.ok
            ? ((await personsRes.json()) as Paginated<Person>)
            : ({ results: [], count: 0, next: null, previous: null } as unknown as Paginated<Person>);
        const countries = countriesRes.ok
            ? ((await countriesRes.json()) as Array<{ country: string; count: number }>)
            : [];
        const categories = categoriesRes.ok
            ? ((await categoriesRes.json()) as Paginated<PersonCategory> | PersonCategory[])
            : [];

        return {
            persons: persons.results ?? [],
            personsCount: persons.count ?? 0,
            countries,
            categories: Array.isArray(categories) ? categories : categories.results ?? [],
            error: personsRes.ok ? null : `HTTP ${personsRes.status}`,
        };
    } catch (e) {
        return {
            persons: [],
            personsCount: 0,
            countries: [],
            categories: [],
            error: e instanceof Error ? e.message : 'Could not load cases.',
        };
    }
}

function buildCountriesQs(params: Record<string, string>): string {
    // Strip `country` (we're aggregating by country — applying it would
    // only return that country) and `page` (irrelevant for the dropdown).
    const clone = { ...params };
    delete clone.country;
    delete clone.page;
    const qs = new URLSearchParams(clone).toString();
    return qs ? '?' + qs : '';
}