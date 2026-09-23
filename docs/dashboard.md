# Phase 5 property dashboard

Route: /properties/[id]/dashboard?month=YYYY-MM. Open 대시보드 from the existing property detail.
The server component calls FastAPI with verified bearer token and organization context.
Charts alone are client components (Recharts 3.10.1); no browser business-table access or KPI formulas.

See [metrics.md](metrics.md) for the dashboard-v1 contract and [api.md](api.md) for endpoints.
Eight cards show revenue, known operating profit, estimated calendar occupancy, estimated ADR,
estimated RevPAR, known costs, reservation count and ALOS. Channel/cost tables, comparisons,
quality warnings, two 12-month line charts and an accessible exact-value trend table accompany them.
Month selection uses a normal GET form. 401 redirects to login, 403 uses the protected error UI,
and foreign/missing properties yield 404. No public data or Phase 6 work is included.

## Runtime and verification commands

Run from the repository root in PowerShell. The checked-in local Compose executable is used here.

```powershell
& './.tools/docker-compose.exe' config --quiet
& './.tools/docker-compose.exe' up --build -d --no-deps --force-recreate frontend
& './.tools/docker-compose.exe' exec -T backend uv run ruff check .
& './.tools/docker-compose.exe' exec -T backend uv run mypy app tests
& './.tools/docker-compose.exe' exec -T -e TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/postgres backend uv run pytest --tb=short -q
& './.tools/docker-compose.exe' exec -T frontend pnpm lint
& './.tools/docker-compose.exe' exec -T frontend pnpm typecheck
& './.tools/docker-compose.exe' exec -T frontend pnpm test
& './.tools/docker-compose.exe' run --rm --no-deps frontend pnpm build
& './.tools/docker-compose.exe' ps
```

Backend source is mounted by development Compose. A frontend rebuild is required for Recharts and
new tests. Webpack development command and production build command are unchanged. No migration
or environment variable is needed; migrations 0001–0003 and runtime least privilege remain intact.
Do not run down -v. Integration tests provision disposable databases; they do not seed application data.

## Manual browser verification with the existing property

1. Log in at http://localhost:3000/login.
2. Open the existing property, then 대시보드. The current property URL is
   http://localhost:3000/properties/3bb63e98-7915-4db2-b844-55ab133a5758/dashboard.
3. Select 2026-09 (the month with imported reservations) and 조회. Check the displayed effective
   end date: it is today only if September is still the current month.
4. Open 예약 목록 in another tab. Sum gross_revenue for non-cancelled check-ins inside the
   effective dates. Compare 매출 and 예약건수; include UNKNOWN and exclude CANCELLED.
5. Sum only the same population's non-null channel_fee. Check missing counts and channel table.
6. Open 비용 관리; use the dashboard's exact first/end dates. Sum manual fixed/variable expenses.
   Phase 4 fee totals include cancelled fees, so reconcile that difference explicitly.
7. Verify known total cost = manual expenses + known fees once, and known profit = gross - cost.
   No fee expense rows should have appeared.
8. Compute each reservation's overlapping nights, excluding checkout; include cross-month stays.
   Divide total by current inventory × effective days for occupancy. It may exceed 100%.
9. Allocate gross proportionally to overlapping/booked nights. Divide by occupied nights for ADR,
   or available nights for RevPAR. Compare rounded values and estimation labels.
10. Verify ALOS from financial-population booked nights / reservation count. Verify channel counts,
    gross and revenue shares sum appropriately.
11. Check previous-month and prior-year comparison dates. Missing baseline must say 비교 데이터 없음;
    occupancy changes use %p. Open 월별 수치 표 보기 to inspect chart values without relying on pixels.
12. Change to a month with no records (for example 2025-01 after confirming no imports then).
    Expect honest no-data message/import action, missing-expense notice and chart gaps.
13. Return to the populated month. Confirm CSV import, reservation and expense navigation still work.

All values come from existing owner records. No invented production/example records are required.

## Read-only API diagnostics

Supply a current access token from your own local authenticated session and its organization ID
through local environment variables; never paste or commit them. These commands do not print tokens.

```powershell
$dashboardHeaders = @{ Authorization = "Bearer $env:STAY_ACCESS_TOKEN"; 'X-Organization-Id' = $env:STAY_ORGANIZATION_ID }
$dashboardProperty = '3bb63e98-7915-4db2-b844-55ab133a5758'
Invoke-RestMethod -Headers $dashboardHeaders -Uri "http://localhost:8000/api/v1/dashboard/summary?property_id=$dashboardProperty&month=2026-09" | ConvertTo-Json -Depth 12
Invoke-RestMethod -Headers $dashboardHeaders -Uri "http://localhost:8000/api/v1/dashboard/trends?property_id=$dashboardProperty&months=12&month=2026-09" | ConvertTo-Json -Depth 8
```

Swagger at http://localhost:8000/docs also exposes both read-only endpoints. Summary includes period,
financial/operational values, quality counts, channels, expense categories, comparisons and metadata.
The authenticated reservation and expense list APIs provide paginated source rows for reconciliation.

## Verification record (2026-09-23)

- Backend Ruff and mypy: pass. PostgreSQL integration/unit suite: 114 passed (including 17 dashboard
  cases), with two existing upstream TestClient deprecation warnings.
- Frontend ESLint: pass. All 30 tests pass, including seven dashboard cases.
- Fresh-container route type generation, TypeScript and production build: pass; dashboard appears
  in the production route manifest. Development remains Next.js 16.3.5 Webpack.
- Compose config validates; frontend/backend/PostGIS healthy. Admin read verifies head 0003_expenses.
- The running development instance reproduced malformed .next/dev/types generated files (trailing
  fragments). Recreating it did not reliably repair this. This is a remaining development-tooling
  limitation, not suppressed TypeScript errors: the clean-container command below passed without
  excluding source files or relaxing type checking. Dashboard browser requests still returned 200.
- Authenticated existing-property browser verification: current month, eight cards, Korean text,
  both rendered charts, twelve-row accessible trend table, UNKNOWN/missing-fee warnings, month
  selection to empty January 2025 and back. Browser console had no errors/warnings at inspection.
  Read-only source reconciliation matched two reservations (gross 290,000, known fee 20,000,
  three nights) and three expenses (1,750,000). UI showed cost 1,770,000 and known profit -1,480,000;
  one-room/23-day occupancy 13.0%, ADR 96,667, RevPAR 12,609, count 2 and ALOS 1.5.
  These are observed local owner records, not development seeds added by this task.
- Existing production data was not modified. Zero/positive/negative baselines, cross-month allocation,
  cancellation and cross-tenant failures use disposable integration-test fixtures.
- Remaining owner review: confirm imported gross/fee semantics and cost coverage against source
  documents; live historical comparisons have no baseline records, so nonempty comparisons were
  verified in tests. No cross-browser or automated WCAG conformance claim is made.

For deterministic type checking while the development type generator is affected:

```powershell
& './.tools/docker-compose.exe' run --rm --no-deps frontend sh -c 'pnpm exec next typegen && pnpm typecheck'
```

This does not alter the server's bundler, generated files in its running container, or TypeScript
configuration. Run production builds in an isolated container as above rather than over the dev cache.
