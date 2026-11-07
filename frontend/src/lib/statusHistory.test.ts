// @vitest-environment jsdom
/**
 * The status history, from the wire to the page.
 *
 * The person page renders two things from one array: the timeline (the
 * full feed) and the banner (the headline "what changed?"). Both read
 * `person.status_history`, which arrives through PersonDetailSchema.
 * Zod strips any key the schema doesn't declare — so a field missing
 * from the schema does not warn, it silently empties the feed. These
 * tests pin the whole path: the wire payload, the parse, and what the
 * reader ends up looking at.
 */
import { describe, it, expect, afterEach } from 'vitest';
import { cleanup, render } from '@testing-library/svelte';
import StatusHistoryTimeline from './StatusHistoryTimeline.svelte';
import StatusTransitionBanner from './StatusTransitionBanner.svelte';
import { PersonDetailSchema } from './schemas/overlays';
import type { StatusHistoryEntry } from './types';

/** The wire shape of one person's detail payload, status history included. */
const wirePerson = {
	id: 229,
	name: 'Yawar Habib',
	country: 'Afghanistan',
	created_at: '2026-10-05T16:16:59.657486Z',
	updated_at: '2026-10-05T16:16:59.657486Z',
	created_by: 10,
	categories: [],
	reports: [],
	media_files: [],
	days_since_last_report: null,
	family: [],
	profile_image_url: null,
	status_history: [
		{
			id: 9,
			person: 229,
			report: null,
			event_date: '2026-10-05',
			event_kind: 'status_change',
			description: 'medical_status: unknown → deceased',
			source: 'auto',
			verification: '',
			created_at: '2026-10-05T16:16:59.659456Z',
			created_by: 10,
			created_by_username: 'nazirafghan9251'
		},
		{
			id: 8,
			person: 229,
			report: null,
			event_date: '2026-10-05',
			event_kind: 'status_change',
			description: 'current_status: disappeared → deceased',
			source: 'auto',
			verification: '',
			created_at: '2026-10-05T16:16:59.657486Z',
			created_by: 10,
			created_by_username: 'nazirafghan9251'
		}
	]
};

function parsedEvents(): StatusHistoryEntry[] {
	const parsed = PersonDetailSchema.parse(wirePerson);
	return parsed.status_history as StatusHistoryEntry[];
}

afterEach(cleanup);

describe('the status history reaches the page', () => {
	it('survives the parse', () => {
		const parsed = PersonDetailSchema.parse(wirePerson);

		expect(parsed.status_history).toHaveLength(2);
		expect(parsed.status_history?.[0].description).toBe('medical_status: unknown → deceased');
	});

	it('renders every event, newest first', () => {
		const { container } = render(StatusHistoryTimeline, { props: { events: parsedEvents() } });
		const rows = container.querySelectorAll('li.status-history-row');

		expect(rows).toHaveLength(2);
		// Newest first: the medical_status change was written last.
		expect(rows[0].textContent).toContain('Unknown');
		expect(rows[0].textContent).toContain('Deceased');
		expect(rows[1].textContent).toContain('Disappeared');
		expect(rows[1].textContent).toContain('Deceased');
	});

	it('names the actor and the date on every row', () => {
		const { container } = render(StatusHistoryTimeline, { props: { events: parsedEvents() } });

		expect(container.querySelectorAll('.status-history-actor')[0].textContent).toBe(
			'by nazirafghan9251'
		);
		expect(container.querySelector('time')?.getAttribute('datetime')).toBe('2026-10-05');
	});

	it('never hides a row of case history', () => {
		const { container } = render(StatusHistoryTimeline, { props: { events: parsedEvents() } });
		const rows = container.querySelectorAll('li.status-history-row');

		// The motion hides a row only until it reaches the viewport. A row
		// that is already on screen is shown from the first frame.
		for (const row of rows) {
			expect(row.getAttribute('data-reveal')).toBe('in');
		}
	});

	it('staggers the rows by their position', () => {
		const { container } = render(StatusHistoryTimeline, { props: { events: parsedEvents() } });
		const rows = container.querySelectorAll<HTMLElement>('li.status-history-row');

		expect(rows[0].style.getPropertyValue('--reveal-index')).toBe('0');
		expect(rows[1].style.getPropertyValue('--reveal-index')).toBe('1');
	});

	it('says nothing when there is no history', () => {
		const { container } = render(StatusHistoryTimeline, { props: { events: [] } });

		expect(container.querySelectorAll('li.status-history-row')).toHaveLength(0);
		expect(container.textContent).toContain('No status changes yet');
	});
});

describe('the transition banner', () => {
	it('leads with the most recent status flip', () => {
		const { container } = render(StatusTransitionBanner, {
			props: { events: parsedEvents() }
		});

		expect(container.textContent).toContain('Status changed from');
		expect(container.querySelector('.badge-disappeared')).not.toBeNull();
		expect(container.querySelector('.badge-deceased')).not.toBeNull();
	});

	it('says nothing when no status changed', () => {
		const { container } = render(StatusTransitionBanner, {
			props: { events: [] }
		});

		expect(container.querySelector('.status-transition-banner')).toBeNull();
	});
});
