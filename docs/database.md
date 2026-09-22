# Stay Insight database design

Status: Phase 3 adds the import/reservation tables documented below. Phase 2 implements organizations, organization_members and properties under the app schema in local PostgreSQL/PostGIS. All other entities below are future proposals. Metric semantics are defined in [product.md](product.md); access boundaries are defined in [architecture.md](architecture.md).

## Implemented Phase 2 foundation

Migration `0001_foundation` (backend/alembic/versions/0001_tenant_property_foundation.py) creates only:

- `app.organizations`: UUID id, required nonempty name, timezone-aware created_at/updated_at.
- `app.organization_members`: UUID id, organization foreign key, external Supabase user UUID, OWNER/MEMBER role, created_at; unique organization/user and indexed user_id. The user UUID deliberately has no local auth.users foreign key: Auth is hosted separately, while business data stays local. No passwords or token credentials are stored.
- `app.properties`: UUID id, organization foreign key, name, address, nullable road_address and paired coordinates, accommodation_type, positive inventory_units, Asia/Seoul timezone, created_at/updated_at. Includes organization index, organization/id unique key, nonempty/bounds/type constraints. No deletes or inventory-history tables in this phase.

All three tables have FORCE RLS. The `stay_insight_runtime` NOLOGIN group receives only required access. An explicitly provisioned `stay_insight_app` login inherits that group and cannot bypass RLS. Runtime connections that are superusers, BYPASSRLS roles or table owners are rejected. Current user/organization settings use transaction-local `set_config` and are cleared by commit/rollback.

Membership reads are limited to the verified user; property reads/writes require both the selected organization and a current membership. Repositories also include explicit scope predicates, including UPDATE and count queries. Bootstrap insert policies permit an OWNER membership only for an organization inserted in the same transaction; a spoofed bootstrap context cannot join an existing organization. No runtime delete/member-update grants exist.

Onboarding uses a user-keyed transaction advisory lock and a same-name retry policy. Service transactions commit before the API response is returned. Upgrade/downgrade/re-upgrade tests run on isolated PostgreSQL databases. Downgrade is destructive to the three application tables and is not a routine update command. The shared NOLOGIN role is retained on downgrade because other databases may use it.

Alembic autogeneration is restricted to the app schema, protecting PostGIS/system tables. See [authentication.md](authentication.md#start-migrate-and-provision-the-local-role) for exact migration/provisioning commands. Startup never calls create_all or automatically migrates; the existing Docker volume is retained.

## Implemented Phase 3 imports

Additive migration 0002_csv_imports creates app.reservation_imports and app.reservations. It does not modify 0001_foundation, organization/property rows or the Docker volume.

reservation_imports records UUID ownership/property, channel, sanitized original filename, SHA-256, status, total/imported/rejected/inserted/updated counts, actor, timezone-aware timestamps, safe error summary, column mapping and adapter version. A partial unique index on property/channel/checksum where COMPLETED prevents repeated successful files while permitting retries after failure. A composite organization/property/id key supports reservation provenance integrity.

reservations records UUID ownership/property/import, channel/external ID, service dates, backend-computed nights, optional guests, exact NUMERIC(18,0) KRW amounts, normalized status and timezone-aware timestamps. Property/channel/external ID is unique. Composite foreign keys prevent cross-organization property/import references. Checks enforce date ordering, matching nights, positive guests, valid statuses/channels and gross/fee/net relationships. Decimal values serialize as strings; no floating-point money exists.

Indexes lead with organization_id and support property history, reservation check-in pagination and import links. Both tables force RLS with current organization/current membership checks. Explicit predicates also scope repository reads/counts/updates; grants exclude deletes and ownership changes. No raw files or raw source rows are persisted.

See [imports.md](imports.md) for transaction, idempotency and correction semantics. The reservation/import proposals below describe later extensions, not additional implemented fields.

The remaining sections describe the broader target design. Phase 2's implemented names replace the earlier memberships/accommodations proposal; historical inventory, revenue and other entities are not implemented.

## Schemas and ownership

| Schema | Responsibility |
| --- | --- |
| `app` | Organizations, owner business facts, import lineage, reporting coverage, consent and audit |
| `market` | Shared public source catalog, ingestion runs, accommodation observations, visitors, events |
| `benchmark` | Approved aggregate releases and private release lineage |
| `auth`, `storage` | Supabase-managed schemas; do not replace their migrations or duplicate passwords/tokens |

Application schemas are not exposed through Supabase Data API or Realtime. Revoke browser roles' privileges on their tables, sequences and functions, including default privileges; review views and functions too. Disable the Data API if unused, while independently enforcing schema/grant restrictions. Public information is served through FastAPI even though its contents are public. PostGIS extension placement follows the supported project configuration.

Use UUID primary keys, UTC `timestamptz` audit times, and local `date` service/expense fields. Money uses signed `bigint` integer KRW with documented bounds; ratios use decimal arithmetic. Every tenant-owned table has a non-null `organization_id`, including import details and audit records. Add `created_at`, `updated_at`, and an optimistic revision where mutable records need conflict detection.

## Tenant entities

| Table | Principal fields and constraints |
| --- | --- |
| `organizations` | `id`, name, status, timezone fixed to Asia/Seoul for MVP, currency KRW; this ID is the tenant scope |
| `organization_members` | Implemented above; external Supabase user UUID, unique organization/user; OWNER and MEMBER |
| `properties` | Implemented above; later inventory history and geospatial enhancements remain proposals |
| `inventory_periods` | Organization/accommodation, inclusive start, exclusive end, sellable unit count; nonnegative capacity and non-overlapping ranges per accommodation |
| `inventory_adjustments` | Organization/accommodation/date, out-of-service units, reason; one effective adjustment per date; count cannot exceed that date's capacity |
| `reporting_coverage` | Organization/accommodation, period start/end, kind (`reservations` or `expenses`), confirmation status, confirmer/time; non-overlapping effective ranges per kind, explicit confirmation rather than absence-as-zero |
| `imports` | Organization/accommodation, uploader, storage key, file hash, encoding, mapping/schema version, state, row counts, idempotency key, preview digest, commit time; unique organization/idempotency key |
| `import_rows` | Organization/import, row number, sanitized normalized payload, source key, validation errors, proposed action and target revision; unique import/row number; purge raw sensitive content |
| `reservations` | Organization/accommodation, source system, external reservation ID, channel code, status, check-in/out, unit quantity, exact gross room charge, tax basis, current import/row references, revision; checkout after check-in and quantity positive |
| `reservation_nights` | Organization/accommodation/reservation, service date, occupied unit count, allocated gross room charge, input method, estimation method/version; unique reservation/date; date must be within stay |
| `revenue_adjustments` | Organization/accommodation/reservation, target service date, signed amount, kind (refund or correction), source adjustment ID, recorded time, import lineage; idempotent source key, immutable history with reversals |
| `expenses` | Organization/accommodation, category, incurred date, signed KRW amount, tax basis, optional channel/reservation link, entry method, revision and void reason/time; ordinary expenses positive, explicit reversals negative |
| `benchmark_consents` | Organization, policy version, opted-in time, withdrawn time; one active consent per organization |
| `audit_events` | Organization, actor user or named system actor, entity type/ID, action, revision references, timestamp, safe change metadata; append-only, no guest details or tokens |

The database does not store a guest directory, payment cards, passwords, or access/refresh tokens. The source reservation ID is opaque and never a public URL. Channel codes are a small canonical lookup with an explicit unknown value; no generic channel service is needed.

Inventory periods preserve history instead of applying today's capacity retroactively. A gap is unknown availability. Corrections to inventory and reservation facts run under a per-accommodation transaction lock and validate total occupied units against available units for each affected date. Use a database non-overlap constraint for inventory periods where supported by the chosen range/operator setup; test concurrent writes and any needed extension. Missing inventory may preserve otherwise valid reservations but prevents occupancy/RevPAR until resolved.

## Relationship integrity and access

Create unique `(organization_id, id)` keys on tenant parents and composite foreign keys for tenant children. A reservation references `(organization_id, accommodation_id)`; its nights and adjustments also reference a reservation key including accommodation so they cannot point to a different property in the same tenant. Import-row references include their import identity. Related expense/import references must agree on organization and accommodation. Global lookup/source tables are the explicit non-tenant exception.

Enable and force RLS on tenant tables. The runtime SQL role is not a table owner, superuser, or `BYPASSRLS` role. Policies use transaction-local verified organization context for both `USING` and `WITH CHECK`. No context means deny. Organization rows compare their `id` against the current context.

Membership bootstrap needs a deliberately narrow exception: the runtime role may read only the membership rows for the verified transaction-local user before choosing an organization. It cannot enumerate other users. Organization creation and its initial owner membership are one transaction with explicit insert policies requiring the verified creator identity; subsequent membership changes are not an open runtime capability. Test bootstrap policies independently from ordinary tenant policies, including attempts to join an existing organization by supplying its ID.

| Identity | Access |
| --- | --- |
| Browser `anon` / `authenticated` roles | Supabase Auth integration only; no business-schema privileges or private-bucket access |
| API runtime DB role | Organization-scoped business access, public snapshot reads, approved benchmark-release reads; no raw cross-tenant aggregation |
| Migration role | Application schema DDL, policies and grants; deployment only, never request handling |
| Public ingestion role | Write `market` snapshots/runs; no owner financial data |
| Benchmark command role | Explicitly audited, read-only access to minimal consented owner facts across tenants and write access to benchmark output/lineage; never supplied to the HTTP API |

The benchmark command is the sole intentional cross-tenant business aggregation path. Keep it in the backend codebase but run separately with its own credentials. It selects only eligible consenting organizations and records the included organization set in private lineage. A dedicated aggregate-reader grant/policy is preferable to an unrestricted service-role connection.

## Public data entities

| Table | Principal fields and constraints |
| --- | --- |
| `market.sources` | Provider, dataset ID, source URL, license/attribution, geography, metric definitions, expected cadence, enabled status |
| `market.ingestion_runs` | Source, start/end, status, retrieved time, content hash, row counts, safe errors, successful snapshot ID |
| `market.accommodation_observations` | Source/run, external record ID, observed date, name/type/status, address/district, optional verified/geocoded point, coordinate source and precision; unique source/external ID/snapshot |
| `market.visitor_observations` | Source/run, geography code, period start/end, measure, unit, value, provider methodology, estimated flag; unique source/geography/period/measure/snapshot |
| `market.events` | Source/run, external event ID, title, local start/end, venue, optional point, source URL, status, provider update time; versioned by snapshot |

All observations retain observation/publication/retrieval times separately, nullable when genuinely unknown. Preserve provider values and normalized values distinctly where transformations occur. Geocoding is labeled with its provider and precision; failed geocoding means no marker, not an invented point. Public records are never automatically linked to an owner's private property; a future explicit match must preserve both identities and provenance.

## Benchmark data entities

`benchmark.releases` stores a unique fixed cohort/month/policy-version release, metric values, calculation version, contributor-count band, period, publication time, and eligible/withheld/invalidated status. Serve values only for eligible releases. Retain suppression reasons internally; do not reveal exact small counts publicly.

`benchmark.release_members` stores release ID, included organization ID, consent version, input revisions, and calculation lineage. This table is private to the benchmark command/migration roles; the API role cannot read it. Withdrawal invalidates affected releases through a narrowly scoped service operation before recomputation; the operation must not reveal other contributors. Enforce the [product privacy policy](product.md#benchmark-release-policy) before publication. No persistent per-competitor metrics are exposed.

## Calculations, indexing, and lifecycle

Do not store dashboard aggregates in the initial MVP. Compute from active reservation-night facts, signed adjustments, inventory and non-void expenses with organization/date filters. Preserve estimation propagation and coverage. Cached aggregates can be introduced only after measured need and a documented invalidation strategy.

Start with indexes on membership user/status, organization/accommodation/service date, organization/accommodation/expense date, organization/import state, and source/geography/observation period. Use unique `(organization_id, accommodation_id, source_system, external_reservation_id)` for deduplication. If source IDs can collide across channels, the adapter must include channel in its source-system namespace. Hash-only matching is insufficient for corrections. Use GiST for queried PostGIS geography columns and assess query plans before adding more indexes.

Reservation corrections replace active nightly facts and retain prior values/revisions in restricted audit/import lineage in one transaction. Refund adjustments are not also subtracted from the stored gross charge; this prevents double-counting. Store commissions as expenses once, with source references for deduplication. Reconfirm reporting coverage after corrections that create gaps or invalidate completeness.

Archive accommodations instead of cascading deletion into historical results. Use restrictive foreign-key deletion behavior for financial records. Organization erasure is an explicit controlled workflow covering facts, uploads, consent, audit retention policy, and affected benchmark releases; its retention/legal requirements must be settled before launch. Do not assume deleting an Auth user deletes their organization.

Alembic owns application tables, indexes, extensions required by the application, policies, and grants. Keep provider-managed schemas untouched except documented supported integration references. Test migration upgrades on an empty database and the previous revision, runtime grants/RLS, constraints and representative calculations. Before production, verify backup/restore, upload cleanup and deletion procedures. Phase 2 migration scope is the three foundation tables documented above.
