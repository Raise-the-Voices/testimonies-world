/**
 * Stub for `$app/state`.
 *
 * See `app-paths.ts` for why these stubs exist.
 *
 * `page.params` is what a route component reads to know which record
 * it is showing (the edit form reads `page.params.id`). A test sets
 * the params it needs before rendering.
 */
export const page = {
	params: {} as Record<string, string>,
	url: new URL('http://localhost/'),
	route: { id: null as string | null },
	status: 200,
	error: null,
	data: {} as Record<string, unknown>,
	form: null
};

export const navigating = {
	from: null,
	to: null,
	type: null,
	willUnload: false,
	delta: null,
	complete: Promise.resolve()
};

export const updated = {
	current: false,
	check: async () => false
};
