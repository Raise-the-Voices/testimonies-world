/**
 * Unit tests for the M15 error-parsing layer in `$lib/api`.
 *
 * These cover the cases that are easy to regress when the parser
 * grows: text-only bodies (Django HttpResponse), the DRF detail
 * envelope, per-field maps, the message/error/non_field_errors
 * conventions, nested serializer errors, and the headline-priority
 * ordering. Anything not covered here either lives in the integration
 * tests (form-audit, testimonial-workflow) or is exercised by every
 * page through `handleApiError`.
 *
 * The parser is pure — no network, no Svelte — so vitest in node
 * mode is enough.
 */
import { describe, expect, it } from 'vitest';
import { ApiError, parseApiErrorBody } from './api/errors';

describe('parseApiErrorBody', () => {
	it('uses the status fallback when the body is empty', () => {
		const out = parseApiErrorBody(null, 503, 'Service Unavailable');
		expect(out.message).toBe('The server is temporarily unreachable. Please try again.');
		expect(out.fieldErrors).toEqual({});
		expect(out.messages).toEqual([]);
	});

	it('falls back to a generic "Request failed" when the status has no fallback', () => {
		const out = parseApiErrorBody(null, 418, "I'm a teapot");
		expect(out.message).toBe('Request failed (418 I\'m a teapot).');
	});

	it('reads the DRF detail envelope', () => {
		const out = parseApiErrorBody({ detail: 'Not authenticated.' }, 401, 'Unauthorized');
		expect(out.message).toBe('Not authenticated.');
		expect(out.messages).toEqual(['Not authenticated.']);
		expect(out.fieldErrors).toEqual({ detail: ['Not authenticated.'] });
	});

	it('reads the message envelope', () => {
		const out = parseApiErrorBody({ message: 'Quota exceeded.' }, 429, 'Too Many Requests');
		expect(out.message).toBe('Quota exceeded.');
	});

	it('reads the error envelope', () => {
		const out = parseApiErrorBody({ error: 'Boom.' }, 500, 'Internal Server Error');
		expect(out.message).toBe('Boom.');
	});

	it('treats a plain string body as a single message', () => {
		// Plain Django HttpResponse('Authentication required.', status=401)
		// reaches us as a string body, not JSON.
		const out = parseApiErrorBody('Authentication required.', 401, 'Unauthorized');
		expect(out.message).toBe('Authentication required.');
		expect(out.messages).toEqual(['Authentication required.']);
	});

	it('ignores whitespace-only string bodies', () => {
		const out = parseApiErrorBody('   \n  ', 401, 'Unauthorized');
		expect(out.message).toBe('You need to log in to do that.');
		expect(out.messages).toEqual([]);
	});

	it('reads DRF field-error maps and uses the first field as the headline', () => {
		const out = parseApiErrorBody(
			{ name: ['This field is required.'], age: ['Must be a positive integer.'] },
			400,
			'Bad Request',
		);
		expect(out.fieldErrors).toEqual({
			name: ['This field is required.'],
			age: ['Must be a positive integer.'],
		});
		expect(out.message).toBe('name: This field is required.');
		// The headline field still appears first in the flat list.
		expect(out.messages[0]).toBe('This field is required.');
		expect(out.messages).toContain('Must be a positive integer.');
	});

	it('reads non_field_errors before falling back to per-field keys', () => {
		const out = parseApiErrorBody(
			{ non_field_errors: ['Passwords do not match.'], password: ['Too short.'] },
			400,
			'Bad Request',
		);
		expect(out.message).toBe('Passwords do not match.');
	});

	it('flattens nested serializer errors', () => {
		// DRF sometimes nests errors: { address: { city: ["required"] } }.
		const out = parseApiErrorBody(
			{ address: { city: ['This field is required.'] } },
			400,
			'Bad Request',
		);
		expect(out.messages).toContain('This field is required.');
		// Nested objects don't get flattened into fieldErrors — we
		// can't safely invent a dotted key.
		expect(Object.keys(out.fieldErrors)).toHaveLength(0);
	});

	it('handles a top-level array of strings', () => {
		const out = parseApiErrorBody(['First problem.', 'Second problem.'], 400, 'Bad Request');
		expect(out.message).toBe('First problem.');
		expect(out.messages).toEqual(['First problem.', 'Second problem.']);
	});

	it('skips non-string scalars inside objects', () => {
		// Some apps embed an error code alongside the human message.
		const out = parseApiErrorBody(
			{ code: 42, message: 'Forbidden.', retry_after: 60 },
			403,
			'Forbidden',
		);
		expect(out.message).toBe('Forbidden.');
		expect(out.messages).toContain('Forbidden.');
	});

	it('does not infinite-loop on self-referential bodies', () => {
		const a: Record<string, unknown> = { message: 'Loop.' };
		a.self = a;
		const out = parseApiErrorBody(a, 500, 'Internal Server Error');
		expect(out.message).toBe('Loop.');
		expect(out.messages).toContain('Loop.');
	});

	it('does not blow up on null nested values', () => {
		const out = parseApiErrorBody(
			{ detail: null, errors: [null, 'real message'] },
			400,
			'Bad Request',
		);
		expect(out.message).toBe('real message');
	});
});

describe('ApiError', () => {
	it('constructs from message + status + fieldErrors (M0 back-compat)', () => {
		const e = new ApiError('Name is required.', 400, 'Bad Request', { name: ['required'] }, { name: ['required'] });
		expect(e.message).toBe('Name is required.');
		expect(e.status).toBe(400);
		expect(e.fieldErrors).toEqual({ name: ['required'] });
		expect(e.body).toEqual({ name: ['required'] });
		expect(e.name).toBe('ApiError');
	});

	it('flags status getters correctly', () => {
		const u401 = new ApiError('x', 401, 'Unauthorized');
		const u403 = new ApiError('x', 403, 'Forbidden');
		const s500 = new ApiError('x', 500, 'ISE');
		const v422 = new ApiError('x', 422, 'Unprocessable');
		expect(u401.isUnauthorized).toBe(true);
		expect(u403.isUnauthorized).toBe(true);
		expect(s500.isServer).toBe(true);
		expect(v422.isValidation).toBe(true);
		expect(u401.isServer).toBe(false);
	});

	it('exposes a messages array derived from the constructor', () => {
		const e = new ApiError(
			'first',
			400,
			'Bad Request',
			{ name: ['first', 'second'] },
			{ name: ['first', 'second'] },
			['first', 'second'],
			'application/json',
		);
		expect(e.messages).toEqual(['first', 'second']);
		expect(e.contentType).toBe('application/json');
	});

	it('falls back to [message] when no messages are passed (older callers)', () => {
		const e = new ApiError('Only one.', 400, 'Bad Request');
		expect(e.messages).toEqual(['Only one.']);
	});

	it('is throwable as an Error', () => {
		const e = new ApiError('boom', 500, 'ISE');
		expect(() => {
			throw e;
		}).toThrow('boom');
		expect(e instanceof Error).toBe(true);
		expect(e instanceof ApiError).toBe(true);
	});
});
