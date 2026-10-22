# Reservation audit and protections

Additive Alembic 0010_manual_reservations follows 0009. Two owner-data tables:

- reservation_manual_overrides: UUID, organization/property/reservation IDs,
  validated field_name, authenticated created_by_subject, UTC created_at.
  Unique reservation+field; release deletes only current protection metadata.
  No updated_at is needed: active protection rows are immutable until released.
- reservation_audit_events: UUID, organization/property/reservation IDs, event_type,
  change_source, authenticated actor_subject, optional reservation_import_id/reason,
  changed_fields, before_values, after_values and UTC clock_timestamp().

Small event vocabulary: MANUAL_CREATE, MANUAL_UPDATE, STATUS_CHANGE,
MANUAL_OVERRIDE_RELEASED, CSV_UPDATE. Source is MANUAL or CSV_IMPORT.
CSV initial creation is represented by import history, not a fabricated per-row
CREATE event. CSV_UPDATE links the actual import and initiating subject.
Historical changes before Phase 12 are unavailable. No guessed actors or names.

Mutable field whitelist: check_in, check_out, gross_revenue, channel_fee,
guest_count, reservation_status, room_units. Audit changed-value snapshots use
ISO dates, exact integer decimal strings, JSON null and canonical enum strings.
Only changed fields are recorded for updates. Creation records initial business
fields. Protection release records MANUAL_PROTECTED → CSV_MANAGED for selected
fields, not a fictitious restoration of old values. No shadow imported baseline.
No raw CSV, JWT, headers, credentials, emails or guest personal data in audit.
Reasons are bounded plain text and rendered as escaped React text.

## Security and transaction boundaries

Composite organization/property/reservation FKs prevent forged relationships.
Both tables ENABLE/FORCE RLS using current organization and current membership.
INSERT policy additionally checks actor/creator against transaction-local user.
Runtime: audit SELECT/INSERT only; protections SELECT/INSERT/DELETE only.
PUBLIC revoked; ingestion gets no grants. Reservation origin/identity has no UPDATE
grant. Runtime can update business fields/version, never DELETE reservations.
Audit timestamps are server-generated. API bodies forbid client audit metadata.
No SECURITY DEFINER escape hatch or frontend business-table access is introduced.

Audit insertion failure rolls back reservation values, protection rows and version.
CSV audit failure rolls back the complete batch's reservations/audits/protections
before recording FAILED. Access is private/no-store; history is bounded and sorted
newest first by timestamp and UUID, with limit/offset and total.

The UI displays a short stable user UUID; there is no display-name system.
Database owners retain maintenance privileges. A compromised runtime SQL client
within its valid tenant/actor context is outside API forgery protection; audit
append-only grants prevent rewriting existing events, not all possible false
inserts by a compromised application. Retention/export/cryptographic audit signing
and actual accounting ledgers remain future separate designs.

Downgrade refuses if MANUAL rows exist because the previous mandatory-import schema
cannot represent them safely. Never delete reservations to force a downgrade.
See [manual workflow](manual-reservations.md).
