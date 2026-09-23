/**
 * Form audit — UX & functional coverage for the SvelteKit frontend.
 *
 * Goals (mirrors the QA ticket):
 *   1. Verify each form actually submits (no silent failures).
 *   2. Verify success and error feedback (toasts + inline banners).
 *   3. Verify inline validation fires for missing/invalid input.
 *
 * Runs under the `advocate` project so the protected forms (testimonial
 * create, /submit, /casework, /contacts) are accessible. The `anon`
 * project deliberately skips the advocate-only tests via test.skip()
 * per spec.
 *
 * The console recorder is attached via test.extend() — any uncaught
 * pageerror or console.error fails the test (catches the silent-failure
 * gaps identified in the audit: Bell.svelte console-only catches,
 * notifications/+page.svelte empty catches, etc.).
 */
import {
  test,
  expect,
  expectToast,
  expectNoToast,
  expectFormError,
  expectFieldError,
  expectFieldValid,
  failRequestsTo,
  respondWith,
  drfFieldErrors,
  PERSON_FIXTURES,
  REPORT_FIXTURES,
  CONTACT_FIXTURES,
  CASEWORK_FIXTURES,
  SUBMIT_FIXTURES,
  goToNewTestimonial,
  goToNewReport,
  goToNewContact,
  goToNewCasework,
  goToSubmitCase,
} from './helpers/form-audit';

test.describe('Form audit — UX & feedback', () => {
  test.beforeEach(async ({ page }) => {
    // Reset any leftover toast from a previous spec.
    await page.keyboard.press('Escape');
  });

  /* ===========================================================
   * TESTIMONIAL FORM (the only Zod-validated form)
   * =========================================================== */

  test.describe('Testimonial create', () => {
    test('happy path: fills required fields, saves draft, lands on detail page', async ({
      page,
    }) => {
      await goToNewTestimonial(page);
      await page.locator('#title').fill(PERSON_FIXTURES.basic.title);
      await page.locator('#country').fill(PERSON_FIXTURES.basic.country);
      await page.locator('#summary').fill(PERSON_FIXTURES.basic.summary);
      await page.locator('#narrative').fill(PERSON_FIXTURES.basic.narrative);

      // "Save draft" button — TestimonialForm.svelte saves a draft and resets.
      await page.getByRole('button', { name: /save draft/i }).click();

      // No toast on draft save (testimonial create intentionally skips).
      await expectNoToast(page);

      // The form clears after a successful draft save.
      await expect(page.locator('#title')).toHaveValue('');
    });

    test('client validation: empty required fields show inline Zod errors', async ({
      page,
    }) => {
      await goToNewTestimonial(page);
      // Click Save Draft without filling anything.
      await page.getByRole('button', { name: /save draft/i }).click();

      // Zod produces the field error map; TestimonialForm.svelte.
      await expectFormError(page, { contains: /some fields need attention/i });
      await expectFieldError(page, 'title');
      await expectFieldError(page, 'country');
      await expectFieldError(page, 'summary');
      await expectFieldError(page, 'narrative');

      // The first errored field should have focus — TestimonialForm focuses
      // the first invalid field after Zod failure.
      const focused = await page.evaluate(() => document.activeElement?.id);
      expect(focused).toBeTruthy();
      expect(['title', 'country', 'summary', 'narrative']).toContain(focused);

      // Validation failures must NOT fire a toast (per design decision —
      // inline UI owns field errors).
      await expectNoToast(page);
    });

    test('server validation: DRF 400 surfaces as field-level error', async ({
      page,
    }) => {
      await goToNewTestimonial(page);
      await page.locator('#title').fill(PERSON_FIXTURES.basic.title);
      await page.locator('#country').fill(PERSON_FIXTURES.basic.country);
      await page.locator('#summary').fill(PERSON_FIXTURES.basic.summary);
      await page.locator('#narrative').fill(PERSON_FIXTURES.basic.narrative);

      // Mock the POST to fail with DRF-style field errors.
      await drfFieldErrors(page, {
        title: ['A testimonial with this title already exists.'],
        summary: ['Summary is too short (minimum 20 characters).'],
      });

      await page.getByRole('button', { name: /save draft/i }).click();
      await expectFieldError(page, 'title', /already exists/i);
      await expectFieldError(page, 'summary', /too short/i);
      // Validation must not fire a toast (kind === 'validation' is skipped).
      await expectNoToast(page);
    });

    test('network drop: status=0 surfaces a clear, friendly banner + toast', async ({
      page,
    }) => {
      await goToNewTestimonial(page);
      await page.locator('#title').fill(PERSON_FIXTURES.basic.title);
      await page.locator('#country').fill(PERSON_FIXTURES.basic.country);
      await page.locator('#summary').fill(PERSON_FIXTURES.basic.summary);
      await page.locator('#narrative').fill(PERSON_FIXTURES.basic.narrative);

      await failRequestsTo(page, /\/api\/testimonials\/?/);

      await page.getByRole('button', { name: /save draft/i }).click();
      // Inline banner with the friendly network copy.
      await expectFormError(page, { contains: /couldn.?t reach the server/i });
      // Transient error toast fires alongside the inline banner.
      await expectToast(page, 'error', { contains: /couldn.?t reach the server/i });
      // Critical: never expose a stack trace or raw fetch text.
      const text = await page.locator('.form-error, .form-error-banner').first().textContent();
      expect(text).not.toMatch(/TypeError|Failed to fetch|at /);
    });

    test('partial failure: create succeeds, submit fails — user sees hybrid state', async ({
      page,
    }) => {
      await goToNewTestimonial(page);
      await page.locator('#title').fill(PERSON_FIXTURES.basic.title);
      await page.locator('#country').fill(PERSON_FIXTURES.basic.country);
      await page.locator('#summary').fill(PERSON_FIXTURES.basic.summary);
      await page.locator('#narrative').fill(PERSON_FIXTURES.basic.narrative);

      // Create works, but the submit/ transition fails with a 500.
      await page.route(/\/api\/testimonials\/\d+\/submit\/?/, (r) =>
        r.fulfill({ status: 500, contentType: 'application/json', body: '{}' }),
      );

      await page.getByRole('button', { name: /submit for review/i }).click();
      // The hybrid message — TestimonialForm tells the user the draft DID save.
      await expectFormError(page, { contains: /saved as draft.*submission failed/i });
      // Server 500 also fires a transient toast.
      await expectToast(page, 'error');
    });
  });

  /* ===========================================================
   * REPORT FORM (the only form wired to fire a success toast)
   * =========================================================== */

  test.describe('Report create (the toast path)', () => {
    test('happy path via /reports modal fires a success toast with details', async ({
      page,
    }) => {
      await goToNewReport(page);
      // Modal form: source_type, narrative required.
      await page.locator('#source_type').selectOption(REPORT_FIXTURES.basic.source_type);
      await page.locator('#narrative').fill(REPORT_FIXTURES.basic.narrative);
      await page.getByRole('button', { name: /save|create/i }).click();

      // The /reports page parent handler fires the toast with details.
      const toast = await expectToast(page, 'success', {
        contains: /report (saved|created)/i,
      });
      // The "View response" toggle should be visible because details is set.
      await expect(toast.getByRole('button', { name: /view response/i })).toBeVisible();
    });

    test('inline validation: missing narrative blocks submit, no toast', async ({
      page,
    }) => {
      await goToNewReport(page);
      await page.locator('#source_type').selectOption('firsthand');
      // Skip narrative.
      await page.getByRole('button', { name: /save|create/i }).click();
      await expectFieldError(page, 'narrative');
      await expectNoToast(page);
    });

    test('server 500 fires an error toast', async ({ page }) => {
      await goToNewReport(page);
      await page.locator('#source_type').selectOption('firsthand');
      await page.locator('#narrative').fill(REPORT_FIXTURES.basic.narrative);

      await respondWith(page, /\/api\/reports\/?/, 500, { detail: 'S3 unreachable' });

      await page.getByRole('button', { name: /save|create/i }).click();
      await expectFormError(page);
      await expectToast(page, 'error');
    });
  });

  /* ===========================================================
   * CASEWORK, CONTACT, SUBMIT-CASE — coverage for inline-only forms
   * =========================================================== */

  test.describe('Casework create', () => {
    test('happy path with no linked persons', async ({ page }) => {
      await goToNewCasework(page);
      await page.locator('#action_type').selectOption(CASEWORK_FIXTURES.basic.action_type);
      // date defaults to today
      await page.locator('#status').selectOption('open');
      await page.locator('#description').fill(CASEWORK_FIXTURES.basic.description);
      await page.locator('#next_steps').fill(CASEWORK_FIXTURES.basic.next_steps);
      await page.getByRole('button', { name: /save|create/i }).click();

      // /casework/new redirects to /casework?saved=1 on success.
      await page.waitForURL(/\/casework/);
    });

    test('client validation: missing description is blocked, no toast', async ({
      page,
    }) => {
      await goToNewCasework(page);
      await page.locator('#action_type').selectOption('legal_filing');
      await page.locator('#status').selectOption('open');
      // Skip description.
      await page.getByRole('button', { name: /save|create/i }).click();
      await expectFieldError(page, 'description');
      await expectNoToast(page);
    });

    test('network failure on POST shows a banner + toast and keeps form state', async ({
      page,
    }) => {
      await goToNewCasework(page);
      await page.locator('#action_type').selectOption('legal_filing');
      await page.locator('#status').selectOption('open');
      await page.locator('#description').fill(CASEWORK_FIXTURES.basic.description);
      await failRequestsTo(page, /\/api\/casework\/?/);

      await page.getByRole('button', { name: /save|create/i }).click();
      await expectFormError(page, { contains: /couldn.?t reach|server/i });
      await expectToast(page, 'error');
      // The user should not lose their input.
      await expect(page.locator('#description')).toHaveValue(
        CASEWORK_FIXTURES.basic.description,
      );
    });
  });

  test.describe('Contact create', () => {
    test('happy path with valid email', async ({ page }) => {
      await goToNewContact(page);
      await page.locator('#name').fill(CONTACT_FIXTURES.basic.name);
      await page.locator('#role').selectOption(CONTACT_FIXTURES.basic.role);
      await page.locator('#email').fill(CONTACT_FIXTURES.basic.email);
      await page.getByRole('button', { name: /save|create/i }).click();
      await page.waitForURL(/\/contacts/);
    });

    test('email regex validation: malformed email is blocked client-side', async ({
      page,
    }) => {
      await goToNewContact(page);
      await page.locator('#name').fill(CONTACT_FIXTURES.basic.name);
      await page.locator('#role').selectOption('family');
      await page.locator('#email').fill('not-an-email');
      await page.getByRole('button', { name: /save|create/i }).click();
      await expectFieldError(page, 'email', /valid email|invalid/i);
      await expectNoToast(page);
    });

    test('DRF duplicate-email 400 surfaces as field error, no toast', async ({
      page,
    }) => {
      await goToNewContact(page);
      await page.locator('#name').fill(CONTACT_FIXTURES.basic.name);
      await page.locator('#role').selectOption('family');
      await page.locator('#email').fill(CONTACT_FIXTURES.basic.email);

      await drfFieldErrors(page, {
        email: ['Contact with this email already exists.'],
      });

      await page.getByRole('button', { name: /save|create/i }).click();
      await expectFieldError(page, 'email', /already exists/i);
      await expectNoToast(page);
    });
  });

  test.describe('Submit Case (combined person + report)', () => {
    test('happy path: minimal valid case', async ({ page }) => {
      await goToSubmitCase(page);
      await page.locator('#name').fill(SUBMIT_FIXTURES.basic.name);
      await page.locator('#country').fill(SUBMIT_FIXTURES.basic.country);
      await page.locator('#narrative').fill(SUBMIT_FIXTURES.basic.narrative);
      await page.getByRole('button', { name: /submit|create/i }).click();
      await page.waitForURL(/\/persons\/\d+/);
    });

    test('draft pill: long-form shows a "Saved Xm ago" indicator', async ({
      page,
    }) => {
      await goToSubmitCase(page);
      await page.locator('#name').fill('Test Person');
      await page.locator('#country').fill('Tunisia');
      // Debounce window is 1.5s in submitDraft.ts.
      await page.waitForTimeout(2_000);
      await expect(page.locator('text=/saved.*ago|saved just now/i')).toBeVisible();
    });

    test('localStorage quota error: draft pill turns red', async ({ page }) => {
      await goToSubmitCase(page);
      // Force quota exceeded on the next setItem.
      await page.evaluate(() => {
        const original = Storage.prototype.setItem;
        Storage.prototype.setItem = function () {
          throw new DOMException('QuotaExceededError', 'QuotaExceededError');
        };
        return () => {
          Storage.prototype.setItem = original;
        };
      });

      await page.locator('#name').fill('Test Person');
      await page.waitForTimeout(2_000);
      await expect(page.locator('text=/could not save draft/i')).toBeVisible();
    });

    test('auto-restore: valid draft pre-fills form silently on mount', async ({
      page,
    }) => {
      // Seed localStorage with a valid draft, then mount the page — same
      // observable effect as "close tab and come back" without relying
      // on page.reload() (which hits Vite dev-server resource limits
      // under headless Playwright). The form should mount with fields
      // pre-filled, no Restore button required.
      await page.goto('/testimonies/');
      const username = await page.evaluate(async () => {
        const r = await fetch('/testimonies/api/session/');
        const d = await r.json();
        return d.username ?? '';
      }).catch(() => '');
      expect(username).toBeTruthy();

      const draft = {
        schemaVersion: 2,
        username,
        savedAt: new Date().toISOString(),
        payload: {
          name: 'Restored Person',
          legalName: '',
          aliasesRaw: '',
          country: 'Tunisia',
          currentStatus: 'unknown',
          medicalStatus: 'unknown',
          roughLocation: '',
          preciseLocation: '',
          lastKnownDate: '',
          ethnicity: '',
          gender: '',
          ageAtIncident: '',
          occupation: '',
          qualityTier: '',
          profileImageCleared: false,
          medicalNotes: '',
          authoritativeSource: '',
          authoritativeUrl: '',
          isPublished: true,
          selectedCategories: [],
          summaryNarrative: '',
          sourceType: 'firsthand',
          sourceAttribution: '',
          reporterName: '',
          reporterContact: '',
          reportDateStart: '',
          reportRoughLocation: '',
          narrative: 'Recovered narrative from the last session.',
          suspectedReason: '',
          officialReason: '',
          sourceEntries: [],
          mediaEntries: [],
        },
      };
      await page.evaluate(
        ([k, v]) => window.localStorage.setItem(k, v),
        [`submit_form_draft_${username}`, JSON.stringify(draft)] as const,
      );

      await goToSubmitCase(page);
      await expect(page.locator('#name')).toHaveValue('Restored Person');
      await expect(page.locator('#country')).toHaveValue('Tunisia');
      await expect(page.locator('#narrative')).toHaveValue(
        'Recovered narrative from the last session.',
      );
      // Old manual-restore controls must be gone.
      await expect(page.getByRole('button', { name: /^restore$/i })).toHaveCount(0);
      // Cleanup so other tests start fresh.
      await page.evaluate(
        ([k]) => window.localStorage.removeItem(k),
        [`submit_form_draft_${username}`] as const,
      );
    });

    test('auto-restore: shows "Draft restored" flash, then steady pill', async ({
      page,
    }) => {
      await page.goto('/testimonies/');
      const username = await page.evaluate(async () => {
        const r = await fetch('/testimonies/api/session/');
        const d = await r.json();
        return d.username ?? '';
      }).catch(() => '');
      expect(username).toBeTruthy();

      const draft = {
        schemaVersion: 2,
        username,
        savedAt: new Date().toISOString(),
        payload: {
          name: 'Flash Person',
          country: 'Egypt',
          narrative: '',
          currentStatus: 'unknown',
          medicalStatus: 'unknown',
          isPublished: true,
          selectedCategories: [],
          sourceEntries: [],
          mediaEntries: [],
          profileImageCleared: false,
        },
      };
      await page.evaluate(
        ([k, v]) => window.localStorage.setItem(k, v),
        [`submit_form_draft_${username}`, JSON.stringify(draft)] as const,
      );

      await goToSubmitCase(page);
      // The flash pill is the first thing visible post-mount.
      await expect(
        page.locator('text=/draft restored from your last session/i'),
      ).toBeVisible({ timeout: 5_000 });
      // After the 6s window it falls back to the steady-state pill.
      await expect(
        page.locator('text=/draft restored from your last session/i'),
      ).toHaveCount(0, { timeout: 9_000 });
      await expect(
        page.locator('text=/saved.*ago|saved just now/i'),
      ).toBeVisible();

      // Cleanup.
      await page.evaluate(
        ([k]) => window.localStorage.removeItem(k),
        [`submit_form_draft_${username}`] as const,
      );
    });

    test('discard draft: button clears form + localStorage', async ({ page }) => {
      // Seed a draft via localStorage so the page mount triggers
      // auto-restore (avoids the page.reload() path that hits Vite
      // dev-server resource limits under headless Playwright).
      await page.goto('/testimonies/');
      const username = await page.evaluate(async () => {
        const r = await fetch('/testimonies/api/session/');
        const d = await r.json();
        return d.username ?? '';
      }).catch(() => '');
      expect(username).toBeTruthy();
      const draft = {
        schemaVersion: 2,
        username,
        savedAt: new Date().toISOString(),
        payload: {
          name: 'Discard Me',
          country: 'Sudan',
          currentStatus: 'unknown',
          medicalStatus: 'unknown',
          isPublished: true,
          selectedCategories: [],
          sourceEntries: [],
          mediaEntries: [],
          profileImageCleared: false,
        },
      };
      await page.evaluate(
        ([k, v]) => window.localStorage.setItem(k, v),
        [`submit_form_draft_${username}`, JSON.stringify(draft)] as const,
      );

      await goToSubmitCase(page);
      await expect(page.locator('#name')).toHaveValue('Discard Me');

      await page.getByTestId('submit-discard-draft').click();

      // Every form field resets; the steady-state pill goes away.
      await expect(page.locator('#name')).toHaveValue('');
      await expect(page.locator('#country')).toHaveValue('');
      await expect(
        page.locator('text=/saved.*ago|saved just now/i'),
      ).toHaveCount(0);
      // localStorage key for this user is gone.
      const stillThere = await page.evaluate(() => {
        const keys = Object.keys(window.localStorage);
        return keys.some((k) => k.startsWith('submit_form_draft_'));
      });
      expect(stillThere).toBe(false);
    });
  });

  /* ===========================================================
   * Cross-cutting: ARIA & accessibility sanity
   * =========================================================== */

  test.describe('Accessibility & ARIA', () => {
    test('testimonial field errors use the modern pattern (class:has-error + role=alert)', async ({
      page,
    }) => {
      await goToNewTestimonial(page);
      await page.getByRole('button', { name: /save draft/i }).click();

      const titleInput = page.locator('#title');
      await expect(titleInput).toHaveAttribute('aria-invalid', 'true');
      const describedBy = await titleInput.getAttribute('aria-describedby');
      expect(describedBy).toBeTruthy();
      // The error message must announce via role=alert (modern pattern).
      const errorMsg = page.locator(`#${describedBy}`);
      await expect(errorMsg).toHaveAttribute('role', 'alert');
      await expect(errorMsg).toContainText(/required|invalid/i);
    });

    test('toast container announces via role=status + aria-live=polite', async ({
      page,
    }) => {
      await goToNewReport(page);
      await page.locator('#source_type').selectOption('firsthand');
      await page.locator('#narrative').fill(REPORT_FIXTURES.basic.narrative);
      await page.getByRole('button', { name: /save|create/i }).click();

      const container = page.locator('.toast').first();
      await expect(container).toHaveAttribute('role', 'status');
      await expect(container).toHaveAttribute('aria-live', 'polite');
    });

    test('form has novalidate and never relies on browser-native tooltips', async ({
      page,
    }) => {
      await goToNewTestimonial(page);
      // The whole app disables native validation.
      const form = page.locator('form').first();
      await expect(form).toHaveAttribute('novalidate', '');
    });

    test('error toasts use the .toast-error variant class', async ({ page }) => {
      await goToNewCasework(page);
      await page.locator('#action_type').selectOption('legal_filing');
      await page.locator('#status').selectOption('open');
      await page.locator('#description').fill('Test description');
      await failRequestsTo(page, /\/api\/casework\/?/);

      await page.getByRole('button', { name: /save|create/i }).click();
      // The error toast must use the .toast-error variant so it gets the red border.
      const errorToast = page.locator('.toast.toast-error');
      await expect(errorToast).toBeVisible();
    });
  });
});
