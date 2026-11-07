import { describe, it, expect } from 'vitest';
import { publicationBlocker } from './caseCardPublication';

/**
 * Tests for the publication-gate explanation.
 *
 * The server decides whether a case may be exported as a poster. This
 * module only says which field is stopping it, so that the advocate
 * looking at the case file is pointed at the field they have to set.
 *
 * The order of the conditions is the server's
 * (`backend/cases/card/serializers.py`), and the first unmet one is
 * the one reported.
 */

/** A case on the public site. */
const PUBLISHED = {
	is_published: true,
	consent_public_publication: 'yes',
};

describe('publicationBlocker', () => {
	it('has no blocker when the case is published', () => {
		expect(publicationBlocker(PUBLISHED)).toBeNull();
	});

	it('reports the unpublished case first', () => {
		expect(publicationBlocker({ ...PUBLISHED, is_published: false })).toBe(
			'the case is not published',
		);
	});

	it('lets a published case through when consent was never filled in', () => {
		// The poster publishes what the public case page publishes, so
		// a blank consent flag is not a refusal.
		expect(publicationBlocker({ ...PUBLISHED, consent_public_publication: '' })).toBeNull();
		expect(publicationBlocker({ ...PUBLISHED, consent_public_publication: 'pending' })).toBeNull();
	});

	it('reports a refused consent', () => {
		expect(publicationBlocker({ ...PUBLISHED, consent_public_publication: 'no' })).toBe(
			'publication consent is declined',
		);
	});

	it('does not block on the identity level or the photograph', () => {
		// Those decide what the poster SHOWS. The server withholds
		// them and names them in `withheld`; they do not stop the
		// download.
		const caseFile = {
			...PUBLISHED,
			public_identity_level: 'anonymous',
			photograph_public: 'no',
		};
		expect(publicationBlocker(caseFile)).toBeNull();
	});

	it('reports the first unmet condition, in the server’s order', () => {
		// Everything is wrong here. The unpublished case comes first,
		// so it is what the advocate is told to go and fix.
		expect(
			publicationBlocker({
				is_published: false,
				consent_public_publication: 'no',
			}),
		).toBe('the case is not published');
	});

	it('treats missing fields as unanswered, not as a refusal', () => {
		expect(publicationBlocker({})).toBeNull();
	});
});
