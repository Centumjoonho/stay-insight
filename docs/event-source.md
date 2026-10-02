# Phase 10 official event source investigation

2026-10-02 (Asia/Seoul). Phase 10A investigation below is historical; the Phase 10B addendum supersedes the access and implementation gate. See [implemented contract](events.md).

## Evidence levels

- VERIFIED: local repository/schema state and absence of TOURISM_EVENT_API_KEY in root .env and running backend (presence checks only).
- DOCUMENTATION ONLY: official catalogue and embedded Swagger inspected on this date. These are not successful API responses.
- LIVE VERIFIED: none. No event API key was sent and no event payload was obtained.
- UNRESOLVED: runtime response shapes, approved account access, full geography mapping, query-window semantics and source lifecycle guarantees.

## Candidate and official references

Primary candidate: 한국관광공사_국문 관광정보 서비스_GW, dataset 15101578.

- [Official catalogue and embedded Swagger](https://www.data.go.kr/data/15101578/openapi.do?recommendDataYn=Y)
- [Provider notice linked by the catalogue](https://api.visitkorea.or.kr/#/cmsNoticeDetail?no=207) (linked reference, not independently inspected).

The catalogue explicitly supports web-service reuse. It lists free access, unrestricted catalogue-level use, automatic development approval, reviewed operating approval and development traffic of 1,000. Actual account approval/quota remains unverified. These catalogue statements do not establish this account's production authorization or blanket image rights. Images have separate restrictions; Phase 10 will not ingest them.

One primary provider is preferred. Busan culture/exhibition services remain FUTURE SUPPLEMENTARY SOURCES, not evaluated/selected or combined here: the preferred candidate already documents event identifiers, dates and structured geography. No claim about supplementary API availability is made.

## Contract checklist

All provider facts below are DOCUMENTATION ONLY unless explicitly marked UNRESOLVED.

| # | Contract | Evidence / open question |
| --- | --- | --- |
| 1 | Provider | 한국관광공사, 디지털인프라팀 |
| 2 | Dataset | 국문 관광정보 서비스_GW, 15101578 |
| 3 | Catalogue | Official link above |
| 4 | Endpoint | HTTPS apis.data.go.kr/B551011/KorService2/searchFestival2 in embedded Swagger; not guessed from older examples |
| 5 | Authentication | Required serviceKey query parameter; private future variable TOURISM_EVENT_API_KEY |
| 6 | Approvals | Development automatic, operation reviewed; this account's event-service approval UNRESOLVED |
| 7 | Reuse | Catalogue-level unrestricted use; images separately qualified |
| 8 | SaaS | Web services explicitly contemplated; operation approval, actual quota and field-specific obligations must still be satisfied |
| 9 | Request | Required MobileOS, MobileApp, eventStartDate, serviceKey. Optional list below |
| 10 | Format | JSON/XML. Swagger models header/body and XML response root; actual JSON wrapper and item object/list shape UNRESOLVED |
| 11 | Identity | contentid documented as content identifier. Stability/reuse across revisions UNRESOLVED |
| 12 | Title | title |
| 13 | Start | eventstartdate, YYYYMMDD |
| 14 | End | eventenddate, YYYYMMDD; missing-end behavior UNRESOLVED |
| 15 | Venue/address | addr1/addr2 available in schema; separate venue field not shown in festival list; do not fabricate one |
| 16 | Region | lDongRegnCd; legacy areacode marked unused/deletion planned |
| 17 | Sigungu | lDongSignguCd; legacy sigungucode marked unused/deletion planned. Exact 16 Busan code/name pairs UNRESOLVED |
| 18 | Coordinates | mapx/mapy described as GPS X/Y strings; exact CRS, precision and missing-value sentinels UNRESOLVED |
| 19 | Detail URL | No event-detail URL in inspected festival-list fields. Catalogue link is safe provenance; do not manufacture event URLs |
| 20 | Status | progresstype describes cancellation/postponement; exact values/null meaning UNRESOLVED. festivaltype describes ongoing/online/biennial form, not a verified cancellation enum |
| 21 | Category | contenttypeid and lclsSystm1/2/3; old cat1/2/3 deprecated. Category dictionary values UNRESOLVED |
| 22 | Images | firstimage/firstimage2 and cpyrhtDivCd documented; catalogue mentions Type1/Type3 and restrictions. Ignore images, no download/rehosting |
| 23 | Pagination | pageNo/numOfRows requests and totalCount/pageNo/numOfRows response; actual behavior UNRESOLVED |
| 24 | Maximum size | UNRESOLVED; no maximum asserted from schema |
| 25 | Query horizon | eventStartDate required, eventEndDate optional, YYYYMMDD. Whether range means overlap or starts-within, and maximum past/future span, UNRESOLVED |
| 26 | Updates | Catalogue says real-time; this is not a guarantee of event accuracy, cancellation latency or future coverage |
| 27 | Removal | UNRESOLVED; absence cannot be treated as cancellation/deletion |
| 28 | Modification | modifiedtime and createdtime fields documented; response timezone/precision UNRESOLVED. Optional modifiedtime request is YYYYMMDD |
| 29 | Missing fields | Runtime null/empty/omitted behavior UNRESOLVED; Swagger optionality alone insufficient |
| 30 | Empty result | UNRESOLVED; no invented fixture |
| 31 | Errors | Catalogue lists gateway/auth errors (including permission, quota, invalid key); actual body shape and success-code value UNRESOLVED |

Optional festival request parameters: numOfRows, pageNo, _type (json; XML default), arrange, eventEndDate, lDongRegnCd, lDongSignguCd, lclsSystm1/2/3, modifiedtime. Legacy areaCode/sigunguCode/cat1/2/3 remain listed but marked unused/deletion planned. arrange A/C/D sorts all records; O/Q/R requires an image, so an image-required sort would silently narrow text-only coverage.

Official `/ldongCode2` is documented on the same service. Required serviceKey/MobileOS/MobileApp, optional pagination/_type/lDongRegnCd/lDongListYn. N returns code/name; Y exposes lDongRegnCd/lDongRegnNm/lDongSignguCd/lDongSignguNm. Obtain real Busan pairs before mapping to existing app.regions by exact name; never reuse visitor code assumptions or local UUIDs.

## Manual archive and access limitations

Catalogue exposes 개방데이터_활용매뉴얼(국문).zip via fn_fileDownload with file identifier FILE_000000003603931, sequence 1. HTML and public helper scripts were inspected, but a resolved archive download URL was not obtained. Archive was not downloaded or inspected; no guide-only fact is marked verified. Embedded Swagger was inspected directly as a separate documentation source.

Root .env and running backend do not have a nonempty TOURISM_EVENT_API_KEY. Other keys were not reused. This prevents a bounded authenticated contract probe. No real fixture, parser, region map, data model or production provider is justified yet.

## Resume gate

1. Obtain approval for this exact dataset; put its key privately in root .env as TOURISM_EVENT_API_KEY. Never paste it into chat or NEXT_PUBLIC variables.
2. Resume implementation to wire the private variable to backend; that wiring does not exist yet. Recreating the current backend alone will not forward this new variable.
3. Resolve/download the official guide; inspect code migration, date predicates, cancellation fields, missing fields and timezone details.
4. Bounded probe: official region lookup, one small Busan event page over a short supported interval, a verified empty case and safe error case. Never bulk-download during discovery.
5. Save sanitized observed fixtures only. Confirm pagination, geography and ongoing-event overlap coverage before choosing persistence and sync window.
6. Only then implement the additive migration, atomic sync, authorized API and separate UI; test before one controlled local sync.

Event presence never establishes lodging demand, revenue, occupancy or pricing effects.


## Phase 10B live evidence superseding the initial gate

User confirmed both service approvals. Approved TOURISM_EVENT_API_KEY was used independently; its value was not compared or printed. LIVE VERIFIED: resultCode 0000; response.header/body/items.item array; integer totalCount/pageNo/numOfRows; legal-dong Busan 26 and all 16 three-digit sigungu codes listed in events.md. October 2–16 query returned totalCount 13, two inspected rows; annual January–December event was included, indicating overlap behavior for this observation. contentid/title/eventstartdate/eventenddate/new legal-dong fields/addr1/addr2/progresstype were observed. Raw status 선택안함 and empty addr2 were observed; no cancellation taxonomy inferred.

One additional bounded request saved backend/tests/fixtures/events/festival.json: SANITIZED OFFICIAL LIVE RESPONSE, TEST ONLY. It retains only consumed fields/envelope, excluding media/phone/unused fields and all request credentials. This is never production fallback. Actual error/zero envelopes remain NOT VERIFIED; errors fail closed and provider-wide zero currently produces EVENT_EMPTY_CONTRACT_UNVERIFIED. No assertion of an unobserved empty schema. Coordinates, venue, category, detail URL and source timestamp normalization are omitted from implementation.

The earlier absent-key statements and production-stop plan describe the initial investigation only. Phase 10B now implements persistence/sync/API/UI; [verification report](phase10b-verification.md) records actual checks separately from documentation facts. Guide archive remains uninspected; source lifecycle/snapshot/maximum page size/future completeness remain unresolved.
