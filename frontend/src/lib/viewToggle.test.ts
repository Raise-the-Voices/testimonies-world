// @vitest-environment jsdom
/**
 * The view toggle.
 *
 * A segmented control with a pill that slides between the two
 * segments. The pill is the risk: a control that moves by animating a
 * layout property re-lays-out on every frame, and a control whose
 * pill is measured after the first paint flashes. So the two segments
 * are the same width, the pill is exactly one of them, and it moves by
 * a transform alone.
 */
import { describe, it, expect, afterEach } from 'vitest';
import { cleanup, render, fireEvent } from '@testing-library/svelte';
import { tick } from 'svelte';
import ViewToggle from './ViewToggle.svelte';
import source from './ViewToggle.svelte?raw';

afterEach(() => {
	cleanup();
	localStorage.removeItem('rtv-cases-view');
});

describe('the view toggle', () => {
	it('shows one pill behind the two segments', () => {
		const { container } = render(ViewToggle);
		const pill = container.querySelector('.view-toggle-pill');

		expect(pill).not.toBeNull();
		expect(pill?.getAttribute('aria-hidden')).toBe('true');
		expect(container.querySelectorAll('button')).toHaveLength(2);
	});

	it('moves the pill by a transform and nothing else', () => {
		const rule = /\.view-toggle-pill \{([^}]*)\}/.exec(source)?.[1] ?? '';
		const transition = /transition:\s*([^;]+);/.exec(rule)?.[1] ?? '';

		expect(transition).toBe('transform var(--motion-duration-overlay) var(--motion-ease-overlay)');
		// The width is set once, not animated: the segments are the
		// same width, so the pill is exactly one of them.
		expect(rule).toMatch(/width:\s*calc\(50% - 0\.25rem\)/);
		expect(source).toContain("transform: translateX(100%);");
	});

	it('gives the two segments the same width', () => {
		expect(source).toMatch(/flex:\s*1 1 0;/);
		expect(source).toMatch(/min-width:\s*92px;/);
	});

	it('slides the selection when a segment is clicked', async () => {
		const { container } = render(ViewToggle);
		const toggle = container.querySelector('.view-toggle');
		const [cards, list] = Array.from(container.querySelectorAll('button'));

		expect(toggle?.getAttribute('data-mode')).toBe('cards');

		await fireEvent.click(list);

		expect(toggle?.getAttribute('data-mode')).toBe('list');
		expect(list.getAttribute('aria-selected')).toBe('true');
		expect(cards.getAttribute('aria-selected')).toBe('false');
	});

	it('opens on the saved choice', async () => {
		localStorage.setItem('rtv-cases-view', 'list');
		const { container } = render(ViewToggle);
		await tick();

		expect(container.querySelector('.view-toggle')?.getAttribute('data-mode')).toBe('list');
	});

	it('still moves with reduced motion asked for', () => {
		// The transition is switched off by the component's own
		// media block; the selection itself still changes.
		expect(source).toMatch(/@media \(prefers-reduced-motion: reduce\) \{[\s\S]*?transition: none;/);
	});
});
