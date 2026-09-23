# Phase 2 API

FastAPI is authoritative. Base URL locally: `http://localhost:8000`. Swagger: `/docs`. OpenAPI: `/api/v1/openapi.json`. Auth and business responses must not be shared-cached.

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
