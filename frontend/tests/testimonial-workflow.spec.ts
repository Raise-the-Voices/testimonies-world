import { test, expect } from '@playwright/test';

/**
 * E2E: Testimonial reject workflow.
 *
 * Runs under the `advocate` project, so the Review queue tab is
 * visible and the Reject button is rendered on the detail page.
 *
 * The auth storageState (playwright/.auth/advocate.json) must be
 * produced by the auth bootstrap (see TESTIMONIAL_E2E_AUTH.md).
 * If the file is missing, Playwright will start the project with
 * an empty cookie jar — the Review queue tab won't render, and the
 * first `.click()` on it will fail with a clear selector error
 * pointing at the missing auth.
 *
 * Pre-conditions (asserted at the start of the test, not in a
 * beforeAll, so the failure message is local to the spec):
 *   - Backend reachable on :8040 (the reject API call resolves)
 *   - At least one testimonial in UNDER_REVIEW status — otherwise
 *     the Review queue is empty and no card is clickable
 *
 * Security:
 *   - This spec NEVER reads /source/ or /precise_location/ — those
 *     endpoints are Advocate-only and surface decryption; they
 *     are out of scope for a *workflow* test and including them
 *     would expand the audit-log surface for no test value.
 *   - The rejection reason used in this spec is a fixed synthetic
 *     string. Real data must never be used in E2E fixtures.
 */
test.describe('Testimonial workflow — Reject', () => {
    test(
      'advocate rejects an under-review testimonial and lands on the Rejected tab',
      {
        tag: ['@critical'],
        // Annotations render in the HTML report's test-detail panel —
        // ticket for traceability, owner so on-call knows who to ping.
        // Keep this list small; the report is read at 2am and noise
        // hurts.
        annotation: [
          { type: 'ticket', description: 'PROJ-1234' },
          { type: 'owner', description: 'advocacy-team' },
        ],
      },
      async ({ page }, testInfo) => {
        // Per-project skip — the 'anon' project intentionally has no
        // storageState, so this advocate-only workflow can't run there.
        // Skipping inside the test body (rather than at describe time)
        // gives us access to testInfo, the only reliable way to
        // detect the current project at collection time in Playwright
        // 1.63.x.
        test.skip(testInfo.project.name === 'anon', 'requires advocate session');
        // 1. Open the UI on the Review queue tab directly. The page reads
        //    ?tab= on mount (see tabFromUrl() in +page.svelte) and the
        //    post-action redirect from WorkflowActions lands back on a
        //    ?tab= URL — so deep-linking is the realistic user path and
        //    also the most robust against any client-side tab-click
        //    races during hydration.
        await page.goto('/testimonies/testimonials?tab=review');

        // 2. Verify the Review queue tab is the active one.
        //    <button role="tab" id="testimonials-tab-review">Review queue</button>
        const reviewTab = page.getByRole('tab', { name: /review queue/i });
        await expect(reviewTab).toHaveAttribute('aria-selected', 'true');
        await expect(reviewTab).toHaveId('testimonials-tab-review');

        // 3. Open the first testimonial in the queue.
        //    TestimonialCard renders as
        //    <a class="testimonial-card" href="/testimonials/{id}">
        //    which SvelteKit's base path prefixes to
        //    /testimonies/testimonials/{id}.
        const firstCard = page.locator('.testimonials-grid a.testimonial-card').first();
        await expect(firstCard).toBeVisible();
        await firstCard.click();

        // Detail page reached.
        await expect(page).toHaveURL(/\/testimonies\/testimonials\/\d+/);

        // 4. Trigger the rejection modal.
        //    Class hook .action-btn-danger is the design-system marker for
        //    destructive transitions; "Reject…" is the only one shown on
        //    an under-review row for an advocate.
        const rejectButton = page.locator('button.action-btn-danger');
        await expect(rejectButton).toBeVisible();
        await rejectButton.click();

        // Modal opens — Modal.svelte renders role="dialog" with aria-modal.
        const dialog = page.getByRole('dialog');
        await expect(dialog).toBeVisible();
        await expect(page.locator('#reject-notes')).toBeVisible();
        await expect(page.locator('#reject-notes')).toBeEnabled();

        // 5. Fill the rejection reason and confirm.
        const reason = 'Source unreliable; needs re-verification.';
        await page.locator('#reject-notes').fill(reason);

        // Confirm button is disabled until the textarea has content —
        // proves we drove the enabled-state transition, not just clicked
        // blindly.
        const confirmButton = page.locator('button.reject-btn-confirm');
        await expect(confirmButton).toBeEnabled();
        await confirmButton.click();

        // 6. Verify the post-action redirect to the Rejected tab.
        //    WorkflowActions.svelte: `await goto(`${base}/testimonials?tab=rejected`)`
        await expect(page).toHaveURL(/\/testimonies\/testimonials\?tab=rejected$/);

        const rejectedTab = page.getByRole('tab', { name: /^rejected\b/i });
        await expect(rejectedTab).toHaveAttribute('aria-selected', 'true');

        // The rejected testimonial surfaces its review_notes on the list
        // card (.rejection-reason-text). Visible only after the
        // authenticated GET refetches the row under the new status —
        // confirms the backend accepted the transition, not just that
        // the client navigated.
        await expect(page.locator('.rejection-reason-text').first()).toContainText(reason);

        // Attach the rejection reason to the report. On failure the next
        // debugger sees "expected X got Y" — but rarely knows what string
        // was actually submitted. test.info().attach puts the text in the
        // HTML report's test-detail panel so the cause is one click away.
        test.info().attach('rejection reason', {
          body: reason,
          contentType: 'text/plain',
        });
      },
    );
  },
);
