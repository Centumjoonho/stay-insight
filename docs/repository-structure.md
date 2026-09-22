# Repository structure

Phase 2 adds authentication and the organization/property foundation. This layout supersedes the original `apps/web`, `apps/api`, npm proposal at the user's explicit request. Product scope and planned domain boundaries remain unchanged.

```text
stay-insight/
  AGENTS.md
  README.md
  .gitignore
  .dockerignore
  package.json                 # root check entry points
  pnpm-workspace.yaml
  pnpm-lock.yaml
  docker-compose.yml           # development frontend, backend, PostGIS
  docs/
    product.md
    architecture.md
    database.md
    repository-structure.md
    bootstrap-verification.md  # executed checks and remaining Docker verification
  frontend/
    package.json
    .env.example
    Dockerfile
    next.config.ts
    next-env.d.ts
    tsconfig.json
    eslint.config.mjs
    postcss.config.mjs
    src/
      app/
        layout.tsx
        globals.css
        page.tsx
        health/page.tsx
      lib/health.ts
    tests/health.test.ts
  backend/
    pyproject.toml
    uv.lock
    .python-version
    .env.example
    .dockerignore
    Dockerfile
    alembic.ini
    alembic/
      env.py
      script.py.mako
      versions/0001_tenant_property_foundation.py
    app/
      main.py
      api/v1/health.py
      core/config.py
      db/
        base.py                # shared SQLAlchemy metadata
        session.py             # lazy connection/session infrastructure
      schemas/health.py
    tests/
      conftest.py
      test_health.py
      test_config.py
```

Python package directories include `__init__.py`. Environment files, dependency installations, build output and caches are ignored. Local verification artifacts are not application source.

## Tooling and boundaries

Use pnpm workspaces with a root lockfile and uv with `backend/uv.lock`. Root scripts combine ESLint/Ruff, TypeScript/mypy, Node health-helper tests/pytest, and the frontend production build. No monorepo orchestrator is needed. The health helper uses Node's built-in test runner rather than adding a frontend testing library.

The root build context is used by the frontend Dockerfile to include the workspace lockfile. The backend has its own Docker context. Source mounts support development reload without mounting host dependency directories into Linux containers.

Phase 2 adds backend models, services, repositories, auth dependencies and schemas; frontend Supabase Auth clients, a central API layer, forms and protected pages. No UI component library is installed. Add `models/`, `services/`, and `repositories/` or focused domain modules only when assigned implementation requires them. Routes stay thin; services own business rules; repositories/queries own explicitly organization-scoped persistence. No generic base-service abstraction is required.

Future Vercel frontend configuration points to `frontend/`; the future Render backend builds `backend/Dockerfile`. The current Dockerfiles are development configurations and must be reviewed for production before deployment. FastAPI remains the only business-data gateway.

## Future testing

The health/configuration tests need no database, but the full suite now requires real PostgreSQL/PostGIS for migrations, RLS and tenant isolation. SQLite cannot replace those checks. Add browser end-to-end tests for future user workflows and keep synthetic business data in development/test fixtures only. No synthetic business data is included in this bootstrap.

See [README.md](../README.md) for actual setup and check commands, and [architecture.md](architecture.md) for the recorded bootstrap decisions.

## Phase 2 additions

- Backend: api/dependencies/tenant.py, api/v1/foundation.py, core/auth/jwt.py, models/foundation.py, repositories/foundation.py, schemas/foundation.py, services/foundation.py, db/context.py and db/provision.py.
- Frontend: src/proxy.ts, lib/supabase/, lib/api/, components/ forms, login/signup/auth callback, and the (protected) App Router group with onboarding and property pages.
- Tests: JWT verification, real PostgreSQL foundation tests, API-client tests; existing health checks retained.
- Documentation: authentication.md, api.md and phase2-verification.md. The tree above remains a compact baseline overview; the verification report lists all changed files.