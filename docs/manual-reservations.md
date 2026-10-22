# Phase 12 manual reservations

The reservation UUID is canonical. Origin is immutable CSV_IMPORT or MANUAL.
Existing rows were created by the import flow (mandatory import FK in 0002);
0010 initializes them as CSV_IMPORT/version 1 without rewriting business facts.
No historical audit events are fabricated. Manual records have no import_id and
may omit external_reservation_id. PostgreSQL allows multiple NULL identities;
non-null (property_id,channel,external_reservation_id) remains unique across origins.
Neither origin may silently merge into the other. Identity fields are immutable
through PATCH for both origins. No fake external ID is generated.

## Owner workflow

1. Sign in, choose a property, open 예약 목록 → 예약 직접 등록.
2. Enter channel, dates and integer KRW gross; optionally external ID, fee, guests,
   room_units. Fee must not exceed gross, checkout must follow checkin, counts must
   be positive integers. No guest names/contact data are collected.
3. Open 상세·수정. Edit business fields, enter a nonblank reason (maximum 500 chars),
   and save. Select 취소 and save to cancel; select 확정/미확인 and save to reopen.
4. CSV records show 수동 보정 only on fields actually changed. Unchanged supplied
   values do not acquire protection. MANUAL rows need no CSV field protection.
5. CSV 자동 갱신 허용 opens an in-page confirmation with its own required reason.
   Current values remain unchanged. The next NEW matching CSV may update the field.
6. On HTTP 409, review the message and reload latest data before editing again.
   Human edits are never automatically retried. Reload discards unsaved local input.

## CSV and concurrency contract

For each CSV_IMPORT row: retain each protected effective field; apply the original
CSV full-row replacement to every other mutable field. Omitted room_units, fee,
guest count become NULL; absent status becomes UNKNOWN. Recompute booked_nights
and net_revenue from the merged effective values. If that combination violates a
date/fee constraint, fail the ENTIRE batch and retain a safe FAILED import record.
MANUAL identity collision likewise fails the entire batch with a clear message.
The response persists protected_fields_count (protected field occurrences, including
equal incoming values); updated_rows retains the historical matched-row count,
not a claim that all matched effective values changed.

Completed identical-byte file idempotency stays unchanged. Reuploading the same
completed file returns its previous result and does not reapply it, including after
protection release. Use a genuinely changed file for subsequent source changes.

Manual create and CSV use the existing organization/property/channel advisory lock.
CSV locks matching rows in UUID order; manual edits/releases lock their single
organization-scoped row, then read protections. They never acquire the channel lock
after a row lock. This serializes CSV vs manual mutations without distributed locks.
Version increments on effective business changes and protection release (which
changes future CSV behavior); reads, no-op edits/releases and protected-only CSV
skips do not increment it or create fake value-change events. A stale expected_version
returns 409 with RESERVATION_VERSION_CONFLICT, with no writes/audits committed.
Creation identity conflict returns 409/RESERVATION_IDENTITY_CONFLICT.
Reservation, protections and audit writes share the request transaction; CSV uses
the existing savepoint for whole-batch rollback and safe failure persistence.

## Endpoints

- POST /api/v1/properties/{property_id}/reservations
- GET /api/v1/reservations and /api/v1/reservations/{id} (existing, extended metadata)
- PATCH /api/v1/reservations/{id}: supplied business fields, expected_version,
  change_reason; immutable fields/actor/origin/version inputs rejected.
- POST /api/v1/reservations/{id}/release-overrides: fields, expected_version,
  change_reason; bounded known field set only.
- GET /api/v1/reservations/{id}/history?limit=50&offset=0: maximum limit 100.

Every endpoint resolves current membership and organization-scoped property access.
Source is owner_manual or owner_csv, with explicit origin/version/protected names.
No reservation DELETE route or runtime DELETE grant exists.

## Boundaries

Existing v1/v2 formulas, status handling, expense calculation, capacity/availability,
public sources and estimation labels remain. Both dashboards consume effective
reservation rows; audit metadata never contributes revenue or room-nights.
Revenue provenance now says owner_reservations to include manual data accurately;
this is metadata, not a new KPI calculation version.
No actual completion, no-show/refund/settlement/accounting recognition, reservation
restore, automatic merging, expense history, export or OTA sync. No dependencies added.
See [audit](reservation-audit.md) and [verification](phase12-verification.md).
