# Dashboard-v2 calculation contract

The primary dashboard UI uses /api/v1/dashboard-v2/summary and /trends.
The original /api/v1/dashboard/summary and /trends remain dashboard-v1 with unchanged
source calculation/service tests. No silent relabeling of v1.

## Frozen financial rules

Financial recognized revenue/fees use check-in date. UNKNOWN remains included and CANCELLED
excluded. Manual expenses, known costs/profit, channel breakdown, average length of stay,
reservation count, Seoul elapsed-day periods and previous-month/year comparison rules are
shared with v1. Channel booked_nights remains reservation nights, not occupied room nights.
Revenue is never multiplied by room_units.

## Operational formulas

For each overlapping stay, checkout is excluded:
occupied_room_nights = sum(overlap_nights * coalesce(room_units, 1)).

For every date in the effective period:
available_units = effective_capacity - recorded_unavailable_units.
available_room_nights = sum(available_units).

For a history gap effective_capacity uses properties.inventory_units as an estimated fallback.
Unrecorded unavailable counts use zero with a separate warning.
Allocated revenue is unchanged: gross * overlap_nights / booked_nights.
ADR = allocated revenue / occupied room-nights.
RevPAR = allocated revenue / available room-nights.
Occupancy = occupied / available * 100.

Decimal precision and HALF_UP two-place ratios follow v1. Allocated revenue is exposed to six
places. A zero denominator yields null, not zero or infinity. No 100% clamping. Count days
where occupied units exceed available units, even if the monthly rate is below 100%.
These remain visibly estimated reservation-derived metrics, not verified actual stays.

Test-only acceptance: 10 rooms for 10 days minus 1 room on 2 days = 98 available room-nights.
One 2-room, 3-night reservation = 6 occupied; occupancy = 6.12%. No normal DB seeding.

## Quality and provenance

calculation_version=dashboard-v2; source=owner; inventory_basis=effective_capacity_minus_unavailable;
room_units_basis=reported_or_estimated_one. Owner CSV/manual-expense and revenue date metadata
remain explicit. Public accommodation/visitors/events never enter this calculation.

Summary and each trend row include:
- missing_room_units_count: overlapping included reservations with null units, counted once.
- capacity_fallback_days: dates without explicit capacity.
- unrecorded_unavailability_days: dates with no exclusion record, assumed zero.
- overcapacity_days: dates exceeding available units.

Korean warnings disclose missing units, fallback history, missing exclusions, overcapacity and
zero availability. Existing fee/status/expense/coverage warnings remain. Comparisons still
require data on both sides; baseline operational values use the same v2 rules. The comparison
response retains the v1 shape; baseline quality is available in that month's summary/trend.

The repository batches all requested periods in one daily inventory query plus the existing
three financial/allocation/expense queries. No provider calls, per-day HTTP requests or
persisted KPI cache. Trend window is bounded to 24 months. Large real-customer volumes may
require measured overlap-query optimization later; no production-scale benchmark is claimed.

See [inventory](inventory-availability.md), [frozen v1](metrics.md), [verification](phase11-verification.md).
