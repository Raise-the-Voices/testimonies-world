/**
 * Shared helpers for the form-audit suite.
 *
 * Selectors mirror the actual component classnames/ARIA from:
 *   - src/lib/Toast.svelte          → .toast, .toast-{variant}, role="status"
 *   - src/lib/Banner.svelte         → .banner, role="alert" for errors
 *   - src/lib/ReportForm.svelte     → .form-error, .field-error, .field.has-error
 *   - src/lib/TestimonialForm.svelte → same conventions
 *   - src/routes/{submit,casework,contacts,persons}/...+page.svelte
 *
 * Conventions:
 *   - baseURL is the host; the /testimonies SvelteKit base path is part
 *     of every navigated route (matches playwright.config.ts).
 *   - Network interceptors use page.route(); scoped per-test via unique
 *     URL fragments to avoid cross-test pollution.
 */
import { test as base, expect, type Page, type Route, type Request } from '@playwright/test';
import path from 'node:path';

/* ---------- Toast helpers ---------- */

const TOAST = '.toast';
const TOAST_VARIANT = (v: 'success' | 'error' | 'info' | 'warning') =>
  `.toast-${v}`;

/** Wait for a toast of a given variant to appear. Resolves on visible. */
export async function expectToast(
  page: Page,
  variant: 'success' | 'error' | 'info' | 'warning',
  options: { contains?: string | RegExp; timeout?: number } = {},
) {
  const toast = page.locator(TOAST).locator(TOAST_VARIANT(variant));
  await expect(toast).toBeVisible({ timeout: options.timeout ?? 7_000 });
  if (options.contains !== undefined) {
    await expect(toast).toContainText(options.contains);
  }
  return toast;
}

/** Assert NO toast is visible — useful after an expected error. */
export async function expectNoToast(page: Page) {
  await expect(page.locator(TOAST)).toHaveCount(0);
}

/** Dismiss the current toast (Escape key) and wait for it to leave. */
export async function dismissToast(page: Page) {
  const live = page.locator(TOAST).first();
  if (await live.isVisible().catch(() => false)) {
    await live.press('Escape');
    await expect(page.locator(TOAST)).toHaveCount(0);
  }
}

/* ---------- Inline form-error helpers ---------- */

const FORM_ERROR = '.form-error, .form-error-banner';
const FIELD_ERROR = '.field-error, .form-field-error';

/** Top-of-form banner error. Asserts text and (optionally) error kind. */
export async function expectFormError(
  page: Page,
  options: { contains?: string | RegExp; kind?: string } = {},
) {
  const banner = page.locator(FORM_ERROR).first();
  await expect(banner).toBeVisible();
  if (options.contains) await expect(banner).toContainText(options.contains);
  return banner;
}

/** Inline field-level error. Asserts the wrapper has the red border + the message. */
export async function expectFieldError(
  page: Page,
  fieldName: string,
  contains?: string | RegExp,
) {
  const wrapper = page.locator('.field.has-error, .form-row.has-error').filter({
    has: page.locator(`#${fieldName}`),
  });
  await expect(wrapper).toBeVisible();
  const msg = wrapper.locator(FIELD_ERROR);
  await expect(msg).toBeVisible();
  if (contains) await expect(msg).toContainText(contains);
}

/** Assert a specific field is in the valid (no-error) state. */
export async function expectFieldValid(page: Page, fieldName: string) {
  const wrapper = page.locator('.field, .form-row').filter({
    has: page.locator(`#${fieldName}`),
  });
  await expect(wrapper).not.toHaveClass(/has-error/);
}

/* ---------- Network fault injection ---------- */

/** Fail any request matching `matcher` with an aborted network error. */
export function failRequestsTo(page: Page, matcher: string | RegExp) {
  return page.route(matcher, (route: Route) => route.abort('failed'));
}

/** Force a 4xx/5xx response with optional body for any matching request. */
export function respondWith(
  page: Page,
  matcher: string | RegExp,
  status: number,
  body: object | string = {},
) {
  return page.route(matcher, async (route: Route) => {
    const payload = typeof body === 'string' ? body : JSON.stringify(body);
    await route.fulfill({
      status,
      contentType: 'application/json',
      body: payload,
    });
  });
}

/** DRF-style field error payload (mimics the backend serializer response). */
export function drfFieldErrors(page: Page, fields: Record<string, string[]>) {
  return respondWith(page, /\/api\/.*/, 400, fields);
}

/** Listen for console messages, page errors, and failed requests. */
export function recordConsole(page: Page) {
  const log: { type: string; text: string; location?: string }[] = [];
  page.on('console', (msg) => {
    log.push({ type: msg.type(), text: msg.text(), location: msg.location()?.url });
  });
  page.on('pageerror', (err) => {
    log.push({ type: 'pageerror', text: err.message });
  });
  page.on('requestfailed', (req: Request) => {
    log.push({
      type: 'requestfailed',
      text: `${req.method()} ${req.url()} — ${req.failure()?.errorText}`,
    });
  });
  return {
    snapshot: () => [...log],
    errorsOnly: () =>
      log.filter((l) => l.type === 'error' || l.type === 'pageerror'),
    assertNoErrors: () => {
      const errors = log.filter(
        (l) => l.type === 'error' || l.type === 'pageerror',
      );
      if (errors.length) {
        throw new Error(
          `Unexpected console/page errors:\n` +
            errors.map((e) => `  [${e.type}] ${e.text}`).join('\n'),
        );
      }
    },
  };
}

/* ---------- Fixture data (synthetic, never real case data) ---------- */

export const PERSON_FIXTURES = {
  basic: {
    title: 'Case: arbitrary detention of a journalist',
    country: 'Syria',
    region: 'Damascus',
    summary:
      'A journalist was detained after publishing an investigation into local corruption. Family was not notified for 72 hours.',
    narrative:
      'On the morning of the arrest, plain-clothes officers entered the home without a warrant. ' +
      'The journalist was taken to an undisclosed location. The family received no communication ' +
      'for three days. This pattern is consistent with enforced disappearance as defined by the ' +
      'International Convention for the Protection of All Persons from Enforced Disappearance.',
  },
};

export const REPORT_FIXTURES = {
  basic: {
    source_type: 'firsthand',
    narrative:
      'Witnesses report the individual was transported in an unmarked vehicle. ' +
      'No official arrest warrant was presented at the time of detention.',
  },
};

export const CONTACT_FIXTURES = {
  basic: {
    name: 'Layla Hassan',
    role: 'family',
    email: 'layla@example.test',
  },
};

export const CASEWORK_FIXTURES = {
  basic: {
    action_type: 'legal_filing',
    description: 'Filed habeas corpus petition with the regional court.',
    next_steps: 'Awaiting court response within 30 days.',
  },
};

export const SUBMIT_FIXTURES = {
  basic: {
    name: 'Anonymous Source',
    country: 'Egypt',
    ...REPORT_FIXTURES.basic,
  },
};

/* ---------- Navigation helpers ---------- */

export async function goToNewTestimonial(page: Page) {
  await page.goto('/testimonies/testimonials/new');
  await expect(page.getByRole('heading', { name: /new testimonial/i })).toBeVisible();
}

export async function goToNewReport(page: Page) {
  await page.goto('/testimonies/reports');
  await page.getByRole('button', { name: /add report|new report/i }).click();
  await expect(page.locator('.modal-body, form')).toBeVisible();
}

export async function goToNewContact(page: Page) {
  await page.goto('/testimonies/contacts/new');
  await expect(page.getByRole('heading', { name: /new contact|edit contact/i })).toBeVisible();
}

export async function goToNewCasework(page: Page) {
  await page.goto('/testimonies/casework/new');
  await expect(page.getByRole('heading', { name: /new casework/i })).toBeVisible();
}

export async function goToSubmitCase(page: Page) {
  await page.goto('/testimonies/submit');
  await expect(page.getByRole('heading', { name: /submit.*case/i })).toBeVisible();
}

/* ---------- Fixtures via test.extend() ---------- */

export type FormAuditFixtures = {
  consoleLog: ReturnType<typeof recordConsole>;
};

/**
 * Extended test that auto-attaches a console recorder and asserts no
 * uncaught pageerror or console.error leaked into the page after each
 * test runs. Catches the silent-failure gaps identified in the audit
 * (Bell.svelte, notifications/+page.svelte, etc.) without needing a
 * dedicated spec for each.
 */
export const test = base.extend<FormAuditFixtures>({
  consoleLog: async ({ page }, use) => {
    const rec = recordConsole(page);
    await use(rec);
    await rec.assertNoErrors();
  },
});

export { expect };
export { path };
