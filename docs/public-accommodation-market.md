# Phase 6: 부산 공식 숙박업 지역 시장

상태: 저장/동기화 계약·집계 API·보호 UI 및 공식 REST API 수집 구현.
[공식 출처 및 매핑](public-accommodation-source.md)을 참조한다. 실제 수집 성공 후에만 숫자를 제공한다.

범위는 숙소에 연결한 부산 구·군의 숙박업 인허가 현황이다.
경쟁업체 매출·ADR·점유율, OTA 수집, 관광 방문자, 행사, 지도, 벤치마크, 예측은 없다.
Phase 5 dashboard-v1 계산과 인증 구조는 변경하지 않았다.

## 구조와 권한

`providers/accommodation.py`는 Pydantic 내부 DTO와 작은 Protocol을 정의한다.
`services/public_sync.py`가 수집 → 검증 → 저장/통계를 조정하며 repositories/market.py가 DB 접근을 맡는다.
HTTP 요청에서 provider를 호출하지 않는다. API는 DB의 마지막 성공 자료만 조회한다.
OfficialAccommodationProvider.fetch는 lodgings_api의 검증된 /info 요청을 실행한다.
가짜 URL, 요청 파라미터, 응답 헤더, 라이브 데이터를 대체하는 fixture 로더는 없다.

공공 테이블은 공유 자료여서 tenant RLS를 흉내 내지 않는다. PUBLIC 권한을 제거하고
stay_insight_runtime에 SELECT만, stay_insight_ingestion에 공공 데이터/수집 이력 INSERT·UPDATE만 준다.
동기화 서비스는 각 트랜잭션에서 SET LOCAL ROLE stay_insight_ingestion으로 권한을 제한한다.
이 역할은 소유자 예약/매출/비용에 접근할 수 없다. 로그인 자격은 별도 운영 설정이다.
브라우저용 DB 정책이나 공개 DB 접근을 추가하지 않았다.

시장 API는 기존 인증/조직 멤버십 의존성과 조직 조건으로 숙소를 먼저 조회한다.
다른 조직의 숙소는 404, 잘못된 조직 멤버십은 403, 인증 없음은 401이다.
기존 app.properties의 강제 RLS는 유지된다. API 응답은 private, no-store다.

## 스키마와 지역 연결

추가 마이그레이션: 0004_public_accommodation. 0001~0003은 수정하지 않는다.

- app.regions: 부산 16개 구·군, 내부 UUID, 시도/시군구 이름, SIGUNGU, 시각. 명칭은 참조 데이터이며 업소 수치 fixture가 아니다.
- app.public_accommodation_licenses: source+source_record_id UNIQUE, 사업장명, 원본/정규화 업태·상태, region_id, 선택 날짜, 수집/수정 시각.
- app.public_data_sync_runs: 수집 시작/종료/성공/실패, 조회/삽입/수정/동일/실패 수, 확인된 구·군 범위, 자료 기준일/폐업일 지원 여부, 안전한 오류 코드.
- app.properties: nullable region_id, region_address, region_road_address 추가. 기존 값은 유지한다.

Phase 7부터 사용자 등록·수정 화면에서 지역을 직접 선택한다.
[지역 연결 계약](property-region.md)이 기존 관리자 전용·주소 변경 무효화 정책을 대체한다.
주소나 좌표를 덮어쓰지 않는다. 지역이 없으면 부산 전체 숫자로 대체하지 않는다.
공식 지역 코드와 좌표는 검증되지 않았으므로 저장하지 않는다. 동/반경/PostGIS 위치 인덱스도 없다.
인덱스는 출처/식별자 유일성, 지역/출처 조회, 최근 출처별 수집 조회에 맞춘다.

## 동기화 계약

동시 실행은 출처별 트랜잭션 advisory lock으로 직렬화한다. 실행 이력을 먼저 남긴다.
정상 전체 배치는 하나의 트랜잭션에서 반영한다. 조회 중 네트워크 예외/불완전 페이지/잘못된 행/중복 ID/
알 수 없는 지역이면 배치 전체 실패, 기존 자료 보존, 별도 트랜잭션에 FAILED를 기록한다.
이 계약에서는 한 행 오류도 부분 결과를 완전한 통계로 발행하지 않는다.
프로세스 강제 종료 시 RUNNING이 남을 수 있으며 마지막 COMPLETED 자료를 계속 사용한다.
DB 자체 장애로 실패 이력 쓰기가 불가능하면 명령은 오류 종료한다. 기록됐다고 주장하지 않는다.

첫 기록은 INSERT, 동일 기록은 UNCHANGED, 내용 변경은 UPDATE. 같은 데이터 재수집에도 마지막 관찰 시각은 갱신한다.
새 응답에서 사라진 기록을 삭제/폐업 처리하지 않는다. 명시적으로 검증된 CLOSED만 폐업으로 사용한다.
과거 source_reference_date 배치로 최신 자료를 덮어쓰지 않는다.
지역별 전체 범위가 명시된 COMPLETED 이력만 미수집과 실제 0건을 구별할 근거가 된다.
다른 구·군만 갱신돼도 해당 지역의 마지막 성공 이력을 잃지 않는다.

라이브 제공자는 서버 전용 키, timeout, 제한된 재시도와 전체 페이지 검증을 사용한다.
Redis/worker/scheduler는 없다. 수집은 명시적인 관리자 명령으로 실행한다.

## 지표 계약 license-market-v1

reference_date 기본값은 Asia/Seoul 오늘. 1901-01-01 이전과 미래 날짜는 422.
최근 12개월 구간은 `(전년도 같은 날짜, 기준일]`이다. 2월 29일의 전년도 시작 기준은 2월 28일로 보정한다.
예: 2026-09-28의 표시 범위는 2025-09-29~2026-09-28.

- open_businesses: 해당 출처/지역의 현재 저장 상태 OPEN만 집계. UNKNOWN/SUSPENDED 제외.
- new_licenses_12m: 기간 내 인허가일 건수. 해당 지역에 인허가일 결측이 있으면 null.
- closures_12m: CLOSED이며 기간 내 폐업일. 제공자의 폐업일 지원이 확인되지 않았거나 폐업일 결측이 있으면 null.
- type_breakdown: OPEN 기록만의 정규화 유형별 건수. 합은 open_businesses와 일치.

영업 상태는 최신 저장 상태이지 reference_date의 과거 상태 복원값이 아니다.
지역은 SIGUNGU와 '부산광역시 구·군명'을 표시한다. 등록 행 수이며 객실 수/전체 숙박 공급량과 같다고 주장하지 않는다.
누락 기록 보존에 따른 오래된 상태 잔존 가능성을 경고한다. 세부 영업상태·유형 원본 매핑은 출처 문서에 정의한다.
신선도는 수집시각과 자료 기준일을 구분하고, 최근 실패 시 마지막 성공 자료임을 표시한다.

## 실행과 수동 확인

현재 루트 .env의 NEXT_PUBLIC_SITE_URL=http://localhost:3000 및 API_PORT=18000을 유지한다.
루트 .env에 PUBLIC_ACCOMMODATION_API_KEY를 추가한다. Compose는 backend에만 전달한다. MARKET_DATABASE_URL은 수집 명령에만 전달하는 비공개 DB 연결값이다.
Compose의 API 환경에 관리자 자격을 상시 넣지 않는다. 기존 .env를 예제로 덮어쓰지 않는다.

```powershell
cd "C:\Users\HDRBRND\Desktop\Web Workspace\accommodation"
docker compose up -d --build
docker compose exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic upgrade head
```

로컬 개발 DB에 한정한 명령 예(운영은 ingestion 전용 로그인 사용):

```powershell
docker compose exec -T -e MARKET_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run python -m app.jobs.sync_accommodation_licenses
```

성공: 종료 코드 0, status=COMPLETED. 키 미설정: API_KEY_REQUIRED.
오류/불완전 페이지는 종료 코드 1이며 이전 성공 자료를 보존한다.
키는 출력하거나 Git에 추가하지 않는다. 키를 수정한 경우 docker compose up -d --no-deps backend로 환경을 다시 적용한다.

수집 상태/행 수 조회:

```powershell
docker compose exec -T db psql -U postgres -d stay_insight -c "SELECT status,started_at,completed_at,fetched_count,inserted_count,updated_count,unchanged_count,failed_count,error_summary FROM app.public_data_sync_runs ORDER BY started_at DESC LIMIT 5;"
docker compose exec -T db psql -U postgres -d stay_insight -c "SELECT source,count(*) FROM app.public_accommodation_licenses GROUP BY source;"
```

아래는 선택적인 관리자 유지보수 명령이다. 일반 사용자는 숙소 정보 수정에서 구·군을 선택한다.
관리자 명령은 실제 주소를 확인한 관리자가 UUID와 정확한 현재 주소를 넣어 실행한다.
다음 꺾쇠 값은 사용자가 확인해 바꿔야 하는 입력이며 그대로 실행할 값이 아니다.
명령은 organization/property를 함께 조건으로 삼고 주소가 다르면 실패한다.

```powershell
docker compose exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run python -m app.jobs.assign_property_region --organization-id "<조직 UUID>" --property-id "<숙소 UUID>" --district "<확인한 부산 구군명>" --confirmed-address "<현재 등록된 정확한 주소>"
```

1. http://localhost:3000 로그인 → 내 숙소 → 기존 숙소 → 지역 시장.
2. 지역 미지정 숙소: '지역 시장 정보를 보려면 숙소의 부산 구·군을 설정해 주세요.' 숫자는 표시하지 않는다.
3. 관리자 확인으로 연결한 숙소: 구·군명, 미수집 안내, 공식 출처 링크, 수집 이력 없음. 아직 0개 카드가 나오면 오류다.
4. 공식 출처 링크가 data.go.kr의 지정 카탈로그인지 확인한다.
5. 실제 수집 완료 후에는 해당 구·군의 숫자와 최근 수집 시각을 표시한다.
6. 무자료/오래된 데이터/실제 0건은 격리 테스트에서 검증한다. 테스트를 위해 운영 자료의 날짜를 수정하거나 fixture를 주입하지 않는다.
7. stale는 마지막 성공 수집/자료 기준이 7일 초과인 경우 '데이터 갱신이 필요합니다.'
8. 별도 실제 자료가 없는 현재에는 아래 테스트가 미수집·지역 없음·stale·폐업일 미확인 UI를 검증하는 재현 방법이다.

```powershell
docker compose exec -T -e TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/postgres backend uv run pytest tests/test_market.py -q
docker compose run --rm --no-deps frontend pnpm test
```

개발 frontend는 이미지 소스이므로 변경 후 재빌드한다. Webpack, polling=false 및 프론트 소스 mount 없음 유지.
[개발 경로 회귀 검사](dev-route-verification.md)에 market을 포함한다. 실제 로그인 200을 확인해야 한다.
프로덕션 빌드는 별도 컨테이너에서 실행한다. 기존 볼륨은 삭제하지 않는다.

## 남은 한계

전체 자료 기준일은 응답에 없어 null이다. 원본은 일 단위 갱신되며 실시간 자료가 아니다.
숙소 지역 지정은 관리자 확인 명령을 유지한다. 사용자 위치/GPS/지도, 자동 스케줄러는 추가하지 않았다.
수집 중 원본 변경에 대한 snapshot token은 없으므로 엄격한 동일시점 snapshot을 보장하지 않는다.
최신 API 연결 검증은 [API 연동 검증](public-api-verification.md)을 참조한다.

## Phase 8 remote execution preparation

[Staging operations](staging-operations.md) selects one Render Cron Job invoking the existing python module daily at 00:00 UTC (09:00 KST). It uses MARKET_DATABASE_URL with a separate restricted collector login and backend-only provider key. No scheduler was deployed or successful remote run claimed. The local automation remains unchanged pending remote verification; never aim both at the same staging DB. license-market-v1, locking, atomic publication and source/freshness semantics are unchanged.
