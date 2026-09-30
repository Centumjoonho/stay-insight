# Local dashboard development fixture

Synthetic development/test data only. These amounts are not market observations or actual owner performance. Never load this fixture into production or use it as a missing-data fallback.

The fixture creates one separately labeled six-room sample property in an existing authorized organization. Existing properties and public market data are not modified. It covers September 2025 through September 2026 with 315 reservations, 78 expenses, and four completed channel CSV imports. Cancellation, cross-month nights, unknown reservation status, and missing platform fees are intentional test cases.

## Run from the repository root

Supply an existing local user's ID and an organization of which that user is a member:

```powershell
docker compose exec -T -e PYTHONPATH=/app backend uv run python tests/fixtures/development_dashboard.py --user-id <USER_UUID> --organization-id <ORGANIZATION_UUID>
```

If the Compose plugin is unavailable, replace `docker compose` with `.\.tools\docker-compose.exe`.

The command requires the development environment and the local `db` database `stay_insight` using the restricted `stay_insight_app` role. It validates membership, preserves tenant scoping/RLS, and commits imports and expenses together. Re-running finds the marked sample property without duplicating or overwriting its data. An existing sample is not reset if manually edited. Generated CSV and expense JSON files remain under this development fixture directory; expenses JSON is a reference fixture, not an application upload format.

## Expected September 2026 dashboard

| Metric | Expected value |
| --- | ---: |
| Recognized gross revenue | KRW 6,192,000 |
| Directly entered operating expenses | KRW 2,114,000 |
| Known platform fees | KRW 519,360 |
| Known total cost | KRW 2,633,360 |
| Known operating profit | KRW 3,558,640 |
| Occupied room nights | 51 |
| Available room nights | 180 |
| Estimated occupancy | 28.33% |
| Estimated ADR | KRW 125,333.33 |
| Estimated RevPAR | KRW 35,511.11 |

Financial revenue follows the existing check-in-date contract; operational estimates allocate revenue across occupied nights. Missing fees remain missing and cause the existing warning. The known operating profit does not assert that all costs are present.

Tests in `tests/test_development_dashboard.py` cover the local-only guard, expected totals, duplicate prevention, and unauthorized membership rejection against PostgreSQL.
