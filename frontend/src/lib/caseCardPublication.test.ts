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

/** A case file cleared for publication. */
const CLEARED = {
	is_published: true,
	consent_public_publication: 'yes',
	public_identity_level: 'full',
	photograph_public: 'yes',
};

describe('publicationBlocker', () => {
	it('has no blocker when the case file says it is cleared', () => {
		expect(publicationBlocker(CLEARED)).toBeNull();
	});

	it('reports the unpublished case first', () => {
		expect(publicationBlocker({ ...CLEARED, is_published: false })).toBe(
			'the case is not published',
		);
	});

	it('reports the missing consent', () => {
		expect(publicationBlocker({ ...CLEARED, consent_public_publication: '' })).toBe(
			'consent fields not set',
		);
		expect(publicationBlocker({ ...CLEARED, consent_public_publication: 'pending' })).toBe(
			'consent fields not set',
		);
		expect(publicationBlocker({ ...CLEARED, consent_public_publication: 'no' })).toBe(
			'consent fields not set',
		);
	});

	it('reports an identity that is not published at full or partial level', () => {
		expect(publicationBlocker({ ...CLEARED, public_identity_level: 'anonymous' })).toBe(
			'the identity is not cleared for publication',
		);
		// Blank is the most restrictive option, so it is not published.
		expect(publicationBlocker({ ...CLEARED, public_identity_level: '' })).toBe(
			'the identity is not cleared for publication',
		);
	});

	it('publishes a partial identity', () => {
		expect(
			publicationBlocker({ ...CLEARED, public_identity_level: 'partial' }),
		).toBeNull();
	});

	it('reports a photograph that is not cleared', () => {
		expect(publicationBlocker({ ...CLEARED, photograph_public: '' })).toBe(
			'the photograph is not cleared for publication',
		);
	});

	it('reports the first unmet condition, in the server’s order', () => {
		// Every flag is wrong here. The consent comes first, so it is
		// what the advocate is told to go and set.
		expect(
			publicationBlocker({
				is_published: false,
				consent_public_publication: '',
				public_identity_level: 'anonymous',
				photograph_public: 'no',
			}),
		).toBe('the case is not published');
	});

	it('treats missing fields as unanswered, not as consent', () => {
		expect(publicationBlocker({})).toBe('consent fields not set');
	});
});
