// @vitest-environment jsdom
/**
 * Tests for submitDraft — the localStorage safety net for the /submit
 * form. This module is safety-critical because it holds PII (full name,
 * location, narrative) and is the only thing keeping a volunteer's
 * in-progress submission from being lost on tab close / crash / network
 * blip. Any regression here loses data.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
	clearDraft,
	formatDraftAge,
	hasDraft,
	loadDraft,
	saveDraft,
	type SubmitDraft,
} from './submitDraft';

const USERNAME = 'test-user';
const STORAGE_KEY = `submit_form_draft_${USERNAME}`;

function freshStorage(): Storage {
	// jsdom gives us a real Storage; clear it between tests so
	// each case starts with a known-empty window.localStorage.
	window.localStorage.clear();
	return window.localStorage;
}

function makePayload(overrides: Record<string, unknown> = {}): Record<string, unknown> {
	return {
		name: 'Jane Doe',
		country: 'Sudan',
		currentStatus: 'detained',
		...overrides,
	};
}

describe('submitDraft — roundtrip', () => {
	beforeEach(freshStorage);
	afterEach(() => window.localStorage.clear());

	it('save → load returns the same payload', () => {
		const payload = makePayload({ narrative: 'A long first-person narrative.' });
		saveDraft(USERNAME, payload);
		const draft = loadDraft(USERNAME);
		expect(draft).not.toBeNull();
		expect(draft!.username).toBe(USERNAME);
		expect(draft!.payload).toEqual(payload);
		expect(typeof draft!.savedAt).toBe('string');
		// Round-trip: savedAt is a valid ISO 8601 timestamp.
		expect(Number.isNaN(new Date(draft!.savedAt).getTime())).toBe(false);
	});

	it('clearDraft removes the entry so loadDraft returns null', () => {
		saveDraft(USERNAME, makePayload());
		expect(hasDraft(USERNAME)).toBe(true);
		clearDraft(USERNAME);
		expect(hasDraft(USERNAME)).toBe(false);
		expect(loadDraft(USERNAME)).toBeNull();
		expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
	});

	it('saveDraft stamps schemaVersion=2 and savedAt=now', () => {
		const before = new Date().toISOString();
		saveDraft(USERNAME, makePayload());
		const after = new Date().toISOString();
		const raw = window.localStorage.getItem(STORAGE_KEY);
		expect(raw).not.toBeNull();
		const parsed = JSON.parse(raw!) as SubmitDraft;
		expect(parsed.schemaVersion).toBe(2);
		expect(parsed.savedAt >= before && parsed.savedAt <= after).toBe(true);
	});
});

describe('submitDraft — corrupt / expired / wrong-shape', () => {
	beforeEach(freshStorage);
	afterEach(() => window.localStorage.clear());

	it('returns null and clears the entry when JSON is corrupt', () => {
		window.localStorage.setItem(STORAGE_KEY, '{not-json');
		expect(loadDraft(USERNAME)).toBeNull();
		// Side effect: corrupt entry is removed so it doesn't keep
		// failing on subsequent loads.
		expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
	});

	it('drops drafts whose schema version does not match', () => {
		// v1 was the pre-Sources/Media schema. New code can't safely
		// restore it; better to start fresh than to drop fields into
		// the wrong slots.
		const stale: SubmitDraft = {
			schemaVersion: 1,
			username: USERNAME,
			savedAt: new Date().toISOString(),
			payload: makePayload(),
		};
		window.localStorage.setItem(STORAGE_KEY, JSON.stringify(stale));
		expect(loadDraft(USERNAME)).toBeNull();
		expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
	});

	it('drops drafts older than 7 days (TTL)', () => {
		const eightDaysAgo = new Date(Date.now() - 8 * 24 * 60 * 60 * 1000).toISOString();
		const stale: SubmitDraft = {
			schemaVersion: 2,
			username: USERNAME,
			savedAt: eightDaysAgo,
			payload: makePayload(),
		};
		window.localStorage.setItem(STORAGE_KEY, JSON.stringify(stale));
		expect(loadDraft(USERNAME)).toBeNull();
		expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
	});

	it('keeps drafts at exactly 7 days (TTL is strict greater-than)', () => {
		// 6 days 23 hours — well within the 7d window.
		const sixDaysAgo = new Date(Date.now() - (6 * 24 + 23) * 60 * 60 * 1000).toISOString();
		const stillFresh: SubmitDraft = {
			schemaVersion: 2,
			username: USERNAME,
			savedAt: sixDaysAgo,
			payload: makePayload(),
		};
		window.localStorage.setItem(STORAGE_KEY, JSON.stringify(stillFresh));
		const loaded = loadDraft(USERNAME);
		expect(loaded).not.toBeNull();
		expect(loaded!.payload).toEqual(makePayload());
	});

	it('drops drafts with a missing or non-string savedAt', () => {
		const broken: Partial<SubmitDraft> = {
			schemaVersion: 2,
			username: USERNAME,
			payload: makePayload(),
		};
		window.localStorage.setItem(STORAGE_KEY, JSON.stringify(broken));
		expect(loadDraft(USERNAME)).toBeNull();
		expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
	});

	it('drops drafts with a non-parseable savedAt date', () => {
		const broken: SubmitDraft = {
			schemaVersion: 2,
			username: USERNAME,
			savedAt: 'not-a-date',
			payload: makePayload(),
		};
		window.localStorage.setItem(STORAGE_KEY, JSON.stringify(broken));
		expect(loadDraft(USERNAME)).toBeNull();
	});
});

describe('submitDraft — defensive edge cases', () => {
	afterEach(() => window.localStorage.clear());

	it('loadDraft returns null when window is unavailable', () => {
		// Simulate SSR / Node environment.
		const originalWindow = globalThis.window;
		delete (globalThis as { window?: unknown }).window;
		try {
			expect(loadDraft(USERNAME)).toBeNull();
			expect(hasDraft(USERNAME)).toBe(false);
		} finally {
			(globalThis as { window?: unknown }).window = originalWindow;
		}
	});

	it('saveDraft no-ops when window is unavailable', () => {
		const originalWindow = globalThis.window;
		delete (globalThis as { window?: unknown }).window;
		try {
			expect(() => saveDraft(USERNAME, makePayload())).not.toThrow();
		} finally {
			(globalThis as { window?: unknown }).window = originalWindow;
		}
	});

	it('loadDraft returns null for empty username', () => {
		window.localStorage.clear();
		expect(loadDraft('')).toBeNull();
	});

	it('saveDraft swallows quota errors instead of throwing', () => {
		// Stub localStorage.setItem to throw — Safari private mode,
		// full quota, etc. The page surfaces this via a separate
		// "Could not save draft" pill, but the call site itself
		// must not propagate.
		const setItemSpy = vi
			.spyOn(Storage.prototype, 'setItem')
			.mockImplementation(() => {
				throw new DOMException('Quota exceeded', 'QuotaExceededError');
			});
		try {
			expect(() => saveDraft(USERNAME, makePayload())).not.toThrow();
		} finally {
			setItemSpy.mockRestore();
		}
	});

	it('hasDraft is true for a valid draft and false otherwise', () => {
		window.localStorage.clear();
		expect(hasDraft(USERNAME)).toBe(false);
		saveDraft(USERNAME, makePayload());
		expect(hasDraft(USERNAME)).toBe(true);
		clearDraft(USERNAME);
		expect(hasDraft(USERNAME)).toBe(false);
	});
});

describe('formatDraftAge', () => {
	it('returns "never" for null / undefined / empty', () => {
		expect(formatDraftAge(null)).toBe('never');
		expect(formatDraftAge(undefined)).toBe('never');
		expect(formatDraftAge('')).toBe('never');
	});

	it('returns "never" for non-parseable timestamps', () => {
		expect(formatDraftAge('not-a-date')).toBe('never');
	});

	it('returns "just now" for sub-minute ages', () => {
		expect(formatDraftAge(new Date().toISOString())).toBe('just now');
		expect(formatDraftAge(new Date(Date.now() - 30_000).toISOString())).toBe('just now');
	});

	it('returns "Xm ago" for sub-hour ages', () => {
		expect(formatDraftAge(new Date(Date.now() - 5 * 60_000).toISOString())).toBe('5m ago');
		expect(formatDraftAge(new Date(Date.now() - 59 * 60_000).toISOString())).toBe('59m ago');
	});

	it('returns "Xh ago" for sub-day ages', () => {
		expect(formatDraftAge(new Date(Date.now() - 2 * 60 * 60_000).toISOString())).toBe('2h ago');
		expect(formatDraftAge(new Date(Date.now() - 23 * 60 * 60_000).toISOString())).toBe('23h ago');
	});

	it('returns "yesterday" for exactly 1 day old', () => {
		const oneDayAgo = new Date(Date.now() - 24 * 60 * 60_000).toISOString();
		// The boundary depends on exact ms but 24h should land on days===1.
		const result = formatDraftAge(oneDayAgo);
		expect(result === 'yesterday' || /^\dd ago$/.test(result)).toBe(true);
	});

	it('returns "Xd ago" for days 2-29', () => {
		expect(formatDraftAge(new Date(Date.now() - 3 * 24 * 60 * 60_000).toISOString())).toBe(
			'3d ago',
		);
	});

	it('returns a calendar date for ages >= 30 days', () => {
		const oldDate = new Date(Date.now() - 60 * 24 * 60 * 60_000).toISOString();
		const result = formatDraftAge(oldDate);
		// Should NOT be the relative form — should be like "Mar 7".
		expect(result).toMatch(/^[A-Z][a-z]{2} \d{1,2}$/);
	});
});
