import { test as setup, expect } from '@playwright/test';

/**
 * Auth bootstrap for the `advocate` Playwright project.
 *
 * Calls the backend's /__test__/login/ endpoint with the per-deploy
 * token, captures the resulting sessionid cookie, and writes it to
 * `playwright/.auth/advocate.json`. The advocate project reads that
 * file as its `storageState` so each spec starts pre-authenticated.
 *
 * Security / config:
 *   - TESTIMONIAL_E2E_AUTH_TOKEN MUST match the value in
 *     backend/.env. The bootstrap fails fast if it is empty.
 *   - E2E_BACKEND_URL defaults to the local dev server on :8040
 *     (gunicorn, started independently of `npm run dev`).
 *   - E2E_ADVOCATE_USERNAME must exist in the DB with the
 *     `Advocate` group membership — see bootstrap notes in the
 *     `Verify security gates` step (backend/.env + manage.py shell
 *     snippet).
 *
 * What this does NOT do:
 *   - It does not touch the frontend. The webServer in
 *     playwright.config.ts still spins up the dev server because
 *     webServer is config-global; the setup spec simply doesn't
 *     navigate to it.
 *   - It does not capture the csrftoken cookie. Django's
 *     CsrfViewMiddleware sets it on the first authenticated
 *     browser GET (the first `page.goto('/testimonials')` in the
 *     spec), and the SvelteKit API mutator reads it via
 *     document.cookie at request time. Capturing it in the setup
 *     would be redundant.
 */

const BACKEND_URL = process.env.E2E_BACKEND_URL ?? 'http://127.0.0.1:8040';
const TEST_TOKEN = process.env.TESTIMONIAL_E2E_AUTH_TOKEN ?? '';
const TEST_USERNAME = process.env.E2E_ADVOCATE_USERNAME ?? 'e2e-advocate';
const STORAGE_STATE_PATH = 'playwright/.auth/advocate.json';

setup('authenticate as advocate via /__test__/login/', async ({ request }) => {
  if (!TEST_TOKEN) {
    throw new Error(
      'TESTIMONIAL_E2E_AUTH_TOKEN env var is unset. The /__test__/login/ ' +
        'endpoint is unreachable without it. See backend/cases/test_auth.py ' +
        'for the security model and how to set one locally.',
    );
  }

  const response = await request.post(`${BACKEND_URL}/__test__/login/`, {
    headers: {
      'X-Test-Auth-Token': TEST_TOKEN,
      'Content-Type': 'application/json',
    },
    data: { username: TEST_USERNAME },
  });

  expect(
    response.status(),
    `test login returned ${response.status()} (expected 204). ` +
      'Likely causes: wrong token, ENABLE_E2E_TEST_AUTH unset on the ' +
      'backend, TESTIMONIAL_E2E_AUTH_TOKEN empty, or username not in DB.',
  ).toBe(204);

  // Persist cookies (sessionid) to disk. The advocate project loads
  // this file as its storageState.
  await request.storageState({ path: STORAGE_STATE_PATH });
});