# Phase 3: generic CSV reservation imports

Phase 3 implements owner-supplied reservation records only. Airbnb-specific CSV parsing is NOT implemented yet. AIRBNB, BOOKING and AGODA are source labels, not format detection or OTA integrations. No KPI, expense, inventory-occupancy calculation, billing, scraping or synchronization is included.

## Workflow

Open a registered property → CSV 가져오기 → choose file and source channel → preview → explicitly map columns → validate → confirm replacement semantics → import → open history or reservations.

The selected File remains in browser memory for preview, validation and commit. The server re-parses and validates every commit; a successful preview is never an authorization or validation token. Changing a file, channel or mapping clears prior validation and confirmation. The API is authoritative even if a client bypasses the wizard.

## File contract

- CSV extension required; filename and MIME alone never establish validity. Filenames are reduced to a basename and checked for length/control characters.
- Maximum CSV bytes: 5 MiB (5,242,880). Maximum data records: 10,000, excluding the header. These retain the product's existing MVP limits.
- Maximum 64 columns, 100 characters per header and 4,096 characters per cell. A maximum 6 MiB multipart request is enforced before parsing, including streamed requests without Content-Length.
- Comma delimiter, standard double-quoted CSV fields, consistent column count. Empty files, empty data sets, duplicate/blank/space-padded headers, binary NUL/control characters, broken quoting and mismatched row widths are rejected.
- UTF-8, UTF-8 BOM, then strict CP949 fallback. CP949 fallback produces a warning so the user can check Korean text. Encoding detection does not imply semantic confidence.
- First 10 records are returned for preview, plus the exact bounded row count and warnings. Record numbers in errors start at 2; embedded line breaks do not change logical record numbering.
- No formula execution. Formula-looking cells are warned about in preview, strict numeric/date/status parsing rejects them in those fields, and formula-prefixed reservation IDs are rejected. Preview text is rendered through React escaping, never HTML. There is no CSV export.
- Raw files are never permanently stored, logged or sent to Supabase Storage. Request-local memory/UploadFile temporary spooling is released when the request finishes. Only metadata and normalized records persist.

## Explicit mapping and normalization

Map each field to a different existing CSV header. Required: external_reservation_id, check_in, check_out, gross_revenue. Optional: channel_fee, guest_count, reservation_status. Unmapped columns, including a supplied nights column, are ignored.

| Field | Contract |
| --- | --- |
| External reservation ID | Trimmed nonempty stable string, max 200 characters; unique within property/channel. No automatic ID generation. Duplicate IDs inside one file block the batch. |
| Dates | Exact YYYY-MM-DD calendar dates; checkout strictly later than check-in. Business dates are Asia/Seoul. |
| Booked nights | Backend computes checkout minus check-in; a CSV nights column is never trusted. |
| Gross revenue | Required owner-reported accommodation charge in whole KRW. No inference from payout/net values. |
| Channel fee | Optional owner-reported fee, whole KRW between zero and gross revenue. Blank means unknown, not zero. |
| Net revenue | gross minus reported fee only when fee is present. Otherwise null. This is a derived amount, not a verified payout, profit or dashboard KPI. |
| Money format | Decimal in Python; NUMERIC(18,0) in PostgreSQL; exact decimal strings in JSON. Plain nonnegative digits or correctly grouped thousands commas; optional .0/.00 only. No floats, scientific notation, currency symbols, fractions or negative amounts. |
| Guest count | Optional positive integer, max six digits. Guests are not inventory units. |
| Status | CONFIRMED, CANCELLED or UNKNOWN. Unmapped/blank is UNKNOWN; other values are rejected rather than guessed. |

The import does not infer actual stay completion, sold unit-nights, room quantities or occupancy from reservation dates or guest counts. Existing property inventory is unchanged. These records alone are not the completed-stay metric inputs described in the future product contract.

## Adapter boundary

app/importers/generic.py defines the CsvAdapter Protocol and GenericCsvAdapter. Shared bounded CSV parsing produces CsvDocument; the adapter normalizes explicitly mapped values and returns normalized records plus a bounded validation summary. No generic repository framework or plugin registry was introduced. Future AirbnbCsvAdapter, BookingCsvAdapter and AgodaCsvAdapter require real verified sample formats and separate tests; none are stubbed as functioning adapters.

## Validation, transactions and statuses

Preview and /imports/validate write neither batches nor reservations. Invalid file syntax/mapping returns 422 (oversize 413). Row validation returns total_rows, valid_rows, invalid_rows, warnings and at most 100 row/field errors, with errors_truncated.

Import is all-or-nothing. A submitted batch with row errors is saved as FAILED metadata with imported_rows=0 and rejected_rows equal to the invalid-row count; otherwise-valid rows are also withheld. The UI makes that distinction explicit. PENDING → PROCESSING → COMPLETED happens synchronously in one transaction, not in a background job.

A savepoint surrounds all reservation upserts. Unexpected failure rolls back new rows and updates together, then records FAILED metadata with a generic message. No raw exception/SQL parameter data is logged or returned. A connection/transaction-level failure can roll back metadata as well; never claim a batch was recorded if the transaction did not commit. A transient failure has rejected_rows=0 unless actual row validation failed.

Database commit precedes the HTTP response through the existing function-scoped transaction dependency. No reservation can point to a property or import in another tenant: composite foreign keys bind organization/property/import together. Timestamps are timezone-aware.

## Idempotency and updates

SHA-256 is computed from the original uploaded bytes, before decoding. A partial unique index prevents two COMPLETED batches with the same property/channel/checksum. Repeating a completed file returns its existing result with duplicate=true and writes nothing, even if it has a different filename or mapping. Failed attempts do not reserve the checksum and can be retried.

Imports acquire a transaction advisory lock keyed by organization/property/channel. Concurrent identical submissions serialize, then the second returns the completed result. Database uniqueness remains the final guard.

Reservation uniqueness is property_id + channel + external_reservation_id. A different valid file updates current normalized values for existing IDs while preserving reservation UUID/created_at, and sets updated_at/import_id to the latest import. Missing optional values replace prior optional values with null/UNKNOWN; an import is a full source snapshot for each supplied ID, not a patch. Rows absent from the file are untouched. The wizard requires acknowledgement before submission.

History records actor, timestamp, checksum, mapping, adapter version and inserted/updated counts. It does not retain the original file or every historical reservation value. Re-uploading an older already-completed file returns its old batch summary; it does not revert subsequent updates. Identical bytes may be imported separately for a different authorized property or channel.

## Tenant and source boundaries

Preview requires a valid authenticated identity. Validation/import/history/reservations additionally require X-Organization-Id and current membership; selected properties are checked against that organization. Both OWNER and MEMBER follow the existing Phase 2 permissions. Foreign object IDs return 404; invalid organization membership returns 403.

Every repository query/count/update carries explicit organization predicates. Both new tables force RLS, use the restricted runtime role and check current organization plus user membership. Runtime grants exclude deletes and ownership changes. Existing Supabase JWT verification, cookies, redirects and service-key boundaries are unchanged.

Reservation responses identify source=owner_csv, reference the latest import_id and describe net_revenue_method. Public market information is not mixed into these records. No production data or fallback sample rows are generated.

## Local manual test

The migration is additive and never recreates Docker storage:

~~~powershell
docker compose up --build -d
docker compose exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic upgrade head
docker compose exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic current
~~~

1. Open http://localhost:3000, sign in, and open a property.
2. Use backend/tests/fixtures/development-reservations.csv only against a development account/property. It is synthetic, clearly marked DEV-ONLY, and is never auto-seeded.
3. Select GENERIC. Preview should show two rows. Map 예약번호 → external_reservation_id, 체크인 → check_in, 체크아웃 → check_out, 총매출 → gross_revenue; optionally map 수수료, 인원, 상태.
4. Validate, acknowledge the source/replacement rules, and import. Expect two inserted reservations, with nights 2 and 1. The second net amount remains unknown because its fee is blank.
5. Open reservation list and history. Test channel/status and check-in date filters, and sign out to check protected-route redirects.
6. Re-upload the same file: expect the existing batch, duplicate=true, no new reservations.
7. In a separate development fixture copy, change the first gross amount, keeping its ID. Re-import: expect an update, not a duplicate reservation.
8. In another fixture copy make checkout precede check-in. Validation identifies that row; no import is enabled. Direct API submission records FAILED and writes no reservations.
9. A second organization's account cannot read/import these records.

Production Supabase configuration continues to use [authentication.md](authentication.md). Never upload synthetic fixtures to a production business.

## Checks and limits

Automated tests use signed local JWT fixtures/dependency overrides only in tests and disposable real PostgreSQL databases with restricted runtime logins. Frontend tests exercise actual React wizard interactions in jsdom, escaped preview/result rendering, mapping validation, multipart transport and auth/error behavior.

Migration 0002_csv_imports follows unchanged 0001_foundation. Tests exercise downgrade to Phase 2 and re-upgrade while retaining organizations/properties; downgrade intentionally removes Phase 3 data and is not a routine operational command.

See [API](api.md), [database](database.md) and [Phase 3 verification](phase3-verification.md).
