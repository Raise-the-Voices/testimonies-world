import { defineConfig } from 'orval';

/**
 * Generates TypeScript types + Zod schemas from the backend's OpenAPI schema.
 *
 *   npm run gen:api          regenerate after backend changes (writes to src/lib/api/generated/)
 *   npm run gen:api:check    CI gate: fails if regenerated output differs from committed copy
 *
 * The backend ships the OpenAPI YAML via `manage.py spectacular --validate --fail-on-warn`.
 * The check command enforces that no serializer changed without regenerating.
 */
export default defineConfig({
  testimonies: {
    input: {
      target: '../openapi.yml',
    },
    output: {
      // One file per endpoint family — keeps the generated tree
      // tree-shakable. The mutator (`./src/lib/api/mutator.ts`) is
      // where every generated endpoint converges for credentials,
      // CSRF, error handling, and (eventually) Zod parsing.
      target: 'src/lib/api/generated/endpoints.ts',
      mode: 'split',
      client: 'fetch',
      clean: true,
      override: {
        mutator: {
          path: 'src/lib/api/mutator.ts',
          name: 'fetcher',
        },
      },
    },
    hooks: {
      // After orval writes files, run the forward-reference fixup.
      // orval emits `export type X = typeof X[...]` BEFORE
      // `export const X = {...} as const`, which fails strict TS.
      // See scripts/fix-orval-order.js.
      afterAllFilesWrite: 'node scripts/fix-orval-order.js',
    },
  },
});