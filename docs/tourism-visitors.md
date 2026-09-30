# Phase 9B official daily regional visitor trends

Phase 9A decision B remains authoritative: only the official daily source is verified. **No official monthly visitor count is produced.** Owner dashboard-v1 and MOIS license-market-v1 remain separate and unchanged.

## Source and categories

KTO dataset 15101972, locgoRegnVisitrDDList only. See [source evidence](tourism-visitor-source.md) and [Phase 9A verification](tourism-visitor-contract-verification.md). Categories remain 1 현지인(a), 2 외지인(b), 3 외국인(c). There is no TOTAL or category addition. The UI defaults to 외지인(b); residents are never relabeled outside visitors or guests.

The immutable 16-code mapping in app/providers/visitor_api.py resolves exact Busan district identities against app.regions, verifies exactly 16 records, and never embeds environment-specific UUIDs. Changed/unrecognized Busan codes/names fail validation. Historical geography/methodology comparability beyond this window is not claimed.

## Storage and permissions

Alembic 0007_tourism_visitor_daily follows 0006_postgis_availability. Shared app.tourism_visitor_daily stores source/dataset, mapped region, source code/name, category code/name, reference date, unscaled NUMERIC value, weekday fields and UTC collected/created/updated timestamps. Unique(source, source_region_code, visitor_category_code, reference_date) makes revisions idempotent. No mobility traces/device IDs/personal coordinates/raw payloads.

Runtime has SELECT only; the existing ingestion role has SELECT/INSERT/UPDATE, no DELETE and no owner-table rights. Existing tenant RLS is unchanged. Add nullable visitor_coverage JSONB to public_data_sync_runs; source KTO_DATALAB_VISITORS_DAILY isolates visitor runs from MOIS. Closure metadata remains its existing false default and has no visitor meaning. Visitor coverage is never stored in closure fields.

A missing provider observation creates no numeric row. If a previously observed key disappears from a successfully fetched date, its value becomes null (withdrawn/unavailable), preserving identity/audit timestamps and suppressing calculations. This prevents stale values from silently completing windows. Explicit zero remains numeric zero. Parser failures roll back publication; they do not turn existing observations into missing values.

## Collection

The command validates dates before calls, uses one calendar day per request window, size 1000, at most 10 pages/day, a 4 MiB response limit, 20-second request timeout, up to three attempts for transient HTTP/network failure and at most 450 HTTP attempts per invocation. Percent-encoded keys are decoded once then encoded with the request query, matching Phase 9A; key/URL/raw error output is forbidden. XML or top-level provider error responses fail safely. HTTP 200 alone is insufficient.

All nationwide rows are checked for types, valid dates, nonnegative exact decimal strings, categories, duplicate identities, weekday/date agreement and pagination consistency; only the 16 verified Busan codes are published. Missing Busan pairs in an otherwise valid complete page sequence are audited as missing, not guessed or padded. No stable upstream snapshot token exists: total changes and duplicate/page corruption are detected, but same-count concurrent revisions cannot be guaranteed absent.

Discovery starts at Seoul yesterday, walks backwards up to TOURISM_VISITOR_LOOKBACK_DAYS (default 60, allowed 1–120), and stops at the newest date with Busan observations. This is the latest available observed date, not an official completion guarantee. If none exists, record failure and preserve last-good data. Partial category coverage does not make a day officially complete.

Bootstrap fetches 120 calendar days ending at the discovered date. Normal refresh uses TOURISM_VISITOR_REFRESH_DAYS (default 35, allowed 1–120). Both recheck empty discovery dates to invalidate withdrawn observations where relevant. These windows are Stay Insight operational choices, not official revision/lag guarantees. Revisions older than the refresh window require an explicitly run bootstrap; no automatic multi-year history fetch.

A visitor-specific transaction advisory lock prevents concurrent visitor publication and does not block the MOIS lock. One transaction holds that lock while fetching/validating and then publishing; this is a deliberate simple local MVP design, with a bounded but potentially long transaction. A committed RUNNING audit precedes it. Failure records safe FAILED status in a fresh transaction and returns nonzero; pre-DB failure has safe command output only. A competing job records VISITOR_ALREADY_RUNNING and exits nonzero. Abrupt process termination can leave RUNNING audit; automatic recovery is not implemented. No scheduler was added or changed.

visitor_coverage records attempted start/end, latest observed date, per-date missing code:category pairs, missing_pair_count and APPLICATION_COVERAGE_ONLY. Discovery dates after the latest observation may legitimately all be missing; distinguish those from gaps inside the bootstrap history.

## Derived metrics and missing data

GET /api/v1/market/visitors requires authenticated organization membership and scoped property ownership before local public-table reads. Parameters: property_id required; category 1/2/3 default 2; days 1–120 default 90. No external calls occur during HTTP requests.

Each selected category/region uses its own latest non-null stored date. History contains every requested calendar day through that date, with null gaps. The latest category date can differ from another category. If no successful visitor data exists, available=false/NOT_SYNCHRONIZED. Without property region, PROPERTY_REGION_UNAVAILABLE and edit CTA; no Busan-wide fallback.

- average_7d: exactly seven consecutive observations ending on latest date, divided by seven.
- average_28d: exactly 28 consecutive observations, never a monthly average.
- previous_7d_average: immediately preceding seven dates.
- change_7d_percent: (current minus previous) / previous * 100 only if both complete and previous > 0.

Decimal calculations use precision 80, display averages/percentages ROUND_HALF_UP to two decimals; API serializes Decimal strings. Percentage uses unrounded averages. Missing any required day suppresses the relevant average/comparison; never divide by fewer days. No same-weekday metric, category total, monthly sum or MoM/YoY visitor metric was added. API returns source/category/scope, history, coverage, selected latest date, last collection time, elapsed days and warnings. Unknown methodology version stays null.

## UI

Existing /properties/[id]/market adds a separate 공식 지역 방문 추이 section. The GET category form uses categories returned by the API and preserves the route. Cards show 최근 제공일, 일별 추정 방문자, 최근 7일 일평균, 최근 28일 일평균 and 직전 7일 대비. Recharts has connectNulls=false; an expandable accessible table contains exact strings and explicit 자료 없음. Number conversion is limited to chart plotting. No client business calculations.

A source/methodology note says these are mobile-network based estimated daily indicators, not lodging guests, reservations or occupancy. Coverage is application coverage, not provider completeness. Publication lag remains unresolved: show latest date/collection time/days elapsed and an informational delay note, not MOIS's seven-day stale rule. Visitor API infrastructure failure has a separate error message while accommodation data remains visible; authorization/redirect errors still propagate.

## Exact local commands

From the repository root; use docker compose instead of .tools/docker-compose.exe if installed. Keep TOURISM_VISITOR_API_KEY in ignored root .env. Compose passes it only to backend; no frontend secret variable.

~~~powershell
.\.tools\docker-compose.exe up -d db backend
.\.tools\docker-compose.exe exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic upgrade head
.\.tools\docker-compose.exe up -d --build --force-recreate backend frontend
# One-time initial history:
.\.tools\docker-compose.exe exec -T -e MARKET_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run python -m app.jobs.sync_tourism_visitors --bootstrap
# Subsequent refresh:
.\.tools\docker-compose.exe exec -T -e MARKET_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run python -m app.jobs.sync_tourism_visitors
~~~

DB credentials above are existing LOCAL DEVELOPMENT defaults only, never hosted settings. Do not delete volumes. Frontend remains localhost:3000, API localhost:18000, internal backend:8000, Webpack development with existing polling workaround. Frontend source is image-copied and requires rebuild after edits. Production Dockerfile excludes tests/fixtures.

Manual browser: login → 내 숙소 → a property with a Busan district → 지역 시장 → select each category and 조회 → inspect latest date, cards, chart, 일별 자료 표 보기, source and coverage. No owner business-data edits are required. [Actual verification and limitations](phase9b-verification.md). No deployment, Render Cron activation, events/maps/benchmark or Phase 10.
