# Phase 8 staging operations

Status: runbook/configuration prepared; no live deployment or remote scheduled run verified. See [deployment](staging-deployment.md) and [backup/restore](backup-restore.md).

## One remote scheduler

Choose Render Cron, reusing the same reviewed Docker image and existing command:

~~~text
python -m app.jobs.sync_accommodation_licenses
~~~

render.staging.yaml schedules 0 0 * * * in UTC, i.e. every day at 09:00 Asia/Seoul (UTC+9, no DST). The PC, Docker Desktop and Codex may be off. There is no GitHub scheduled ingestion workflow. CI only tests; no duplicate sync implementation or API trigger is added.

Cron receives only MARKET_DATABASE_URL (restricted collector), PUBLIC_ACCOMMODATION_API_KEY and APP_ENV=staging. It does not need the API runtime/admin connection. The existing command retains transaction-local ingestion role, advisory lock, pagination checks, atomic publication, failure audit and last-success preservation. The UI continues to show unavailable/stale public data honestly. Upstream source age is distinct from job execution time; daily collection is not real-time market demand.

Render allows one active invocation per job; scheduled executions wait for an active run, while a manual trigger cancels an active run. Inspect state before manual triggering. The database lock remains the second guard. The platform maximum run duration is 12 hours. A connection failure before a database transaction may prevent recording a sync row: in that case the nonzero job exit/log is the evidence. Do not claim every infrastructure failure has a database audit row.

Before creating resources, approve the billable web instance and Cron. Official Cron documentation states a minimum $1/month per job plus applicable usage; free web service limitations do not provide a free reliable Cron replacement. Confirm the selected web-instance price, regional availability, protection and database backup entitlements in dashboards. No charge was approved or incurred here.

## Daily operator check

1. Render API deployment and /api/v1/ready healthy; /api/v1/health is only liveness.
2. Last Cron exit 0, final safe status COMPLETED and recent persisted public_data_sync_runs success. ALREADY_RUNNING is not evidence of a successful refresh; inspect the other run.
3. Market UI source, last collection, reference-date availability and stale/coverage messages agree with stored public data. Never infer ADR/occupancy or competitor revenue from license registrations.
4. For failure: inspect Render job logs and sanitized failure code; check credentials, connection mode, upstream quota and timeout. Fix configuration, ensure no run is active, then trigger once. Preserve last good records; no destructive cleanup/full-table reset.

After the REMOTE scheduler is verified, disable the old local Codex automation for staging-purpose synchronization to avoid duplicate/confusing operation. Do not automatically delete it. A retained local-development-only schedule must point exclusively to local DB. Never point both schedules at staging.

## Logging and revision evidence

The hosted entrypoint logs startup environment/revision and a safe startup error code. Hosted HTTP logs contain route templates and response status; raw paths, query strings, bodies, CSV rows, JWTs and database exceptions are not emitted. Unexpected hosted exceptions return a generic 500. Development/test exception propagation remains unchanged. Render access logging is disabled in Uvicorn so callback/query credentials cannot leak through it; inspect provider-level logging settings too.

Review build/deploy logs in Render and Vercel dashboards. Do not paste entire environment output or provider request URLs. No external logging integration is added. DEPLOYMENT_VERSION may be set to a reviewed commit; Render's commit variable is the fallback. Keep API and Cron on the same approved revision; manual deployments are separate operations.

## Remote E2E acceptance checklist — pending

Use a new approved staging test user, two organizations and clearly labeled staging-only test records. Do not import local development fixtures or production customer data. Record actual results; all entries below are pending until remote execution:

- Protected HTTPS frontend and API; liveness/readiness; allowed-origin CORS and rejected unexpected origins.
- Signup email confirmation redirects to actual staging origin; login/logout/login; expired/invalid JWT rejected; a valid non-allowlisted user denied.
- Organization onboarding and property create/read; optional Busan sigungu selection/change/clear and unsupported code validation.
- Tenant A cannot read/update/import/list/count Tenant B records; revoked membership rejected. Test runtime role, not administrator.
- Small new staging CSV preview/commit, duplicate/idempotent retry, invalid CSV rollback; reservation list and imports history.
- Expense create/edit/delete and month boundaries; dashboard actual metrics/month comparison/channel totals with source labels; no unavailable denominator converted to misleading zero.
- Nested property/import/dashboard/market URLs resolve; market no-region/empty/stale states and collected official records remain separate from owner KPIs.
- Keyboard navigation, labeled controls, focus and accessible errors on the existing journeys.
- Manual remote sync COMPLETED; next scheduled invocation after local PC is off; no duplicated local staging job.
- Manual staging backup and disposable restore verification; previous revision redeploy exercise with schema compatibility check.

Local tests are supporting evidence, not proof of these external journeys.

## Rollback

1. Pause new writes and scheduled sync; record current deployment IDs, revision, Alembic head and take a STAGING backup.
2. For code-only incidents, redeploy the previously known-good API revision and matching Cron revision in Render; promote/redeploy the previous Vercel deployment with its matching public env. No automatic schema downgrade.
3. Phase 8 migration 0006 only ensures PostGIS and intentionally does not remove the shared extension on downgrade. Earlier schema and metric contracts stay unchanged. A previous API image must be tested against the current schema before rollback approval; this has not been exercised on staging.
4. For data/schema corruption, restore to a disposable target first using the backup runbook. Validate restricted roles/RLS, counts and application journeys; then plan an explicit cutover and credential changes. Never restore over a running staging DB or drop provider Auth schemas.
5. Recheck readiness/login/tenant isolation/dashboard/market, then resume the single scheduler. Record outcome and data-loss window. Do not claim a rollback validated merely because the procedure exists.

## CI and local development

.github/workflows/ci.yml runs validation for PRs and main/Phase 8 pushes. It installs pinned pnpm/uv, builds frontend and production backend image, and runs all backend tests with an ephemeral PostgreSQL/PostGIS service. It receives no staging secrets and does not deploy. Remote GitHub CI has not run for uncommitted changes; local equivalents are checked separately.

Existing local commands remain:

~~~powershell
docker compose up -d --build
# After frontend edits, rebuild image-copied source:
docker compose up -d --build --force-recreate frontend
~~~

If docker compose is unavailable, substitute .\.tools\docker-compose.exe. No volume deletion, route rewrite, development bundler change or backend port change is required. A production frontend build must run in an isolated container/workspace, not in the running dev .next directory.
