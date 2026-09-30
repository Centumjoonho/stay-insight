# Phase 9A official visitor contract verification

2026-09-30: **DECISION B: ONLY OFFICIAL DAILY SOURCE VERIFIED**.

## Outcome and scope

Official guide read: yes. Live basic-government API called: yes. All 16 Busan source codes and three categories: live-verified. Historical range: sampled dates only, not complete coverage. Monthly source: not found in reviewed official sources. Sanitized real fixtures: yes. Production visitor implementation: no.

The user configured TOURISM_VISITOR_API_KEY privately in root .env after the initial blocked check. Private tooling loaded it without printing it or credential URLs. Ten bounded requests were made, all to the documented basic-government daily operation. One request fetched a single day's 807 rows; the others requested at most one row. No bulk historical download, DB writes, migration, sync job, API/UI, monthly aggregation, cloud deployment, commit or push.

The official guide was read in the preceding verification. ZIP SHA-256: CBFC39E78D62DD2545E63D23033A54A25A24A06FF2953E504B61CDBACB32F7F0. It contains v4.1 API manual (299187 bytes) and v3.3 application manual (553858 bytes), both revised 2024-03-27. See [guide contract and official references](tourism-visitor-source.md). Current findings supersede the earlier blocked state.

## Actual request evidence

All requests used HTTPS, MobileOS=ETC, MobileApp=StayInsight, _type=json and pageNo=1. All returned HTTP 200. No secrets/headers/request URLs saved.

| Probe | Requested size | Observed result |
| --- | --- | --- |
| 2026-09-01 (initial and fixture capture) | 1 | Empty success, totalCount=0 |
| 2026-08-01 (initial) | 1 | One row, totalCount=807 |
| 2025-09-01 | 1 | One row, totalCount=792 |
| 2024-09-01 | 1 | One row, totalCount=792 |
| 2021-05-13 | 1 | One row, totalCount=772 |
| 2026-08-01 (fixture capture) | 1000 | All 807 rows, including 48 Busan rows |
| Invalid start/end date strings | 1 | Empty success, not parameter error |
| 2026-08-31 | 1 | One row, totalCount=807 |
| Missing startYmd | 1 | Separate top-level JSON error, resultCode=11 |

Success: response.header contains 0000/OK; response.body contains items, numOfRows, pageNo, totalCount. Nonempty items.item is always an array in these captures, even one row. Item fields: signguCode, signguNm, daywkDivCd, daywkDivNm, touDivCd, touDivNm, touNum, baseYmd, all strings. Values preserve fractional decimal notation.

Empty success has items as an empty string, numOfRows=0 and totalCount=0. Missing startYmd instead returns top-level responseTime/resultCode/resultMsg, with NO_MANDATORY_REQUEST_PARAMETERS_ERROR1(startYmd). XML gateway errors remain documentation-only. Null/missing values within real items were not observed; negative test mutations reject these rather than manufacture zero. Future application validation must reject malformed dates before HTTP requests.

Historical probes demonstrate particular dates beyond 13/24 months, not continuous retrieval. Do not use the 2021 sample as earliest date or August 31 as latest complete date. Maximum date span, page-size ceiling, publication delay, snapshot ordering, completeness guarantees and revision/backfill window remain unresolved. No source-updated timestamp or methodology version was inferred from collection time or error responseTime.

## Explicit proposed Busan mapping

Source codes/names below appeared in the real 2026-08-01 response. Local UUIDs were rechecked with read-only app.regions SELECT. Mapping is documentation only and is not persisted. Other deployments must verify their own local region identities. Source codes must be retained as strings, never generated via fuzzy matching.

| Source signguCode | Local region name | Existing region UUID |
| --- | --- | --- |
| 26110 | 중구 | 0dd96af3-cae1-56f6-bd0f-f743941a87bd |
| 26140 | 서구 | f1e636cf-7ec0-5660-ba22-455ee05cdc83 |
| 26170 | 동구 | 4901db44-0a5b-5e25-b6b1-ae89bcb1ce44 |
| 26200 | 영도구 | 172c1bf9-775a-5d67-8a17-f541fe1d2dd7 |
| 26230 | 부산진구 | 885579b3-91bd-56bf-ad81-17359856202d |
| 26260 | 동래구 | 7b24689b-96c4-5c43-932a-f8df2f5dd494 |
| 26290 | 남구 | 82f4877e-2919-5c86-bec7-5185151ca875 |
| 26320 | 북구 | 61466d9c-aba1-5ad7-8584-6df3c0341663 |
| 26350 | 해운대구 | 19e35a3d-8966-56f7-ac20-effad3a9c2d1 |
| 26380 | 사하구 | 265ee221-7706-50ba-8a4f-a7f88d2a3e43 |
| 26410 | 금정구 | b1236bab-c562-5853-9ef8-117442f93314 |
| 26440 | 강서구 | bd0cf63a-2266-5f71-8056-a685a515f2cd |
| 26470 | 연제구 | 49a83933-bbea-5342-8f58-134c392dd76a |
| 26500 | 수영구 | 94791b64-8b66-504c-b454-a067145f22b6 |
| 26530 | 사상구 | 29531ae7-f96c-5c9a-883c-5508202dc8fa |
| 26710 | 기장군 | c0a63187-ab08-57aa-9584-dcb5a63b8311 |


For every listed code, the observed category pairs are 1/현지인(a), 2/외지인(b), 3/외국인(c). No total category is documented or observed. Categories must remain separate; residents must not become outside visitors. Additivity, classification thresholds and API methodology-version comparability are not established by matching labels.

## Phase 9B recommendation and remaining gates

**OFFICIAL MONTHLY VISITOR SOURCE NOT FOUND** in the reviewed guide/catalogue. Only daily observations are verified. Recommend separately labeled DERIVED DAILY METRICS: latest published daily estimate, 7/28-day daily averages, daily trend and same-weekday comparison. All require same geography/category/methodology and full valid coverage; missing data must suppress results, never imply zero. Do not claim official monthly totals or monthly unique visitors. This provides owners regional trend context, not hotel demand, guests, prices or competitor performance.

Before enabling production collection, resolve latest-complete/publication policy, documented request limits and revisions; verify historical code/methodology changes for any requested comparisons. A key and successful response do not complete production readiness. No further setup or Docker rebuild is needed to inspect these test fixtures; the existing application still does not load this key or run a visitor job.

## Files and checks

This continuation changes docs/tourism-visitor-source.md, this report, adds backend/tests/test_tourism_visitor_wire_contract.py and backend/tests/fixtures/tourism_visitors/ (README plus five sanitized response files). The full one-day fixture preserves actual pagination counts and all 16 Busan categories. Test-only parsing harness has no imports from application callers; the production UnverifiedVisitorProvider remains disabled. Negative mutations are clearly test-only, not captured observations. No dependencies added. Prior Phase 9 uncommitted work preserved.

Final checks: Ruff passed; mypy passed on 82 files; full pytest passed 218 tests (including 15 new contract tests), 0 skipped, 2 existing dependency deprecation warnings. Local PostgreSQL integration tests ran against isolated test databases. Changed-file secret scan, relative links and whitespace passed; root .env is Git-ignored. Frontend unchanged; frontend checks not rerun for this backend contract-verification phase.
