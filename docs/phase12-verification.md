# Phase 12 verification — 2026-10-22

Implementation, automated checks and authenticated local browser verification completed.
No cloud deployment, hosted migration, external data sync, scheduler or Phase 13.

## A–AK status

| Item | State | Evidence / decision |
| --- | --- | --- |
| A. Starting Git | VERIFIED | Clean working tree before editing. |
| B. Branch/HEAD | VERIFIED | phase9/tourism-visitors / 10d658e, remote synchronized at start. |
| C. Starting migration | VERIFIED | heads/history: 0009_inventory_availability. |
| D. Existing contract | VERIFIED | UUID PK; property/channel/external identity; optional null/UNKNOWN replacement, checksum idempotency and savepoint inspected. |
| E. Origin | VERIFIED AGAINST POSTGRESQL | CSV_IMPORT and MANUAL; existing 317 rows have verified mandatory import lineage; no invented historical audits. |
| F. Create | VERIFIED BY AUTOMATED TEST | Manual API/form; optional external/import ID, nullable counts; money/date/status and collision checks. |
| G. Edit | VERIFIED BY AUTOMATED TEST | PATCH supplied fields, derived nights/net, changed fields only, required reason. |
| H. Cancellation | VERIFIED BY AUTOMATED TEST | Existing CANCELLED and reopening with reason/audit; no DELETE. |
| I. Protections | VERIFIED AGAINST POSTGRESQL | Unique known reservation/field rows; no protection necessary for MANUAL rows. |
| J. CSV policy | VERIFIED AGAINST POSTGRESQL | Per-field protection; unprotected updates; invalid merged row/manual collision rolls back whole batch. |
| K. Release | VERIFIED AGAINST POSTGRESQL | Required reason/version; values retained, metadata removed, audit/version advanced; completed identical bytes still no-op. |
| L. Audit | VERIFIED AGAINST POSTGRESQL | Append-only schema, canonical before/after snapshots, source/import linkage, bounded newest-first reads. |
| M. Actor/reason | VERIFIED AGAINST POSTGRESQL | Authenticated subject; bounded trimmed reason; INSERT actor policy; API actor forgery rejected; safe UI escaping. |
| N. Locking | VERIFIED AGAINST POSTGRESQL | Deterministic locks; competing edits yield one 200/one 409; CSV/manual consistency; failed mutation has no false audit. |
| O. Migration | VERIFIED AGAINST POSTGRESQL | 0010_manual_reservations; isolated upgrade/downgrade/upgrade; local reapplication while new tables empty; old business hashes preserved. |
| P. RLS/grants | VERIFIED AGAINST POSTGRESQL | Forced RLS and composite FKs; minimal grants; no audit UPDATE/DELETE, reservation DELETE or ingestion access; missing/revoked/cross-org tests. |
| Q. API | VERIFIED BY AUTOMATED TEST | Create, extended detail/list, PATCH, release-overrides, paginated history; private/no-store. |
| R. Frontend | VERIFIED BY AUTOMATED TEST | Register/detail/edit, origin/protection labels, release confirmation, semantic history, conflict/reload action and labels. |
| S. Dashboard-v1 | VERIFIED BY AUTOMATED TEST | Calculation service/repository/original tests unchanged; room correction preserves v1 formula. Source metadata now owner_reservations. |
| T. Dashboard-v2 | VERIFIED BY AUTOMATED TEST | Calculation service/repository/original tests unchanged; correction/cancellation change effective inputs. Estimate wording retained. |
| U. CSV | VERIFIED BY AUTOMATED TEST | Existing suite passes; nullable room units, atomic rollback, identity/checksum rules retained; protected_fields_count added. |
| V. Inventory | VERIFIED BY AUTOMATED TEST | Existing capacity/exclusion PostgreSQL and React form tests pass. |
| W. Public market | VERIFIED BY AUTOMATED TEST / ACTUALLY VERIFIED IN BROWSER | Provider/jobs unchanged; suites pass; authenticated market source/visitor/event sections render. No live sync. |
| X. Backend | VERIFIED BY AUTOMATED TEST | Ruff/mypy pass; full pytest and focused totals recorded below. |
| Y. Frontend | VERIFIED BY AUTOMATED TEST | Lint/typegen/typecheck, 54 tests, isolated next build pass. |
| Z. PostgreSQL | VERIFIED AGAINST POSTGRESQL | Real PostGIS DBs/restricted logins; tenant policies, grants, locks, rollback and actor checks. |
| AA. Docker | VERIFIED | Compose config --quiet; all three services healthy; final frontend image rebuilt/recreated; original dev workaround retained. |
| AB. Production image | VERIFIED | Dockerfile.prod built; UID10001, modules import; no tests/fixtures/.env/.git, pytest or Ruff. |
| AC. Browser | ACTUALLY VERIFIED IN BROWSER | Register/edit/audit/cancel/reopen, stale-write conflict and reload, CSV field protection/release, dashboard/inventory/market verified after Supabase resumed. |
| AD. Cleanup | VERIFIED | Two explicitly labeled development reservations created and cancelled through the UI; three test imports and their audit history retained. Automated fixtures use isolated test DBs. |
| AE. Preservation | VERIFIED AGAINST POSTGRESQL | Existing owner/public row counts and aggregate hashes match, excluding only new schema keys. |
| AF. Limitations | DOCUMENTED | Actual completion, no-show/refund/settlement/accounting, delete/restore, auto-merge, expense history and OTA remain excluded; no full WCAG/load/cloud check. |
| AG. Files | VERIFIED | File inventory below; no dependencies, lockfile or environment changes. |
| AH. Commit | DELIVERY RECORD | Commit containing this report follows all checks and browser acceptance; exact hash/message is reported in final delivery and Git history. |
| AI. Push | DELIVERY RECORD | Normal push to configured remote; final delivery records actual result. No force push. |
| AJ. Manual workflow | DOCUMENTED | See below and manual-reservations.md. |
| AK. Next Phase | RECOMMENDATION ONLY | Separately scope accuracy or staging; no Phase 13 work. |

## Executed checks

- Ruff whole backend passed; mypy app/tests passed (115 files).
- Final full pytest: 298 passed, 2 existing dependency deprecation warnings, no skips.
  Focused Phase 12 suite: 27 passed. Ruff and mypy also passed on final sources.
- Frontend 54 tests, lint/typegen/typecheck and isolated production build passed.
  Build includes reservations/new and reservations/[reservationId].
- Production image reused the existing ignored image-check Compose helper.
- One earlier test run was interrupted by planned backend recreation, not counted
  as successful. Stable-container reruns are reported separately.
- Two existing Starlette/httpx/anyio dependency deprecation warnings remain.
- Report creation initially rejected by automatic review because a command contained
  a DB credential literal. This report omits connection values and references existing
  local operations documentation instead; no security policy bypass was attempted.

## Data preservation

Before/after aggregate hashes match. Reservation comparison excludes only new
origin/version keys; imports exclude only protected_fields_count. Raw rows and
provider responses were not printed. No meaningful business row edited for testing.

| Table | Rows |
| --- | ---: |
| organizations | 2 |
| organization_members | 2 |
| properties | 3 |
| reservation_imports | 5 |
| reservations | 317 |
| expenses | 81 |
| public_accommodation_licenses | 4717 |
| tourism_visitor_daily | 5760 |
| tourism_events | 28 |
| property_capacity_periods | 0 |
| property_availability_overrides | 0 |

317 existing reservations: CSV_IMPORT/version1. No fabricated audit rows.
Browser follow-up adds only DEV-PHASE12-BROWSER-20261022 and DEV-PHASE12-CSV-20261022, both CANCELLED. Existing reservations remain 317 (319 including tests); imports are 8 including 3 test batches. Audit history is retained; only the test CSV status protection remains.

## Local commands

Run at repository root. Migration is already applied to the current local DB.
For a new local DB copy, use the existing approved administrator migration setup in
[Phase 11 operations](phase11-verification.md). Do not paste credentials into chat
or add environment files to Git. No new environment variable or API key required.

~~~powershell
docker compose up -d
docker compose up -d --no-deps --build frontend
docker compose config --quiet
docker compose exec -T backend uv run ruff check .
docker compose exec -T backend uv run mypy app tests
docker compose run --rm --no-deps frontend sh -c 'pnpm lint && pnpm exec next typegen && pnpm typecheck && pnpm test && pnpm build'
~~~

Full backend pytest uses the existing TEST_DATABASE_URL integration configuration
documented in [authentication](authentication.md#automated-verification).
Never build in running dev .next, delete volumes, or force downgrade with MANUAL rows.

## Executed actual browser journey

1. Sign in; use a clearly identified disposable development property. Open 예약 목록.
2. 예약 직접 등록: gross300000/rooms1/dates; optional external ID DEV-PHASE12.
   Save and verify 수동. No real guest personal data.
3. Edit gross320000/rooms2 with an actual test reason; inspect actor/before/after
   history. MANUAL rows correctly have no CSV protection badge.
4. Set 취소 with reason and save; inspect audit. Reopen to 확정 with a new reason.
5. Use a separate disposable CSV reservation gross300000/rooms1. Edit rooms2 only;
   verify 수동 보정. Never edit meaningful old sample rows to perform this check.
6. New matching CSV gross320000 with rooms omitted: gross320000/rooms2 remain,
   protected count reported, CSV_UPDATE audit available.
7. CSV 자동 갱신 허용, reason, confirm: current rooms stay2. New file gross330000
   with rooms omitted sets room_units null under the existing source contract.
8. Open two tabs, save B, then stale A: require 409 and explicit reload action.
9. Open dashboard, inventory and market; check separate public sections and real
   nested-route 200 responses. Compilation is not proof of authenticated HTTP 200.
10. Cancel disposable reservations with reasons. There is no normal hard delete.
    Clean only explicitly identified disposable test data through approved local
    maintenance, preserving meaningful business history.

The journey above was executed using the existing development sample property. The manual record was finally cancelled at version 5; CSV record at version 6. CSV gross 300000 -> 320000 retained protected rooms2; release retained rooms2; next CSV gross330000 cleared omitted rooms to null. Two-tab stale save showed the conflict/reload UI. Dashboard, inventory and market returned HTTP200 and rendered source/estimate labels. The registration link now uses the existing high-contrast action style. Browser automation intermittently timed out during dev compilation; completed states were checked afterward. Full WCAG and load checks remain outside this verification.

## Changed files

- backend/alembic/versions/0010_manual_reservations.py
- backend/app/api/v1/reservations.py
- backend/app/main.py
- backend/app/models/__init__.py
- backend/app/models/imports.py
- backend/app/models/reservations.py
- backend/app/repositories/imports.py
- backend/app/repositories/reservations.py
- backend/app/reservation_fields.py
- backend/app/schemas/dashboard_v2.py
- backend/app/schemas/dashboard.py
- backend/app/schemas/imports.py
- backend/app/schemas/reservations.py
- backend/app/services/imports.py
- backend/app/services/readiness.py
- backend/app/services/reservations.py
- backend/tests/test_config.py
- backend/tests/test_reservations.py
- docs/api.md
- docs/architecture.md
- docs/dashboard-v2.md
- docs/database.md
- docs/imports.md
- docs/manual-reservations.md
- docs/metrics.md
- docs/phase12-verification.md
- docs/product.md
- docs/reservation-audit.md
- frontend/src/app/(protected)/properties/[id]/reservations/[reservationId]/page.tsx
- frontend/src/app/(protected)/properties/[id]/reservations/new/page.tsx
- frontend/src/app/(protected)/properties/[id]/reservations/page.tsx
- frontend/src/components/dashboard-view.tsx
- frontend/src/components/import-views.tsx
- frontend/src/components/import-wizard.tsx
- frontend/src/components/reservation-editor.tsx
- frontend/src/components/reservation-table.tsx
- frontend/src/lib/api/client.ts
- frontend/src/lib/api/dashboard-types.ts
- frontend/src/lib/api/import-types.ts
- frontend/src/lib/api/server.ts
- frontend/src/lib/api/transport.ts
- frontend/src/lib/reservations.ts
- frontend/tests/inventory.test.ts
- frontend/tests/reservations.test.ts
- README.md

Cleanup note: one empty temporary test database remained after interruption. It had
no user relations, no matching test login and zero active connections; only that
explicitly checked empty database was removed. Actual stay_insight data and volumes
were untouched.
