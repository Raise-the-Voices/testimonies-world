# CI gate — operator setup

The blocking CI gate is wired in `.github/workflows/ci.yml` (new
`backend-pg` job) and `.github/workflows/deploy.yml` (concurrency +
`workflow_run` + production environment). These changes ship
mechanically; the items below must be done in the GitHub UI once, by
a repo admin.

## 1. Required secrets

Repo → Settings → Secrets and variables → Actions → New repository secret.

| Secret | Used by | How to generate |
|---|---|---|
| `CI_DJANGO_SECRET_KEY` | `backend-pg` job env | `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `CI_TESTIMONIALS_FERNET_KEY` | `backend-pg` job env | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |

Both are CI-only. They are not the production values — production
reads `SECRET_KEY` and `TESTIMONIALS_FERNET_KEY` from its systemd
EnvironmentFile. The CI values exist so the `backend-pg` job runs
with the same fail-closed posture as prod (missing key → `ImproperlyConfigured`).

If either secret is missing, the `backend-pg` job fails on import
with a clear error pointing at the missing name. That is the intended
behavior — a silent fallback would defeat the purpose.

## 2. Branch protection on `main`

Repo → Settings → Branches → `main` → Edit.

- ✅ Require a pull request before merging
- ✅ Require approvals: **1**
- ✅ Dismiss stale pull request approvals when new commits are pushed
- ✅ Require status checks to pass before merging
  - Add these required checks:
    - `backend` (existing SQLite job — fast feedback)
    - `backend-pg` (new Postgres + prod-config job)
    - `frontend-tests`
    - `frontend`
  - **Do NOT require** `audit` — Lighthouse is `continue-on-error: true`
    by design (H-7) and its score regressions are advisory.
- ✅ Require linear history
- ✅ Do not allow force pushes
- ✅ Do not allow deletions

Do **not** enable "Require signed commits" unless every contributor
has signing keys set up — that's a separate decision.

## 3. `production` GitHub Environment

Repo → Settings → Environments → New environment → name: `production`.

- **Deployment protection rules**:
  - ✅ Required reviewers: add at least 2 sudoers from the voluntask
    VM roster (`golda`, `peter`, `sia`, `marwan`). Two so one person
    can't single-handedly bypass a red CI during an outage.
  - Wait timer: leave at 0 (reviewers approve when ready).
- **Environment secrets**: add `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_KEY`,
  `DEPLOY_PORT` here (move from repo-level secrets). Environment-scoped
  secrets only exist for workflows that declare `environment: production`
  — `.github/workflows/deploy.yml` is the only such workflow today.

## 4. Emergency bypass

When CI is red during an active prod outage:

1. A required reviewer approves the queued `production` deployment in
   the GitHub Actions UI — this overrides the workflow_run gate by
   manually triggering `workflow_dispatch` (or by approving the
   held environment when the run reaches the reviewer).
2. Open an issue titled `postmortem: <one-line summary>` immediately
   after, linking to the red CI run. Don't fix it later — the audit
   log + GitHub audit event + issue are the postmortem trail.

## 5. Verification

After the UI changes above, push a no-op commit to a feature branch
and confirm:

- [ ] `backend`, `backend-pg`, `frontend`, `frontend-tests` all run
      green on the PR
- [ ] Merging the PR triggers `deploy.yml` exactly once (not twice
      from both `push` and `workflow_run` — the `if:` clause
      deduplicates them)
- [ ] The `production` environment shows the deployment in its
      history view
- [ ] Pushing directly to `main` with a known-red CI job is blocked
      by branch protection

If step 3 fires twice, the `if:` clause needs revisiting — likely
the `github.event.workflow_run.conclusion` check is wrong for the
first event shape.
