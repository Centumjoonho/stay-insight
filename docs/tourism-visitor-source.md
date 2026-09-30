# Tourism visitor source verification

## Phase 9A live continuation — current result

2026-09-30: **DECISION B: ONLY OFFICIAL DAILY SOURCE VERIFIED**. Private root .env key is now available and authenticated requests succeeded. This section supersedes the earlier blocked report below. The production provider remains disabled; no storage, sync, endpoint or UI was enabled.

LIVE-VERIFIED: locgoRegnVisitrDDList returns HTTP 200 JSON with response.header resultCode=0000/resultMsg=OK. One-day 2026-08-01 response returned all 807 rows for requested numOfRows=1000; body.numOfRows is the returned row count, not necessarily the requested size. items.item is an array, including one-row pages. All eight documented item fields are strings. All 16 Busan codes and categories 1/2/3 are present (48 rows). See the explicit code-to-local-UUID mapping in [live verification](tourism-visitor-contract-verification.md).

LIVE-VERIFIED empty result: 2026-09-01 returned items="", numOfRows=0, totalCount=0, pageNo=1 with success header. Invalid date strings also returned empty success. Missing startYmd returned HTTP 200 JSON with top-level responseTime/resultCode/resultMsg, resultCode=11, without the normal response wrapper. A future parser must inspect application status/envelope, not just HTTP 200. XML gateway errors remain documentation-only; they were not induced. Null/missing item values were not observed and must not be inferred as zero.

Historical single-row probes found data on 2021-05-13, 2024-09-01 and 2025-09-01. Thus sampled data exists beyond 24 months, but continuous 13/24-month coverage, earliest date and historical administrative comparability remain UNRESOLVED. 2026-08-31 has rows; 2026-09-01 has none. This does not establish the latest available date or latest complete date. Daily publication lag, maximum date span, page-size maximum, ordering and revision policy remain UNRESOLVED. Successful size 1000 is an observed accepted request, not a documented maximum.

**OFFICIAL MONTHLY VISITOR SOURCE NOT FOUND** in the reviewed official guide/catalogue. Recommend the daily-derived Phase 9B proposal below, conditional on resolving publication/completeness and operational limits. The guide was read; live fixtures and test-only parsing checks now exist. No official monthly unique totals, category sums or production adapter are inferred.

## Earlier documentation-only verification (historical)

Phase 9A, 2026-09-30: **DECISION C: LIVE/CONTRACT VERIFICATION STILL BLOCKED**.
**LIVE API RESPONSE NOT VERIFIED**. The official local guide was read successfully; the private key was not available to this execution environment. The foundation provider remains disabled. No visitor persistence, sync, API, UI or monthly aggregation was added.

This section supersedes the historical discovery record below. See [Phase 9A evidence and next steps](tourism-visitor-contract-verification.md).

## Evidence and confidence

- VERIFIED: the user-supplied ZIP contains the official-named v4.1 API manual and v3.3 application manual. Both DOCX XML contents were extracted in memory and read, including request/response tables. No archive files were installed or executed.
- DOCUMENTATION-ONLY: guide v4.1 (revision 2024-03-27), sections II and III, documents two daily operations, parameters, categories, sample XML and error codes. Application manual v3.3 documents per-operation development quota. These are not captured live responses.
- LIVE-VERIFIED: no external visitor API facts. Read-only local PostgreSQL inspection confirms 16 existing Busan regions; it does not verify TourAPI codes.
- USER-PROVIDED: development application approved. No independent account login or approval check was performed.
- UNRESOLVED: actual HTTP/JSON/empty/error responses, Busan codes, available history, latest complete day, request limits, revision policy and API-specific methodology applicability.

Official references: [dataset 15101972 and guide download](https://www.data.go.kr/data/15101972/openapi.do), [Data Lab methodology](https://datalab.visitkorea.or.kr/datalab/portal/getMetaInfoList.do), [regional visitor interpretation](https://datalab.visitkorea.or.kr/datalab/portal/loc/getAreaVisitDataForm.do). The catalogue was rechecked during Phase 9A. The local ZIP has the same guide name advertised there; independent byte-for-byte download provenance was not verified.

## Guide contract (DOCUMENTATION-ONLY)

Base: https://apis.data.go.kr/B551011/DataLabService . Use HTTPS only.

| Operation | Scope and period |
| --- | --- |
| /metcoRegnVisitrDDList | Metropolitan/provincial daily observations; areaCode and areaNm |
| /locgoRegnVisitrDDList | Basic local government daily observations; signguCode and signguNm |

These are all visitor operations listed in the guide. **OFFICIAL MONTHLY VISITOR SOURCE NOT FOUND** in the reviewed guide/catalogue. This is a bounded finding, not proof that no other officially supported export exists. No private chart endpoints were queried.

| Request field | Required | Documented semantics |
| --- | --- | --- |
| serviceKey | Yes | Approved private service key; URL encoding required by parameter table |
| MobileOS | Yes | IOS / AND / WIN / ETC |
| MobileApp | Yes | Actual service/application name |
| startYmd, endYmd | Yes | YYYYMMDD start and end dates |
| pageNo | No | Current page; example 1 |
| numOfRows | No | Page size; example 10; maximum unspecified |
| _type | No | json requests JSON; XML is the default |

No region/category filter or monthly selector is documented. The guide's key encoding narrative distinguishes older/newer issued keys, so avoid blindly double-encoding a pre-encoded key; actual private request behavior remains to be tested. Page ordering/snapshot guarantees, zero/negative page handling and maximum date span are unspecified. Examples are not guaranteed defaults or limits.

XML sample envelope: response/header/{resultCode,resultMsg}, response/body/{items/item,numOfRows,pageNo,totalCount}. Sample success is **0000 / OK**, while the provider error-code table says **00 / NORMAL_CODE**: preserve this discrepancy until live verification. JSON is advertised, but wrapper shape, singleton/list behavior and numeric/string types are not independently live-verified. The guide says item fields are alphabetically ordered; parsers must not depend on object-key ordering.

Basic-government fields: baseYmd, signguCode, signguNm, daywkDivCd, daywkDivNm, touDivCd, touDivNm, touNum. All are marked required in the guide response table. Metro substitutes areaCode/areaNm. Codes must remain strings. touNum has fractional sample values; a future parser must preserve exact Decimal values. Null/omitted/blank/suppressed representations are unspecified; none may silently become zero. Weekday codes: 1 Monday through 7 Sunday.

| touDivCd | Exact guide touDivNm | Interpretation boundary |
| --- | --- | --- |
| 1 | 현지인(a) | Local residents; do not label as outside visitors |
| 2 | 외지인(b) | Non-local category; catalogue identifies KT domestic inputs |
| 3 | 외국인(c) | Foreign category; catalogue identifies SKT foreign inputs |

No total category is documented. The labels alone do not prove non-overlap/additivity. Do not sum categories, districts into Busan, or daily observations into official monthly values. Resident classification, dwell thresholds and methodology version boundaries need further API-specific evidence. The current generic DTO is not authorization to publish category 1 as visitor demand.

## Errors, quota and freshness

Guide gateway errors are XML even when JSON is requested: OpenAPI_ServiceResponse/cmmMsgHeader with errMsg, returnAuthMsg, returnReasonCode. Documented gateway codes: 01, 04, 12, 20, 22, 30, 31, 32, 99. Provider table additionally lists 02 DB_ERROR, 03 NODATA_ERROR, 05 SERVICETIMEOUT_ERROR, 10 invalid parameter, 11 missing mandatory parameter, 21 temporary key disable, 33 unsigned call. Catalogue's current gateway list also includes 23 per-second limit and 29 blocked IP; the older manual is not an exhaustive current list. Exact HTTP statuses and actual payloads are unverified. NODATA_ERROR documentation does not establish whether empty success uses an empty string, array, null or omitted items.

The v3.3 application guide specifies **1,000 calls per operation per day** for development; actual account quota and per-second limit remain unverified. The v4.1 guide says **daily refresh**, without a publication hour or delay. Catalogue's “real-time” metadata is not a promise of same-day complete observations. Do not invent a D-1/D-2 cutoff or copy MOIS freshness rules.

Earliest date, latest complete date, 13/24-month availability and maximum request span are UNRESOLVED. The 2021-05-13 sample is not a historical-retention guarantee; a service start date is not a data start date. Data Lab warns that historical estimates can change and explains why summing rounded daily figures does not reproduce official monthly figures. API backfill horizon, revision identifiers and completeness signals are not specified in this guide.

## Proposed Phase 9B contract (not implemented)

Only after live response, geography and completeness checks: show each supported category separately with estimated/source/reference-day/collection-time labels. Prefer 외지인 and 외국인; omit 현지인 from visitor cards. Proposed metrics are **DERIVED DAILY METRICS**: latest published daily estimate, 최근 7일 일평균 추정 방문자, 최근 28일 일평균 추정 방문자, daily trend and same-weekday comparison.

Require all 7/28 consecutive valid days of the same geography/category/methodology for the corresponding average; missing days suppress the result rather than count as zero. Show exact coverage and avoid claiming a day is complete without evidence. Suppress relative change on zero/missing baseline or incompatible methods. Never call these monthly visitors, monthly tourists, monthly unique visitors or provider-published averages. They offer regional trend context for owners, not lodging demand, guest counts, pricing advice or causal explanations of owner revenue. No implementation approval is implied.

## Phase 9 foundation discovery record (historical)

Status: **LIVE VISITOR PROVIDER NOT VERIFIED** (2026-09-30). An official daily-data candidate exists, but the full monthly product/source gate has NOT passed. No live request with a key, official response ingestion, persistence or monthly chart has been implemented. This document distinguishes facts from unresolved requirements.

## Official evidence

- S1: [한국관광공사_빅데이터_지역별 방문자수_GW, catalogue 15101972](https://www.data.go.kr/data/15101972/openapi.do). Read the catalogue and its embedded Swagger on 2026-09-30. Catalogue modified date shown: 2026-05-13; guide named TourAPI_Guide_(관광빅데이터)v4.1.zip. The ZIP itself was not retrieved/read; do not claim its contents verified.
- S2: [한국관광 데이터랩 데이터 설명](https://datalab.visitkorea.or.kr/datalab/portal/getMetaInfoList.do). Read official methodology/interpretation notes, including daily vs monthly rounding, revisions and administrative changes. This describes Data Lab methodology; API-version applicability still requires verification.
- S3: [방문자기준 지역방문현황](https://datalab.visitkorea.or.kr/datalab/portal/loc/getAreaVisitDataForm.do). Confirms population estimation and caution about absolute values.
- S4: [한국관광 데이터랩](https://datalab.visitkorea.or.kr/datalab/portal/main/getMainForm.do). The portal's public webpage is not permission to scrape its private chart endpoints. No scraping/internal endpoint discovery is implemented.

## Discovery gate checklist

| Requirement | Verified fact / unresolved point |
| --- | --- |
| Provider and dataset | S1 identifies 한국관광공사 and the exact dataset above |
| Official API existence | S1 embeds DataLabService Swagger with two daily operations listed below |
| License/cost | S1 displays 이용허락범위 제한 없음 and 무료 |
| Customer-facing SaaS | Catalogue reuse indication is favorable; production-account use requires the stated review. No approval for this account/service was verified; do not claim an approved commercial deployment |
| Access | S1 requires a service key; development automatic approval, operation review |
| Rate limit | S1 advertises development traffic 1,000; actual account quota, maximum page/date span and per-second limits unverified |
| Geography | S1 distinguishes 광역 and 기초지자체. Busan 16-district code list/actual coverage not verified |
| Stable region mapping | Field names exist; actual official code values and mapping/version unverified |
| Historical availability | Actual earliest/latest dates and 13–24-month retrievability unverified |
| Time granularity | Two documented operations are daily (DD/baseYmd); no monthly operation confirmed |
| Meaning | S1 describes regional visitors outside usual residence/commute/school activity; not synonymous with tourists or lodging guests |
| Estimate | S3 describes population estimation; S1 identifies KT domestic and SKT foreign inputs |
| Duplicates | S1 describes daily unique visitors: the same person's multi-day visit contributes on each day, not one monthly unique person |
| Visitor categories | touDivCd/touDivNm exist; accepted category codes and combining categories not verified |
| Methodology/version | S2 explains estimation/rounding/revisions. Exact API methodology-version boundaries unverified |
| Update lag | Catalogue says 실시간; this is NOT proof of real-time visitor observations. Actual publication calendar/lag unverified |
| Revision/backfill | S2 says historical results can change; safe refresh horizon and API backfill behavior unverified |
| Pagination | pageNo/numOfRows/totalCount documented; page-size maximum, ordering, empty envelopes and stable snapshot behavior unverified |
| Missing values | Wire representation of no observation/suppression/zero unverified; never coerce absence to zero |
| Source period | baseYmd documented as reference day; timezone/cutoff/complete-day guarantees unverified |
| Incomplete month | No verified monthly publication/completeness contract |

## Why daily rows cannot satisfy the requested monthly UI yet

S2 says published rounded daily values must not simply be added to reproduce official monthly totals: monthly values are aggregated before rounding. It also warns against summing districts into a province/city total. Thus there is no authorized automatic daily→monthly or district→Busan conversion in this feature. A sum cannot be presented as an official monthly observation or a monthly unique-person count.

Resolve this by obtaining an officially supported monthly API/export with explicit automation/reuse permission and definition, or by separately agreeing on a differently labeled daily product. A displayed web chart is not a verified external API contract. Do not silently change Phase 9's monthly requirement.

## Observed request/schema facts — documentation only

S1 embedded Swagger host: apis.data.go.kr/B551011/DataLabService, with HTTPS supported.

| Operation | Documented scope |
| --- | --- |
| /metcoRegnVisitrDDList | 광역 지자체 일별 방문자 |
| /locgoRegnVisitrDDList | 기초 지자체 일별 방문자 |

The embedded operation request lists name MobileOS, MobileApp, serviceKey, startYmd, endYmd, numOfRows and pageNo. Dates are YYYYMMDD. Requiredness shown: first five required, pagination optional. No undocumented region filter, month selector or response-format switch was invented. Keys were not used in discovery and no authenticated API URL was logged.

Response metadata names: resultCode/resultMsg, pageNo/numOfRows/totalCount, items/item. Daily fields: baseYmd; areaCode/areaNm for 광역, signguCode/signguNm for 기초; touDivCd/touDivNm/touNum; daywkDivCd/daywkDivNm. touNum is documented as a string. The raw label contains 관광객, but the catalogue explicitly distinguishes visitors from tourists; the internal metric label is 추정 방문자 수. Actual JSON envelope/list shape and empty/error response semantics still require the guide and a sanitized real response. No wire parser is implemented or claimed tested.

Future adapter candidates: date → reference_date; region code/name → opaque source fields; visitor code/name → opaque category; value → exact Decimal. These are proposed internal mappings, not a production parser. Day-of-week fields are unnecessary for the monthly goal; raw payload and personal/location traces are not stored. source_updated_at/methodology_version stay unknown unless independently documented; collection timestamp is not the source update date.

## Region strategy and next evidence

Reuse app.regions after an explicit versioned official-code mapping is verified. Existing Region UUIDs are internal, not provider codes. No production code/name mapping is currently supplied. No address/GPS inference, city-number fallback or second regions table.

To unlock live work, obtain the official guide and approved access for this dataset, then confirm monthly availability/semantics with the provider (AI인프라센터 / TourAPI operations via S1). Specifically request monthly precision, calendar/completeness, Busan district codes, historical range, category semantics, publication lag, revisions, pagination limits and missing-value examples. Preserve sanitized field/shape evidence in test fixtures after verification. Account keys belong only in backend/private configuration, never chat, Git or NEXT_PUBLIC_*.
