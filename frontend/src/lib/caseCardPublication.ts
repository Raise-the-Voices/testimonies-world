/**
 * Case card publication — the gate on exporting a poster.
 *
 * The SERVER decides whether a case may be shared as an image: it
 * computes `exportable` from the consent flags on the case row
 * (`backend/cases/card/serializers.py`) and the browser may not
 * overrule it. This module does not decide anything.
 *
 * What it does is explain. The advocate who clicks "Download poster"
 * and cannot needs to know WHICH part of the case file is stopping
 * them — "not approved" on its own sends them looking for a policy
 * instead of a field. The case file they are already looking at
 * carries the flags, so the reason is read from there, using the same
 * conditions and in the same order the server applies them.
 *
 * The reason is a short phrase, not a sentence: the UI composes it
 * ("Publication not approved — consent fields not set"), and the same
 * phrase is used in tests.
 */

/** The case-file fields the publication gate reads. */
export interface PublicationCase {
	is_published?: boolean;
	consent_public_publication?: string | null;
	public_identity_level?: string | null;
	photograph_public?: string | null;
}

/**
 * The first unmet condition of the publication gate, or null when the
 * case file itself says the case is cleared.
 *
 * The order matches the server's (`backend/cases/card/serializers.py`):
 * the case must be published, consent for public publication must be
 * on file, the identity must be published at full or partial level,
 * and the photograph must be cleared for publication. The first one
 * that fails is the one reported — a case that fails several is still
 * one field away from being exportable, and the first one is the
 * shortest way to it.
 */
export function publicationBlocker(person: PublicationCase): string | null {
	if (person.is_published === false) return 'the case is not published';

	if (trim(person.consent_public_publication) !== 'yes') {
		return 'consent fields not set';
	}

	const identity = trim(person.public_identity_level);
	if (identity !== 'full' && identity !== 'partial') {
		return 'the identity is not cleared for publication';
	}

	if (trim(person.photograph_public) !== 'yes') {
		return 'the photograph is not cleared for publication';
	}

	return null;
}

/**
 * The identity levels the server publishes: the full name, or the
 * first name and an initial. Blank is treated as the most restrictive
 * option, so it is never published.
 */
export const PUBLISHED_IDENTITY_LEVELS = ['full', 'partial'] as const;

/** Trim to a comparable string; anything else becomes ''. */
function trim(value: unknown): string {
	return typeof value === 'string' ? value.trim().toLowerCase() : '';
}
