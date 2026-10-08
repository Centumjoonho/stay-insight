# Phase 11 verification — 2026-10-08

Local implementation only. The subsequent user instruction authorized commit/push. No hosted migration/deployment, public sync,
scheduler, or Phase 12 work. Starting clean tree was confirmed before editing.

## A–Z completion report

| Item | Status | Evidence / decision |
| --- | --- | --- |
| A. Starting Git | VERIFIED | phase9/tourism-visitors; ccf1ac6; clean working tree. |
| B. Alembic | VERIFIED | Actual code head inspected: 0008_tourism_events. Local DB now 0009_inventory_availability. |
| C. dashboard-v1 | VERIFIED | API, schemas, repository, service and original test_dashboard.py unchanged. One reservation=one room; current default × days remains. New tests prove v1 ignores room_units while v2 uses it. |
| D. Capacity history | VERIFIED | Inclusive dated aggregate capacity, nullable open end, positive integer. Service overlap check plus GiST exclusion. Explicit history authoritative; property field remains labeled default/compatibility. |
| E. Availability | VERIFIED | One date row, >=0 and <= effective capacity, 4 reasons and optional memo. Bounded 366-day reads; upsert/delete. No reservation-derived exclusions. |
| F. Reservation units | VERIFIED | Nullable positive integer column; existing 317 local reservations still null. No false backfill. |
| G. CSV | VERIFIED | Optional mapping, strict positive integer validation, persistence, duplicate no-op, whole-row replacement including clearing omitted units. Existing limits/atomicity unchanged. |
| H. Migration | VERIFIED | One additive revision; no prior migration edits. Isolated PostgreSQL tests upgrade/downgrade/upgrade. Actual existing-table hashes match before/after. |
| I. Security | VERIFIED | Composite property FK, explicit predicates, forced RLS, restricted column grants, missing/revoked membership denial, pooled context isolation, ingestion SELECT/DELETE and privilege denial. Existing JWT tests pass. |
| J. v2 calculation | VERIFIED | Occupied overlap × reported units (null estimated 1); sum daily capacity minus exclusions. Existing allocated revenue/financial/cost/profit/channel/status rules preserved. |
| K. Fallback | VERIFIED | Missing room units, history days and exclusion records have separate counts and Korean warnings. No fake history generation. |
| L. Overcapacity | VERIFIED | Daily affected count even if monthly rate <100%; no clamping. Zero availability produces null occupancy/RevPAR with warning. |
| M. APIs | VERIFIED | /api/v1/properties/{id}/capacity and /availability, explicit /api/v1/dashboard-v2/summary and /trends. Existing v1 preserved. See api.md. |
| N. Frontend | VERIFIED | Capacity add/edit/delete, exclusions upsert/edit/delete, bounded daily table, explicit v2 client, optional CSV room mapping, 미입력 reservation units, accurate chart/source/default labels. |
| O. Backend tests | VERIFIED | Full pytest: 271 passed, 2 existing dependency deprecation warnings, no skips. Ruff whole backend passed; mypy app+tests passed (108 files). 16 Phase 11 parametrized cases. |
| P. Frontend tests | VERIFIED | 51 passed; ESLint, route typegen, TypeScript and isolated next build passed. Real React form interactions include deletion confirmation/cancel, overlap error, reservation units and v2 warnings. |
| Q. PostgreSQL | VERIFIED | Real local PostGIS PostgreSQL; restricted runtime and ingestion tests; overlap constraint and concurrent capacity/exclusion writes; default reduction and history deletion rollback. |
| R. Docker | VERIFIED | Compose config --quiet passes; backend/db/frontend healthy. Frontend rebuilt/recreated; Webpack dev preserved; production build uses separate disposable container. Ports unchanged. |
| S. Production image | VERIFIED | Existing Dockerfile.prod built with the existing image-check helper. UID 10001, new modules import, no tests/.env/.git or pytest/Ruff. No hosted execution claimed. |
| T. Browser | ACTUALLY BROWSER VERIFIED | Existing authenticated IAB session: properties → development sample → inventory. Create/edit/delete verified, 7×30−2=208 available, 51 occupied, displayed 24.5%. v2 and quality warnings rendered. Reservation list shows 미입력. Nested routes HTTP 200. Details below. |
| U. Public regression | VERIFIED / ACTUALLY BROWSER VERIFIED | Existing accommodation/visitor/event tests pass; source/job/UI contracts unchanged. Market sections render. No sync run. Public row hashes unchanged. |
| V. Limitations | NOT VERIFIED | Full WCAG audit, production-scale load, hosted btree_gist availability/permissions and actual deployment. Administrative SQL can bypass cross-table service validation. No full revision/undo log. |
| W. Future work | NOT IMPLEMENTED | Physical rooms, manual reservation CRUD/export, maps, OTA, forecasts, billing and anonymous benchmark remain outside Phase 11. |
| X. Manual steps | VERIFIED | Commands and owner journey below. No new environment variable/key required. |
| Y. Files | VERIFIED | Complete changed-file inventory below; no lockfile/dependency changes. One PostgreSQL extension (btree_gist). |
| Z. Next phase | RECOMMENDATION ONLY | Define owner reservation corrections and audit history before expanding operational workflows; user should authorize a separate scope. No Phase 12 implementation. |

## Actual browser details

Property: 67fcf013-eaeb-4a94-9c87-3057bd721792, explicitly labeled
[개발용 더미] 해운대 6객실 샘플; not a real owner property.

- Opened properties/detail/inventory using existing signed-in session.
- Created capacity, corrected dates to 2026-09-01–30 and changed 6 to 7 rooms.
- Created sale exclusions, edited September 1 from 1 to 2 rooms.
- September dashboard showed occupied 51, available 208, occupancy 24.5% (display rounding),
  ADR 125,333 KRW and RevPAR 30,731 KRW; recognized revenue 6,192,000 KRW unchanged.
- Missing reservation units warning counted 26 overlapping reservations; 29 days lacked
  explicit exclusion records. October view displayed history fallback warning.
- Native date-fill automation required keyboard change events to commit React state;
  stored dates were checked, not inferred from attempted fills.
- Browser native confirmation stalled the automation. User accepted that initial test
  confirmation. Final UI now uses in-page confirmation like expenses. Then both exclusion
  and capacity deletion were actually browser verified without native dialogs.
- All records created during this browser test were removed. DB confirms zero capacity
  and exclusion rows for the development property. Existing demo reservations unchanged.
- Market showed Haeundae 393 open licenses, visitor latest observed 2026-08-31, and the
  official event section. Data freshness text remains; no new public collection occurred.
- Reservation page showed room count column and 미입력 for old CSV rows.
- After cleanup, September showed 180 available room-nights, 51 occupied and 28.3% occupancy, with 30 fallback days explicitly warned.
- Semantic labels/headings and keyboard date input were exercised. Full WCAG audit was
  not performed. No real property or real reservation was edited.

## Existing data preservation

Whole-row aggregate hashes were equal before/after migration for the tables below.
Reservation hash intentionally excludes only the new nullable room_units key.
No raw rows, keys, tokens, or provider responses were printed.

| Table | Before / after rows |
| --- | ---: |
| organizations | 2 |
| organization_members | 2 |
| properties | 3 |
| reservation_imports | 5 |
| reservations | 317 |
| expenses | 81 |
| public_accommodation_licenses | 4,717 |
| tourism_visitor_daily | 5,760 |
| tourism_events | 28 |

## Exact local commands

Working directory: C:\Users\HDRBRND\Desktop\Web Workspace\accommodation.
The migration and frontend rebuild below were already run for this task.
The administrator credential here is only the established local development credential.
No new .env setting is needed.

~~~powershell
# Usual next startup:
docker compose up -d

# Only when applying this revision to another copy of the LOCAL development DB:
docker compose exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic upgrade head

# After frontend source changes:
docker compose up -d --build frontend

# Verification:
docker compose config --quiet
docker compose exec -T backend uv run ruff check .
docker compose exec -T backend uv run mypy app tests
docker compose exec -T -e TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/postgres backend uv run pytest -q
docker compose run --rm --no-deps frontend sh -c 'pnpm lint && pnpm exec next typegen && pnpm typecheck && pnpm test && pnpm build'
~~~

Standard Compose was available (v5.5.1). If absent, substitute .\.tools\docker-compose.exe
for docker compose. Never use down -v. Do not build in the running dev .next directory.
Production image audit reused ignored .tools/phase9-image-check.compose.yml, which points
to backend/Dockerfile.prod; its historical helper/tag name does not change application version.

Owner manual check:
1. Sign in at http://localhost:3000 and choose a clearly marked development property.
2. Open 객실 운영. Add an accurate test date range and room count; confirm an overlapping
   period is rejected. Edit an existing period rather than making overlapping open ends.
3. Register a sales exclusion on a date inside the period; verify daily available units.
4. Edit exclusion, then inspect the matching dashboard month and version/source warnings.
5. Delete only your test exclusion and capacity via the in-page confirmation.
6. Verify dashboard fallback and visit 지역 시장; owner and public indicators remain separate.
7. For room_units importing, use a disposable development CSV with an explicit positive room
   column. Review the warning that omitted room_units clears known units on a changed-file upsert.

## Files changed

- README.md
- backend/alembic/versions/0009_inventory_availability.py
- backend/app/api/v1/dashboard_v2.py
- backend/app/api/v1/inventory.py
- backend/app/importers/generic.py
- backend/app/main.py
- backend/app/models/__init__.py
- backend/app/models/imports.py
- backend/app/models/inventory.py
- backend/app/repositories/dashboard_v2.py
- backend/app/repositories/imports.py
- backend/app/repositories/inventory.py
- backend/app/schemas/dashboard_v2.py
- backend/app/schemas/imports.py
- backend/app/schemas/inventory.py
- backend/app/services/dashboard_v2.py
- backend/app/services/foundation.py
- backend/app/services/inventory.py
- backend/app/services/readiness.py
- backend/tests/test_config.py
- backend/tests/test_inventory.py
- docs/api.md
- docs/architecture.md
- docs/dashboard-v2.md
- docs/dashboard.md
- docs/database.md
- docs/imports.md
- docs/inventory-availability.md
- docs/metrics.md
- docs/phase11-verification.md
- docs/product.md
- frontend/src/app/(protected)/properties/[id]/dashboard/page.tsx
- frontend/src/app/(protected)/properties/[id]/inventory/page.tsx
- frontend/src/app/(protected)/properties/[id]/page.tsx
- frontend/src/app/(protected)/properties/page.tsx
- frontend/src/components/dashboard-charts.tsx
- frontend/src/components/dashboard-view.tsx
- frontend/src/components/import-wizard.tsx
- frontend/src/components/inventory-manager.tsx
- frontend/src/components/property-form.tsx
- frontend/src/components/reservation-table.tsx
- frontend/src/lib/api/client.ts
- frontend/src/lib/api/dashboard-types.ts
- frontend/src/lib/api/import-types.ts
- frontend/src/lib/api/inventory-types.ts
- frontend/src/lib/api/server.ts
- frontend/src/lib/api/transport.ts
- frontend/src/lib/imports.ts
- frontend/src/lib/inventory.ts
- frontend/tests/imports.test.ts
- frontend/tests/inventory.test.ts
