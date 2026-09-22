# Phase 2 authentication and local setup

Phase 2 uses hosted Supabase **Auth only**. Organizations, memberships and properties remain in the existing local PostgreSQL/PostGIS service. Neither the browser nor Next.js queries Supabase business tables. No Supabase service-role key, signing secret or backend API key is required.

## Authentication flow

The browser uses `@supabase/ssr` with `@supabase/supabase-js` for signup, password sign-in, session retrieval and sign-out. Cookies carry the session for App Router server rendering. `src/proxy.ts` refreshes/verifies claims and preserves refreshed cookies; server-side API helpers verify claims again before retrieving an access token for transport. Protected pages render dynamically and fetch with no shared caching.

All business requests go through `src/lib/api/` to FastAPI with `Authorization: Bearer <access_token>`. FastAPI independently verifies the signature using the configured project's JWKS. It allows RS256/ES256 only, checks issuer, audience, expiry, issued-at, authenticated role and UUID subject, and rejects anonymous sign-ins. A decoded header is used only for key selection, never authorization. Editable user metadata is ignored.

JWKS are fetched from `SUPABASE_URL/auth/v1/.well-known/jwks.json`, with a five-second timeout and bounded 300-second key-set cache. Unknown key IDs trigger the verification library's refresh behavior. Legacy HS256 projects must migrate to asymmetric signing keys; this application does not accept a shared signing secret. A valid-format request with missing Auth configuration/provider outage fails closed with 503. Missing, malformed, expired or invalid tokens return 401 and a Bearer challenge.

Membership is read fresh from PostgreSQL on every business request. Logout removes the browser session, but an already-issued access token can remain cryptographically valid until expiry. Membership removal immediately denies that organization's API access. User-account/session revocation beyond access-token expiry is not represented as immediate token invalidation.

## Routing and authorization

- Unauthenticated visits to `/onboarding` and `/properties/*` redirect to `/login`.
- Server page helpers repeat auth checks; a layout or Proxy alone is not the security boundary.
- Authenticated users without memberships go to onboarding.
- Onboarding redirects existing members to properties; login does not redirect automatically, preventing failure loops.
- Phase 2 UI uses the first membership returned by `/me`. The schema/API support multiple organizations; no invitations/member-management UI is implemented.
- Property APIs require `X-Organization-Id`. FastAPI verifies membership before setting transaction-local organization context.
- OWNER and MEMBER can create/read/update properties in their organization. Ownership cannot be reassigned in the request body.
- API 401 means sign in again; 403 means no membership. Foreign property IDs inside an authorized organization return 404 without disclosing existence.
- Both success and error API responses use `Cache-Control: private, no-store`.

## Configure Supabase manually

1. Create/select a Supabase project. Only Auth is used in this phase; do not migrate the Docker database to Supabase.
2. Enable Email/password authentication and account signups. Keep email confirmation enabled for realistic verification.
3. In Auth URL configuration set Site URL to `http://localhost:3000` and add `http://localhost:3000/auth/callback` to allowed redirect URLs.
4. Use the default confirmation template that honors the confirmation URL/redirect. Signup requests that callback explicitly; it exchanges the PKCE code, then opens onboarding. Open confirmation in the same browser that initiated signup. If a code/verifier is no longer available, sign in after confirming the email.
5. Under JWT signing keys, ensure an asymmetric RS256 or ES256 signing key is active. Do not copy its private key or a legacy JWT secret into this project.
6. Copy the project HTTPS URL and **publishable** key from the project connection/API settings. The optional legacy public anon key is supported as a fallback, but never use a service-role/secret key.
7. From the repository root, run the PowerShell copy commands below, then edit the blank public settings. Do not overwrite existing local configuration files blindly.

```powershell
Copy-Item .env.example .env
Copy-Item frontend/.env.example frontend/.env.local
Copy-Item backend/.env.example backend/.env
```

For Compose, edit root `.env`:

```dotenv
NEXT_PUBLIC_SITE_URL=http://localhost:3000
SUPABASE_URL=<your project HTTPS URL>
SUPABASE_PUBLISHABLE_KEY=<your public publishable key>
```

For host Next.js development, edit `frontend/.env.local`:

```dotenv
NEXT_PUBLIC_SITE_URL=http://localhost:3000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=<same project HTTPS URL>
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=<same public publishable key>
```

For host FastAPI development, edit `backend/.env`:

```dotenv
APP_ENV=development
DATABASE_URL=postgresql+psycopg://stay_insight_app:stay_insight_local@localhost:5432/stay_insight
CORS_ORIGINS=http://localhost:3000
SUPABASE_URL=<same project HTTPS URL>
SUPABASE_JWT_AUDIENCE=authenticated
```

The shown database credentials are local development defaults only. For a different password, provision it and change DATABASE_URL consistently. Compose injects values from root `.env`; it does not read the per-application files. Never set database credentials as NEXT_PUBLIC variables. Public frontend variables require restart/rebuild after changes.

## Start, migrate, and provision the local role

Run from the repository root, with Docker Desktop running Linux containers:

```powershell
docker compose config
docker compose up --build -d
docker compose exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic upgrade head
docker compose exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight -e APP_DB_PASSWORD=stay_insight_local backend uv run python -m app.db.provision
docker compose exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic current
docker compose ps
```

Migrations use the local administrator only for that explicit command. Normal API requests connect as `stay_insight_app`, a restricted login inheriting `stay_insight_runtime`. The API rejects a superuser, BYPASSRLS role, or application-table owner. The provision command is explicit and is never run on API startup. The health endpoint still works before migrations because it measures liveness.

Migration `0001_foundation` creates only the three requested tables under `app`, their constraints/indexes, and RLS/grants. It does not replace the PostGIS container, initialize a new production database, or remove any Docker volume. Never run `down -v` as a migration step.

For host commands, run Alembic from `backend/` using an administrator DATABASE_URL temporarily, provision the login, then restore the restricted runtime URL. Do not leave administrator credentials in the normal application environment.

## Verify the complete live flow

Open `http://localhost:3000/signup`, create an account, confirm the email, sign in, create a business organization, register a property, and open its detail page. Sign out and confirm protected pages redirect to login. Use a second account to confirm its property list is separate.

With missing Supabase settings, login/signup show a configuration message and disable submission. Protected routes redirect to login; health and homepage remain available. No placeholder credentials or development bypass exist.

## Automated verification

Tests never contact live Supabase. JWT tests generate signing keys and supply a local JWKS fixture; application tests override only the authenticated-user dependency in test code. PostgreSQL integration tests apply the migration to a uniquely named disposable test database and connect with a real restricted login. No SQLite replacement is used.

```powershell
docker compose exec -T -e TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/postgres backend uv run pytest
```

TEST_DATABASE_URL must be an administrator connection with permission to create/drop test databases and roles. Tests create only `stay_insight_test_<random UUID>` databases and random test logins, and clean up those resources. They do not drop the application database or volume. Missing TEST_DATABASE_URL fails the integration suite instead of silently skipping it.

For host tests, set TEST_DATABASE_URL to the same local administrator with host `localhost`, then run the documented root checks. Synthetic names/keys are confined to automated tests.

## References

- [Supabase SSR clients and verified claims](https://supabase.com/docs/guides/auth/server-side/creating-a-client?queryGroups=framework&framework=nextjs).
- [Supabase JWT verification](https://supabase.com/docs/guides/auth/jwts).
- [Next.js authentication and authorization guidance](https://nextjs.org/docs/app/guides/authentication).

Relevant documentation was checked during implementation. The Markdown changelog endpoint did not render in the documentation browser; no claim of a completed changelog audit is made.

## Public redirect origin

NEXT_PUBLIC_SITE_URL is the single public application origin for signup emailRedirectTo, callback success/failure redirects and Proxy login redirects. Locally set it to http://localhost:3000 in root .env (Compose) and frontend/.env.local (host development). Set the deployment origin in production. Origins with credentials, paths, queries/fragments or unspecified bind hosts are rejected; there is no request-origin fallback.

The callback previously resolved redirects against request.url, which Next.js constructed with its Docker bind host, producing http://0.0.0.0:3000/login. The bind address remains in dev/start commands only; redirect construction now uses the validated public origin. Keep Supabase Site URL and allowed callback URL aligned with this setting.

After changing the Compose environment, run docker compose up -d --force-recreate frontend. The development container runs next dev with mounted source, so an image rebuild is not required for the runtime fix. To include updated examples/tests in the image, use docker compose up --build -d frontend. A plain docker compose restart does not load changed Compose environment. Production next build must receive NEXT_PUBLIC_SITE_URL at build time; rebuild/redeploy after changing it because Next.js inlines public environment variables.

Regression tests cover signup URLs, actual callback route success/failure/missing-code branches, Proxy redirects and rejected bind-host configuration without contacting Supabase. A local HTTP request reproduced the original invalid Location header.
