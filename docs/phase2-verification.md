# Phase 2 verification

Verified on 2026-09-22 in C:/Users/HDRBRND/Desktop/Web Workspace/accommodation.

## Outcome

Implemented Supabase Auth, organization onboarding, memberships and property create/list/detail/update APIs with minimal Korean pages. Existing local PostGIS, three-service Compose architecture, Dockerfiles and database volume are retained. No Phase 3 features or production sample records were added.

FastAPI validates JWT signatures and resolves membership independently. Tenant queries carry organization predicates; restricted PostgreSQL roles and forced RLS provide additional isolation. Browser business requests use the dedicated FastAPI client. Authentication fixtures and identity overrides exist only in tests.

## Significant changes

| Files / area | Purpose |
| --- | --- |
| backend/app/core/auth/jwt.py; core/config.py | Supabase JWT verification and environment validation |
| backend/app/api/dependencies/tenant.py; db/context.py | Fresh membership checks, transaction-local identity/organization and unsafe runtime-role rejection |
| backend/app/models/foundation.py; schemas/foundation.py | UUID entities, constraints, request/response validation |
| backend/app/repositories/foundation.py; services/foundation.py | Scoped persistence, atomic/concurrent/idempotent onboarding and property rules |
| backend/app/api/v1/foundation.py; main.py | Versioned endpoints, CORS and private no-store responses |
| backend/alembic/versions/0001_tenant_property_foundation.py | Revision 0001_foundation: three tables, indexes, constraints, forced RLS and grants |
| backend/alembic/env.py; alembic.ini; app/db/base.py | Model metadata, app-schema-only autogeneration and Windows path support |
| backend/app/db/provision.py | Explicit local restricted-login provisioning; never runs at startup |
| backend/tests/test_auth.py; test_foundation.py | Cryptographic fixtures and real PostgreSQL security/migration/API tests |
| backend/tests/test_config.py; test_health.py | Configuration/model assertions and CORS coverage |
| frontend/src/lib/supabase/; src/proxy.ts | Auth clients, cookie refresh, verified claims and protected redirects |
| frontend/src/lib/api/; tests/api.test.ts | Central bearer transport, tenant header, timeout, no-store, error handling and typed contracts |
| frontend/src/components/ | Korean authentication, onboarding, property forms and sign-out |
| frontend/src/app/login/; signup/; auth/callback/ | Signup, login and PKCE confirmation callback |
| frontend/src/app/(protected)/ | Protected onboarding and property list/new/detail, loading/error states |
| frontend/src/app/page.tsx; globals.css | Entry link and minimal form styling |
| frontend/next-env.d.ts | Next.js-generated type references |
| frontend/package.json; pnpm-lock.yaml | Supabase SSR/client dependencies and lockfile |
| backend/pyproject.toml; uv.lock | PyJWT cryptographic verification dependency and lockfile |
| docker-compose.yml; .env.example files | Auth settings and restricted runtime connection; services preserved |
| AGENTS.md; README.md; docs/architecture.md; database.md; repository-structure.md | Phase 2 contracts and decisions |
| docs/authentication.md; api.md; phase2-verification.md | Setup, API reference and execution report |

Product documentation and historical bootstrap verification are unchanged. Empty Python initializers establish module boundaries.

## Commands and results

The host lacked docker on PATH. An official standalone Compose client under ignored .tools/docker-compose.exe connected to the existing engine. Commands below use the equivalent normal docker compose spelling. Tool downloads are development tooling, not application dependencies.

| Commands executed | Result |
| --- | --- |
| pnpm --dir frontend lint | Passed |
| pnpm --dir frontend typecheck | Passed |
| pnpm --dir frontend test | 7 passed |
| pnpm --dir frontend build | Passed |
| uv run ruff check . (backend directory) | Passed |
| uv run mypy app tests (backend directory) | Passed: 31 files |
| uv run pytest (backend directory, isolated host PostgreSQL configured) | 35 passed |
| docker compose config --quiet | Passed |
| docker compose up --build -d | Built; frontend/backend/db healthy |
| docker compose exec -T backend uv run ruff check . | Passed |
| docker compose exec -T backend uv run mypy app tests | Passed |
| docker compose exec -T -e TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/postgres backend uv run pytest --tb=short -q | 35 passed |
| docker compose exec -T frontend pnpm lint; typecheck; test (separate commands) | Passed; 7 tests |
| docker compose run --rm --no-deps frontend pnpm build | Passed; protected pages dynamically rendered |
| docker compose ps | All three healthy |
| docker compose exec -T db psql -U postgres -d stay_insight -c 'SELECT PostGIS_Version();' | PostGIS 3.5 |

Migration and provisioning commands executed:

~~~powershell
docker compose exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic upgrade head
docker compose exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight -e APP_DB_PASSWORD=stay_insight_local backend uv run python -m app.db.provision
docker compose exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic current
docker compose exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic check
~~~

Head is 0001_foundation. Alembic check detected no missing upgrade operations. Integration fixtures exercise upgrade → downgrade → upgrade in disposable databases. Application table counts remain organizations 0, memberships 0, properties 0. No volume was deleted.

Tests cover invalid/missing/expired JWTs, signatures/claims, atomic and concurrent onboarding, owner membership, property CRUD/validation, both membership roles, cross-tenant rejection, revoked membership, direct RLS enforcement, pooled context cleanup, forged bootstrap membership rejection and unsafe database-role rejection.

Browser verification used the running Docker frontend: homepage, health connected state, Korean login/signup configuration notices and anonymous protected-route redirects. Browser errors were empty.

## Review and remaining manual verification

This repository copy has no .git directory. A repository git diff was unavailable; existing source was captured in ignored .tools/baseline before edits and inspected with no-index comparisons and a source inventory. No Git repository or commit was created.

Two upstream test-client deprecation warnings remain (Starlette/httpx and AnyIO BlockingPortal). They do not fail tests. Automated tests do not contact live Supabase. Real email delivery, signup/login, session refresh and the complete authenticated browser journey remain unverified because project credentials were not supplied.

Follow [exact Supabase configuration steps](authentication.md#configure-supabase-manually), then [the complete live flow](authentication.md#verify-the-complete-live-flow). Set project URL/public publishable key, enable email signup/confirmation, allow http://localhost:3000/auth/callback, and use asymmetric signing keys. Restart/rebuild Compose after setting root .env. No service-role key is needed.

The Docker stack is left running for local use. Phase 3 was not started.

## Source file inventory


### Created

- .env.example
- backend/alembic/versions/0001_tenant_property_foundation.py
- backend/app/api/dependencies/__init__.py
- backend/app/api/dependencies/tenant.py
- backend/app/api/v1/foundation.py
- backend/app/core/auth/__init__.py
- backend/app/core/auth/jwt.py
- backend/app/db/context.py
- backend/app/db/provision.py
- backend/app/models/__init__.py
- backend/app/models/foundation.py
- backend/app/repositories/__init__.py
- backend/app/repositories/foundation.py
- backend/app/schemas/foundation.py
- backend/app/services/__init__.py
- backend/app/services/foundation.py
- backend/tests/test_auth.py
- backend/tests/test_foundation.py
- docs/api.md
- docs/authentication.md
- docs/phase2-verification.md
- frontend/src/app/(protected)/error.tsx
- frontend/src/app/(protected)/layout.tsx
- frontend/src/app/(protected)/loading.tsx
- frontend/src/app/(protected)/onboarding/page.tsx
- frontend/src/app/(protected)/properties/[id]/page.tsx
- frontend/src/app/(protected)/properties/new/page.tsx
- frontend/src/app/(protected)/properties/page.tsx
- frontend/src/app/auth/callback/route.ts
- frontend/src/app/login/page.tsx
- frontend/src/app/signup/page.tsx
- frontend/src/components/auth-form.tsx
- frontend/src/components/onboarding-form.tsx
- frontend/src/components/property-form.tsx
- frontend/src/components/sign-out.tsx
- frontend/src/lib/api/client.ts
- frontend/src/lib/api/server.ts
- frontend/src/lib/api/transport.ts
- frontend/src/lib/api/types.ts
- frontend/src/lib/supabase/client.ts
- frontend/src/lib/supabase/config.ts
- frontend/src/lib/supabase/server.ts
- frontend/src/proxy.ts
- frontend/tests/api.test.ts

### Modified

- AGENTS.md
- backend/.env.example
- backend/alembic.ini
- backend/alembic/env.py
- backend/app/core/config.py
- backend/app/db/__init__.py
- backend/app/db/base.py
- backend/app/main.py
- backend/pyproject.toml
- backend/tests/test_config.py
- backend/tests/test_health.py
- backend/uv.lock
- docker-compose.yml
- docs/architecture.md
- docs/database.md
- docs/repository-structure.md
- frontend/.env.example
- frontend/next-env.d.ts
- frontend/package.json
- frontend/src/app/globals.css
- frontend/src/app/page.tsx
- pnpm-lock.yaml
- README.md
