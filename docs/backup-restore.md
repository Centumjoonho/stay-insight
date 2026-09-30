# Staging logical backup and disposable restore

**Status: procedure prepared; no staging backup exists from this task and no staging restore has been tested.** Never treat local-development dumps/tests as a staging backup. Do not upload the existing local DB. Follow the [deployment gate](staging-deployment.md) first.

## Backup coverage and prerequisites

Confirm Supabase plan, backup retention, last successful backup and any PITR entitlement in the project's Database Backups/Billing screens. Provider automatic backups were not verified. [Supabase backup documentation](https://supabase.com/docs/guides/platform/backups) describes plan-dependent coverage; do not assume it exists on this project. Storage objects and external Auth settings require separate provider recovery planning; the MVP app backup below is not a full Supabase project backup.

Use PostgreSQL 17 client tools for the current 17.x candidate, or a compatible newer pg_dump. Use direct or verified session-mode TLS connections. Prepare a private libpq service file and password file OUTSIDE the repo, with OS permissions limited to the operator. Set PGSERVICEFILE and PGPASSFILE privately. Define service stay_insight_staging_source for the confirmed hosted ADMIN source and stay_insight_restore_disposable for a NEW throwaway database. No passwords in command arguments or committed files. Never use the local development service as source.

Before running, independently confirm source host/database/project in the provider UI and disposable target identity. Set application writes quiet and pause Cron for a consistent counts manifest. Record UTC time, commit, Alembic version and aggregate table counts only; no owner/guest rows. pg_dump itself is transaction-consistent. Encrypt backups at rest, restrict access, retain a chosen short staging retention (initial proposal: 7 daily copies), and keep a protected off-machine copy. Retention/storage policy is not automatically configured by this task.

## Manual STAGING backup

Run from the repository root in PowerShell after configuring the private libpq services:

~~~powershell
$env:PGSERVICE = 'stay_insight_staging_source'
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
New-Item -ItemType Directory -Force -Path '.local-backups' | Out-Null
$stagingDump = Join-Path '.local-backups' "STAGING-$stamp.dump"
pg_dump --format=custom --no-owner --schema=app --file=$stagingDump
if ($LASTEXITCODE -ne 0) { throw 'Staging application backup failed; do not use partial output' }
# A schema filter excludes public.alembic_version, so capture it separately.
$versionDump = Join-Path '.local-backups' "STAGING-$stamp-version.dump"
pg_dump --format=custom --no-owner --table=public.alembic_version --file=$versionDump
if ($LASTEXITCODE -ne 0) { throw 'Staging version backup failed' }
pg_restore --list $stagingDump | Out-File ".local-backups/STAGING-$stamp-manifest.txt"
if ($LASTEXITCODE -ne 0) { throw 'Backup archive is unreadable' }
Get-FileHash -Algorithm SHA256 $stagingDump, $versionDump |
    Export-Csv ".local-backups/STAGING-$stamp-sha256.csv" -NoTypeInformation
~~~

Do not migrate between the two dumps. The app-schema archive includes application tables, data, constraints, policies and grants, but not global roles, provider auth/storage schemas or the shared PostGIS extension. The version archive captures Alembic's version table separately. Both are required. .local-backups/ and *.dump are ignored by Git; never attach dumps to issues/chat. Source credentials are not stored in these commands.

## Restore into a disposable target only

Provision an empty disposable PostgreSQL/PostGIS environment with a different database/project identifier; approve any cost first. Do NOT use the live staging service as destination. Use an administrator to prepare the two NOLOGIN group roles (stay_insight_runtime, stay_insight_ingestion) with NOSUPERUSER/NOBYPASSRLS and PostGIS. These are prerequisites because global roles/extensions are outside the app-schema dump. Runtime logins/passwords are newly provisioned after restore and are not copied from a dump.

For a fresh isolated disposable cluster, execute this prerequisite SQL through psql with ON_ERROR_STOP=1, then restore:

~~~sql
CREATE ROLE stay_insight_runtime NOLOGIN NOSUPERUSER NOBYPASSRLS;
CREATE ROLE stay_insight_ingestion NOLOGIN NOSUPERUSER NOBYPASSRLS;
CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA extensions;
~~~

~~~powershell
$env:PGSERVICE = 'stay_insight_restore_disposable'
# Independently confirm this service targets a NEW disposable database first.
pg_restore --exit-on-error --single-transaction --no-owner --dbname='service=stay_insight_restore_disposable' $stagingDump
if ($LASTEXITCODE -ne 0) { throw 'Disposable app restore failed' }
pg_restore --exit-on-error --single-transaction --no-owner --dbname='service=stay_insight_restore_disposable' $versionDump
if ($LASTEXITCODE -ne 0) { throw 'Disposable version restore failed' }
~~~

No --clean, DROP DATABASE or restore-over-live operation is provided. Keep ACL restoration enabled; using --no-acl would omit required grants. Restored objects are owned by the disposable administrator, never the runtime login. If roles already exist, inspect attributes/membership before reuse rather than issuing broad grants or overwriting identities. Do not run migrations over the target before this full-schema restore; that would conflict with archived objects.

## Required restore verification

Using only the disposable target:

1. Verify app schema, all nine expected application tables and public.alembic_version match the source manifest (currently 0006_postgis_availability).
2. Compare aggregate counts for organizations, organization_members, properties, reservation_imports, reservations, expenses, regions, public_accommodation_licenses and public_data_sync_runs while source writes were paused.
3. Confirm all six tenant tables have both ENABLE and FORCE RLS, original policies exist, runtime column grants are intact, and PostGIS is installed.
4. Provision fresh restricted runtime/collector logins through the documented staging provisioner in a disposable hosted staging target; verify readiness/role checks using its actual URLs. For a local disposable target use equivalent manually reviewed restricted logins: the hosted provisioner intentionally rejects local addresses.
5. Run missing-context/cross-tenant read/write tests, ingestion tenant-read rejection and pooled-context checks against disposable data. A successful administrator SELECT does not verify RLS.
6. Point an isolated application at the disposable target and perform login/property/dashboard/market checks using approved staging test subjects. No emails/scheduled imports/other external jobs should run unintentionally.
7. Record dump checksums, target identity, UTC times, versions, counts, privilege test results and verified recovery duration. Only then call this particular backup RESTORE VERIFIED. Dispose of the target only after explicit confirmation of its identity and evidence retention.

RPO/RTO have not been measured; a daily manual backup proposal implies up to roughly one day of data loss only if actually executed successfully every day. This task creates no backup scheduler. Do not promise disaster recovery based on a written runbook alone.
