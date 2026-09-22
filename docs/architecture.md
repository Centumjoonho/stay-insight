# Stay Insight architecture

Status: Phase 3 implements generic CSV imports and normalized reservation reads alongside the Phase 2 authentication, organization/membership and property foundations. Business PostgreSQL remains the local Docker PostGIS service; hosted Supabase is used only for Auth. The rest is target architecture.

## System boundaries

```text
Browser -- authentication --> Supabase Auth
Browser <-- UI --> Next.js App Router (Vercel)
Browser / Next.js -- bearer-authenticated /api/v1 --> FastAPI (Render, Docker)
FastAPI -- restricted SQLAlchemy connection --> local PostgreSQL + PostGIS (Phase 2)
FastAPI -- server-only storage access --> Supabase private Storage
Backend ingestion commands -- verified sources --> public-data schema
Browser -- domain-restricted JavaScript SDK --> Kakao Maps
```

Next.js owns presentation and session integration. Use Server Components for suitable initial views and small Client Components for forms, Recharts, and Kakao Maps. Both server rendering and browser interactions obtain business data from FastAPI. Do not put business logic or a second data API in Next.js. Auth callbacks may use frontend routes; they are not business endpoints.

FastAPI is one deployable application with domain modules: identity, accommodations, reservations, imports, expenses, analytics, market, and benchmarks. A request flows from route and Pydantic input through an application service to domain-specific SQLAlchemy queries. Services own transactions and orchestration; calculation functions remain independently testable. Use concrete query functions rather than a generic repository abstraction.

## Authentication and authorization

Use Supabase Auth sessions. Frontend auth integration obtains/refreshes access tokens and forwards them to FastAPI as bearer tokens; do not log or persist tokens in application tables. Verify signature using the project's configured signing keys/JWKS, permitted algorithms, issuer, audience, expiry, and subject. Reject unsupported token types. Cache verification keys with bounded refresh for rotation. Pin actual SDK versions and verify their session behavior when implementing.

For every protected request, derive the user from the verified token and check current active membership in the database. Client-selected organization IDs are selectors, not authority. Onboarding grants OWNER. OWNER and MEMBER may manage properties; invitations and role-management APIs remain out of scope. Model membership separately so a user may own more than one organization later. Never authorize from editable user metadata or stale role claims alone.

Within a transaction, set the verified user context locally, perform a self-membership lookup, then set the authorized organization context locally before tenant queries. Missing context denies access. These values must reset on commit/rollback and never survive pooled-connection reuse. Every tenant query still contains explicit organization predicates, including single-row lookups and writes. Cross-tenant object IDs return a non-disclosing not-found response.

Deleting a user or revoking a session does not necessarily revoke an issued JWT immediately. Check active application membership on every call; use Supabase session/user validation for account-sensitive operations and document the remaining access-token expiry window at implementation. Logout clears the frontend session and invokes supported Auth sign-out behavior.

## API contract

All application endpoints, operational health endpoints, and OpenAPI live under `/api/v1`. Swagger is available at `/docs` as explicitly requested for Phase 1 tooling. Proposed resource groups are `/api/v1/me`, `/api/v1/organizations`, `/api/v1/accommodations`, `/api/v1/imports`, `/api/v1/reservations`, `/api/v1/expenses`, `/api/v1/analytics`, `/api/v1/market`, and `/api/v1/benchmarks`. These are planning names, not implemented endpoints.

Use Pydantic request/response models and FastAPI OpenAPI as the contract source. Generate TypeScript transport types once scaffolding exists; do not hand-maintain duplicate calculation logic. Amounts serialize as exact integer-KRW strings and computed decimal ratios as decimal strings or null; UI converts only for bounded chart rendering. Include pagination, validated date ranges, bounded query sizes, stable error codes, safe field errors, and request IDs. Do not expose SQL errors or raw import rows in generic error responses.

Tenant responses default to `Cache-Control: private, no-store`, including server-side frontend fetches; never put them in shared Next.js/CDN caches. Public snapshots can later use explicit freshness policies. Configure CORS for exact frontend origins and required methods/headers. Bearer authorization is required at FastAPI; frontend cookie-based mutations also require origin/CSRF controls. CORS is not an authorization layer.

## Imports, storage, and public ingestion

Future storage design (deferred in Phase 3): uploads pass through FastAPI into a private Storage bucket. The backend owns object names, organization checks, size/encoding checks, and retrieval. Browser credentials receive no bucket access. Keep server-only storage credentials separate from the runtime database identity; a storage credential must never become the business-query credential.

Bounded CSV preview/commit runs synchronously for the initial MVP. Persist an import state machine: uploaded, validated, rejected, committed, failed. Commit validates current source revisions and performs all business writes, lineage, and final state atomically. A failed commit leaves no partial business records. Use content hashes, stable source IDs, and a unique idempotency key; retried committed requests return their previous result. Do not rely on in-process background tasks for durable work.

Storage and database transactions are not atomic together. Record upload state, use server-generated keys, and periodically remove orphaned objects through an idempotent command. Proposed raw-upload retention is 30 days after terminal import status, subject to an explicit launch retention policy; preserve normalized facts and non-sensitive audit metadata. Never retain raw guest identifiers merely for debugging.

Public ingestion runs as explicit commands from the same backend codebase, manually first and on a scheduler when needed. Use a restricted ingestion role, timeouts, bounded retries, source hashes and unique provider keys. Publish a snapshot only after validation and a successful transaction. Failed ingestion retains last-good data and records failure/freshness status. No queue service or separate ingestion microservice is needed.

## Deployment and operation

Frontend: Vercel. API: a single Docker image on Render using Python 3.12 or later. Database/Auth/private Storage: Supabase. Keep development, staging, and production credentials and data separate. Select compatible service regions based on actual availability and latency before provisioning. Use TLS for external connections and configure a bounded connection pool appropriate to the chosen Supabase connection mode.

Alembic migrations run once as a controlled deployment step using a dedicated migration identity, never on each API process startup. Test migrations, RLS/grants, backups and restore procedures before production. Prefer additive schema changes for rolling deployments; document backfills and rollback/roll-forward plans for destructive changes.

Environment examples added during scaffolding contain placeholders only. Browser-visible configuration may include Supabase URL/publishable key, API base URL, and domain-restricted Kakao JavaScript key. Database URLs, Supabase secret/service-role credentials, and server provider keys stay on the backend. Vercel has no business database credential. Keep logs structured with request IDs, operation, duration, and safe error codes; redact personal data and secrets. Health checks reveal no credentials or infrastructure detail.

## Verification strategy

Unit tests cover metric formulas, exact money, nightly allocation, coverage, import parsing, and benchmark eligibility. Integration tests use actual PostgreSQL/PostGIS with migrations and the restricted runtime role to cover tenant isolation, composite foreign keys, RLS, rollback, and concurrency. SQLite is insufficient for these checks.

API tests cover invalid/expired tokens, current membership revocation, organization spoofing, unauthorized object IDs, bounded uploads, duplicate imports, stale previews, and error schemas. Frontend tests cover source/estimate labels, empty/error states, and Korean formatting. Browser journeys cover onboarding, import preview/commit, expenses, dashboard filters, and absence of direct business-table requests. Scan built frontend configuration for secret exposure. Public ingestion tests use fixtures, never live-provider assumptions.

Every feature must pass lint, type-check, and tests; required CI checks cannot silently skip integration tests because a database is absent. Establish tooling when scaffolding is authorized. Documentation-only validation is described in [AGENTS.md](../AGENTS.md).

## Initial decision records

| ID | Decision | Rationale and consequence |
| --- | --- | --- |
| ADR-001 | Monorepo, one modular FastAPI API, one Next.js frontend | Keeps deployment and transactions simple; modules provide boundaries without distributed systems |
| ADR-002 | FastAPI is the only business-data gateway | One authoritative authorization/calculation layer; browser and Next.js cannot bypass it |
| ADR-003 | Supabase managed Auth, PostgreSQL/PostGIS, and private Storage | Uses the requested managed platform while keeping business schema access private; browser Auth is the explicit direct-access exception |
| ADR-004 | Explicit organization predicates plus restricted-role RLS and tenant-safe foreign keys | Protects against accidental unscoped reads and cross-tenant relationships; requires realistic integration tests and transaction-local context |
| ADR-005 | Alembic is the sole application migration authority | Avoids divergent migration histories; provider-owned Auth/Storage schemas remain managed by Supabase |
| ADR-006 | Exact KRW and service-night management reporting | Produces explainable monthly metrics; nightly allocations and incomplete coverage must remain visible |
| ADR-007 | Separate owner facts, public observations, benchmark releases | Prevents false precision and unsupported comparisons; provenance is part of API contracts |
| ADR-008 | Bounded synchronous imports and backend commands first | Avoids unnecessary infrastructure; larger imports require revisiting limits before adding durable workers |
| ADR-009 | Benchmarks withheld until consent, eligibility, and privacy gates pass | Empty state is correct at launch; thresholds alone are insufficient protection |
| ADR-010 | Initial documentation phase introduced no scaffolding | Historical decision; Phase 1 now adds only the requested bootstrap |
| ADR-011 | Phase 1 uses `frontend/`, `backend/`, pnpm and uv | Supersedes the initial `apps/web`, `apps/api`, npm proposal per explicit request; product scope is unchanged |
| ADR-012 | Local PostGIS and development Compose; `/docs` tooling exception | Health remains `/api/v1/health`; no business models, migrations, authentication or Supabase integration yet |
| ADR-013 | Separate browser and container API addresses | Browser health uses configured public URL; container checks use `backend` service DNS. Health is liveness, not DB readiness |

## Phase 2 decisions

- ADR-014: Supabase Auth uses asymmetric JWKS verification in FastAPI; Next.js uses SSR cookies, Proxy refresh and per-page server checks. No insecure bypass or shared signing secret.
- ADR-015: Business data remains on local PostGIS. Alembic owns the app schema and RLS. A separate restricted login serves API traffic; migration credentials are supplied only to explicit commands.
- ADR-016: The assigned names are organization_members and properties. User UUIDs refer to external Auth identities without a local auth.users table. OWNER/MEMBER are supported without member administration.
- ADR-017: A user-scoped transaction lock makes initial onboarding retry-safe. Same intended name returns the existing sole owned organization; conflicting repeated onboarding returns 409.
- ADR-018: X-Organization-Id is a selector, validated against current membership. All property statements and RLS policies are organization-scoped. The first-membership UI is intentionally minimal.

See [API](api.md) and [authentication](authentication.md) for the implemented endpoints and setup. Future routes/domain plans elsewhere in this document do not imply implementation.

## Platform references

Checked on 2026-09-22. These references support integration boundaries, not a claim that implementation is complete:

- [Next.js App Router documentation](https://nextjs.org/docs/app).
- [Supabase Data API security](https://supabase.com/docs/guides/api/securing-your-api): grants and schema exposure must be configured deliberately.
- [Supabase JWT documentation](https://supabase.com/docs/guides/auth/jwts): verify tokens using the configured project signing mechanism.

The Supabase Markdown changelog could not be fetched by the documentation browser in this task. Recheck relevant current platform changes when scaffolding; no version-specific implementation is committed here.

- ADR-019: NEXT_PUBLIC_SITE_URL is the explicit public origin for Auth email/callback and Proxy redirects. Never derive browser redirect origins from request.url or the Docker bind hostname. Production supplies its own build-time origin.

## Phase 3 decisions

- ADR-020: GenericCsvAdapter is the only implemented adapter. Source channel and parsing format remain separate; future provider adapters require real verified formats.
- ADR-021: Retain the 5 MiB/10,000-row product limits and support strict CP949 fallback with a visible warning. Raw files are request-local and never retained; this overrides the future storage/retention proposal above for Phase 3.
- ADR-022: Validation is a separate authenticated dry-run; commit always revalidates. Row errors block the whole batch. A savepoint rolls back all reservation writes on unexpected failure while allowing safe FAILED metadata.
- ADR-023: SHA-256 plus property/channel prevents repeated completed files; a transaction advisory lock serializes imports within that scope. Stable property/channel/external IDs drive upserts, with explicit user acknowledgement in the UI.
- ADR-024: Use Decimal/NUMERIC(18,0) for exact whole KRW per the Phase 3 request. Net is derived only from supplied gross and fee. Reservation records are not actual-stay KPI facts; no metric computation is added.
- ADR-025: Existing restricted-role RLS and explicit organization predicates extend to imports/reservations. Composite foreign keys enforce tenant/property provenance. One modular FastAPI process remains authoritative.

See [imports.md](imports.md) for implemented behavior and boundaries. Dependencies added: python-multipart for FastAPI uploads; jsdom and its TypeScript types for interactive React tests only. No storage SDK, queue, provider-specific importer or additional service is introduced.