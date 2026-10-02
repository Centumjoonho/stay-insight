# Phase 2 API

FastAPI is authoritative. Base URL in local Docker: `http://localhost:18000`. Swagger: `/docs`. OpenAPI: `/api/v1/openapi.json`. Auth and business responses must not be shared-cached.

## Endpoints

| Method/path | Authentication/context | Result |
| --- | --- | --- |
| GET /api/v1/health | Public | 200, {"status":"ok"} |
| GET /api/v1/me | Bearer | 200, user_id and memberships (organization_id, organization_name, role) |
| POST /api/v1/onboarding | Bearer | 200, organization |
| POST /api/v1/properties | Bearer + X-Organization-Id | 201, property |
| GET /api/v1/properties | Bearer + X-Organization-Id | 200, items and total |
| GET /api/v1/properties/{property_id} | Bearer + X-Organization-Id | 200, property |
| PATCH /api/v1/properties/{property_id} | Bearer + X-Organization-Id | 200, updated property |

No deletion or membership-management endpoint exists. OWNER and MEMBER have the same property-management permissions in Phase 2. Schema support for multiple memberships is independent of the initial UI's first-membership selection.

## Onboarding

Request fields: `organization_name` (trimmed, 1–200 characters). The service takes a transaction-scoped advisory lock keyed to the verified user, creates an organization and OWNER membership in one transaction, and returns id, name, created_at and updated_at.

Retrying with the same name and the user's sole OWNER membership returns the existing organization. An already-onboarded user with a different name/membership context receives 409. Names are not globally unique: different owners may use the same business name. Concurrent identical requests cannot duplicate organizations. No client-supplied user or organization ID is accepted.

## Properties

Creation fields:

| Field | Contract |
| --- | --- |
| name | Required, trimmed nonempty string, max 200 |
| address | Required, trimmed nonempty string, max 500 |
| road_address | Optional/null, max 500 |
| accommodation_type | HOTEL, MOTEL, HOSTEL, GUESTHOUSE, LIFESTYLE_ACCOMMODATION, PENSION, VACATION_RENTAL, OTHER |
| inventory_units | Required integer, 1 through PostgreSQL integer maximum |
| timezone | Asia/Seoul by default; Phase 2 reporting scope is fixed to this timezone |
| latitude / longitude | Optional/null pair, latitude -90..90, longitude -180..180, finite numbers |

Organization ownership comes from the verified header context, never the JSON body. Unknown fields are rejected, including `organization_id`. Responses include the above fields plus id, organization_id, created_at and updated_at. UUIDs and timezone-aware timestamps serialize as strings.

PATCH accepts any nonempty subset of creation fields. Required fields cannot be set to null. Coordinates may be cleared together; merged values are validated before writing. Organization ownership and IDs are immutable. Updates include explicit organization predicates and PostgreSQL RLS checks.

List pagination: `limit` defaults to 50 (1–100), `offset` defaults to 0 (nonnegative). Ordering is created_at, then id. The total count is scoped to the same organization.

## Errors and headers

- 401: missing/invalid/expired token, with WWW-Authenticate: Bearer.
- 403: selected organization is not a current membership.
- 404: property does not exist in the authorized organization, including a foreign property ID.
- 409: conflicting repeat onboarding.
- 422: malformed UUID/header, invalid or missing fields, null required values or inconsistent coordinates.
- 503: authentication configuration/provider is unavailable, or the database runtime role is unsafe.

Errors use FastAPI's detail response shape. The UI maps common errors to Korean messages and never renders raw database errors. Access tokens are not included in response models. CORS allows only configured origins and the necessary Authorization, Content-Type and X-Organization-Id headers; browser origins do not authorize data access.

See [authentication.md](authentication.md) for Supabase configuration, token flow and migration commands.

## Phase 3 imports and reservations

All endpoints below require Bearer authentication. All except preview also require X-Organization-Id and current membership.

| Method/path | Input / result |
| --- | --- |
| POST /api/v1/imports/preview | Multipart file; encoding, headers, first 10 rows, exact total_rows, warnings. No writes. |
| POST /api/v1/imports/validate | Multipart file, property_id UUID, channel, column_mapping JSON string; validation summary. No writes. |
| POST /api/v1/imports | Same multipart fields; import metadata/result, duplicate flag, counts, safe validation errors. |
| GET /api/v1/imports | Optional property_id/channel, limit 1–100 (default 50), offset >=0; items and total. |
| GET /api/v1/imports/{import_id} | Organization-scoped batch metadata and validation summary. |
| GET /api/v1/reservations | Optional property_id/channel/from/to/reservation_status plus limit/offset; items and total. |
| GET /api/v1/reservations/{reservation_id} | Organization-scoped normalized reservation. |

Channels: GENERIC, AIRBNB, BOOKING, AGODA, DIRECT. These are source labels; only GenericCsvAdapter exists. Statuses: CONFIRMED, CANCELLED, UNKNOWN. Date filters use inclusive check-in dates; from > to returns 422. Lists order imports by newest created_at then id, reservations by latest check_in then id.

Example column_mapping form field (a JSON string, not a separate JSON request body):

~~~json
{"external_reservation_id":"예약번호","check_in":"체크인","check_out":"체크아웃","gross_revenue":"총매출","channel_fee":"수수료"}
~~~

Import responses include id, property_id, organization_id, channel, filename/checksum, status, total_rows, imported_rows, rejected_rows, inserted_rows, updated_rows, actor/timestamps, mapping/adapter version, validation_errors, error_message and duplicate. Successful and failed processed batches return 200 with explicit status; callers must inspect status. Duplicate completed files return the previous batch with duplicate=true. Malformed CSV/mapping returns 422, oversized files/requests 413. No partial import is performed.

Validation responses contain total_rows, valid_rows, invalid_rows, errors[{row,field,message}], errors_truncated and warnings. Only the first 100 errors are returned and stored. Errors never echo raw cell values. Unexpected batch-write errors roll back all reservation changes and return safe FAILED metadata when the outer transaction remains usable.

Reservation amounts are exact decimal strings/null, dates are YYYY-MM-DD, timestamps carry UTC offsets, booked_nights is backend-calculated, and source=owner_csv with import_id identifies provenance. net_revenue_method describes gross minus reported fee; missing fee yields null net. No KPIs are returned.

See [imports.md](imports.md) for encoding, limits, full-replacement upsert semantics, retries, source contract and manual testing.

## Phase 4 expenses

All expense endpoints require Bearer + X-Organization-Id and current membership.
See [expenses.md](expenses.md) for exact validation, source/coverage metadata and manual testing.

| Method/path | Contract |
| --- | --- |
| POST /api/v1/expenses | property_id, expense_date, category, explicit cost_type, exact amount, optional memo; 201 |
| GET /api/v1/expenses | Required property_id; optional inclusive from/to, category, cost_type, limit 1–100, offset >=0; items/total |
| GET /api/v1/expenses/summary | Required property_id/from/to; manual/fixed/variable/fee/known totals and breakdowns |
| GET /api/v1/expenses/{expense_id} | Authorized manual expense; 200 |
| PATCH /api/v1/expenses/{expense_id} | Nonempty subset of expense_date/category/cost_type/amount/memo; 200 |
| DELETE /api/v1/expenses/{expense_id} | Authorized physical manual-expense deletion; 204 without body |

Static summary route precedes UUID routes. Unknown request fields are rejected. Only memo is nullable
on PATCH; ownership/source/creator/property are immutable. Decimal amounts serialize as strings.
Lists sort newest expense date, then creation timestamp and ID descending.
404 conceals foreign IDs, 403 rejects nonmembers, 401 rejects missing/invalid auth, 422 rejects
invalid fields/ranges. OWNER and MEMBER can manage expenses; no runtime migration grants are added.

Summary uses expense_date for manual rows and check_in for non-null reservation fees, inclusive bounds,
all reservation statuses. It includes reservations_with_fee/reservations_missing_fee and source metadata.
known_cost_total is manual_expense_total + channel_fee_total. No synthetic fee expenses or profit calculation.
Category/type list filters do not narrow the period-wide summary.

## Phase 5 dashboard (read-only)

| Endpoint | Query |
| --- | --- |
| GET /api/v1/dashboard/summary | Required property_id UUID, optional month YYYY-MM (Seoul current month default) |
| GET /api/v1/dashboard/trends | Required property_id UUID, optional months integer 1–24 default 12, optional ending month YYYY-MM |

Verified JWT, current organization membership and scoped property lookup are mandatory. Foreign
properties return 404, nonmembership/revocation 403, missing/invalid JWT 401, malformed/future months
or out-of-range months 422. Responses use no-store and existing error handling.

Summary returns property, period (inclusive dates, is_current_month, is_partial), financial,
operations, data_quality, channels, category_breakdown, metadata and comparisons.previous_month /
previous_year. Each comparison has the actual comparison period and a metrics map containing
available, absolute_delta, percentage_change and percentage_points. Decimal quantities are strings;
undefined ratios/changes are null. Occupancy is a percentage value, not a 0–1 fraction.

Trends returns property, metadata and chronological items for every month, including zero-data
months. Each row includes month/end_date/is_partial, revenue, manual expenses, known fees/cost/profit,
occupancy/ADR/RevPAR/count, financial/operational presence flags and expense_count. These flags
distinguish aggregate zero from evidence of no business activity. No channels endpoint is needed.

See [metrics.md](metrics.md) for formulas, status policy, rounding, source and missing-data semantics,
and [dashboard.md](dashboard.md) for authenticated diagnostics and manual reconciliation.
Phase 4 expense summary retains all-status semantics; Phase 5 excludes CANCELLED.

## Phase 6 public accommodation context

GET /api/v1/market/accommodations?property_id=<UUID>&reference_date=<YYYY-MM-DD>
requires existing Bearer + X-Organization-Id authorization. Reference date defaults to Seoul today;
future dates and dates before 1901-01-01 return 422. Foreign properties return 404, nonmembers 403,
missing/invalid auth 401. No provider calls or writes occur during this request.
Response: property_id, region (SIGUNGU/name/admin association), reference/window dates,
market_context_available, reason, nullable metrics, freshness, warnings, source_category=public,
calculation_version=license-market-v1. Missing region and unsynchronized coverage return 200 with
PROPERTY_REGION_UNAVAILABLE / NOT_SYNCHRONIZED and metrics=null. Confirmed zero needs a completed
coverage assertion. Closure/new counts remain null when necessary dates are unavailable.
See [market contract](public-accommodation-market.md). The live REST adapter is implemented; availability still requires a successful sync and district association.
Current Docker host API is http://localhost:18000; the initial 8000 examples above are historical/host-only.

## Phase 7 property region selection

GET /api/v1/regions requires Bearer authentication, no organization header. Optional sido defaults
to 부산광역시 and level to SIGUNGU; unsupported scope returns 422. Returns an array of
{id, sido_name, sigungu_name, region_level} from supported normalized DB rows. No source raw payload.

POST/PATCH /api/v1/properties accept region_id (UUID or null). POST omission/null means unset;
PATCH omission preserves, null clears. Unsupported/nonexistent region returns 422. Existing
organization membership, tenant-scoped 404 and RLS remain mandatory. Property create/detail/list/update
responses add region_id and region (reference object or null). Addresses do not infer/change region.

Market response region.assignment_method is now EXPLICIT_SELECTION; it includes legacy explicit
admin choices without claiming administrator verification for new owner choices. Scope derives from
current property.region_id, independent of legacy address snapshots. All count/freshness/source
semantics stay license-market-v1. See [region behavior](property-region.md).

## Phase 9 source gate

No visitor HTTP endpoint is registered. /api/v1/market/visitors is a proposed name only, not an available route. No page-load external visitor calls or changes to accommodation responses. Source verification must precede persistence/read API/UI implementation; see [visitor status](tourism-visitors.md).

## Phase 9B daily visitors (supersedes Phase 9 source gate above)

GET /api/v1/market/visitors?property_id=UUID&category=2&days=90 is implemented. Authenticated membership and tenant-scoped property access are mandatory; cross-tenant property 404, invalid category or days outside 1–120 returns 422. category 1/2/3 only, default 2. Response includes available/reason, scope, selected category and official categories, latest date/value, rolling averages/change, daily gap-preserving history, source and coverage. Decimal values are JSON strings, missing values null. PROPERTY_REGION_UNAVAILABLE and NOT_SYNCHRONIZED are unavailable states, not zero. No upstream API calls during requests. See [full daily contract](tourism-visitors.md).

## Phase 10B events

GET /api/v1/market/events: required property_id; optional from_date/to_date and limit 1–100. Default today through +90 days, max date difference180. JWT/membership/scoped-property checks precede shared event reads. Source metadata and coverage separate from owner/visitor data; no upstream calls during HTTP request. [Full response/state/sort contract](events.md).
