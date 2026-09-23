/**
 * Dashboard E2E — verifies the operator command center survives
 * (a) a successful authenticated load with real data,
 * (b) a network failure on /api/dashboard/ showing the inline error
 *     card + Retry button,
 * (c) recovery: clicking Retry re-fetches and renders normally.
 *
 * Coverage gap this fills: the dashboard's `data.error` fallback
 * (dashboard/+page.svelte:191-197) was untested. A bug in that path
 * (e.g. a stale ref to a renamed field) would only surface in
 * production when the backend was already unhappy — the worst time
 * to discover a UX regression.
 *
 * Runs under the `advocate` project. The advocate role is the
 * mid-tier audience; this spec doesn't depend on advocate-specific
 * data, but using advocate means we exercise the same session that
 * would hit the dashboard in production.
 */
import { test, expect } from '@playwright/test';

const DASHBOARD_URL = '/testimonies/dashboard';
const DASHBOARD_API = /\/api\/dashboard\/?$/;

/** Minimal happy-path payload — mirrors the shape the
 *  DashboardViewSet returns. Only the fields the page reads need
 *  to be present; the rest is noise. */
const HAPPY_PAYLOAD = {
  scope: 'advocate',
  summary: {
    open_cases: 130,
    stale_cases: 42,
    my_open_casework: 7,
    unread_notifications: 3,
  },
  recent_persons: [],
  recent_reports: [],
  recent_casework: [],
  activity: [],
  by_status: { detained: 50, released: 80 },
};

test.describe('Dashboard — load and recovery', () => {
  test('authenticated user sees all 4 KPI tiles with values from the API', async ({
    page,
  }) => {
    // Mock the dashboard endpoint so the test is hermetic — no DB
    // state required, no flake from a populated dataset.
    await page.route(DASHBOARD_API, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(HAPPY_PAYLOAD),
      });
    });

    await page.goto(DASHBOARD_URL);

    // Header + scope label render.
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();

    // Four KPI tiles, each with an aria-label like "Total cases: 130".
    // Using aria-label sidesteps any layout / class drift and reads
    // exactly what a screen reader user hears.
    await expect(page.getByLabel(/Total cases.*130/i)).toBeVisible();
    await expect(page.getByLabel(/Stale cases.*42/i)).toBeVisible();
    await expect(page.getByLabel(/My open casework.*7/i)).toBeVisible();
    await expect(page.getByLabel(/Unread notifications.*3/i)).toBeVisible();

    // No error card visible on success.
    await expect(page.locator('[role="alert"]')).toHaveCount(0);
  });

  test('network failure on /api/dashboard/ shows error card with Retry button', async ({
    page,
  }) => {
    // Single-shot abort: the first /api/dashboard/ call fails. The
    // page should render its inline error card (not the global
    // +error.svelte — that's only for uncaught load throws).
    let callCount = 0;
    await page.route(DASHBOARD_API, async (route) => {
      callCount += 1;
      await route.abort('failed');
    });

    await page.goto(DASHBOARD_URL);

    // Inline error card — distinct copy from the global error page.
    await expect(
      page.getByText(/couldn't load the dashboard/i),
    ).toBeVisible();

    // Retry button (the dashboard calls it "Try again" inline;
    // matches the audit's documented fallback).
    const retry = page.getByRole('button', { name: /try again/i });
    await expect(retry).toBeVisible();

    // No KPI tiles rendered — the error branch is the only content.
    await expect(page.getByLabel(/Total cases/i)).toHaveCount(0);

    // Confirm at least one network attempt happened.
    expect(callCount).toBeGreaterThanOrEqual(1);
  });

  test('Retry button recovers after the network is restored', async ({
    page,
  }) => {
    // First call: abort. Second call (after Retry): succeed. Tests
    // that the dashboard's `refresh()` actually re-fetches, not just
    // re-renders the error card.
    let callCount = 0;
    await page.route(DASHBOARD_API, async (route) => {
      callCount += 1;
      if (callCount === 1) {
        await route.abort('failed');
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(HAPPY_PAYLOAD),
        });
      }
    });

    await page.goto(DASHBOARD_URL);

    // Error card visible first.
    await expect(
      page.getByText(/couldn't load the dashboard/i),
    ).toBeVisible();

    // Click Try again — calls invalidateAll() which re-runs +page.ts.
    await page.getByRole('button', { name: /try again/i }).click();

    // Success state: KPI tiles render with the values from the
    // mocked second response.
    await expect(page.getByLabel(/Total cases.*130/i)).toBeVisible({ timeout: 10_000 });
    await expect(
      page.getByText(/couldn't load the dashboard/i),
    ).toHaveCount(0);

    // Confirm the retry actually re-fetched (not just re-rendered).
    expect(callCount).toBeGreaterThanOrEqual(2);
  });
});
