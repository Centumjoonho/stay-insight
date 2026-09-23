# Phase 4 verification

Verified 2026-09-23 in C:/Users/HDRBRND/Desktop/Web Workspace/accommodation.

## Result

Implemented property-level manual expense CRUD, period/category/type filtering, pagination,
explicit fixed/variable selection, Korean UI, source-separated known-cost summary and confirmed
physical deletion. FastAPI remains authoritative; no business-table requests bypass it.
No Phase 5 KPI/profit functionality, dependencies or fee-copying model was introduced.
Webpack development, authentication, earlier migrations and Docker volumes are unchanged.

## Checks and commands executed

The host uses the existing official standalone Compose client .tools/docker-compose.exe.
Below, docker compose is the equivalent portable spelling. Commands were run from the repository
root. No runtime-role migration privileges were granted.

| Check / command | Final result |
| --- | --- |
| docker compose exec -T backend uv run ruff check . | Passed |
| docker compose exec -T backend uv run mypy app tests | Passed, 46 files |
| docker compose exec -T -e TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/postgres backend uv run pytest --tb=short -q | 97 passed; 2 existing upstream test-client warnings |
| docker compose exec -T frontend pnpm lint | Passed |
| docker compose exec -T frontend pnpm typecheck | Passed after fresh dev metadata |
| docker compose exec -T frontend pnpm test | 23 passed |
| docker compose run --rm --no-deps frontend pnpm build | Passed; all three expense routes included |
| docker compose config --quiet | Passed |
| docker compose up --build -d --no-deps --force-recreate frontend | Rebuilt/recreated successfully |
| docker compose up -d --no-deps --force-recreate frontend | Regenerated malformed transient development metadata |
| docker compose ps | Frontend/backend/db healthy |
| git diff --check; git diff --stat; git status --short | Reviewed, no whitespace errors |
| git diff of existing migrations and frontend/package.json | Empty; unchanged |

Additional development commands: targeted ruff check --fix and ruff format for new Python files;
frontend/backend container logs; PostgreSQL psql row-count/digest queries before/after migration.
New untracked source files were read explicitly as well as reviewing tracked diffs.
Source files were checked as UTF-8 and local documentation links checked.

Migration commands executed:

~~~powershell
docker compose exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic upgrade head
docker compose exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic current
docker compose exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic check
~~~

Head: **0003_expenses**. No new upgrade operations detected. Before/after full-row digests and
counts of organizations, memberships, properties, imports and reservations matched. No manual
expenses were seeded into the application database. The backend's existing source mounts loaded
the Python changes; no backend image or database recreation was necessary.

## Test coverage and browser verification

Backend tests cover creation, zero/exact large amounts, invalid/fractional/nonfinite amounts,
category/type/date/memo validation, client ownership/source spoofing, missing/foreign properties,
list ordering, pagination and filters, patch validation, owner/member deletion, repeat deletion,
cross-tenant reads/writes/list/summary denial, revoked membership, direct restricted-role RLS
and pooled-context reset, schema constraints and immutable ownership grants.

Summary tests cover fixed/variable/manual/category/type totals, inclusive date boundaries,
cross-month check-in attribution, missing versus reported-zero fees, cancelled/unknown statuses,
empty periods, separation of sources and no synthetic fee rows/double counting.
The entire existing Phase 1–3 suite passes, including JWT and CSV import/upsert tests.

Migration tests execute upgrade/downgrade/re-upgrade in uniquely named disposable PostgreSQL
databases and specifically verify Phase 3 imports/reservations survive downgrade to 0002 and
subsequent upgrade. The live database was only upgraded.

Frontend tests exercise actual React create/edit/delete flows in jsdom, explicit selection,
cancel and failed/successful delete confirmation, API context/transport, refresh behavior,
exact amounts above JavaScript's safe integer limit, escaped memos, rendered source/coverage
labels, 204 handling, safe 401/403 errors, Seoul year/month/leap-year boundaries and filter queries.

Authenticated live Chrome verification used an existing property. Property navigation, expense
list/summary, new form, FIXED/date-filtered view and the existing import wizard rendered.
The real September fee summary showed 20,000원 with one reported fee and one missing fee;
those values came from existing imported reservations, not fixtures.
Korean labels and accessible labels/headings/table headers were inspected in browser state.

Create/edit/delete mutations were tested through real FastAPI/restricted PostgreSQL in disposable
databases and through the real React components with stubbed transport in jsdom. They were NOT
submitted through the live user's browser; no invented manual costs were inserted into that property.
The exact live manual mutation scenario remains available in [expenses.md](expenses.md#exact-local-manual-test).

## Significant file inventory

| Files created | Responsibility |
| --- | --- |
| backend/alembic/versions/0003_expenses.py | Additive expense schema, constraints, index, forced RLS and restricted grants |
| backend/app/models/expenses.py | Expense persistence model and category/cost-type enums |
| backend/app/schemas/expenses.py | Exact amount/request validation and typed response/summary contracts |
| backend/app/repositories/expenses.py | Explicitly scoped persistence, pagination and SQL aggregation |
| backend/app/services/expenses.py | Property authorization, CRUD orchestration, period validation and summary assembly |
| backend/app/api/v1/expenses.py | Versioned HTTP endpoints; static summary before UUID detail |
| backend/tests/test_expenses.py | New expense/security/summary/migration regression tests |
| frontend/src/lib/api/expense-types.ts | Expense transport contracts and Korean category/type labels |
| frontend/src/lib/expenses.ts | Client validation, Seoul month defaults, query validation and exact formatting |
| frontend/src/components/expense-form.tsx | Shared create/edit form |
| frontend/src/components/expense-delete.tsx | Explicit confirmation, delete request and refresh |
| frontend/src/components/expense-views.tsx | Read-only source-separated summary and manual expense table |
| frontend/src/app/(protected)/properties/[id]/expenses/page.tsx | Protected property list/summary/filter/pagination page |
| frontend/src/app/(protected)/properties/[id]/expenses/new/page.tsx | Protected creation page |
| frontend/src/app/(protected)/properties/[id]/expenses/[expenseId]/edit/page.tsx | Protected editor with property/expense association check |
| frontend/tests/expenses.test.ts | Validation/date/format/render/transport tests |
| frontend/tests/expense-interactions.test.ts | Real React creation, editing and deletion interactions |
| docs/expenses.md | Model, categories, security, source/date rules, operations and manual test guide |
| docs/phase4-verification.md | This verification report |

| Files modified | Change |
| --- | --- |
| backend/app/main.py | Register expense routes and allow DELETE in existing CORS policy |
| backend/app/models/__init__.py | Register Expense metadata for Alembic |
| backend/tests/test_config.py | Include expenses in expected model metadata |
| frontend/src/lib/api/client.ts | Centralized create/update/delete expense calls |
| frontend/src/lib/api/server.ts | Centralized expense detail/list/summary reads |
| frontend/src/lib/api/transport.ts | Handle empty 204 delete responses and expense-specific 404 message |
| frontend/src/app/(protected)/properties/[id]/page.tsx | 비용 관리 navigation |
| AGENTS.md | Current Phase 4 domain/document pointer |
| docs/api.md | Expense endpoint contract |
| docs/database.md | Implemented Phase 4 table, RLS and grant contract |
| docs/architecture.md | ADR-027 through ADR-030 |
| docs/product.md | Explicitly supersede proposed manual OTA commission entry and defer profitability |

## Assumptions and remaining limitations

- Fixed/variable is always user-selected; no category inference.
- Fees use inclusive check-in dates and all recorded statuses. No actual-stay/refund inference.
- Missing fees stay unknown and are disclosed. Known costs are not proof of complete costs.
- List category/type filters do not narrow summary cards; the UI states this.
- Physical deletion has no recovery/history; creator and timestamps describe extant rows only.
- Enum exclusion and UI warnings cannot prevent a user intentionally mislabeling an OTA fee as OTHER.
- No live-browser expense mutation or exhaustive accessibility audit was performed. Automated
  component/API/tenant tests and read-only live browser verification passed.
- Two upstream Starlette/httpx and AnyIO deprecation warnings persist.
- One development run produced malformed .next/dev/types/routes.d.ts and omitted nested routes,
  even under Webpack. Recreating only the frontend regenerated it; typecheck and live routes then
  passed. This was a transient dev-metadata failure, not resolved by weakening routes/auth or
  changing the production build. Recurrence may require upstream Next.js investigation.

Follow [exact manual steps](expenses.md#exact-local-manual-test) for the requested
1,200,000 + 250,000 + 300,000 expense scenario. No Phase 5 work was started.
