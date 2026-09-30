# Phase 9 — source-gated visitor foundation

**LIVE VISITOR PROVIDER NOT VERIFIED. Monthly visitor feature is NOT COMPLETE.**

The source-discovery exception in the Phase 9 request limits this change to a provider interface, normalized internal contract, tests, configuration placeholder and source documentation. See [verified facts and blockers](tourism-visitor-source.md). No visitor DB table, sync command, HTTP endpoint or market UI is claimed to exist.

## Pre-implementation inspection

Started with clean main at 3bb4da4. Phase 8 had been committed separately at 59e9584 on phase8/staging-deployment. Existing phase9/tourism-visitors also pointed to 3bb4da4; switched to it and fast-forwarded to 59e9584 without creating a commit. No reset/stash/clean/revert, user work deletion or push.

Current market: MOIS provider → LicenseRecord/ProviderBatch → public_sync service → market repository → app public tables. HTTP reads stored data only. Source-keyed lock, transaction-local ingestion role, atomic publish, safe failure audit and last-good preservation are reusable patterns; accommodation-specific date/closure rules must not be copied blindly.

Current Alembic file head: 0006_postgis_availability. Actual local application DB at inspection: 0005_property_region_write. No migration created/applied in this phase. A future verified storage model will require an additive migration after 0006; no speculative columns, constraints or grants are added now.

Region stores internal UUID, sido_name, sigungu_name and SIGUNGU for 16 Busan districts. Property selection is explicit and nullable. Source codes need independent mapping. public_data_sync_runs has source and generic status/counts but also accommodation-specific closure/reference fields: future visitor runs should reuse it with a distinct source and separately reviewed coverage metadata, not overwrite MOIS runs.

The protected Next.js market page uses serverApi.accommodationMarket → /api/v1/market/accommodations. FastAPI verifies signed JWT, membership, restricted-role context and organization-scoped property access. Those paths, dashboard-v1, license-market-v1, existing source labels and all Phase 8 files remain unchanged.

## Internal code and tests

backend/app/providers/tourism_visitors.py provides DailyVisitorObservation, VisitorProvider and UnverifiedVisitorProvider. It has no HTTP or DB access. The placeholder always raises LIVE_VISITOR_PROVIDER_NOT_VERIFIED, even with a configured key; it cannot be enabled accidentally through configuration.

The immutable daily DTO preserves exact Decimal/null, separate source geography/category strings, reference day, estimated terminology, optional methodology version/source-update timestamp and aware collection time. It rejects floats, negative/nonfinite values, false actual-count claims, unsupported scope, monthly relabeling and unexpected ownership fields. Unknown provider metadata stays null. Source region/category strings are deliberately opaque; accepting a DTO does not certify a production mapping.

Tests contain clearly labeled internal TEST identifiers and arithmetic boundary inputs based on documented daily semantics. They are NOT real API responses, real Busan visitor values or provider-contract verification fixtures. No fixture loader, startup seed, monthly aggregation, MoM/YoY or live fallback exists. Tests stay under backend/tests and are excluded from Dockerfile.prod.

## Pending implementation after gate passes

Only after the source contract is resolved: exact storage/unique key and minimum ingestion grants; dataset-specific lock; idempotent revision-aware sync/audit; bounded HTTP/page handling; property-authorized read endpoint; monthly comparisons and chart/table. Missing month remains null; denominator <=0 or incompatible methodology/scope suppresses comparison. Latest month means latest provided complete period, not today. Staleness must follow verified publication cadence, not MOIS's seven-day rule.

Visitor statistics are not accommodation reservations, guests, occupied rooms, competitor revenue or accommodation demand. They do not enter owner KPIs, causal analyses, rankings or scores.

## Local manual support

Use localhost:3000 and backend localhost:18000; Swagger localhost:18000/docs. Existing Docker contracts are unchanged. No frontend source edit means no frontend rebuild is needed for this foundation.

| Requested check | What is actually available now |
| --- | --- |
| Environment | No new required variable. backend/.env.example contains commented reserved TOURISM_VISITOR_API_KEY only; not read or wired into Compose |
| Visitor sync command | None implemented: do not run a guessed app.jobs.sync_tourism_visitors command |
| Sync status | No visitor run can be created; existing MOIS history unchanged |
| Visitor row count | No visitor table; absence is not an observed count of zero |
| Available periods/latest region | Not available; no official observations stored |
| Existing property | Open localhost:3000/properties, choose an existing property |
| 지역 시장 | Follow 지역 시장; existing official accommodation information remains |
| Visitor section | Not added under the discovery gate; no placeholder numbers/chart |
| MoM/YoY | Not implemented until official monthly/comparability contract is verified |
| Missing month | DTO null vs zero tested; monthly history/chart tests are deferred |
| No region | Existing Phase 7 behavior unchanged; visitor behavior deferred |
| Not synchronized | No visitor endpoint/state exists; do not mislabel provider-unverified as a completed integration waiting for sync |
| Fixtures vs live | All new sample values are test-only; no live visitor data has been fetched |

Safe test command from the repository (no provider key/network calls):

~~~powershell
.\.tools\docker-compose.exe exec -T backend uv run pytest tests/test_tourism_visitors.py -q
~~~

Read-only confirmation that no visitor table was created (expected blank/null):

~~~powershell
.\.tools\docker-compose.exe exec -T db psql -U postgres -d stay_insight -c "SELECT to_regclass('app.tourism_visitor_stats');"
~~~

Do not edit existing demo rows, source timestamps or market data to simulate visitor scenarios. No cloud deploy, remote migration, Render Cron activation or local automation change is part of this phase.
