# Phase 9 verification — source-gated foundation only

2026-09-30. **LIVE VISITOR PROVIDER NOT VERIFIED. Monthly visitor product feature is not complete.** The request's sections 5–6 prohibit inventing a provider and restrict implementation at the unverified-source gate. This report does not mark deferred DB/sync/API/UI work complete.

| Section | Actual result |
| --- | --- |
| A. Starting Git state | Clean main at 3bb4da4. Existing phase9/tourism-visitors fast-forwarded to committed Phase 8 59e9584. No new commit/push; current changes are this task only |
| B. Official source selected | Candidate: 한국관광공사_빅데이터_지역별 방문자수_GW, catalogue 15101972. Not enabled for ingestion |
| C. Contract verified | Official catalogue and embedded daily Swagger verified; full monthly/source gate unresolved. See 23-point [source checklist](tourism-visitor-source.md) |
| D. Repository changes | Internal provider/DTO, 24 new tests, commented configuration placeholder, source/implementation/report docs and related README/API/database/architecture notes |
| E. Migration | None. Repository head 0006; actual local app DB remains 0005; no migration execution |
| F. Model | In-memory daily normalized DTO only, exact Decimal/null and mandatory estimated label. No SQLAlchemy entity/table |
| G. Mapping | Opaque source region fields only. No invented Busan official codes or automatic name mapping |
| H. Sync | No command, storage or sync audit implemented; placeholder provider always raises a fixed unverified error |
| I. API | No visitor endpoint added; existing versioned market/tenant boundaries unchanged |
| J. UI | No visitor section/chart added; existing accommodation page retained |
| K. Metadata | Daily reference date separate from aware collection/source-update time; unknown version/update stays null. No stale rule/monthly comparison guessed |
| L. Backend checks | Ruff passed; mypy passed on 81 source files; full pytest 203 passed, 0 skipped, 2 existing dependency deprecation warnings |
| M. Frontend checks | Lint, isolated route type generation/typecheck, 40 tests and isolated production build passed |
| N. PostgreSQL | Full existing suite ran with actual PostGIS and restricted-role integration fixtures. No new visitor persistence tests because no visitor persistence exists |
| O. Docker | Compose config passed; frontend/backend/db healthy. New local production image built, provider import/non-root/no-tests/no-.env audit passed |
| P. Live official API | None. No service key sent, no official visitor rows stored, no COMPLETED run claimed |
| Q. Browser | Authenticated local property list/detail, dashboard, market, CSV form, reservation list and expense page visibly rendered. Read-only navigation; no repeated signup/import/write journey |
| R. Phase 1–8 regression | Existing suites green; dashboard-v1/license-market-v1, JWT/membership/RLS, region selection and MOIS sync code unchanged. Phase 8 production image and files preserved |
| S. Unverified | Monthly availability, historical coverage, Busan code mapping, categories, response/empty shapes, publication lag, revisions, account access and full SaaS operational approval |
| T. Source limits | Daily estimated visitor figures are not monthly unique persons, hotel guests or demand. Official methodology warns against summing rounded daily/district numbers into official monthly/city totals |
| U. Environment | Comment-only reserved TOURISM_VISITOR_API_KEY; unused. No required settings/Compose/frontend/remote secrets added |
| V. Local sync command | Does not exist while gated. Only actual contract test command is documented; do not run a guessed module |
| W. Manual browser steps | localhost:3000 → 내 숙소 → existing property → 지역 시장. Existing lodging context remains; no visitor data is expected. Backend/Swagger use localhost:18000. See [manual checks](tourism-visitors.md) |

## Actual commands

From the repository root using the existing .tools/docker-compose.exe:

~~~powershell
.\.tools\docker-compose.exe exec -T backend uv run ruff check .
.\.tools\docker-compose.exe exec -T backend uv run mypy app tests
.\.tools\docker-compose.exe exec -T -e TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/postgres backend uv run pytest -q
.\.tools\docker-compose.exe exec -T frontend pnpm lint
.\.tools\docker-compose.exe run --rm --no-deps frontend sh -c 'pnpm exec next typegen && pnpm typecheck && pnpm test && pnpm build'
.\.tools\docker-compose.exe config --quiet
~~~

The DB credentials above are existing LOCAL TEST defaults only. PostgreSQL tests create isolated databases and roles; they do not upload or seed the application DB. The production image was checked through an ignored .tools/phase9-image-check.compose.yml using unchanged backend/Dockerfile.prod; one-off container removed automatically. No dependency/lockfile changes or paid resources.

## Remaining work and exact next evidence

Obtain the candidate's approved official guide/access and a supported monthly source/definition before adding persistence and the 12-month UI. Confirm the unresolved facts in tourism-visitor-source.md; a key alone does not resolve the monthly/rounding issue. If only daily observations can be obtained, explicitly agree on a different daily product before changing scope. Do not scrape Data Lab chart endpoints or manufacture monthly values.

No cloud deployment, hosted migrations, Render Cron activation, local automation change, events/maps/benchmark or Phase 10 work occurred. Existing owner demo data and public lodging records were not edited by this task.
