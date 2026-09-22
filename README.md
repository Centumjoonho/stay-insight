# Stay Insight

Korean accommodation business management SaaS, initially focused on Busan. Phase 2 adds Supabase authentication, organization onboarding, memberships and property registration/list/detail/update APIs. Business data stays on local PostgreSQL/PostGIS. Read [authentication setup](docs/authentication.md) before using the new flow; no reservations, financial features or market data are implemented.

## Repository

```text
frontend/                 Next.js App Router, TypeScript, Tailwind, ESLint
  src/app/                Home, health, auth, onboarding and property pages
  src/lib/                Central API, health and Supabase Auth clients
  tests/                  Node API-client and health tests
backend/                  FastAPI, SQLAlchemy 2, Alembic, Pydantic Settings
  app/api/v1/             Versioned health and foundation routes
  app/core/               Environment configuration
  app/db/                 Engine/session factory, tenant context, local-role setup
  app/schemas/            Explicit response schemas
  alembic/                Foundation migration, RLS and grants
  tests/                  JWT, tenant, migration, property, health and config tests
docs/                     Product and architecture contracts
docker-compose.yml        Development frontend, backend and PostGIS
pnpm-lock.yaml            Frontend/workspace lockfile
backend/uv.lock           Backend lockfile
```

Read [AGENTS.md](AGENTS.md) and [docs/product.md](docs/product.md) before changes. FastAPI remains the authoritative business API. Normal API connections now require the restricted login. Use the local administrator only for explicit migration/provisioning commands.

## Prerequisites

- Docker Desktop with Linux containers and Docker Compose v2 for the full stack.
- For host development/checks: Node.js 24 LTS, pnpm 11.19.0, Python 3.12+, uv 0.12.17.
- Ports 3000, 8000 and 5432 available; registry access for dependencies/images.

Install pnpm with `npm install --global pnpm@11.19.0` if needed. Follow the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/) for uv.

## Environment setup

From the repository root:

```powershell
Copy-Item frontend/.env.example frontend/.env.local
Copy-Item backend/.env.example backend/.env
```

Use `cp` on macOS/Linux. These local files are ignored; examples contain development defaults only.

Frontend: `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`. The browser calls `${NEXT_PUBLIC_API_BASE_URL}/api/v1/health`; no backend URL fallback is embedded in source. Missing configuration displays `backend unavailable`. Restart/rebuild after changing public variables because they are included in frontend builds.

Backend:

```dotenv
APP_ENV=development
DATABASE_URL=postgresql+psycopg://stay_insight_app:stay_insight_local@db:5432/stay_insight
CORS_ORIGINS=http://localhost:3000
```

`CORS_ORIGINS` is a comma-separated list of exact HTTP(S) origins without paths or trailing slashes. Wildcards are rejected. All example database credentials are LOCAL DEVELOPMENT defaults only. For a backend running on the host, change `db` to `localhost` in `backend/.env`. Run backend commands from `backend/` so settings read its `.env`.

## Docker Compose

```sh
docker compose config
docker compose up --build
```

Compose supplies local defaults and reads blank/public Supabase settings from root `.env` (copy root `.env.example`). Login needs the settings in [authentication.md](docs/authentication.md). Edit Compose values when customizing its environment. Source directories are bind-mounted for reload; rebuild after dependency or unmounted configuration changes. Database storage persists in a named volume. Published ports bind to loopback only.

| Resource | URL |
| --- | --- |
| Frontend | http://localhost:3000 |
| Connectivity page | http://localhost:3000/health |
| Backend base | http://localhost:8000 (no root route) |
| Swagger | http://localhost:8000/docs |
| OpenAPI | http://localhost:8000/api/v1/openapi.json |
| Health | http://localhost:8000/api/v1/health |

Health returns `{"status":"ok"}`. The frontend displays `checking`, then `backend connected` or `backend unavailable`, with a five-second timeout. This proves API liveness, not database readiness. Compose checks PostGIS separately.

Browser requests use the host's `localhost:8000`. Container-side frontend health checks use `API_INTERNAL_BASE_URL=http://backend:8000`; the backend database host is `db`. Docker service names must not be used in browser-visible URLs.

```sh
docker compose ps
docker compose logs backend frontend
docker compose exec db psql -U postgres -d stay_insight -c "SELECT PostGIS_Version();"
docker compose exec backend uv run --no-sync alembic current
docker compose down
```

`down` preserves database storage. Do not delete volumes unless you intend to erase local data. Dockerfiles and Compose are development configurations, not production deployment recipes.

## Host development

From the root:

```sh
pnpm install --frozen-lockfile
docker compose up -d db
```

Backend terminal:

```sh
cd backend
uv sync --locked
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend terminal, from the root:

```sh
pnpm --dir frontend dev
```

Health and Swagger can run without an active database. DATABASE_URL is still required configuration; connections are lazy. Online Alembic commands require PostgreSQL. Apply migration `0001_foundation` and provision the restricted login using [these commands](docs/authentication.md#start-migrate-and-provision-the-local-role). Startup never calls `create_all` or migrates automatically.

## Checks

Frontend, from the root:

```sh
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
```

Backend:

```sh
cd backend
uv sync --locked
uv run ruff check .
uv run mypy app tests
uv run pytest
uv run alembic heads
uv run alembic upgrade head --sql
```

Root `pnpm lint`, `pnpm typecheck`, `pnpm test`, and `pnpm build` combine checks and require pnpm/uv on PATH. The equivalent `npm run` entry points invoke pnpm; do not generate an npm lockfile. The full backend suite requires TEST_DATABASE_URL, an administrator URL used only to create isolated test databases/logins. It fails rather than skips when the variable is missing. See [test setup](docs/authentication.md#automated-verification).

Within Compose use `docker compose exec -T -e TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/postgres backend uv run pytest` and `docker compose exec frontend pnpm lint` (or `typecheck`, `test`). Run a production build in a separate frontend container with `docker compose run --rm --no-deps frontend pnpm build` to avoid sharing `.next` with the running dev server.

In a browser, open `/`, follow the health link, and confirm `backend connected`. Stop the backend and reload `/health` to confirm `backend unavailable`, then restart it. No business data or production credentials are needed.

See [Phase 2 verification](docs/phase2-verification.md) for current results and [Phase 1 verification](docs/bootstrap-verification.md) for the historical bootstrap report.
