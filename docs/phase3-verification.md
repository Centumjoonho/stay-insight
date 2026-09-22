# Phase 3 verification

Verified 2026-09-22 in C:/Users/HDRBRND/Desktop/Web Workspace/accommodation.

## Result

Implemented the generic owner CSV workflow: authenticated preview → explicit mapping → server validation → atomic import/upsert → property import history and filtered/paginated reservation list.

No Airbnb-specific format, Storage integration, dashboard KPI, expense, market data, benchmarking, billing, AI, synchronization or Phase 4 feature was added. No sample data was inserted into the application database. The existing Auth/public-origin code, Phase 2 migration and Docker volumes were preserved.

## Checks executed

Portable commands are shown below. On this host, Docker commands used the repository-local official standalone Compose client .tools/docker-compose.exe; host uv commands used the repository-local uv executable and the existing bundled Python runtime.

| Check | Executed command(s) | Result |
| --- | --- | --- |
| Backend lint | uv run --project backend ruff check backend; docker compose exec -T backend uv run ruff check . | Passed |
| Backend types | uv run --project backend mypy --config-file backend/pyproject.toml backend/app backend/tests; docker compose exec -T backend uv run mypy app tests | Passed, 40 files |
| Backend tests | docker compose exec -T -e TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/postgres backend uv run pytest --tb=short -q | 74 passed, including existing Phase 2 tests |
| Frontend lint | pnpm --dir frontend lint; docker compose exec -T frontend pnpm lint | Passed |
| Frontend types | pnpm --dir frontend typecheck; docker compose exec -T frontend pnpm typecheck | Passed |
| Frontend tests | pnpm --dir frontend test; docker compose exec -T frontend pnpm test | 18 passed, including interactive wizard and existing Auth redirects |
| Production build | docker compose run --rm --no-deps frontend pnpm build | Passed |
| Compose | docker compose config --quiet; docker compose up --build -d frontend backend; docker compose ps | Build/start succeeded; all three services healthy |
| Schema drift | docker compose exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic check | No new upgrade operations detected |
| Review | git diff --check; git diff --numstat; git diff of modified source; explicit new-file review | Passed; only expected Phase 3 changes |
| Browser/runtime | Isolated agent-browser session open/snapshot/get URL/errors/screenshot/close; HTTP requests to preview and callback | Home/health render; backend connected; protected import route returns localhost login; no browser errors; unauthenticated preview returns 401 |

Dependency commands: uv sync --project backend after adding python-multipart, and pnpm --dir frontend add -D --save-exact jsdom @types/jsdom. Lockfiles were updated. python-multipart is needed for multipart uploads; jsdom/types are development-only for real React event tests. No production frontend dependency was added.

Ruff format/fix was used on new Python modules and tests. Temporary migration-generation and verification tools remain ignored under .tools and are not application dependencies.

## Migration

Created backend/alembic/versions/0002_csv_imports.py, revision 0002_csv_imports, down_revision 0001_foundation. It contains standalone SQL for app.reservation_imports and app.reservations, composite tenant-safe foreign keys, uniqueness/check constraints, indexes, forced RLS and restricted grants.

Applied to the existing Docker database with:

~~~powershell
docker compose exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic upgrade head
docker compose exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic current
docker compose exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic check
~~~

Current revision: 0002_csv_imports (head). Before/after full-row digests of organizations, memberships and properties match. Isolated migration tests downgrade to 0001_foundation, verify existing property access, re-upgrade and import successfully. Original 0001 migration was not edited. No Docker volume was deleted.

## Test coverage

Backend tests cover UTF-8/BOM/CP949, malformed CSV, extension/size/row/cell limits, all required mappings, duplicate mapping/header/IDs, invalid dates and money, exact large KRW, derived nights, nullable net values, bounded errors, preview/validation without writes, successful imports, full-batch rejection, updates, duplicate checksums across scopes, concurrent duplicate requests, rollback after writes, filters/pagination, revoked memberships, direct restricted-role RLS and forged cross-tenant foreign keys.

Frontend tests render actual preview/mapping/result components, verify HTML escaping/formula text, exercise mapping requirements, assert multipart bearer/tenant headers and error handling, and drive the real wizard through file selection, preview, mapping, validation, acknowledgement, import and stale-state invalidation. The DOM test stubs only API responses and navigation; it is not a live Supabase end-to-end test.

## Significant files

| Files | Change |
| --- | --- |
| backend/app/importers/generic.py and __init__.py | Bounded CSV parsing, adapter contract, explicit normalization and safe row summaries |
| backend/app/models/imports.py; models/__init__.py | New import/reservation metadata registration and exact-money models |
| backend/app/schemas/imports.py | Typed preview, validation, import and reservation API responses |
| backend/app/repositories/imports.py | Organization-scoped reads/counts/updates, import lock, checksum lookup, batched PostgreSQL upserts |
| backend/app/services/imports.py | Property authorization, dry-run validation, transaction/savepoint orchestration and failed metadata |
| backend/app/api/v1/imports.py; api/upload_limit.py; main.py | Versioned endpoints and bounded multipart requests |
| backend/alembic/versions/0002_csv_imports.py | Additive Phase 3 migration |
| backend/tests/test_imports.py; test_config.py | New integration/unit tests and expected metadata update |
| backend/tests/fixtures/development-reservations.csv | Clearly marked development-only fixture, never auto-seeded |
| backend/pyproject.toml; uv.lock | Multipart parser dependency and pinned resolution |
| frontend/src/lib/api/import-types.ts; client.ts; server.ts; transport.ts | Import contracts, authenticated multipart calls, list reads and upload-specific timeout/errors |
| frontend/src/lib/imports.ts | Explicit mapping validation and multipart construction |
| frontend/src/components/import-wizard.tsx; import-views.tsx; reservation-table.tsx | Functional Korean wizard, safe preview/results and exact-money table display |
| frontend/src/app/(protected)/properties/[id]/imports/new/page.tsx | Property-scoped wizard route |
| frontend/src/app/(protected)/properties/[id]/imports/page.tsx | Paginated/filterable import history |
| frontend/src/app/(protected)/properties/[id]/reservations/page.tsx | Paginated reservation list with dates/channel/status filters |
| frontend/src/app/(protected)/properties/[id]/page.tsx | Links to new property workflows |
| frontend/tests/imports.test.ts; import-wizard.test.ts | Rendering, transport and interactive wizard regression tests |
| frontend/package.json; pnpm-lock.yaml | DOM testing dependencies only |
| AGENTS.md; README.md | Phase 3 contributor/setup pointers |
| docs/imports.md; api.md; database.md; architecture.md; product.md; phase3-verification.md | Implemented contracts, decisions, manual testing and this report |

## Remaining manual verification and limitations

No implementation/test/build failure remains. The two existing upstream Starlette/httpx and AnyIO test-client deprecation warnings remain. Authenticated browser-to-live-Supabase-to-API import was not performed with a real user account; this task did not receive login credentials or use the user's private session. The authenticated API path is covered against disposable PostgreSQL, and browser interactions are covered independently in jsdom.

Current records retain their latest import provenance; batch history retains checksum/mapping/actor/counts, not original files or all historical reservation field values. Imports are synchronous and limited to 5 MiB/10,000 rows. These documented limits are deliberate Phase 3 boundaries.

Use [the local manual test](imports.md#local-manual-test) and the development-only fixture at backend/tests/fixtures/development-reservations.csv. The stack is running at http://localhost:3000. Phase 4 was not started.

