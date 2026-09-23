# Phase 5 metric contract: dashboard-v1

Implemented for one property at a time. This reservation-based management contract supersedes the
proposed service-night/completed-stay contract in product.md **for the Phase 5 dashboard only**.
It is not a tax statement or accounting net profit. No public, competitor or benchmark data is included.

## Period and eligible records

Dates are Asia/Seoul business DATEs. Default month is the server's current Seoul month.
A completed past month uses its first through last day, inclusive. Current month uses first through
today, inclusive (September 23 means 23 days). Future months are rejected; earliest selectable month
is 1901-01. Audit/calculation timestamps are UTC.

CONFIRMED and UNKNOWN reservations count; CANCELLED does not. UNKNOWN remains unchanged in storage
and its financial/overlapping counts are disclosed. One reservation represents one room because
Phase 3 does not store room quantity. Guest count is not room quantity. These are reservation
proxies, not verified completed-stay observations.

## Definitions

Let S = first day and E = inclusive effective last day.
Financial population F: eligible reservations with S <= check_in <= E.
Operational population O: eligible reservations with check_in <= E and check_out > S.

| API field / Korean label | Definition |
| --- | --- |
| recognized_gross_revenue / 매출 | Sum of F.gross_revenue, before channel fees; owner CSV reported gross, not payout |
| reservation_count / 예약건수 | Number of F reservations |
| average_length_of_stay / 평균 숙박일수 | Sum F.booked_nights / count(F); null when count is zero |
| occupied_room_nights / 예약 객실박 (추정) | Sum overlap nights: min(check_out, E + 1 day) - max(check_in, S); one room per reservation |
| available_room_nights | Current property.inventory_units × inclusive calendar days S through E |
| occupancy_rate / 점유율 (추정) | occupied_room_nights / available_room_nights × 100 |
| allocated_operational_revenue | Sum O.gross_revenue × overlap nights / booked_nights; analytical only, no stored revenue mutation |
| adr / ADR (추정) | allocated_operational_revenue / occupied_room_nights |
| revpar / RevPAR (추정) | allocated_operational_revenue / available_room_nights |
| manual_expense_total | Sum MANUAL expenses with S <= expense_date <= E |
| fixed_expense_total / 고정비 | Same expenses with FIXED cost_type |
| variable_expense_total / 변동비 | Same expenses with VARIABLE cost_type |
| category_breakdown | Manual expenses grouped by category; reconciles to manual total |
| known_channel_fee_total | Sum non-null F.channel_fee; count known and missing separately |
| known_cost_total / 확인된 총 비용 | manual_expense_total + known_channel_fee_total, exactly once |
| known_operating_profit / 확인된 영업이익 | recognized_gross_revenue - known_cost_total; negative values allowed |
| known_operating_margin / 확인된 영업이익률 | known_operating_profit / recognized_gross_revenue × 100; null for zero revenue |
| channels | Group F by channel: count, gross, known fee, booked nights, known/missing fee counts |
| revenue_share_percent | Channel gross / total recognized gross × 100; null when total is zero |

The main revenue card uses financial recognition. ADR/RevPAR use operational allocation.
August 31–September 3, gross 300,000: September gets two operational nights and 200,000 allocated
revenue, but no September recognized financial revenue. Checkout September 1 contributes no
September nights. September 22–25 observed through September 23 contributes two nights.

Three rooms over September 1–23 gives 69 available nights. 47 occupied nights gives 68.12%.
RevPAR approximately equals ADR × occupancy_rate / 100, subject to rounding. Values above 100%
are returned unchanged with OCCUPANCY_OVER_100; review inventory/duplicate or overlapping bookings.

## Precision, coverage and source

Stored KRW and financial totals remain exact Decimal/NUMERIC values. PostgreSQL performs numeric
proportional allocation without rounding each night to won; Python Decimal handles ratios.
API decimals serialize as strings. Ratios/ADR/RevPAR round HALF_UP to two decimal places;
allocated revenue is exposed to six places. UI formats KRW to nearest won and ratios to one
decimal; it never calculates financial totals. Recharts uses numeric coordinates only; an
accessible table preserves exact source-value formatting, and unsafe chart numbers are omitted.

Null denominators yield null, never NaN/Infinity. Zero-data aggregate sums are zero with explicit
has_financial_reservations/has_operational_reservations flags. This is not evidence of zero trading.
No-reservation UI hides primary cards and offers CSV import. Missing expenses disclose incomplete
coverage. A channel with no known fee returns null; reported zero fees remain valid zero.
Mixed known/missing fees show the known sum plus missing count, never impute missing fees.

Metadata carries owner source, owner_csv/MANUAL origins, financial/operational date bases,
calculation version, estimation method, estimated metric list, current-inventory basis and UTC time.
Calendar inventory does not reflect blocked/maintenance/unavailable dates, and current registered
inventory is applied retrospectively. Revenue has no verified tax/refund/completion reconciliation.
Known profit excludes unregistered taxes, interest, depreciation and other missing costs.

## Comparisons and trends

Summary compares previous calendar month and same month last year. For an incomplete current
month, compare the same elapsed day range, capped to the comparator month's last day.
September 1–23 compares August 1–23 and prior September 1–23. Past full months compare full months.

Normal metrics return absolute_delta and percentage_change = delta / baseline × 100 only when
baseline > 0. Zero/negative baseline retains absolute delta with null percentage. Occupancy and
margin return percentage_points, never percentage change. Direction is neutral in the UI.
Comparison available=false and null deltas when either period lacks relevant recorded inputs.
This coverage gate does not certify that all revenue/expenses were imported.

Trends return every month chronologically, default 12 and bounds 1–24, ending at optional month
or current month. Past trend months are full; current month stops today. Thus prior-month trend
totals can differ from the partial comparator. Missing-record months are chart gaps, not fictitious
zero observations. Expense-only months may show known costs, with no profit line.

## Phase 4 compatibility

Phase 4 expense summary deliberately includes ALL reservation statuses; Phase 5 explicitly
excludes CANCELLED. Both use check_in dates, known non-null fees and no synthetic expense rows.
Totals reconcile for the same effective dates when no cancelled fees are present; otherwise the
difference is the cancelled reservations' fees. Also select the same dates when comparing a
partial dashboard month with Phase 4's full-month default. Phase 4 remains unchanged.
