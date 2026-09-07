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
 * ============================================================================
 *  Determinism contract
 * ============================================================================
 *  The byte-for-byte output of this script IS the source of truth for
 *  the drift gate. To keep the locally-generated schema bit-identical
 *  to what CI generates, the spawned `manage.py` process is given a
 *  TIGHT, EXPLICIT environment — never `process.env` directly.
 *
 *  The leaks that previously caused drift:
 *
 *    - The dev machine's `.env` might point at Postgres (PG_HOST, ...).
 *      spectacular reads the DB-bound bounds for BigIntegerField from
 *      the live connection, so PG vs SQLite emit different bounds.
 *      → We override USE_SQLITE to 'True' to mirror CI.
 *
 *    - A developer might have DATABASE_URL set for some side tool, or
 *      DEBUG=0 from a venv probe. Spectacular doesn't read those, but
 *      downstream apps do, and we want a *minimal* env to keep
 *      surprising imports out of the schema-generation import path.
 *
 *    - PYTHONPATH / PYTHONHOME from a poetry shell could shadow the
 *      installed package set.
 *
 *  All non-essential vars are stripped. Add a var here only with a
 *  comment explaining why it's part of the determinism contract.
 *
 *  If a future maintainer hits drift, run this script with DEBUG=1 and
 *  inspect which environment the spawned process saw.
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
	// `--validate` checks the file against the OpenAPI 3.0 JSON schema.
	// This is the gate we want: anything spectacular produces must be
	// valid OpenAPI, or CI fails.
	'--validate',
	// `--fail-on-warn` makes spectacular exit non-zero if it has
	// *anything* to say about the schema (missing descriptions, enum
	// naming collisions, etc.). That's a feature — those warnings have
	// caught real serializer problems before. Surface them to CI logs
	// via the explicit stderr separation below; don't suppress them.
	'--fail-on-warn',
	// Color is suppressed (CI logs are not a TTY and `--color` produces
	// raw ANSI escapes that pollute the log artifact).
];

// The minimal environment. Anything not listed here is *intentionally*
// absent — re-adding vars requires updating CI_CD_TROUBLESHOOTING.md
// with the reason.
const childEnv = {
	PATH: process.env.PATH || '/usr/bin:/bin',
	HOME: process.env.HOME || '/tmp',
	VIRTUAL_ENV: process.env.VIRTUAL_ENV || '',
	// Django configuration
	DJANGO_SETTINGS_MODULE: 'testimonies.settings',
	DJANGO_SECRET_KEY: 'spectacular-not-secret-discard-after-run',
	// Force the SQLite swap in backend/testimonies/settings.py. CI
	// also sets this; see the determinism contract above for why it
	// matters (BigIntegerField bounds are DB-dependent).
	USE_SQLITE: 'True',
	// Disable bytecode-cache writes — pyc files in the workspace
	// have shown up in diffs and confused the drift gate in the
	// past on shared CI caches.
	PYTHONDONTWRITEBYTECODE: '1',
	// PYTHONUNBUFFERED ensures spectacular's stderr shows up in
	// CI logs in real time, instead of being held in the stdio
	// buffer until the process exits.
	PYTHONUNBUFFERED: '1',
	// Locale — spectacular has historically emitted locale-sensitive
	// descriptions when LC_ALL was unset. Force C.UTF-8 for stability.
	LC_ALL: 'C.UTF-8',
	LANG: 'C.UTF-8',
};

if (process.env.DEBUG) {
	console.error('--- run-spectacular.js: child env ---');
	for (const [k, v] of Object.entries(childEnv)) {
		// Redact secrets even in debug mode.
		const display = k.includes('SECRET') || k.includes('KEY') || k.includes('PASSWORD')
			? '<redacted>'
			: v;
		console.error(`${k}=${display}`);
	}
	console.error('--- end child env ---');
}

// `stdio: ['ignore', 'pipe', 'pipe']` lets us split stdout and stderr
// so warnings are visible in CI logs WITHOUT failing on them at the
// Node layer (spectacular already exits non-zero for real warnings
// because of --fail-on-warn, so we don't double-fail).
const result = spawnSync(python, args, {
	cwd: join('..', 'backend'),
	env: childEnv,
	stdio: ['ignore', 'inherit', 'inherit'],
});

if (result.stderr && result.stderr.length > 0) {
	// Defensive: if a future spawnSync config accidentally inherits
	// stdio, surface stderr to the user with a clear separator.
	process.stderr.write('--- spectacular stderr ---\n');
	process.stderr.write(result.stderr.toString());
	process.stderr.write('--- end stderr ---\n');
}

process.exit(result.status ?? 1);
