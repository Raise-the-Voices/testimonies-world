/**
 * Run `manage.py spectacular` regardless of whether Django lives in a
 * venv (local dev) or system Python (CI).
 *
 *   Local:  /home/aya/testimonies-world/backend/.venv/bin/python manage.py spectacular …
 *   CI:     python manage.py spectacular …  (deps installed via pip install -r requirements.txt)
 *
 * Picks the first one that exists. Exits with the same code as
 * spectacular so `gen:api:check` correctly detects drift.
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
	env: { ...process.env, DJANGO_SECRET_KEY: 'spectacular-ci-not-secret' },
});

process.exit(result.status ?? 1);