import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright config — testimonies.world frontend E2E.
 *
 * Conventions:
 *   - baseURL is the SvelteKit base path so `page.goto('/testimonials')`
 *     resolves to /testimonies/testimonials. Spec URLs stay short and
 *     stable across dev / staging / prod.
 *   - webServer starts the frontend dev server with PUBLIC_BASE_PATH
 *     set, on a known port. The Django backend is NOT started here —
 *     it is expected to be running already (see ../CLAUDE.md "Key
 *     commands"). The webServer probe checks the URL is reachable
 *     before tests run, which doubles as a "did the dev server boot"
 *     guard.
 *   - storageState is referenced per-project so adding a new audience
 *     (anon, volunteer, advocate, admin) is one row, not a global
 *     flag. The advocate project is the one that exercises the
 *     reject workflow; anon is for public-surface smoke tests.
 *
 * Security posture:
 *   - The .auth/ directory is gitignored; this config NEVER writes
 *     or reads auth state from a tracked path.
 *   - This config does NOT define a backend auth bypass or a
 *     "test-mode" cookie. The auth JSON is expected to be produced
 *     by an out-of-band bootstrap that the team approves (see
 *     TESTIMONIAL_E2E_AUTH.md).
 */
export default defineConfig({
  testDir: './tests',
  // Output lives outside testDir so report + artefacts don't shadow
  // spec files in editors / coverage tools.
  outputDir: './test-results',

  timeout: 30_000,
  expect: { timeout: 5_000 },

  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  reporter: process.env.CI ? 'list' : 'html',

  use: {
    // baseURL is the origin only — Playwright replaces the path
    // component on goto('/foo'). Specs include the SvelteKit base
    // path (/testimonies) in their routes explicitly.
    baseURL: 'http://127.0.0.1:3040',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    // Auth bootstrap. Runs before any project that depends on it.
    // Produces playwright/.auth/advocate.json from a real
    // /__test__/login/ round-trip — no fabricated sessions.
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
      use: { ...devices['Desktop Chrome'] },
    },

    // Public-surface smoke tests — no auth required.
    {
      name: 'anon',
      use: { ...devices['Desktop Chrome'] },
    },

    // Advocate session — required for the testimonial reject workflow.
    // storageState is produced by the `setup` project (see
    // tests/auth.setup.ts) and must NOT be committed (gitignored).
    {
      name: 'advocate',
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'playwright/.auth/advocate.json',
      },
    },
  ],

  webServer: {
    // VITE_API_PROXY_TARGET=http://127.0.0.1:8040 routes the dev
    // server's /testimonies/api proxy at the local Django, not
    // production. See vite.config.ts for the rationale.
    command:
      'VITE_API_PROXY_TARGET=http://127.0.0.1:8040 PUBLIC_BASE_PATH=/testimonies npm run dev -- --host 127.0.0.1 --port 3040',
    url: 'http://127.0.0.1:3040/testimonies/testimonials',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
});