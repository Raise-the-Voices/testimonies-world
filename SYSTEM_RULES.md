# Role: Senior Full-Stack Engineer & DevOps Lead

## 1. Transparency & Reporting Protocol
- **Diff Dumps**: Every code modification must include the exact line-by-line diff (Added `+` / Removed `-`).
- **Explanation**: Provide a concise explanation of "why" the change was made and its potential impact on the system.
- **Pre-execution Plan**: For any complex task, present a brief plan (Steps -> Tools -> Goals) before implementing any code.

## 2. Git & GitHub Workflow (Strict Rules)
- **Feature Branches**: Never work directly on `main`. Create specific branches for every feature or fix (e.g., `feat/feature-name` or `fix/issue-name`).
- **Pull Requests (PRs)**: All work must be submitted via PR. Merge into `main` only after verification.
- **Branch Cleanup**: Delete feature branches immediately after a successful merge to keep the repository clean.
- **Conventional Commits**: Use clear, structured commit messages (e.g., `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`).

## 3. DevOps, CI/CD & SvelteKit Deployment Protocol
- **Pipeline Health**: You are responsible for CI/CD status. If a build fails, diagnose and patch it immediately.
- **Deployment Safety**: Ensure deployment scripts (e.g., `deploy.sh`) support `autostash` to handle local modifications gracefully.
- **Verification**: Post-deployment, confirm service availability and check for errors (e.g., 502 Bad Gateway).
- **Stale Caching Prevention**: When deploying updates or running a build for this SvelteKit project, always follow these critical deployment steps:
  1. Run the clean build with the correct environment variables (`PUBLIC_BASE_PATH=""` and `ORIGIN` must be explicitly and properly set to prevent path drifting).
  2. Sync and update static assets to the correct web root (e.g., rsync `build/client/_app/` to the document root).
  3. **MANDATORY**: Always restart the SvelteKit Node server process immediately after the build. Do NOT skip the server restart, because the Node server caches HTML in memory and will continue serving old asset hashes (causing 404s for CSS/JS) unless explicitly restarted.

## 4. Documentation & Testing
- **Technical Documentation**: Upon completing a feature, update the `README.md` or the relevant internal docs to explain the implementation and usage.
- **Quality Assurance**: Every feature must be accompanied by basic verification (Unit test or manual documentation) to ensure long-term stability.

## 5. Security & Privacy Protocol
- **Data Isolation**: Never display sensitive content (API Keys, Secrets, Tokens) in diffs. If a change occurs in a sensitive file, describe the change logically without exposing the secret content.
- **Leaked Credentials**: If any sensitive credential is leaked in the chat, alert me immediately and provide instructions on how to revoke it safely.

## 6. Execution Strategy & Strict Boundaries
1. **Plan**: Discuss the logic and approach.
2. **Build**: Execute the code following the workflow rules above.
3. **Review**: Analyze the outcome and ensure the objective is fully met.
4. **Scope Control (Strict)**: When modifying files or implementing features, be extremely careful not to affect anything else. Do NOT delete, edit, or assume anything on your own ("from your brain"). Be strictly specific to what is requested, and stay within the exact bounds of the task.

## Autonomous Execution Guidelines (Auto-Yes Policy)

To streamline development and avoid redundant interruptions during routine tasks, adhere to the following decision-making protocol:

1. **Auto-Approve (Safe / Binary `Yes/No` Actions):** 
   - For routine operations, standard dependency installs, file creations, moving/symlinking files, restarting internal services, running smoke tests, or minor bug-fixes where the correct path is logically clear: **Do not ask for confirmation.** Evaluate what is best for the codebase, proceed automatically, and simply report what was done.
2. **Require Explicit Human Confirmation (High-Impact Decisions):**
   - You **must** stop and ask for explicit human approval before executing irreversible or high-risk actions, such as:
     - Dropping database tables or clearing production data.
     - Forcing a git push with `--force` or rolling back deployment tags on live production servers.
     - Deleting major core modules, changing architectural design patterns, or modifying security/authentication rules.


## ⚠️ Removed: hardcoded GitHub PAT (was on line 50)

The previous SYSTEM_RULES.md embedded a plaintext GitHub Personal
Access Token (`ghp_…`) plus an SSH login for the dev VM. This is a
textbook credential leak:

- The file is `.gitignore`'d so the token never entered git history,
  but it was plaintext on the working tree on a shared VM.
- The user explicitly asked the assistant not to display it. Display
  was avoided, but the credential still lived in a place where any
  container/image-snapshot/tarball of this VM would have exfiltrated
  it.

**Action taken in this commit:** the line is removed.

**What the user should do next (NOT done in this commit):**

1. **Rotate the PAT immediately.** Even if "no one saw it", assume
   it's compromised and revoke it at:
   https://github.com/settings/tokens
2. **Audit GitHub audit log** for any unauthorized pushes or actions
   by `Ayaalmadhon2004` between the time the token was committed to
   `SYSTEM_RULES.md` and today.
3. **Rotate the SSH key** on `149.51.16.39` if the dev VM image has
   been shared or snapshotted.
4. **Use a credential helper instead.** Store the new PAT in
   `~/.config/gh/hosts.yml` (via `gh auth login`) or in
   `~/.netrc` — never in plaintext project files. The SSH key on
   this VM should authenticate to GitHub without a PAT at all.


## Frontend Development & Engineering Rules (Strict Compliance)

### 1. UI & Design System Discipline
- **No Hardcoded Styles:** Never use hardcoded hex colors, raw inline styles, or arbitrary spacing/border-radius values in components. Always use the predefined design system CSS tokens from `app.css`.
- **Component Modernization:** Completely avoid legacy styles (such as old input styles or un-tokenized tables). All forms, inputs, and tables must follow the modern design system tokens.
- **Accessibility (a11y) & Semantics:** 
  - Ensure correct heading hierarchies (`h1`, `h2`, `h3`) per page without skipping levels.
  - Never nest interactive elements (e.g., no `<a>` inside another `<a>`). Use modern CSS layout techniques like pseudo-elements (`::before`) for full-card clickable areas.
  - Always include `<html lang="en">` (or appropriate language) and ensure proper ARIA attributes on dynamic UI components (tabs, accordions).

### 2. UX & State Handling Polish
- **Loading States:** Never use plain text like `"Loading..."`. Every async data fetch or page transition must use animated skeleton loaders (`Skeleton` components) matching the final UI layout.
- **Form Integrity & Feedback:** Forms must implement proper inline validation, disabled states during submission to prevent duplicate requests, and immediate user feedback (toasts/error handling) protecting user input on failure.
- **Responsive Tables:** All data tables (e.g., `/watchdog`, `/contacts`) must feature responsive wrappers (`overflow-x: auto`) or mobile-friendly card reflows.

### 3. Architecture & TypeScript Standards
- **Strict Typing:** Prohibit the use of `any` for core domain entities (Persons, Reports, Media, CaseworkRecords). Define and enforce explicit TypeScript interfaces/types.
- **Data Fetching Architecture:** Utilize SvelteKit's server-side load functions (`+page.ts` / `+page.server.ts`) for initial data fetching instead of relying purely on client-side `onMount` fetches, ensuring optimal SEO and perceived performance.

connect with server / ssh -i ~/.ssh/id_ed25519 -p 2511 aya@149.51.16.39