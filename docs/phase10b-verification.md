# Phase 10B verification — 2026-10-02

Status: implemented and locally verified. No deployment, commit, push, scheduler or Phase 11 work.

VERIFIED = automated/local inspection. LIVE VERIFIED = actual provider/local DB/browser execution. NOT VERIFIED = explicitly unresolved external contract or check.

| Item | Status | Evidence/result |
| --- | --- | --- |
| A. Starting Git | VERIFIED | phase9/tourism-visitors at bb18d25. Expected Phase 10A README/architecture edits and event-source/events/phase10-verification documents preserved. |
| B. Alembic | LIVE VERIFIED | 0007_tourism_visitor_daily → 0008_tourism_events in local DB only. |
| C. Source contract | LIVE VERIFIED | HTTPS apis.data.go.kr/B551011/KorService2/searchFestival2; response.header resultCode 0000; body items.item list, pageNo/numOfRows/totalCount. Sanitized two-row official fixture, test-only. |
| D. Geography | LIVE VERIFIED | lDongRegnCd=26 and lDongSignguCd; no deprecated areaCode/sigunguCode dependency. |
| E. Busan mapping | VERIFIED | 110 중구, 140 서구, 170 동구, 200 영도구, 230 부산진구, 260 동래구, 290 남구, 320 북구, 350 해운대구, 380 사하구, 410 금정구, 440 강서구, 470 연제구, 500 수영구, 530 사상구, 710 기장군. Exact existing region identity, no UUID constants; all 16 checked before sync. |
| F. Adapter | VERIFIED | Required contentid/title/dates/geography; optional addr1/addr2/progresstype. Timeout 20s, 3 bounded transient attempts, HTTPS/no redirects, 2 MiB response cap, 2 rows/page, 100-page maximum. Safe fixed errors; no credential URLs logged. |
| G. Model | VERIFIED | Shared app.tourism_events; source+source_event_id unique; region FK, official geography codes, title, date interval, optional address/raw status, last_seen/collected/audit timestamps. One row per event. |
| H. Migration | VERIFIED | One additive migration 0008; table/checks/unique/composite region-start index/grants; nullable event_coverage in public_data_sync_runs. Old migrations unchanged. Isolated test DB upgrade/downgrade/upgrade passed. |
| I. Security | VERIFIED | Runtime SELECT only; ingestion SELECT/INSERT/UPDATE only, no DELETE or owner-table access. Restricted-role integration tests; tenant property authorization before public-data lookup; JWT architecture unchanged. |
| J. Sync | LIVE VERIFIED | app.jobs.sync_events; committed RUNNING audit, event-specific advisory lock, transactional publication, safe FAILED audit and rollback, nonzero exit on failure. |
| K. Window | LIVE VERIFIED | Seoul today-30 through today+180: 2026-09-02–2027-03-31. Metadata SOURCE_QUERY_ONLY, not complete real-world event coverage. |
| L. Identity/update | VERIFIED | Repeated identical fixture no duplicate; corrected fields update same official identity; unchanged records refresh last-seen/collected times. No second live sync used to demonstrate idempotence. |
| M. Missing records | VERIFIED | Retained, never automatically deleted/cancelled. Missing row and publication-failure tests preserve previous records. |
| N. Live sync | LIVE VERIFIED | One controlled run fdfc4e9e-49bb-4046-94ec-da087edfc7f4; exit 0; persisted COMPLETED; fetched 28, inserted 28, updated 0, unchanged 0, failed 0. |
| O. Coverage | LIVE VERIFIED | 28 rows, 12 districts; earliest start 2026-01-01, latest end 2026-12-31; ongoing 5, starting next 30 days 14; missing address 0. Earliest start precedes query because a long-running event overlaps it. Venue/coordinates deliberately not stored; no missing-count claim for omitted fields. |
| P. API | VERIFIED | GET /api/v1/market/events, property_id and authorized org; stored data only; bounded dates/limit; ongoing-first stable ordering; independent summary counts; no-region/not-synced/outside-coverage/valid-empty distinction. |
| Q. UI | LIVE VERIFIED | Official event section after existing accommodation/visitors; Korean dates, addresses, temporal labels, source/collection, source coverage and no-demand/revenue-impact disclaimer. Error isolated to section for upstream server failure. |
| R. Backend | VERIFIED | Ruff passed; mypy 98 files passed; full pytest 255 passed, 2 existing warnings. Includes 14 event test cases and PostgreSQL tests. |
| S. Frontend | VERIFIED | pnpm lint; next typegen; pnpm typecheck; 47 tests passed; isolated pnpm build passed on Next 16.3.5. No dependency additions. |
| T. PostgreSQL | VERIFIED | Real PostGIS isolated DB migration roundtrip, constraints, restricted grants, all 16 mappings, tenant negatives, locks, idempotence, corrections, rollback. |
| U. Docker | LIVE VERIFIED | Compose config --quiet passed; frontend rebuilt and backend/frontend recreated; backend/db/frontend running healthy. Webpack dev and localhost ports preserved. |
| V. Production image | VERIFIED | Dockerfile.prod built; non-root asserted; app.providers.events import works; /app/tests, .env, .git, pytest and Ruff absent. Existing ignored image-check helper reused. No remote CI run claimed. |
| W. Browser | LIVE VERIFIED | Existing authenticated IAB account: /properties → Busan sample property → 지역 시장. Full-page screenshot inspected; HTTP 200 confirmed in frontend logs, no nested-route 404. Existing license section and visitor chart intact. Events: BPAM ongoing Oct1–7; illustration fair upcoming Nov6–8; marathon Dec6. Haeundae counts ongoing1/next30-start0. Source link keyboard Tab usable. Full WCAG audit NOT VERIFIED. |
| X. Regression | VERIFIED | Full suites pass; before/after whole-row aggregate hashes equal on all 8 preexisting data tables listed below. No dashboard/import/expense/auth/visitor calculation changes. |
| Y. Limitations | NOT VERIFIED | Provider-wide zero-result wire shape, live provider error shape, complete cancellation/deletion semantics, snapshot consistency, guaranteed maximum range/page size, guide archive contents. TotalCount=0 fails closed with EVENT_EMPTY_CONTRACT_UNVERIFIED; district-level valid empty supported. Same-count upstream mutation cannot be fully detected. Abruptly killed jobs may leave RUNNING. Stored missing records can become stale, visibly disclosed. |
| Z. Manual procedure | VERIFIED | Commands below; manual event sync only. Backend event key separate from visitor key. No keys printed or committed. |

## Preserved preexisting data

Whole-row aggregate hashes matched immediately before and after the controlled sync:

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

## Exact local commands

Run in C:\Users\HDRBRND\Desktop\Web Workspace\accommodation. Existing private root .env supplies TOURISM_EVENT_API_KEY; do not put it in frontend variables. The following DB credential is exclusively the existing local development credential.

~~~powershell
# Already completed for this implementation; rerun only when applying code changes.
.\.tools\docker-compose.exe exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic upgrade head
.\.tools\docker-compose.exe up -d --build backend frontend

# Manual refresh, when required.
.\.tools\docker-compose.exe exec -T -e MARKET_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run python -m app.jobs.sync_events

# Open the local application.
Start-Process 'http://localhost:3000/properties'
~~~

Select a Busan-scoped property → 지역 시장 → 공식 행사·축제. The page reads stored data and does not call TourAPI on each view. Standard docker compose can replace the executable prefix if installed. Never delete data volumes. Future staging scheduling should review accommodation, visitors and events together.

## Related contracts

- [Event source](event-source.md)
- [Event implementation](events.md)
- [Architecture](architecture.md), decisions 055–057
- [API](api.md)
- [Database](database.md)
- [Market page](public-accommodation-market.md)

Phase 10A documents are historical discovery evidence; this implementation report supersedes their pre-implementation gate status.
