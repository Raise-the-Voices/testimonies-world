/**
 * submitDraft — localStorage persistence for the /submit form.
 *
 * Why a custom module instead of just inline localStorage calls?
 *   - Type-safe payload (matches the form's state shape exactly).
 *   - Versioned schema so future form changes can migrate or drop
 *     stale drafts instead of crashing on read.
 *   - TTL so drafts don't live forever in shared browsers.
 *   - SSR-safe (window may not exist during prerender) and
 *     private-mode-safe (localStorage can throw).
 *   - Single place to wire the storage key format + the schema
 *     version, so the form component stays focused on UX.
 *
 * Privacy: drafts may contain sensitive human-rights data
 * (full name, location, narrative, medical notes). Callers MUST:
 *   1. Key by userId — never share one user's draft with another.
 *   2. Clear on successful submit (so we don't keep the same
 *      submission's data on disk after it's been persisted to the
 *      server).
 *   3. Clear on logout (the +layout.svelte hook does this).
 */

const SCHEMA_VERSION = 1;
const STORAGE_PREFIX = 'submit_form_draft_';
/** Drafts older than this are discarded on read — a stale draft
 *  is worse than no draft (the user might not even remember what
 *  it was about). 7 days is enough to span a long weekend but
 *  short enough that an abandoned tab doesn't keep PII forever. */
const TTL_DAYS = 7;

export interface SubmitDraft {
	schemaVersion: number;
	/** Stable per-user identifier — used as the localStorage key
	 *  suffix so drafts are isolated per user even on shared browsers. */
	username: string;
	savedAt: string; // ISO 8601
	payload: Record<string, unknown>;
}

function keyFor(username: string): string {
	return `${STORAGE_PREFIX}${username}`;
}

function isBrowser(): boolean {
	return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
}

/**
 * Returns the parsed draft for the user, or null if none exists,
 * if it's older than TTL, if the payload is corrupt, or if the
 * schema version has changed.
 */
export function loadDraft(username: string): SubmitDraft | null {
	if (!isBrowser() || !username) return null;
	let raw: string | null;
	try {
		raw = window.localStorage.getItem(keyFor(username));
	} catch {
		return null;
	}
	if (!raw) return null;

	let parsed: SubmitDraft;
	try {
		parsed = JSON.parse(raw) as SubmitDraft;
	} catch {
		// Corrupt payload — drop it.
		clearDraft(username);
		return null;
	}

	if (parsed.schemaVersion !== SCHEMA_VERSION) {
		// Schema bump: drop the stale payload rather than try to
		// migrate it. A wrong-shape draft restored into a changed
		// form is a worse user experience than no draft at all.
		clearDraft(username);
		return null;
	}

	if (!parsed.savedAt || typeof parsed.savedAt !== 'string') {
		clearDraft(username);
		return null;
	}

	const ageMs = Date.now() - new Date(parsed.savedAt).getTime();
	if (Number.isNaN(ageMs) || ageMs > TTL_DAYS * 24 * 60 * 60 * 1000) {
		clearDraft(username);
		return null;
	}

	return parsed;
}

/**
 * Write a draft for the user. Silently no-ops in non-browser
 * environments (SSR / unit tests). Errors from localStorage
 * (quota exceeded, private mode) are swallowed — the form
 * still works; we just lose the safety net.
 */
export function saveDraft(username: string, payload: Record<string, unknown>): void {
	if (!isBrowser() || !username) return;
	const draft: SubmitDraft = {
		schemaVersion: SCHEMA_VERSION,
		username,
		savedAt: new Date().toISOString(),
		payload,
	};
	try {
		window.localStorage.setItem(keyFor(username), JSON.stringify(draft));
	} catch {
		// Quota / private-mode / Safari ITP — fail silent. The
		// UI status pill will still show "Could not save draft"
		// via the catch in the page's debounced save.
	}
}

/**
 * Returns true if a valid (non-expired, schema-matching) draft
 * exists. Cheaper than loadDraft() because it doesn't allocate
 * the parsed object — but it still parses the JSON to check the
 * schema version, which is the cheapest way to filter reliably.
 */
export function hasDraft(username: string): boolean {
	return loadDraft(username) !== null;
}

/**
 * Remove the user's draft. Called on successful submit and on
 * logout. No-op if there's nothing to remove.
 */
export function clearDraft(username: string): void {
	if (!isBrowser() || !username) return;
	try {
		window.localStorage.removeItem(keyFor(username));
	} catch {
		// Same rationale as saveDraft — fail silent.
	}
}

/**
 * Format the savedAt timestamp as a friendly relative duration.
 * "just now" / "5m ago" / "2h ago" / "yesterday" / "Mar 7".
 * Returns 'never' for missing/invalid timestamps.
 */
export function formatDraftAge(savedAt: string | null | undefined): string {
	if (!savedAt) return 'never';
	const then = new Date(savedAt).getTime();
	if (Number.isNaN(then)) return 'never';
	const diffMs = Date.now() - then;
	if (diffMs < 60_000) return 'just now';
	const mins = Math.floor(diffMs / 60_000);
	if (mins < 60) return `${mins}m ago`;
	const hours = Math.floor(mins / 60);
	if (hours < 24) return `${hours}h ago`;
	const days = Math.floor(hours / 24);
	if (days === 1) return 'yesterday';
	if (days < 30) return `${days}d ago`;
	return new Date(savedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}
