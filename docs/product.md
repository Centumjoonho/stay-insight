# Stay Insight product specification

Status: broader MVP contract. Phases 1–3 implement the platform, authentication, property foundation and generic CSV reservation imports. Later financial/market capabilities below remain proposals. See imports.md for the current import contract; Phase 3 supports CP949 fallback, full-row upserts and request-local files, without room quantities, actual-stay confirmation or KPI computation.

## Purpose and audience

Help Korean accommodation owners manage their actual reservations, revenue, expenses, and operating results in one place, with separately attributed public market context. Initial public-data coverage is Busan. Use Korean UI copy, KRW, and Asia/Seoul business dates. One organization can own multiple accommodations; the first onboarding flow creates one organization and its owner membership.

## MVP acceptance scope

| Capability | Minimum acceptance behavior |
| --- | --- |
| Authentication | Supabase sign-up, verification, sign-in, sign-out, and password recovery; API rejects invalid sessions and inactive memberships |
| Accommodation registration | Owner manages name, type, address/district, optional coordinates, and dated sellable-unit inventory; access is organization-scoped |
| CSV import | Download documented template, upload, map/validate, preview row errors and proposed changes, then explicitly commit atomically; repeat imports do not duplicate data |
| Expenses | Create, list, correct, and void categorized KRW operating expenses by accommodation and incurred date, with audit history |
| Dashboard | Period and accommodation filters; actual revenue, ADR, occupancy, RevPAR, operating profit, channel breakdown, and monthly comparison, with completeness and estimation labels |
| Public accommodation market | Busan list/map with official source, geographic coverage, observation date, and refresh date; public listings never imply actual occupancy or revenue |
| Visitor trends | Display available visitor time series with provider definition, unit, geography, and period; visitor estimates are labeled |
| Local events | Source-linked event dates, location, status, and last update; events provide context without claiming revenue causation |
| Anonymous benchmarks | Show only approved aggregate releases meeting consent and privacy rules; otherwise show an insufficient-data state |

No Airbnb scraping, booking engine, OTA live synchronization, AI pricing, investment analysis, billing, native mobile app, or microservices.

## Core workflow

An owner signs in, registers an accommodation and its inventory history, imports a reservation CSV, reviews validation, and commits. They enter operating expenses and review results for a chosen period. A separate market area displays public Busan listings, visitor trends, and events. Benchmark cards remain unavailable until an eligible release exists.

The MVP uses a documented canonical CSV with manual column mapping. It does not promise universal OTA file compatibility. Initial limits: 5 MiB and 10,000 rows per file, UTF-8 or explicitly selected CP949; reject unsupported formats and ambiguous dates/numbers. These are product defaults to validate with real owner samples before launch.

Required reservation data: stable source reservation ID, source system/channel, check-in, check-out, status, room quantity, and gross accommodation charge. Completed stays also require actual occupied-unit-night evidence, either nightly rows or an owner-confirmed completed-stay record. Nightly revenue and refunds may be supplied explicitly. Do not silently treat net payout as gross revenue. Reject unsupported currency, same-day stays, contradictory statuses, or unclassified fees; same-day/day-use accounting needs a later explicit metric contract.

An import previews additions, exact duplicates, corrections, and errors. Exact duplicates are no-ops. Changed source records require explicit correction confirmation and replace prior active facts in one transaction. Any blocking row error prevents the whole commit. A preview is revalidated at commit so concurrent changes cannot silently overwrite it.

## Proposed service-night metric contract, version 1 (future)

These are management reporting metrics, not statutory accounting or tax statements. Each rentable room or whole-home listing is one sellable unit; guests and beds are not units unless the property's declared inventory model explicitly sells beds. Only comparable inventory models can share a benchmark cohort.

Use half-open local-date intervals `[start, end)`; checkout date contributes no occupied night. Audit timestamps use UTC. Recognize completed-stay accommodation revenue on service nights, not booking, settlement, or payout date. Future confirmed stays are shown separately as booked activity and excluded from actual performance. Do not automatically mark elapsed bookings completed.

| Metric | Definition and exclusions |
| --- | --- |
| Room revenue / 매출 | Completed-stay gross accommodation charges minus linked accommodation refunds, before channel commissions. Exclude deposits, cleaning/ancillary charges, cancellation fees, and no-show fees from MVP revenue calculations; unsupported amounts are flagged during import |
| Sold unit-nights | Actual occupied units summed by service date; completed complimentary stays count as occupied, with zero room revenue. Cancellations and no-shows contribute zero |
| Available unit-nights | Sum of dated sellable capacity minus owner-recorded out-of-service units; unsold rooms remain available |
| ADR / 평균 객실 단가 | Room revenue divided by sold unit-nights |
| Occupancy / 객실 점유율 | Sold unit-nights divided by available unit-nights, multiplied by 100 |
| RevPAR / 판매 가능 객실당 매출 | Room revenue divided by available unit-nights |
| Operating expenses | Non-void operating expense entries recognized by incurred date, including separately entered OTA commissions; exclude capital purchases, loan principal, distributions, and income tax |
| Operating profit / 영업이익 | Room revenue minus recorded operating expenses; label as management operating profit and show expense coverage, since excluded ancillary income and incomplete expenses affect completeness |
| Channel revenue | Room revenue grouped by normalized booking channel; unknown channel is an explicit bucket; groups reconcile to total revenue |
| Monthly comparison | Calendar months in Asia/Seoul; show absolute change and percentage change against the previous month. For a current partial month, compare equivalent elapsed days and label partial periods; use null percentage if prior value is zero or negative |

Normalize tax basis as owner-reported VAT-inclusive accommodation charges and expenses for this management MVP. Do not estimate tax from a net-only amount. Records with unknown/incompatible tax basis cannot enter comparable metrics until resolved. Display the basis in reports; this definition must be reviewed with pilot owners before implementation is finalized.

Money is integer KRW, including signed refund adjustments. Divide with decimal arithmetic and round only display values (KRW to nearest won, ratios to two decimal places, half-up). If allocating a multi-night total without supplied nightly amounts, distribute integer won evenly and assign the remaining won to earliest nights deterministically. Label affected revenue-by-period, ADR, RevPAR, and profit as estimated, even though the reservation total is owner-provided. Link later refunds to the original stay and restate affected service periods; preserve correction history and calculation timestamps.

Compute organization totals from summed numerators/denominators, not averages of property ratios. Missing inventory, unconfirmed completion, missing income coverage, or unconfirmed expense coverage must be explicit. A zero is valid only where relevant coverage is confirmed. Return null with a reason when a required input or denominator is missing or zero. Do not silently sum incomplete properties as a complete organization total. Block contradictory inventory/occupancy facts instead of capping occupancy at 100 percent.

## Trust and source presentation

Each metric/result includes source category (`owner`, `public`, or `benchmark`), source references, reporting period, scope/geography, calculation version and time, coverage, `is_estimated`, and estimation method where applicable. Public results additionally identify publisher, dataset URL/ID, unit, provider methodology, observation/publication time, retrieval time, and license. Unknown metadata stays unknown, not fabricated.

Use distinct UI sections and labels for owner facts, public market context, and benchmark releases. No blended market/owner revenue total. Label stale, unavailable, partial, estimated, and insufficient-data states in Korean. Public accommodation counts and visitors do not establish competitors' revenue, occupancy, or causal event effects. Comparisons require compatible period, unit, inventory model, and calculation basis.

Candidate sources are official Busan/open-government accommodation and event datasets and official tourism statistics. Provider selection, licensing, geographic coverage, refresh schedules, and field definitions must be verified before integration. No provider availability or data values are promised here. A failed refresh retains the last successful snapshot with its timestamp and stale state; it must never generate sample production results.

## Benchmark release policy

Default off until owners opt in and the implementation passes privacy review and tests. Proposed launch floor: at least 10 distinct consenting organizations per fixed cohort/month; multiple properties from one organization count once toward the floor. This is a conservative product threshold, not a guarantee of anonymity.

Use fixed completed-month cohorts by broad Busan geography and inventory type. Require complete compatible reporting and no organization contributing more than 20% of either available unit-nights or room revenue. Suppress failing cohorts; do not publish zero or interpolated results. Publish only approved aggregate metrics, a coarse contributor-count band, methodology, and release date. Do not expose identifiers, raw observations, per-property rankings, or arbitrary filters. Prevent overlapping releases and differencing through a fixed release grid and complementary suppression; this must be designed and tested before activation.

Consent withdrawal excludes future computation and invalidates affected served releases pending recomputation. The regular API can read releases only; it cannot run arbitrary cross-tenant aggregation. Until all gates pass, the feature displays insufficient data and requires no synthetic benchmark.

## Delivery gates

1. Agree on this product/data contract and scaffold tooling without shipping features implicitly.
2. Deliver authentication, organization isolation, accommodation/inventory, with negative authorization tests.
3. Deliver import and expenses, with transactional and correction tests.
4. Deliver metrics/dashboard, with formula, coverage, attribution, and browser tests.
5. Integrate verified public sources and Kakao Maps; then enable benchmarks only when their release gates are met.

Each feature needs lint, type-check, and relevant tests before completion. No credentials or deployments are required for this documentation task.


## Implemented Phase 4 cost foundation

[expenses.md](expenses.md) defines the implemented operating-expense contract. It supersedes the
earlier proposal to enter OTA commissions manually: reservation channel_fee is the sole reported
platform-fee source in Phase 4. Do not duplicate it in manual operating costs.
Manual expenses require explicit FIXED/VARIABLE and accept whole nonnegative KRW including zero.
Physical deletion with explicit UI confirmation is allowed; historical void/audit revisions remain
a future proposal. The period summary attributes fees to check-in date, all recorded statuses,
and discloses missing fees. This known-cost view is separate from the future service-night metric
contract above and must not be treated as profitability.

Operating profit is NOT implemented in Phase 4. Phase 5 must explicitly design reconciliation
between reservation fees, revenue recognition and completed-stay metrics before financial KPIs ship.

## Implemented Phase 5 dashboard-v1

The current dashboard implements the separately versioned [metrics.md](metrics.md) contract.
Its primary revenue uses eligible check-in dates; operational ADR/RevPAR use proportional overlapping
night allocation. CONFIRMED and UNKNOWN count, CANCELLED does not. These reservation proxies use one
room per reservation and current registered inventory; occupancy/ADR/RevPAR are explicitly estimated.
They do not claim actual completed-stay or sellable-inventory measurement. The earlier service-night,
dated-inventory, refund and verified-completion definitions remain future proposals, not this release.

Known operating profit is recorded gross minus manual expenses and known reservation fees once.
Missing fees and expenses are disclosed; profit is not net/accounting profit. Current months stop
today in Seoul and compare equivalent prior-month/year days. No-data states must not fabricate zero
business activity. Phase 4 all-status cost summaries remain unchanged, with cancellation/date-range
differences explained in the dashboard. No Phase 6/public/benchmark features are implemented.
