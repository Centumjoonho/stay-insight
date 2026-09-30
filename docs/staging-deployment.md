# Phase 8: private staging deployment

Status (2026-09-30): **CODE PREPARED; no new cloud resources created, no deployment, no live staging verification.** Repository preparation does not complete the remote Phase 8 acceptance criteria. See [operations](staging-operations.md) and [backup/restore](backup-restore.md).

## Architecture and boundaries

Browser → Vercel Next.js (frontend/ root) → Render FastAPI Docker web service → existing Supabase PostgreSQL/PostGIS candidate. Supabase Auth remains the identity provider. One Render Cron Job invokes the existing public-data job. Vercel does not connect to business tables. No local application database, fixture or dump is uploaded. Create new explicitly identified staging test records through the application.

Use a separate Vercel staging project with a stable HTTPS origin. Enable its available Deployment Protection and verify that it covers the selected domain/alias; plan coverage varies. The API also requires STAGING_ALLOWED_USER_IDS (verified Supabase subject UUIDs). JWT signature, issuer, audience and expiry checks run first; organization membership and forced RLS continue independently. An empty staging allowlist denies access. Health/readiness contain no business data and remain public. CORS is not an access-control substitute.

Local Compose remains separate: localhost:3000, localhost:18000, backend:8000 internally; Webpack dev, image-copied frontend source and disabled polling. No local startup, database volume or fixture command changes.

## Hosted compatibility gate — NOT PASSED YET

Read-only provider metadata observed on the existing stay-insight Supabase project: PostgreSQL 17.6, postgres can create roles but is not superuser, PostGIS available but not installed, app schema absent, no existing Stay Insight roles. This is promising metadata, **not proof** that connections, grants, RLS or ingestion work. No hosted schema changes were made.

Obtain connection details privately from the Supabase Connect panel. Do not paste credentials into chat or Git. Prefer direct port 5432 when the operator and Render have IPv6 connectivity. If IPv4 is needed, evaluate the session pooler port 5432, using the exact host and role/project username given by the provider. Do not guess hostnames. The transaction pooler on 6543 is not selected; the hosted entrypoint rejects it. TLS sslmode=require is the minimum; prefer verify-full with the provider CA where supported. URL-encode passwords exactly once.

Before ANY Alembic migration, run ops/hosted-compatibility.sql through the proposed administrator connection using psql -X -v ON_ERROR_STOP=1. It transactionally probes role creation/membership, schema/table/grants, SET LOCAL ROLE, forced RLS with tenant context and PostGIS creation, then rolls everything back. Require successful exit, context_reset=true and empty_app_schema=true. Inspect that no probe role/schema remains. Run it using the proposed connection path from the deployment/operator network; testing a local superuser is not hosted evidence.

With the private libpq service configured as described in the backup runbook, run from the repository root:

~~~powershell
psql -X -v ON_ERROR_STOP=1 --dbname='service=stay_insight_staging_source' --file=ops/hosted-compatibility.sql
if ($LASTEXITCODE -ne 0) { throw 'Hosted compatibility gate failed; do not migrate' }
~~~

Check both boolean results as well as the exit code. Do not proceed with empty_app_schema=false.

If the gate fails, stop hosted bootstrap and record the failed capability. Do not weaken permissions or switch providers. A separately approved dedicated PostgreSQL/PostGIS host is an alternative, not an automatic fallback.

## Environment ownership

| Location | Variables | Policy |
| --- | --- | --- |
| Vercel staging | NEXT_PUBLIC_SITE_URL | Exact stable frontend HTTPS origin, no path/trailing slash |
| Vercel staging | NEXT_PUBLIC_API_BASE_URL | Exact external Render HTTPS origin, no /api/v1 suffix |
| Vercel staging | NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY | Same Auth project as backend; public publishable key only |
| Vercel staging | NEXT_PUBLIC_SUPABASE_ANON_KEY | Legacy public anon fallback only if needed |
| Vercel staging | API_INTERNAL_BASE_URL | Leave unset to use public API base; never backend:8000 |
| Render API | APP_ENV=staging, DATABASE_URL | Restricted stay_insight_app login with TLS |
| Render API | SUPABASE_URL, SUPABASE_JWT_AUDIENCE=authenticated | Public Auth origin; no signing/service key |
| Render API | CORS_ORIGINS | Exact staging frontend origin; comma-separated exact origins if necessary |
| Render API | STAGING_ALLOWED_USER_IDS | Comma-separated approved test subject UUIDs; no editable user metadata |
| Render API | DEPLOYMENT_VERSION | Optional safe revision label; RENDER_GIT_COMMIT is fallback |
| Render Cron | APP_ENV=staging, MARKET_DATABASE_URL | Separate restricted collector login with ingestion membership |
| Render Cron | PUBLIC_ACCOMMODATION_API_KEY | Backend job secret only |
| One-time operator | MIGRATION_DATABASE_URL | Administrator connection; never API/Cron/Vercel |
| One-time provisioner | APP_DB_PASSWORD, INGESTION_DB_PASSWORD | Distinct generated passwords, at least 24 characters |

No secret/service-role key, database URL, JWT secret or MOIS key belongs in NEXT_PUBLIC_* variables. Public Next.js variables are build-time values: redeploy after changes. Provider secret fields/password-manager injection are preferred; do not put credentials on command lines. Examples contain placeholders only. Local example credentials remain explicitly local defaults.

## Ordered bootstrap and deployment

1. Review the working changes and authorize commit/push separately. This task does not commit/push. Cloud Git builds cannot see uncommitted files. Obtain user approval for Render web service and Cron charges before creating resources.
2. Choose the Vercel team/project and stable domain; prepare a staging-only project rooted at frontend/. Use Next.js detection, Node 24, pnpm 11.19.0, frozen install, pnpm build, default Next.js output. Include files outside Root Directory so the root pnpm workspace/lockfile is available. No custom vercel.json is necessary. Avoid connecting preview deployments to shared staging writes unintentionally; use only approved origins and protected staging access.
3. Obtain private hosted connection credentials and pass the compatibility gate above. Verify this is an empty APPLICATION schema on the intended project. Existing Auth users are not application rows and must not be copied from local DB.
4. In a trusted operator shell, install uv dependencies with uv sync --project backend --frozen. Run the following PowerShell with MIGRATION_DATABASE_URL already securely injected. Alembic still reads DATABASE_URL; the assignment is temporary, not API configuration:

~~~powershell
$previousDatabaseUrl = $env:DATABASE_URL
try {
    $env:DATABASE_URL = $env:MIGRATION_DATABASE_URL
    uv run --project backend alembic -c backend/alembic.ini upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'Staging migration failed' }
    uv run --project backend alembic -c backend/alembic.ini current
    if ($LASTEXITCODE -ne 0) { throw 'Version check failed' }
} finally { $env:DATABASE_URL = $previousDatabaseUrl }
~~~

Run from repository root. Expected head: 0006_postgis_availability. Earlier schema migrations are unchanged; 0006 installs PostGIS if absent and preserves an already installed extension. Empty bootstrap includes the existing normalized Busan region references, never demo owner data. Do not use a Supabase dashboard migration chain. Protect operator error logs; never share connection exceptions unredacted.

5. Provision two fresh restricted logins AFTER migrations, using a trusted operator shell with APP_ENV=staging, MIGRATION_DATABASE_URL, APP_DB_PASSWORD, INGESTION_DB_PASSWORD and CONFIRM_STAGING_PROVISION=yes injected privately:

~~~powershell
uv run --directory backend python -m app.db.provision_staging
~~~

The command is transactional, refuses existing logins, and creates only stay_insight_app → stay_insight_runtime and stay_insight_collector → stay_insight_ingestion. It never resets an existing user's password. Runtime owns no tables and has no migration privileges; collector does not receive runtime membership. Remove provisioning inputs from the shell when finished. Reruns require inspection, not dropping live roles.

6. With the actual restricted DATABASE_URL and MARKET_DATABASE_URL temporarily injected in a trusted shell, APP_ENV=staging:

~~~powershell
uv run --directory backend python -m app.db.verify_staging
~~~

Require STAGING_ROLE_AND_CONNECTION_CHECKS_PASSED. This checks forced RLS/grant readiness, missing-user row suppression, pooled transaction context reset and ingestion separation on the chosen connection mode. Repeat from the Render network before allowing real use. Never leave both URLs or administrator credentials on the API service.

7. After cost approval, review render.staging.yaml in Render Blueprints. It creates one Docker web service and one Cron Job, each using backend/Dockerfile.prod and explicit/manual deploys. Use the chosen branch and same reviewed commit. Current plan placeholder 0.5c-512mb is billable: confirm dashboard price and region before Apply. No hosted resources were created by this task. There is no automatic migration/pre-deploy command.
8. Populate each service's separate secrets from the table. Build/deploy the API only after migration and role checks. Confirm /api/v1/health returns 200 with status ok and /api/v1/ready returns 200 with status ready. A bad hosted configuration exits safely; an unreachable/unsafe DB yields readiness 503. Server binds 0.0.0.0:$PORT only internally. No reload, one non-root Uvicorn process, no fixtures/dev dependencies in the image.
9. Add Vercel public env values, deploy, then configure Supabase Auth URL Configuration: Site URL = actual stable staging HTTPS origin; Redirect URLs include that origin + /auth/callback AND http://localhost:3000/auth/callback. Preserve existing necessary localhost entries. Do not add 0.0.0.0 or broad wildcard redirects. Configure approved staging test UUIDs on the API; register/confirm new test users through normal Auth flow as needed. Confirm email returns to staging, not localhost or container bind address.
10. Manually trigger the Render Cron only after the restricted ingestion check. Require exit 0 and COMPLETED in its safe result and persisted sync record; confirm the market page source/freshness. Enable daily operation and run the remote E2E/backup exercises in the linked runbooks.

## Verification status and release gate

Repository tests are reported separately in the completion report. Hosted direct/session authentication, full compatibility probe, migration, role provision, TLS from Render, Auth redirects, Vercel protection, scheduled run, external E2E, staging backup/restore and actual rollback remain UNVERIFIED until performed against real staging. No live URLs are claimed. Vercel connector returned no available team target; Render target/credentials and billing approval were unavailable. Supabase metadata access does not supply private database passwords.

Do not label Phase 8 LIVE VERIFIED until every remote acceptance step is recorded with UTC time, reviewed commit, environment identifier and sanitized result.

## Platform references checked

- [Render Blueprint fields](https://render.com/docs/blueprint-spec)
- [Render Cron pricing, UTC scheduling and concurrency](https://render.com/docs/cronjobs)
- [Supabase connection modes](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Supabase database roles](https://supabase.com/docs/guides/database/postgres/roles)
- [Vercel monorepos](https://vercel.com/docs/monorepos)
- [Vercel deployment protection](https://vercel.com/docs/deployment-protection)
- [FastAPI Docker guidance](https://fastapi.tiangolo.com/deployment/docker/)
