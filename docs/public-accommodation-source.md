# 공식 숙박업 API 출처와 매핑

2026-09-28: 파일 다운로드 경로 대신 승인된 공식 REST API로 연결한다.
기존 파일 서버 403 조사 결과는 API 부재를 의미하지 않았다.

- [행정안전부_문화_숙박업 조회서비스](https://www.data.go.kr/data/15155124/openapi.do)
- 제공기관: 행정안전부 지역디지털협력과. 무료, 이용허락범위 제한 없음.
- HTTPS endpoint: https://apis.data.go.kr/1741000/lodgings/info
- 요청: serviceKey, pageNo, numOfRows, returnType=json.
- 실제 조회 검증: resultCode="0", response.body.items.item 배열, totalCount/pageNo/numOfRows.
- 실제 서버는 numOfRows=1000 요청에도 100으로 제한했다. 구현은 100을 요청한다.
- 매일 갱신되는 2일 전 기준 자료. 실시간 상태가 아니다.
- /history는 이번 범위에서 사용하지 않는다. 현재 상태를 과거 상태로 표시하지 않는다.

## 매핑

| 원본 | 사용 |
| --- | --- |
| OPN_ATMY_GRP_CD + MNG_NO | source_record_id = 자치단체코드:관리번호. source와 함께 유일 |
| BPLC_NM | 사업장명 |
| ROAD_NM_ADDR / LOTNO_ADDR | 부산 구·군 판정. 둘이 충돌하거나 부산 구·군을 판정할 수 없으면 실패 |
| BZSTAT_SE_NM | 원본 업태 보존; 숙박업(생활)은 생활 숙박, 일반호텔/숙박업(일반)은 일반 숙박. 나머지 OTHER |
| SALS_STTS_CD/NM + DTL_SALS_STTS_CD/NM | 원본 코드·명칭 모두 보존 |
| LCPMT_YMD / CLSBIZ_YMD | YYYY-MM-DD, 공백/null은 미제공. 잘못된 날짜는 실패 |
| DAT_UPDT_PNT | 행 갱신 시각, Asia/Seoul로 해석 후 UTC 저장 |

OPEN은 01/영업·정상 + 상세 01/영업 조합만 허용한다.
CLOSED는 03/폐업과 상세명 폐업, SUSPENDED는 02/휴업과 상세명 휴업일 때만 허용한다.
취소/말소/만료/정지/중지 및 새 코드는 UNKNOWN이다. 미분류를 폐업으로 추정하지 않는다.
실제 응답에서 OPEN 01/영업·정상/01/영업, CLOSED 03/폐업/02/폐업을 확인했다.
일반호텔을 관광호텔로 분류하지 않는다. 단일 숙박업 인허가의 등록 수이며 전체 숙박시설 수가 아니다.
주소는 분류에만 사용하고 원본 전체 주소, 전화번호, 좌표, 시설정보 및 raw payload를 저장하지 않는다.
공식 좌표계 EPSG:5174를 위경도로 취급하지 않는다. 지도/GPS 수집 없음.

## 완전성과 신선도

전국 모든 페이지를 읽은 뒤 부산 16개 구·군만 저장한다. 비부산 행도 식별자 중복 검사에 포함한다.
페이지 번호, 행 수, 총수 변화, 중복, malformed 응답, 결과 코드를 검사한다.
첫 페이지를 마지막에 다시 읽어 식별자/총수 변동을 검사한다. 이 API는 검증된 snapshot token이
없으므로 수집 중 모든 행의 원자적 일관성을 보장하지는 못한다. 변동 감지 시 배치 전체를 실패한다.
전국 0건 응답도 정상 부산 0건으로 발행하지 않는다. 전국 전체 검증 성공 이후의 지역별 0건만 유효하다.

응답에는 전체 자료 기준일이 없어 source_reference_date는 null을 유지한다.
오늘-2일 또는 행 갱신 시각의 최댓값을 자료 기준일로 만들지 않는다.
수집 시각과 원본 갱신 주기를 구분한다. 마지막 성공 자료/기준일의 7일 stale 정책 유지.

## 통신과 인증

PUBLIC_ACCOMMODATION_API_KEY는 서버 전용이다. 원문 키와 1회 URL 인코딩 키를 허용하고
unquote 후 urlencode 한 번으로 요청한다. +를 공백으로 변환하지 않는다.
API 주소는 코드의 고정된 공식 HTTPS endpoint이며 redirect를 허용하지 않는다.
응답당 8 MiB, 최대 200,000행, 요청 timeout 30초, 일시적 네트워크/429/5xx 최대 3회 시도.
로그/DB에는 안전한 오류 코드만 기록하고 URL/키/원본 응답은 남기지 않는다.
합성 upstream 형태의 테스트는 backend/tests/test_lodgings_api.py에만 존재한다.
