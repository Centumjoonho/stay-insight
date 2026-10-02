# Phase 10B official event context

Local-only implementation; no deployment, scheduler, map or owner-KPI changes. [Source evidence](event-source.md) and [verification](phase10b-verification.md).

## Source and geography

One provider: KTO KorService2/searchFestival2. TOURISM_EVENT_API_KEY is backend-only and independent of TOURISM_VISITOR_API_KEY even when credential values match. No image ingestion, raw payload storage, geocoding or manufactured detail URL. Provenance links to the official catalogue.

New fields lDongRegnCd=26 and lDongSignguCd map the 16 verified districts: 110 중구, 140 서구, 170 동구, 200 영도구, 230 부산진구, 260 동래구, 290 남구, 320 북구, 350 해운대구, 380 사하구, 410 금정구, 440 강서구, 470 연제구, 500 수영구, 530 사상구, 710 기장군. Resolve exact existing 부산광역시/SIGUNGU names and require all 16 exactly once; no UUID constants or legacy areaCode/sigunguCode dependency. Missing/unknown geography fails the batch, not fuzzy/address mapping or silently city-wide scope.

## Persistence and identity

Migration 0008_tourism_events follows 0007, adds app.tourism_events and nullable public_data_sync_runs.event_coverage only. Unique(source,source_event_id); identity uses official contentid, not title/date. Required source/dataset, region FK, legal-dong codes, title, start/end DATE; nullable address and raw source_status (progresstype). Collection/last-seen/created/updated timestamps are UTC. Dates must be valid and ordered. No missing-end repair: unverified missing required dates fail.

Venue/category/coordinates/detail URL/source-modified timestamp are omitted because their useful normalization contract is not sufficiently verified. Address combines optional addr1/addr2. No new dependency. One (region_id,start_date) index supports geographic date reads; unique identity also indexed. Runtime SELECT only; ingestion SELECT/INSERT/UPDATE, no DELETE or added tenant rights.

## Collection and failure

Actual command: python -m app.jobs.sync_events. Collection uses Seoul today minus 30 through plus 180 days inclusive (210-day difference). Earlier-starting multi-day events are retained as one row when returned overlapping the window. A bounded live observation showed a January–December event returned for an October query; this is evidence of overlap behavior, not an exhaustive completeness guarantee.

Page size 2 is the observed working size, an intentionally conservative initial choice. Maximum 100 pages (200 rows), 2 MiB/response, 20 seconds/request, maximum 3 attempts/page. Operational bounds are not provider quota promises. Retry only network errors/429/5xx; reject permanent 4xx, malformed JSON and response-contract errors. HTTPS only, redirects rejected, one-time key decoding before URL encoding; no key/URL/raw provider errors in diagnostics.

Validate page/count consistency, duplicate content IDs, required dates/geography and overlap; changes in totalCount fail. Same-count concurrent upstream mutation cannot be fully detected (no verified snapshot token). No live zero-result envelope was captured: totalCount=0 currently fails with EVENT_EMPTY_CONTRACT_UNVERIFIED rather than guessing an empty wire schema. District-level empty API results after a successful Busan sync are supported. This conservative provider-wide zero limitation is explicit, not a successful empty ingestion claim.

Own advisory lock public-events:KTO_TOURAPI_EVENTS; a committed RUNNING row precedes a locked fetch/validate/publish transaction, following existing public-sync patterns. Event source differs from MOIS/visitor. Success has COMPLETED counts and event_coverage start/end/SOURCE_QUERY_ONLY. Does not reuse visitor_coverage or closure semantics. Failed parsing/network/publication rolls back event updates, records safe FAILED where DB reachable, and command exits nonzero. A killed process may leave RUNNING; long network-bound transaction is bounded but not optimized with a queue.

Same identity updates corrections without duplicates; identical rows update last_seen_at/collected_at and count unchanged. Missing rows are retained, never interpreted as cancelled/deleted. Retained rows may be outdated; UI warns and future date filtering hides past events. Provider cancellation field is displayed literally when meaningful; no invented enum. Source completeness and cancellation latency remain unknown.

## API and UI

GET /api/v1/market/events requires property_id, authenticated JWT and organization membership, then scoped property lookup. Optional from_date/to_date; default today to today+90, maximum difference 180 days; limit default50, 1–100. Stored DB only. Missing property region does not become Busan-wide data.

Response: available/reason, scope, from_date/to_date/reference_date, events, total_count/truncated, summary, source, warnings. Latest successful event collection window must contain requested dates or reason OUTSIDE_COLLECTED_WINDOW; never-synced is NOT_SYNCHRONIZED. latest_sync_status reports last attempt separately. Explicit valid empty list means no stored matching official-source events, not no real-world events.

Temporal state relative to Seoul today: UPCOMING if start>today, PAST if end<today, otherwise ONGOING. Date overlap filters both endpoints inclusively. Ongoing first, then start_date and source_event_id for deterministic ordering. Summary counts all stored region events ongoing today / starting in (today,today+30], independent of result limit and custom read window; suppressed when that summary interval is outside collection coverage.

The existing market page adds EventView after accommodation and visitors. Server API forwards token/org; event 5xx becomes a section error, auth/non-API errors propagate. Semantic list, h2/h3, time elements, Korean dotted dates and textual statuses. No images/map/client business calculations. Source status and date-derived status are distinct. UI clearly states source-limited coverage and no accommodation demand/revenue effect.

## Local operations

From repository root, after code updates (existing local development credentials only):

~~~powershell
.\.tools\docker-compose.exe exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic upgrade head
.\.tools\docker-compose.exe up -d --build backend frontend
.\.tools\docker-compose.exe exec -T -e MARKET_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run python -m app.jobs.sync_events
~~~

Private root .env supplies TOURISM_EVENT_API_KEY; Compose forwards only to backend. Standard docker compose may replace the prefix when available. Never print rendered full Compose environment or delete volumes. Production frontend builds run in a separate one-off container. Keep localhost:3000 / localhost:18000 and internal backend:8000; existing Webpack and image-copied frontend behavior unchanged.

Browser: login → 내 숙소 → a Busan-scoped property → 지역 시장 → 공식 행사·축제. No real owner edits needed. No automatic event sync: later review MOIS, visitors and events scheduling together, without creating cloud jobs here.
