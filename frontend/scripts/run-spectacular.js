/**
 * Run `manage.py spectacular` regardless of whether Django lives in a
 * venv (local dev) or system Python (CI).
 *
 *   Local:  /home/aya/testimonies-world/backend/.venv/bin/python manage.py spectacular …
 *   CI:     python manage.py spectacular …  (deps installed via pip install -r requirements.txt)
 *
 * Picks the first one that exists. Exits with the same code as
 * spectacular so `gen:api:check` correctly detects drift.
 *
 * Always forces `USE_SQLITE=True` so the schema emitted by `spectacular`
 * matches what CI produces (CI uses SQLite for the drift gate — see
 * `.github/workflows/ci.yml`). Without this override, a local `.env`
 * pointing at the remote Postgres would emit Postgres-specific
 * bounds for `BigIntegerField` (e.g. `quality_tier`: ±2^63), while
 * CI emits SQLite bounds (±2^31). The two would not match, and
 * `gen:api:check` would flag drift even though both files were
 * freshly regenerated.
 */
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { join } from 'node:path';

const VENV_PY = join('..', 'backend', '.venv', 'bin', 'python');
const SYSTEM_PY = 'python';

const python = existsSync(VENV_PY) ? VENV_PY : SYSTEM_PY;

const args = [
	'manage.py',
	'spectacular',
	'--file',
	'../openapi.yml',
	'--validate',
	'--fail-on-warn',
	'--color',
];

const result = spawnSync(python, args, {
	cwd: join('..', 'backend'),
	stdio: 'inherit',
	env: {
		...process.env,
		DJANGO_SECRET_KEY: 'spectacular-ci-not-secret',
		// Force the SQLite swap in backend/testimonies/settings.py so
		// the locally-generated schema is byte-identical to the one CI
		// produces. See comment above.
		USE_SQLITE: 'True',
	},
});

process.exit(result.status ?? 1);