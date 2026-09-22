# Phase 1 bootstrap verification

Scope: project bootstrap only. No authentication, Supabase integration, UI component library, business domain model, business table or business feature was added. Product and database specifications are unchanged.

## Result

Implemented the requested scaffold and verified every check available without Docker. Full Docker acceptance remains unverified, not passed.

| Check | Result |
| --- | --- |
| Docker Compose config | Blocked: `docker` executable not installed/on PATH; standard Docker Desktop path also absent |
| Docker Compose up/build | Blocked for the same reason |
| Compose YAML | Parsed successfully with the already-installed js-yaml parser; exactly frontend, backend and db services. This is not Compose CLI validation |
| Local homepage | HTTP/browser success, visible content and functioning health navigation |
| API health | Real HTTP 200, exact `{"status":"ok"}` |
| Swagger /docs | HTTP 200 and browser-rendered operation/schema |
| Frontend health | Initial HTML contains checking; browser shows connected, unavailable after API shutdown, and connected after restart |
| Browser errors | No errors or Next.js error overlay on successful flow; offline failure was intentional |
| Frontend ESLint | Passed without warnings after cleanup |
| Frontend TypeScript | Passed |
| Frontend tests | 4 passed |
| Frontend production build | Passed, Next.js 16.3.5; home and health routes generated |
| Frontend frozen install | Passed; no peer dependency issues |
| Backend Ruff | Passed |
| Backend mypy | Passed, 15 source files |
| Backend pytest | 8 passed; 2 upstream deprecation warnings |
| uv lock check | Passed; 38 packages resolved |
| Alembic heads/offline upgrade | Passed; no revisions, offline BEGIN/COMMIT only |
| Live PostgreSQL/PostGIS and online Alembic | Not executed: no Docker engine/database available |
| Secrets/scope review | Only local development/test database credentials; env files ignored; no production secrets or business features |
| Repository review | git status/diff checks, source review, whitespace scan and tested-copy comparison completed |

The backend warnings come from Starlette's TestClient use of httpx and an AnyIO BlockingPortal alias. Tests pass; no unrelated dependency migration was added to this bootstrap.

## Environment limitation

Package tools failed to write into the project directory (ENOENT/FileNotFoundError), while the file-editing tool could create source files. Dependency resolution, builds, tests and local servers therefore ran from a temporary copy under the host's Temp directory. Network downloads required tool escalation. Generated manifests and lockfiles were brought back into the repository. A normalized-content comparison confirmed 35 application/configuration/lock files match the verified copy (line endings excluded). This is not an in-place build claim.

Temporary uv and agent-browser tooling were used without adding them as application dependencies. Temporary servers and browser were stopped after verification. No Git commit was created; the repository began with untracked documentation, so ordinary `git diff` alone could not cover added files. Added source was inspected explicitly.

## Commands executed

Commands below use portable `uv`/Python names; this host used the bundled Python executable and temporary `tools/bin/uv.exe`. Run backend commands from `backend/` unless a project/config argument is shown.

Dependency/setup commands:

```sh
node --version
pnpm --version
npm view next version
npm view pnpm version
python --version
python -m pip install --target <temporary-tools-directory> uv
pnpm --filter @stay-insight/frontend add --save-exact next@16.3.5 react@latest react-dom@latest
pnpm --filter @stay-insight/frontend add --save-dev --save-exact typescript@latest @types/node@24 @types/react@latest @types/react-dom@latest tailwindcss@latest @tailwindcss/postcss@latest eslint@9 eslint-config-next@16.3.5
pnpm --filter @stay-insight/frontend add --save-dev --save-exact typescript@5.9.3 @types/node@24.13.6 eslint@9.39.5
pnpm install --frozen-lockfile
pnpm peers check
uv sync --project backend --python <bundled-python>
uv lock --project backend --check
```

TypeScript latest resolved to 7.0.2, outside the installed ESLint parser's supported peer range; it was replaced with 5.9.3. pnpm's optional unrs-resolver build script was explicitly disabled; final install, lint and build passed without it. All dependency resolution is recorded in the lockfiles.

Checks:

```sh
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
uv run --project backend ruff check backend
uv run --project backend mypy --config-file backend/pyproject.toml backend/app backend/tests
uv run --project backend pytest -c backend/pyproject.toml backend/tests
uv run --project backend alembic -c backend/alembic.ini heads
uv run --project backend alembic -c backend/alembic.ini upgrade head --sql
docker compose config
docker compose up --build
git diff --check
git diff --stat
git status --short
git ls-files
git check-ignore frontend/.env.local backend/.env
```

Docker commands failed because the executable was unavailable. Additional PowerShell/Node checks parsed Compose YAML, scanned whitespace/secret patterns, confirmed ignored environment files, and compared the tested copy with repository contents.

Runtime/browser checks:

```sh
uv run --no-sync uvicorn app.main:app --host 127.0.0.1 --port 8000
pnpm --dir frontend dev
npm exec --yes --package=agent-browser -- agent-browser --version
```

With the isolated `stay-insight-phase1` agent-browser session, executed `open`, `snapshot -i`, `screenshot --annotate`, `get text body`, `eval` for error-overlay detection, `errors`, `find role link click`, and `close`. Visited homepage, health page and Swagger. PowerShell `Invoke-WebRequest` checked health JSON, Swagger HTTP status and the initial checking text. Stopped/restarted only the API process created for this task to verify unavailable/recovery states.

## Files changed

Modified existing files:

- `AGENTS.md`: current bootstrap status, pnpm/uv commands and explicit bootstrap boundaries.
- `docs/architecture.md`: current implementation status, /docs exception, and ADR-011 through ADR-013.
- `docs/repository-structure.md`: actual frontend/backend layout replacing the earlier proposal.

Unchanged: `docs/product.md` and `docs/database.md`.

Created files:

```text
.dockerignore
.gitignore
README.md
backend/.dockerignore
backend/.env.example
backend/.python-version
backend/Dockerfile
backend/alembic.ini
backend/alembic/env.py
backend/alembic/script.py.mako
backend/alembic/versions/.gitkeep
backend/app/__init__.py
backend/app/api/__init__.py
backend/app/api/v1/__init__.py
backend/app/api/v1/health.py
backend/app/core/__init__.py
backend/app/core/config.py
backend/app/db/__init__.py
backend/app/db/base.py
backend/app/db/session.py
backend/app/main.py
backend/app/schemas/__init__.py
backend/app/schemas/health.py
backend/pyproject.toml
backend/tests/conftest.py
backend/tests/test_config.py
backend/tests/test_health.py
backend/uv.lock
docker-compose.yml
docs/bootstrap-verification.md
frontend/.env.example
frontend/Dockerfile
frontend/eslint.config.mjs
frontend/next-env.d.ts
frontend/next.config.ts
frontend/package.json
frontend/postcss.config.mjs
frontend/src/app/globals.css
frontend/src/app/health/page.tsx
frontend/src/app/layout.tsx
frontend/src/app/page.tsx
frontend/src/lib/health.ts
frontend/tests/health.test.ts
frontend/tsconfig.json
package.json
pnpm-lock.yaml
pnpm-workspace.yaml
```

## Outstanding acceptance work

On a Docker-capable host, run `docker compose config`, `docker compose up --build`, `docker compose ps`, the documented PostGIS query and online Alembic check. Confirm all three containers become healthy and browser health still connects. No further business implementation is authorized by Phase 1.
