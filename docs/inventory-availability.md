# Inventory availability — Phase 11

This is owner business data, separate from all public market observations.

## Capacity contract

A capacity period has an inclusive effective_from/effective_to (null end means open-ended),
positive integer inventory_units, organization/property identity and UTC audit timestamps.
Adjacent dates are allowed; overlapping dates are rejected by service validation and the
PostgreSQL GiST exclusion constraint. The additive 0009 migration enables btree_gist;
no Python/JavaScript dependency is added. Hosted extension compatibility is not verified.

Capacity history is authoritative by date. properties.inventory_units remains a compatibility
and estimated-default field: v1 continues using it; v2 uses it only where history is absent.
It is not automatically synchronized with history or described as today's verified capacity.
Changing the default cannot rewrite explicit history. It can change estimates in gaps, with
visible fallback metadata; this is intentionally not a fabricated historical backfill.
No history is generated for existing properties. Up to 1,000 periods per property via API.

## Unavailable units

One aggregate row per organization/property/date. unavailable_units is an integer >= 0
and cannot exceed effective capacity (or the property's fallback for a gap).
MAINTENANCE / OWNER_BLOCK / SALES_STOP / OTHER are informational reasons.
Optional memo is at most 1,000 characters. Do not enter guest personal information.
Zero is a recorded zero; no row is an unrecorded assumed zero, visibly differentiated.
These rows represent rooms not offered for sale, not booked rooms. Reservations do not
automatically create exclusions. There are no physical room identities or assignments.

Availability reads require a date range of at most 366 days, inclusive. API dates are
1901-01-01 through 9998-12-31. Capacity end dates are inclusive, checkout dates excluded.
All business dates use Asia/Seoul.

## Transactions and security

Every HTTP operation verifies JWT, active membership, and property access through existing
dependencies. Every query carries organization/property predicates. Both new tables have
composite property foreign keys and ENABLE/FORCE RLS with the existing membership policy.
Runtime gets SELECT/INSERT/DELETE and UPDATE only on editable columns, never tenant identity.
The public ingestion role receives no privileges. No browser business-table access.

Capacity create/update/delete, exclusion upsert/delete, and property default updates all
lock the same scoped property row FOR UPDATE. Under the existing READ COMMITTED transaction,
the lock is acquired before dependent reads; waiting writers re-read committed values.
Capacity changes validate all existing exclusions after flush, within a savepoint. Rejected
edits roll back. Deleting history also checks the fallback before allowing the resulting gap.
Simple invariants and period overlap are database constraints; cross-table capacity comparison
is an application-service invariant. Administrative SQL must not bypass that service contract.

Rows have created/updated timestamps; there is no full revision log or undo workflow.
Deletion removes only the explicitly selected inventory record. Never delete existing demo
reservations or public records to demonstrate this feature.

## Owner workflow

1. Open a property, then **객실 운영 · 이력 / 판매 제외**.
2. Add known dates and room count. End the old period before adding a new non-overlapping one.
3. Enter an exclusion date, count, reason and optional memo. Saving the same date replaces it.
4. View the bounded daily table. Edit/delete the selected record as needed.
5. Open the dashboard for the relevant month. Changes affect v2 denominators immediately.
6. For reservation room counts use the optional generic CSV mapping; no manual reservation CRUD.

See [dashboard-v2](dashboard-v2.md), [imports](imports.md), and [verification](phase11-verification.md).
