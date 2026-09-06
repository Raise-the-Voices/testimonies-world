/**
 * Parse-on-fetch helper.
 *
 * The pattern: every endpoint that crosses the API boundary calls
 * `parseResponse(schema, p)` where `p` is the orval-generated Promise
 * and `schema` is a Zod schema. The result is the parsed, typed value
 * (with `Date`, etc., not raw strings).
 *
 * On parse failure, throws `WireFormatError` with the schema path and
 * the actual issue — loud failure beats silent type drift. The call
 * site should let this propagate to the global error boundary; in
 * TanStack Query land, set `retry: false` for `WireFormatError` so the
 * user sees a clear error instead of three retries.
 */
import type { z } from 'zod';

export class WireFormatError extends Error {
	constructor(
		public endpoint: string,
		public zodError: z.ZodError,
	) {
		super(`Wire format mismatch on ${endpoint}: ${zodError.message}`);
		this.name = 'WireFormatError';
	}
}

export async function parseResponse<T extends z.ZodTypeAny>(
	endpoint: string,
	promise: Promise<unknown>,
	schema: T,
): Promise<z.infer<T>> {
	const raw = await promise;
	const result = schema.safeParse(raw);
	if (!result.success) {
		throw new WireFormatError(endpoint, result.error);
	}
	return result.data as z.infer<T>;
}

/**
 * Wrap an orval endpoint with parse-on-fetch. Use like:
 *
 *   const getPerson = (id: number) =>
 *     withSchema(`/api/persons/${id}`, getPersonRaw({ id }), PersonDetailSchema);
 */
export function withSchema<T extends z.ZodTypeAny>(
	endpoint: string,
	promise: Promise<unknown>,
	schema: T,
): Promise<z.infer<T>> {
	return parseResponse(endpoint, promise, schema);
}