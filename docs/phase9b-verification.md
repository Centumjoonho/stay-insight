# Phase 9B verification report

2026-09-30, local development only. Implemented and verified official DAILY regional visitor trends. No official monthly visitor count is produced. No commit/push, hosted deployment, Cron activation or Phase 10 work.

## A–Z acceptance record

| Item | Actual evidence |
| --- | --- |
| A. Starting Git | Clean phase9/tourism-visitors at d45dd8e (Phase 9A committed). No reset/stash/clean/revert. |
| B. Migration/head | Repository initially 0006, local DB 0005. Exactly one new migration 0007_tourism_visitor_daily; local upgrade applied through 0006 to 0007. Test databases upgrade/downgrade/base/upgrade successfully via existing fixture. Old migration files unchanged. |
| C. Official contract | Phase 9A decision B retained. Only locgoRegnVisitrDDList; actual normal/empty/top-level error shapes and Decimal strings. |
| D. Provider | One day/window, bounds on pages/bytes/attempts, valid dates, matching totals/pages, duplicates and malformed rows rejected. Exact existing encoded-key handling; no credential output. |
| E. Busan mapping | All 16 verified immutable codes resolve exactly once by exact Busan region names. Environment UUIDs not hard-coded. Live storage covers 16 regions. |
| F. Categories | 1 현지인(a), 2 외지인(b), 3 외국인(c), separate in storage/API/UI. No total/category addition. |
| G. Schema | Shared tourism_visitor_daily, UUID/region FK/source/code/category/date identity, exact unscaled NUMERIC, UTC timestamps, unique source/region-code/category/date. Nullable value only for withdrawn prior observations. |
| H. Security | Runtime SELECT only; ingestion SELECT/INSERT/UPDATE, tenant reads and visitor DELETE rejected. Existing tenant isolation/JWT tests green. |
| I. Bootstrap | Discover backwards from Seoul yesterday up to 60 days; collect 120 calendar days ending at latest observed Busan day. Maximum 450 request attempts. |
| J. Refresh | Default 35-day revision window, configurable 1–120. Idempotent and changed-value/missing-value tests pass. This is not an official revision guarantee. |
| K. Live sync | Exactly one controlled local bootstrap: exit 0, COMPLETED, run 330ac967-2feb-4af0-984d-28f43119c3e7; 5760 inserted, 0 updated, 0 unchanged. |
| L. Coverage | 2026-05-04 through 2026-08-31 inclusive: 120 dates, 16 regions, 5760 rows, 1920/category, no null rows or missing pairs inside the stored interval. Discovery 2026-09-01–09-29 empty: 29 × 48 = 1392 missing pairs audited, no zero rows inserted. |
| M. Metrics | Complete consecutive 7/28-day averages and adjacent 7-day change, Decimal precision 80, HALF_UP two decimals; zero baseline/missing days suppress percentage. Latest reference date is not today. |
| N. API | GET /api/v1/market/visitors, property_id, category default 2, days default90/max120; membership and scoped property access first, only local data. Gap-preserving daily history and source/freshness/coverage. |
| O. Frontend | Separate market section, server-provided categories, cards, 90-day Recharts with gaps, exact-value accessible table, source/estimated notice, no-region/no-sync/incomplete/error states. |
| P. Backend | Ruff passed, mypy passed 90 files, full pytest 241 passed/0 skipped. Two existing Starlette/httpx and anyio deprecation warnings. 23 new Phase 9B tests, previous 218 retained. |
| Q. Frontend | ESLint passed, next typegen + TypeScript passed, 44 tests passed, production next build passed. Four new visitor tests; existing market test dependencies updated. |
| R. PostgreSQL | Real isolated PostGIS tests cover migration cycle, exact numeric persistence, uniqueness/checks, restricted roles, idempotency/revision/rollback/locks, tenant API and missing data. |
| S. Docker | Compose config passed; backend/db/frontend healthy. Frontend rebuilt/recreated; backend recreated for private key wiring. Local ports, Webpack, copied-source and polling behavior preserved. No volume deletion. |
| T. Production image | Unchanged Dockerfile.prod built as local stay-insight-api:phase9-check. One-off runtime check passed non-root UID, app provider import, no /app/tests, no /app/.env. No deploy. |
| U. Browser | Existing authenticated IAB session, two existing properties (67fc…1792 and 3bb6…5758), both currently 해운대구. All three categories rendered; keyboard submit changed query and values. Chart visibly rendered, details table expanded with dates/exact values. HTTP 200 recorded for market/default/category1/category3. No owner edits or login setup. |
| V. Source limits | Daily mobile estimates are not guests/demand/occupancy. Some provider foreign values have long fractional tails; preserved rather than repaired. No official monthly/source total or rounding claim. |
| W. Unresolved | Official release/completion schedule, true page/date limits, historical method/code revisions and backfill horizon. Same-count upstream snapshot changes cannot be fully detected. Long bounded sync transaction and orphan RUNNING audit after forced process death remain operational limitations. |
| X. Commands | Exact bootstrap/refresh/local upgrade commands below; secrets come only from ignored root .env. |
| Y. Manual steps | Existing property → 지역 시장 → select each category → 조회 → compare date/cards → expand 일별 자료 표 보기. No data edits needed. |
| Z. Files | Explicit list below. No dependencies or previous migrations changed. |

## Live plausibility and preservation

The selected 해운대구 daily latest reference is 2026-08-31 for all three categories. Browser coverage shows 90/90 days; rolling cards exist. Stored date span has every expected 16 × 3 pair for every day. Audit missing count includes empty publication-discovery dates after August, and must not be misreported as missing bootstrap history.

Owner-table pg_stat_user_tables insertion/update/deletion counters were identical immediately before/after bootstrap for organizations, organization_members, properties, reservation_imports, reservations and expenses. No owner-row contents were queried for this comparison. Existing MOIS page remains 392 open/46 recent permits for the selected district, with unavailable closures as before; original MOIS collection time remains unchanged. Dashboard/CSV/expense/region regression suites pass. Existing Phase 8 production files were not edited; remote GitHub CI/staging were not run.

UI accessibility was checked through rendered semantic label/select/button, heading, table caption/row/column headers and keyboard category submission/detail expansion. Chart checked visually. This is not a full WCAG or external accessibility audit. Missing/no-region/error scenarios are covered by tests rather than destructive edits to existing owner data.

## Exact local commands

Run from C:/Users/HDRBRND/Desktop/Web Workspace/accommodation. Local DB defaults only; never use these credentials for hosted services.

~~~powershell
# Already applied in this task; needed on another local checkout/database:
.\.tools\docker-compose.exe exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic upgrade head
.\.tools\docker-compose.exe up -d --build --force-recreate backend frontend
# First history collection (already completed here):
.\.tools\docker-compose.exe exec -T -e MARKET_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run python -m app.jobs.sync_tourism_visitors --bootstrap
# Normal subsequent refresh:
.\.tools\docker-compose.exe exec -T -e MARKET_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run python -m app.jobs.sync_tourism_visitors
~~~

The standard docker compose prefix is equivalent if available. Existing startup remains docker compose up -d; new code or env changes require the documented rebuild/recreate. No automatic visitor schedule has been activated. [Contract and operations](tourism-visitors.md).

## Files changed

- Configuration: .env.example, backend/.env.example, docker-compose.yml.
- Migration/model: backend/alembic/versions/0007_tourism_visitor_daily.py, backend/app/models/visitors.py, backend/app/models/market.py, backend/app/models/__init__.py.
- Backend: backend/app/providers/visitor_api.py, backend/app/repositories/visitors.py, backend/app/services/visitor_sync.py, backend/app/services/visitors.py, backend/app/schemas/visitors.py, backend/app/jobs/sync_tourism_visitors.py, backend/app/api/v1/market.py.
- Backend tests: backend/tests/test_visitor_daily.py, backend/tests/test_config.py. Real Phase 9A fixtures remain unchanged.
- Frontend: frontend/src/lib/api/visitor-types.ts, frontend/src/lib/api/server.ts, frontend/src/components/visitor-view.tsx, frontend/src/components/visitor-chart.tsx, frontend/src/app/(protected)/properties/[id]/market/page.tsx.
- Frontend tests: frontend/tests/visitors.test.ts, frontend/tests/market.test.ts.
- Docs: README.md, docs/tourism-visitors.md, docs/tourism-visitor-source.md, docs/api.md, docs/database.md, docs/architecture.md, docs/product.md, docs/public-accommodation-market.md, docs/phase9b-verification.md.

Local ignored .tools image-check Compose file from Phase 9A reused only for verification. Final diff/secret/relative-link checks are performed before handoff. No actual key belongs to any changed tracked file.
