# Phase 8 verification report — 2026-09-30

**REPOSITORY READY FOR STAGING. CODE PREPARED. NOT DEPLOYED / NOT LIVE VERIFIED.**

## A. Starting repository/Git state

Repository: C:\Users\HDRBRND\Desktop\Web Workspace\accommodation. Clean starting tree, branch phase8/staging-deployment, HEAD 3bb4da4. Existing application DB version was 0005_property_region_write and remains there. All current changes are this task's uncommitted work. No commit/push/stash/reset/clean performed.

## B. Architecture chosen

Vercel frontend, Render Docker API, existing Supabase PostgreSQL candidate conditional on hosted compatibility, and one Render Cron Job. No Phase 9, new product metrics, microservices or runtime dependency additions. Existing JWT/membership/forced RLS contracts preserved.

## C. Repository changes

Added Dockerfile.prod, hosted runtime entrypoint, readiness service/route, explicit staging provision/verify commands, rollback-only hosted SQL gate, migration 0006 for PostGIS availability, CI, Render Blueprint and three runbooks. Updated environment examples, ignore rules, README, database/Auth/public-market docs and ADR-044–048. Added staging admission and safe hosted error/request logging with regression tests.

## D. Frontend staging preparation

Existing frontend/ Next.js application retained. Documented Vercel project root, monorepo lockfile access, Node/pnpm versions, public HTTPS origins and build-time variables. No frontend route/business logic or dev bundler change. No unnecessary vercel.json.

## E. Backend staging preparation

Production image built locally as stay-insight-api:phase8. Confirmed non-root UID, no /app/tests or /app/.env, pytest absent. Real entrypoint starts without reload; isolated image smoke test returned health 200 and readiness 503 for deliberately unavailable test DB. Missing hosted configuration exits 1 with a safe code. Temporary smoke container removed; local application services unchanged.

## F. Hosted DB compatibility result

Existing provider metadata: PostgreSQL 17.6, CREATEROLE available to postgres, not superuser; PostGIS available but not installed; app schema absent; no app roles. Hosted credentials/connection-path checks unavailable. **Hosted gate NOT PASSED**. SQL probe passed only on local test database, including RLS read/write denial, context reset and rollback; probe objects were confirmed absent afterward. This is not hosted evidence.

## G. Migration/security-role result

New test databases migrate base→head, downgrade→base and upgrade→head through existing integration fixtures. Forced RLS and restricted-role tests pass. Runtime and collector remain distinct; no broad grants to existing roles added. No hosted migration or login provisioning executed. New hosted provisioner fails closed and refuses existing login identities; actual provider execution remains pending.

## H. Supabase Auth staging configuration

Documented real staging Site URL/exact callback plus retained localhost callback. Staging UUID admission happens after signed JWT verification; rejected subject and expired token tests pass. No hosted Auth setting changed. Frontend protection and actual email journey pending.

## I. Remote scheduler decision

Render Cron only, existing command, 00:00 UTC / 09:00 KST daily, scoped collector and provider key. Blueprint prepared; scheduler not created or run. Cost approval required. Existing local automation untouched.

## J. CI result

Workflow prepared and YAML parsed with existing ESLint dependency (no install). Local equivalent checks pass. GitHub-hosted workflow has NOT run because changes were not committed/pushed. No deploy jobs, scheduled jobs or staging secrets in CI. Render YAML also parses; provider Apply validation is pending.

## K. Backup result

Manual staging pg_dump procedure documented, ignored/encrypted storage and source verification specified. Provider plan/backup entitlement not verified. **No staging backup taken.**

## L. Restore result

Full-schema app + separate Alembic version archives, required roles/PostGIS, disposable-only restore, counts/RLS/privilege verification documented. **No staging restore performed.**

## M. Rollback result

Manual previous-revision redeploy, schema compatibility gate, backups and disposable data recovery documented. PostGIS intentionally retained on migration downgrade. **No remote rollback exercised.**

## N. Automated tests actually run

| Check | Actual result |
| --- | --- |
| Frontend pnpm lint | Passed |
| Next route type generation + pnpm typecheck | Passed |
| Frontend pnpm test | 40 passed, 0 skipped |
| Isolated frontend pnpm build | Passed; nested imports/dashboard/market routes included |
| Backend uv run ruff check . | Passed |
| Backend uv run mypy app tests | Passed, 79 source files |
| Full pytest with actual PostgreSQL/PostGIS | 179 passed, 0 skipped; 2 dependency deprecation warnings |
| Production backend Docker build/image audit | Passed |
| Hosted entrypoint smoke/error handling | Passed locally with synthetic configuration |
| docker compose config --quiet | Passed |
| Rollback-only SQL probe on local test DB | Passed; no residual probe role/schema |
| CI/Render YAML parse | Passed; remote provider/workflow not executed |
| git diff --check; runbook links/fences | Passed |
| Tracked/new file secret scan | 215 files at scan time; no actual configured secret/private-key matches; values not printed |

Existing Starlette/httpx and anyio test-client deprecation warnings are not test failures; no dependency upgrades were added to this deployment task. No secret was committed; no commit was made at all.

## O. Docker/local regression result

backend/db/frontend all running and healthy. Local application DB remains 0005; no real local business-data writes or migrations. Authenticated browser displayed existing market and dashboard, CSV import form, reservations and import history without Next.js 404. One navigation timed out in the browser tool, but a later DOM check confirmed the dashboard loaded. These are read-only route checks, not a repeat of signup/create/import mutations. No UI redesign/accessibility changes; existing frontend tests cover labels/accessible tables. Full remote accessibility journey is pending.

## P. Live cloud resources actually created

None. Existing Supabase metadata was read only. Vercel connector returned no team target. No Render target/credentials or paid-resource approval available. No provider switch or local data upload.

## Q. Live staging URLs

None created or verified. localhost is not a staging URL.

## R. Live staging E2E actually verified

None. Checklist in [operations](staging-operations.md) remains pending, including remote scheduled success with the local PC off.

## S. Items requiring user action

Authorize commit/push separately; choose Vercel team/project and stable staging origin; securely provide hosted DB connection credentials in operator/provider configuration (never chat); select/approve Render web and Cron charges. Then apply the ordered deployment runbook. No credentials or purchase were requested merely to finish repository work.

## T. Unverified items

Actual hosted direct/session TLS/role semantics, PostGIS installation, migrations, role provisioning, deployment protection, CORS/email redirects, Render builds/health, remote CI, Cron success, staging backup/restore/rollback and remote E2E.

## U. Known limitations

Repository-ready is not a live private service. Backup entitlement and recovery objectives are unverified. Health checks are not full business acceptance tests. Existing Supabase Auth project may be shared with local development; distinct app DB and staging allowlist prevent automatic application membership, but a dedicated Auth project can be considered separately if stronger environment isolation is required. Never silently create one or switch providers.

## V. Exact next manual commands/UI actions

Follow [deployment](staging-deployment.md) in order: protected Vercel target and billing approval → private DB service → psql rollback-only compatibility gate → temporary admin DATABASE_URL / Alembic head → explicit restricted login provision → role/connection verification → manual Render API and Vercel deployments → exact Auth callback/CORS settings → one manual Cron run and daily schedule → remote E2E → actual staging backup/disposable restore. The runbook includes copyable PowerShell commands and exact dashboard settings. Do not jump directly to migration before the compatibility gate.
