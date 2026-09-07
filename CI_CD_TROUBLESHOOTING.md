# CI/CD Troubleshooting

A runbook for when the GitHub Actions pipeline fails. Start at the top — most
failures are "wrong env, not wrong code."

The pipeline has three jobs in [`.github/workflows/ci.yml`](.github/workflows/ci.yml):

| Job | Catches | Does NOT catch |
|---|---|---|
| `frontend` | Type errors, build failures | Backend-specific issues |
| `backend`   | Django misconfig, migration drift, broken tests | Frontend type drift |
| `api-drift` | OpenAPI / generated TS out of sync | Pure code bugs |

If two jobs failed, the failures are **probably independent** — debug each
separately instead of assuming one caused the other.

---

## 1. Frontend job fails

### 1.1 `npm ci` fails (network / lockfile)

**Symptom**: error message containing `EINVALIDPACKAGECONTENT`,
`ETARGET`, or `lockfile doesn't match package.json`.

**Fix**:
1. Locally: `cd frontend && rm -rf node_modules && npm ci`.
2. If your `package-lock.json` is now different from the committed one,
   you or someone added a dep without locking it. `git diff
   frontend/package-lock.json` should be reviewed in the PR.

### 1.2 `npm run check` (svelte-check) reports errors

**Symptom**: CI log shows `N ERRORS M WARNINGS` with `N > 0`.

**Fix**: svelte-check has a tap-through schema. The first error blocks
correctness for any file that follows. Fix errors top-to-bottom — fixing
a downstream error often makes upstream errors disappear because the
type graph completes.

Warnings are noise from stylistic issues. They do NOT fail the job.

### 1.3 `npm run build` fails

**Symptom**: A Vite/Svelte build error message, e.g.
`Could not resolve ...` or `Unexpected token`.

**Fix**: Most build failures also show up as type errors in `npm run
check`. Fix them there first; the build's job is just smoke-testing.

---

## 2. Backend job fails

### 2.1 `manage.py check` fails

**Symptom**: An error from Django or DRF, e.g.
`ImportError`, `ImproperlyConfigured`, `SystemCheckError`.

**Fix**: Run it locally first:
```sh
cd backend
USE_SQLITE=True DJANGO_SECRET_KEY=dev python manage.py check
```

If the local run succeeds but CI fails, the env vars differ. The CI env
is in `.github/workflows/ci.yml` under `env:` for that step. Most
likely:
- `DJANGO_SECRET_KEY` not set (settings.py requires it)
- `USE_SQLITE=True` not set (Postgres connection fails on the runner)

### 2.2 `manage.py makemigrations --check --dry-run` reports new migrations

**Symptom**: Output ends with `Migrations for 'cases':` or similar.

**This is a workflow error, not an env error.** You changed a model
field and forgot to generate the migration. Fix:
```sh
cd backend
USE_SQLITE=True DJANGO_SECRET_KEY=dev python manage.py makemigrations
git add backend/<app>/migrations/
git commit -m "chore(<app>): migration for <model> change"
```

### 2.3 `manage.py test` fails

**Symptom**: A test failure traceback, ending in `FAILED (...)` and
`FAILED (errors=N)`.

**Fix**:
1. Check if the failure is reproducible locally:
   ```sh
   cd backend
   USE_SQLITE=True DJANGO_SECRET_KEY=dev \
     python manage.py test --keepdb --verbosity=2 <app>.tests.<TestCase>.<test_name>
   ```
2. If it's NOT reproducible locally, the test is using env-specific
   data — search the test file for `os.environ`, `config(...)`, or
   `random` calls. CI sets `USE_SQLITE=True` but most tests don't
   read env directly.
3. If reproducible, debug per the test's own conventions.

A test that takes > 60 seconds individually is doing too much — that's
a code smell and the author should refactor before debugging.

### 2.4 The test "passes" but takes 4+ minutes before finishing

**Symptom**: Job times out at the GitHub Actions default of 360
minutes. Or completes after a long time.

**Fix**: The `--keepdb` flag against an in-memory SQLite sometimes
holds on to a corrupted DB across tests. Add `--noinput` and
remove `--keepdb` for a one-shot debug. Long-term: convert the offending
test to use `pytest` fixtures which scope DB creation per-test.

---

## 3. API drift gate fails

This is the most common failure mode and the most diagnosable.

### 3.1 Read the diff in the CI log

The drift-gate job, on failure, prints the diff before exiting:

```
=== DRIFT DETECTED — diff above ===
Run `npm run gen:api` locally and commit the result.
```

The diff is git's standard unified format. Read each `+/-` block:

- **BigIntegerField bounds changed** (`±2^63` vs `±2^31`): you're
  generating against Postgres locally but CI uses SQLite.
  → Run with `USE_SQLITE=True` in the env. See [§ 3.4](#34-its-still-failing-after-regen).
- **Serializer field added/removed/renamed**: your edit is real;
  regenerate and commit.
- **Whole sections of `paths:` re-ordered**: someone added a
  `SORT_OPERATIONS`, `SCHEMA_PATH_PREFIX`, or other ordering-affecting
  key to `SPECTACULAR_SETTINGS`. Revert. See the
  `SPECTACULAR_SETTINGS` comment in `backend/testimonies/settings.py`.

### 3.2 If you DO want to commit a real change

This is the normal workflow:

```sh
cd /opt/shared/repos/testimonies-world  # or wherever the repo lives
cd frontend
npm run gen:api       # writes openapi.yml + src/lib/api/generated/

# inspect the diff
git diff -- openapi.yml src/lib/api/generated/

# commit only the regenerated artifacts, not your debug work
git add openapi.yml src/lib/api/generated/
git commit -m "feat(api): regenerate types for <serializer change>"

# the API drift gate passes once the artifact diff is in the commit
```

### 3.3 "I ran `gen:api` and it says exit 0, but CI still fails"

**Symptom**: Locally, `npm run gen:api:check` returns 0 and shows
no diff. CI fails the same gate.

**Cause**: Locally and CI saw different environments when generating.
Most common reasons:

| Local env | CI env | Difference |
|---|---|---|
| Dev `.env` says Postgres | SQLite | BigIntegerField bounds flip |
| `DEBUG=1` | `DEBUG` unset | Django loads dev-only debug views (rarely affects schema) |
| `PYTHONPATH` with extra paths | clean install | spectacular sees unexpected apps |
| Locale `*` (user's shell) | `C.UTF-8` (default in ubuntu-latest) | description strings reorder |

**Fix**: The
[`scripts/run-spectacular.js`](frontend/scripts/run-spectacular.js)
script now sets an explicit, minimal env for the spawned process. If
that script was bypassed (you ran `manage.py spectacular` directly),
you're seeing local-env output. Always regenerate through the script.

### 3.4 It's still failing after regen

**The "last resort" diagnostic flow.** Run these in order; the first
one that succeeds identifies the cause:

```sh
cd /home/aya/testimonies-world

# 1. Is the new SPECTACULAR_SETTINGS determinism contract intact?
diff <(git show HEAD:backend/testimonies/settings.py | \
       grep -E "^[A-Z_]+:'.*[A-Z]" | sort) \
     <(grep -E "^[A-Z_]+:'.*[A-Z]" backend/testimonies/settings.py | sort)
# Should be EMPTY. If anything prints, you changed a key.

# 2. Is your dev DB connection forcing the wrong backend?
unset PG_HOST PG_USER PG_PASSWORD PG_DB PG_PORT
unset DATABASE_URL USE_SQLITE
env | grep -iE 'postgres|sqlite|database' || echo "clean env"

# 3. Can you regenerate twice and get a bit-identical file?
USE_SQLITE=True DJANGO_SECRET_KEY=x \
  backend/.venv/bin/python backend/manage.py spectacular \
  --file /tmp/spec-1.yml --validate --fail-on-warn
USE_SQLITE=True DJANGO_SECRET_KEY=x \
  backend/.venv/bin/python backend/manage.py spectacular \
  --file /tmp/spec-2.yml --validate --fail-on-warn
diff -q /tmp/spec-1.yml /tmp/spec-2.yml
# Should print NOTHING (no diff).

# 4. Then run the actual CI gate end-to-end:
cd frontend && unset USE_SQLITE && unset DJANGO_SECRET_KEY
npm run gen:api:check; echo "EXIT=$?"
# EXIT=0 means you're good. EXIT=1 with a diff below means
# something in the script doesn't match what CI does.
```

If step 1 shows nothing AND step 3 is bit-identical AND step 4 still
fails, the divergence is in orval — almost always a non-deterministic
input it picked up. Run `npx orval --config ./orval.config.ts` twice
and diff the output dir; it should be identical.

---

## 4. Deploy fails

The deploy workflow (`.github/workflows/deploy.yml`) SSHes into the
prod VM and runs `scripts/deploy.sh`. Failures are usually one of:

| Failure | Cause |
|---|---|
| `git stash pop` conflicts | `backend/.env` or `testimonies/settings.py` drifted on the host. |
| `pip install` fails | Network to PyPI is restricted. Check `pip` error log. |
| `manage.py migrate` fails | A migration applied locally but not in the deploy commit. |
| `npm run build` fails | Subset of CI frontend failures; see § 1.3. |
| nginx `nginx -t` fails | Recent `scripts/nginx/rtv-cases` change has a syntax error. |
| Smoke test never gets `assets=200` | Static file serving is broken. Check the symlink under `build/server/chunks/client`. |
| Smoke test `/media/` returns 200 | The nginx `/media/` block wasn't applied (must return 401 unauth — Django-gated). |

For all of these, the deploy.sh writes a detailed diagnostic at the
end (the `DEPLOY FAILED:` section). That's the source of truth.

---

## 5. Preventive measures

These reduce the surface area of the failure modes above:

1. **Never bypass `scripts/run-spectacular.js`.** Running
   `manage.py spectacular` directly uses your dev env, which is
   almost never the same as CI.

2. **Pin dependency versions in lockfiles.** Both
   `frontend/package-lock.json` and `backend/requirements.txt` are
   committed; the `==` pins are deliberate.

3. **Commit `gen:api` output in the same PR as the serializer change.**
   Splitting the change across commits fails the drift gate on the
   intermediate state.

4. **If you add a `SPECTACULAR_SETTINGS` key, regenerate and commit
   the regenerated `openapi.yml` and `src/lib/api/generated/` in the
   same commit.** Don't leave them for a follow-up.

5. **No `:latest` or floating-version specifiers** in requirements
   files. Pin with `==`.
