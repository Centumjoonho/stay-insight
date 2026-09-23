# Phase 4: operating expenses

Phase 4 implements manual property operating expenses and a known-cost summary.
**Operating profit is NOT implemented in Phase 4.** Operating margin, ADR, occupancy,
RevPAR, break-even analysis and all other profitability calculations are deferred to Phase 5.

## Data and validation

app.expenses contains UUID id, organization_id, property_id, expense_date (DATE),
category, cost_type, amount (NUMERIC(18,0)), nullable memo (max 1,000 characters), source,
created_by_user_id, and timezone-aware created_at/updated_at.

Amount is exact whole KRW, from 0 through 999999999999999999. Python uses Decimal;
JSON responses use decimal strings. Requests accept integer JSON amounts or exact decimal
strings; floating-point JSON numbers, fractional KRW, negatives, booleans and nonfinite
amounts are rejected. The browser sends strings and formats with BigInt, never Number.
Zero is a valid recorded amount. A zero aggregate means no recorded amount, not proof
that all costs are recorded.

Source is MANUAL only. The VARCHAR field and explicit constraint can be extended by a future
migration; IMPORT, INTEGRATION and SYSTEM are not accepted today. Actor, source, ownership,
IDs and creation timestamp cannot be supplied or changed by the client.

Every expense explicitly selects FIXED (generally exists irrespective of occupancy) or
VARIABLE (generally varies with occupancy or activity). Category never infers cost type.

| Category | Korean label / use |
| --- | --- |
| RENT | 월세: property rent |
| MANAGEMENT_FEE | 관리비: building management charges |
| CLEANING | 청소비: cleaning services |
| LAUNDRY | 세탁비: linen/laundry |
| ELECTRICITY | 전기료 |
| GAS | 가스비 |
| WATER | 수도료 |
| SUPPLIES | 소모품 |
| LABOR | 인건비 |
| MARKETING | 마케팅: advertising and promotion |
| MAINTENANCE | 수선·유지보수 |
| SUBSCRIPTION | 구독료: operating software/services |
| INSURANCE | 보험료 |
| TAX_AND_FEE | 운영 관련 세금·공과금; not income tax, financing or tax accounting |
| OTHER | 기타 operating costs requiring a useful memo |

OTA_FEE and PLATFORM_FEE are not categories. Do not use OTHER or TAX_AND_FEE to duplicate
reservation fees. The UI warns against duplicate entry; it cannot determine whether a user's
free-form OTHER expense is actually an OTA charge. Manually adjusted platform fees require
a later explicit design. No recurring generation or receipts are implemented.

## Summary contract and sources

For one authorized property and inclusive from/to dates:

- manual_expense_total = recorded expenses in the expense_date range.
- fixed_expense_total and variable_expense_total partition manual expenses.
- category_breakdown and cost_type_breakdown partition manual expenses only.
- channel_fee_total = sum of non-null reservation.channel_fee in the check_in range.
- known_cost_total = manual_expense_total + channel_fee_total, each source counted once.

Reservation fee attribution is the **check-in DATE**, not checkout, payout, import timestamp
or nightly allocation. This matches Phase 3 inclusive check-in filtering. All recorded
reservation statuses participate (including CANCELLED and UNKNOWN) when a reported fee
exists; no cancellation/refund/actual-stay fee inference is performed. Cross-month stays
attribute the whole reported fee to check-in. Missing fee is unknown, excluded from the sum,
and disclosed as reservations_missing_fee; a reported zero counts as present.
reservations_with_fee gives coverage of the reported sum.

No expense row is synthesized from reservations. Latest imported reservation values are read
on each summary request, so an upsert changes the derived fees without copying them.
The response includes property, period, MANUAL and owner_csv source labels, check_in date
basis, and is_estimated=false: no fee is estimated. These are reported known costs, not audited
costs or complete financial performance. Public/market data is not used.

Summary cards always cover the selected date period. Category/type filters affect the manual
list only; this is explicitly labeled in the UI. This avoids presenting a filtered subset as
the property's full known costs.

## API and security

All endpoints require a verified Bearer identity, X-Organization-Id and current membership.
Existing OWNER and MEMBER roles have equal expense permissions. FastAPI resolves the property
within the authorized organization; foreign/missing property or expense IDs return 404.
A forged/revoked organization selection returns 403; missing/invalid/expired auth returns 401.

Repositories scope every read, count, aggregate, update and delete by organization.
Composite organization/property foreign keys prevent mismatched ownership. Forced RLS checks
transaction-local organization and current user membership. The runtime role receives SELECT,
INSERT, DELETE and UPDATE only for editable columns plus updated_at; no migration/schema powers.
The API rejects client organization/source/actor overrides. Changes commit before responding.

POST /api/v1/expenses returns 201.
GET /api/v1/expenses requires property_id; optional from/to/category/cost_type; limit 1–100
(default 50), offset >= 0. Order: expense_date, created_at, id descending. Returns items/total.
GET /api/v1/expenses/summary requires property_id/from/to; registered before UUID routes.
GET and PATCH /api/v1/expenses/{expense_id} return 200.
PATCH requires a nonempty subset of date/category/cost_type/amount/memo; only memo may be null.
DELETE /api/v1/expenses/{expense_id} returns 204 and physically removes the manual row.
The browser asks for explicit confirmation and refreshes the server-rendered list and summary.
No soft deletion, historical revisions or recovery are promised in this phase.

Invalid enums, reversed dates, out-of-bounds pagination and invalid amounts return 422.
All business responses remain private/no-store. CORS adds DELETE for configured origins only.
All frontend calls use the existing centralized FastAPI client; no direct business-table access.

## Migration and operation

0003_expenses follows unchanged 0002_csv_imports and 0001_foundation.
It adds only the expense table, constraints, organization/property/date/id index and RLS/grants.
The composite index supports property/date scans; low-cardinality category/type indexes are
deferred until measured query plans justify them.

Run from the repository root, using the existing local development administrator for migrations:

~~~powershell
docker compose config --quiet
docker compose exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic upgrade head
docker compose exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic current
docker compose exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic check
docker compose up --build -d --no-deps --force-recreate frontend
~~~

These are the documented local default admin credentials; use your configured migration
credentials if different. The normal restricted application login stays unchanged and is not
granted access to alembic_version. Source/migration directories are mounted into the development
backend, so no backend rebuild is needed for these Python-only changes.
Never remove the database volume. Downgrade drops expenses and is tested only in disposable
databases; do not run it against expense records you need to retain.
Webpack development and the production build command remain unchanged.

## Exact local manual test

Use an existing development property with imported reservations. Do not invent missing fees
or add synthetic records to a real production business.

1. Sign in at http://localhost:3000 and open the property, then 비용 관리.
2. The initial range is the current Asia/Seoul calendar month. Set a range containing the
   actual expense dates and reservation check-in dates you want to inspect.
3. Choose 비용 추가 and record RENT / FIXED / 1200000.
4. Add MANAGEMENT_FEE / FIXED / 250000, then CLEANING / VARIABLE / 300000,
   using dates inside that range. Each save opens the saved date so it is visible; return the
   filter to the full month when comparing monthly totals.
5. For a period without other manual expenses, confirm manual total 1,750,000원,
   fixed 1,450,000원 and variable 300,000원. With existing expenses, include their recorded amounts.
6. Check the separate read-only platform-fee card against the imported non-null channel_fee
   values whose check-in dates lie in the inclusive range. Do not assume any particular fee value.
7. Known total must equal 1,750,000 plus those fees (plus any preexisting manual expenses).
   Missing-fee counts must remain visible; no fee is manufactured.
8. Edit cleaning to 350000. For the same range, manual total becomes 1,800,000원
   when no other expenses exist; fixed is unchanged.
9. Choose 삭제 on cleaning, test 취소 first, then explicitly confirm deletion.
   Manual total becomes 1,450,000원; variable becomes 0원 if no other variable entries exist.
10. Filter FIXED: only fixed manual rows appear; summary still describes the full selected period.
11. Change the date range and category, and exercise pagination when more than 50 rows exist.
12. A different organization's user must receive 404 for these object IDs and 403 for a forged
    organization selection. Sign out: protected pages must require login.
13. Reopen CSV import/history/reservations to verify the existing workflows still resolve.

See [API](api.md), [database](database.md) and [architecture](architecture.md).
