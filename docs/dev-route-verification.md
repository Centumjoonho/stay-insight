# Docker development route regression check

Verified 2026-09-28 on Windows Docker Desktop, Next.js 16.3.5, Webpack dev.

## Evidence and scope

The old Windows frontend source bind mount plus WATCHPACK_POLLING=true produced
missing nested AppRoutes and malformed generated .next/dev/types files despite
existing source pages. Image-local source with polling disabled restored them.
This is a tested configuration workaround, not proof of a specific upstream race.
Production bundling, routes, authentication, and business logic are unchanged.

## Repeatable checks

1. Run `docker compose config --quiet` then `docker compose up -d --build`.
2. Run `docker compose exec -T frontend pnpm typecheck` against the live dev output.
   Do not run next typegen first: it could hide a dev-generated route failure.
3. Sign in normally and open an existing property's dashboard, imports/new,
   imports and reservations. Expect rendered pages and HTTP 200 in frontend logs.
   A login redirect alone does not prove that a protected route renders.
4. Run `docker compose restart frontend`, then repeat steps 2 and 3.
5. Run `docker compose up -d --no-deps --force-recreate frontend`, then repeat.
6. Run production checks in an isolated container to avoid touching live .next:

```sh
docker compose run --rm --no-deps frontend sh -c 'pnpm lint && pnpm exec next typegen && pnpm typecheck && pnpm test && pnpm build'
```

## Actual results

- Compose config valid; frontend, backend and database healthy.
- Live dev typecheck passed after initial corrected startup, restart and recreation.
- After recreation, authenticated dashboard, imports/new, imports and reservations
  rendered successfully. Dashboard/imports logs confirmed HTTP 200.
- Frontend lint, typecheck, 30 tests and isolated production build passed.
- Backend lint, mypy and 114 tests passed during the preceding same-day review;
  backend source was not modified by this configuration fix.
- No new dependency, database migration, business-data mutation or Phase 6 feature.

Frontend edits now require `docker compose up -d --build frontend`.
A plain restart preserves the existing image source. Database volumes are preserved.
See [architecture](architecture.md) ADR-034/035 and [startup](../README.md#docker-compose).