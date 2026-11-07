/**
 * Case card publication — the gate on exporting a poster.
 *
 * The SERVER decides whether a case may be shared as an image: it
 * computes `exportable` from the case row
 * (`backend/cases/card/serializers.py`) and the browser may not
 * overrule it. This module does not decide anything.
 *
 * The poster publishes what the public case page already publishes, so
 * the gate is narrow: a case that is on the public site can be
 * exported, a case that is not cannot, and an explicit refusal of
 * publication consent blocks it.
 *
 * What this module does is explain. The advocate who clicks "Download
 * poster" and cannot needs to know WHICH part of the case file is
 * stopping them — "not approved" on its own sends them looking for a
 * policy instead of a field. The case file they are already looking at
 * carries the flags, so the reason is read from there, using the same
 * conditions and in the same order the server applies them.
 *
 * The reason is a short phrase, not a sentence: the UI composes it
 * ("Publication not approved — publication consent is declined"), and
 * the same phrase is used in tests.
 */

/** The case-file fields the publication gate reads. */
export interface PublicationCase {
	is_published?: boolean;
	consent_public_publication?: string | null;
}

/**
 * The first unmet condition of the publication gate, or null when the
 * case file itself says the case is cleared.
 *
 * The order matches the server's (`backend/cases/card/serializers.py`):
 * the case must be published, and publication consent must not have
 * been refused.
 *
 * The identity level and the photograph clearance are NOT blockers.
 * They decide what the poster may SHOW, and the server withholds
 * those items and names them in `withheld` — a poster that leaves the
 * photograph out is still a poster.
 */
export function publicationBlocker(person: PublicationCase): string | null {
	if (person.is_published === false) return 'the case is not published';

	if (trim(person.consent_public_publication) === 'no') {
		return 'publication consent is declined';
	}

	return null;
}

/** Trim to a comparable string; anything else becomes ''. */
function trim(value: unknown): string {
	return typeof value === 'string' ? value.trim().toLowerCase() : '';
}
