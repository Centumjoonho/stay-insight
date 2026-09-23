# Stay Insight: contributor instructions

## Product and scope

Stay Insight is a Korean SaaS for accommodation owners, initially in Busan. Read [product](docs/product.md), [architecture](docs/architecture.md), [database](docs/database.md), and [repository structure](docs/repository-structure.md) before changing the application.

Phase 2 adds Supabase Auth, organization onboarding, memberships and properties on the existing local PostGIS database. Read docs/authentication.md and docs/api.md for the implemented contract. Phase 3 adds generic CSV imports and reservation reads; read docs/imports.md for that contract. Phase 4 adds manual operating expenses and a source-separated known-cost summary; read docs/expenses.md. Other business domains remain proposals. Implement only the feature explicitly assigned.

MVP: authentication, accommodation registration, CSV reservation/revenue import, expenses, operating dashboard, revenue, ADR, occupancy, RevPAR, operating profit, channel breakdown, monthly comparisons, public Busan accommodation information, tourism visitor trends, local events, and conditional anonymous benchmarks.

Out of scope: Airbnb scraping, booking engine, OTA live synchronization, AI pricing, real estate investment analysis, subscriptions/billing, mobile app, and microservices.

## Non-negotiable boundaries

- Use Next.js latest stable at scaffolding time, App Router, TypeScript, Tailwind CSS, shadcn/ui, Recharts, and Kakao Maps. Backend: Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2, Alembic. PostgreSQL/PostGIS, Auth, and Storage are hosted on Supabase. Deploy frontend to Vercel and the Dockerized API to Render.
- Browser and Next.js business-data requests go through FastAPI. Do not query business tables through Supabase clients, server actions, route handlers, or direct SQL in the frontend.
- Supabase Auth is the permitted direct authentication integration. Storage stays private and is accessed through the API in the MVP.
- All application API paths begin with `/api/v1`. FastAPI is the authoritative business API; frontend calculations are presentation formatting only.
- Keep routes thin: parse input, invoke authentication/authorization dependencies and application services, serialize output. Domain services own business rules; query modules own persistence.
- Every tenant read and write, including joins, counts, imports, exports, jobs, file retrieval, and aggregates, must be scoped to an authenticated organization. Resolve membership in the backend; never trust a client organization identifier by itself.
- Use explicit organization predicates plus database RLS as defense in depth. Test with the restricted runtime database role, not only an administrator.
- Do not use editable user metadata for authorization. Never expose database credentials, Supabase secret/service-role keys, or provider secrets to the browser or `NEXT_PUBLIC_*` variables.
- Never invent production data. Synthetic examples belong only in development/test fixtures and must never seed production or appear as a fallback for missing data.
- Preserve source, period, geography, freshness, coverage, and estimation metadata. Owner data, public observations, and anonymous benchmark releases are distinct sources. Every estimated metric must be visibly labeled estimated.
- Follow the metric contract in `docs/product.md`. Changes to definitions require documentation, calculation-version changes, and regression tests.

## Implementation discipline

- Prefer one modular backend, explicit functions, and ordinary transactions. Do not add microservices, generic repository frameworks, queues, caches, or monorepo orchestration without a demonstrated need.
- Keep code within domain boundaries. Share API contracts, not Python database models with the frontend. Add dependencies only when necessary; explain them and pin resolved versions with lockfiles.
- Alembic is the sole application migration history, including application RLS and grants. Do not create a competing Supabase migration chain. Review generated migrations and verify them against PostgreSQL/PostGIS.
- Store KRW amounts exactly, never as floating point. Use Asia/Seoul business dates, UTC audit timestamps, and explicit rounding.
- Validate uploads, enforce bounds, reject ambiguous input, and keep import commits atomic and idempotent. Do not log tokens, guest details, raw CSV rows, or private document contents.
- Do not introduce guest names/contact information unless a separately approved requirement needs them. Preserve auditability for corrections and deletes.
- Document important decisions with numbered entries in `docs/architecture.md`; split into `docs/adr/` only when useful. Update related product and database contracts together.

## Completion and verification

Every completed feature includes appropriate tests and must pass lint, type-check, and tests before it is marked complete. Security and data changes need negative tests, not only happy paths.

Use pnpm for the frontend workspace and uv for the backend. Run these root commands for code tasks (equivalent `npm run` entry points delegate to pnpm):

| Command contract | Intended coverage |
| --- | --- |
| `pnpm lint` | ESLint for web; Ruff for API |
| `pnpm typecheck` | TypeScript without emit; mypy for API |
| `pnpm test` | Frontend API/health tests and pytest; TEST_DATABASE_URL is required for real PostgreSQL integration tests |
| `pnpm build` | Production frontend build for frontend changes |

These commands require installed dependencies, pnpm and uv. For documentation-only work, check Markdown structure, relative links, whitespace, and cross-document consistency. Never conceal skipped checks. Follow the current `frontend/` and `backend/` layout. Swagger `/docs` is the explicitly requested tooling exception; application APIs remain under `/api/v1`. Do not add shadcn/ui, authentication, or Supabase integration during bootstrap.

Required feature coverage includes tenant isolation across every operation, expired/invalid tokens and revoked membership, pooled-connection context isolation, CSV validation/idempotency/rollback, cross-month metric calculations and missing denominators, source/estimate labels, and benchmark suppression. Run relevant browser journeys and accessibility checks for user-facing features. Report what changed, actual checks/results, and unresolved limitations.
