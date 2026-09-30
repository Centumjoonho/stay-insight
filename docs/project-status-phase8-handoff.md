# Stay Insight current status — Phase 8 handoff

감사일: 2026-09-30, Asia/Seoul. 대상: `C:/Users/HDRBRND/Desktop/Web Workspace/accommodation`.

이 문서는 **현재 작업 트리 + 실행 중 Docker + 실제 로컬 개발 DB**를 조사한 결과다. Phase 8 구현 문서가 아니다. Phase 1–7 기능은 로컬 구현 상태이며, 운영 출시 완료를 뜻하지 않는다. 제품 코드/환경설정/업무 데이터는 변경하지 않았고, 이 파일만 추가했다. 테스트는 별도 임시 DB를 사용했다. 커밋·푸시·마이그레이션 적용·공공 API 재수집·컨테이너 재빌드는 하지 않았다.

## 1. Product purpose

부산 숙박업 소유자가 예약 CSV, 직접 입력 비용, 운영 성과를 관리하고 별도 출처의 공식 지역 정보를 확인하는 한국어 SaaS다. FastAPI가 업무 데이터와 지표의 유일한 권위다. 브라우저와 Next.js는 업무 테이블에 직접 접근하지 않는다.

현재 이용 가능한 핵심 흐름은 로그인 → 조직 온보딩 → 숙소 등록/부산 구·군 선택 → CSV 예약 등록 → 비용 입력 → 운영 대시보드 → 구·군 숙박업 인허가 현황이다. 지역 시장은 경쟁 숙소 가격/매출/점유율이나 수요 예측 서비스가 아니다.

## 2. Current repository and Git state

- 브랜치: `main`, upstream: `origin/main`.
- HEAD: `82a2147e6c6a1b7d423c0dfbcaf744aab6264f6a` (`feat: connect Busan public accommodation market API`).
- 로컬 tracking 기준 ahead/behind: `0 / 0`. 별도 읽기 전용 `git ls-remote origin refs/heads/main`도 같은 SHA를 확인했다. 첫 sandbox 네트워크 시도는 실패했고 승인된 읽기 전용 재시도는 성공했다. fetch/push는 하지 않았다.
- `git log --oneline -10` 결과 이 checkout의 이력은 7개였다: `82a2147`, `f440ae9`, `cb2c208`, `297b56e`, `2ab2f8f`, `e95023c`, `27e526b`.
- Phase 6 공식 API 연결까지 HEAD에 포함. **Phase 7은 전부 미커밋**이며 적용된 로컬 DB revision이 HEAD의 migration 파일보다 앞서 있다. 원격 checkout만으로 현재 상태를 재현할 수 없다.
- 감사 시작 시 수정된 tracked 파일 25개, untracked 파일 21개, staged 변경 없음. 이 보고서 추가 후 untracked 22개.
- Phase 7 이전 사용자 작업은 AGENTS.md의 Next session 문단과 `docs/next-steps.md`다. Phase 7 보고서의 시작 상태와 현재 diff를 대조했다. 출처/작성자를 Git만으로 완전히 증명할 수는 없다.

### 미커밋 변경의 분류

| 묶음 | 파일/내용 | 상태 |
| --- | --- | --- |
| 기존 작업 | AGENTS.md의 Next session, docs/next-steps.md | 기존 메모 보존; Phase 7으로 해결된 역사적 우선순위 |
| Phase 7 backend | foundation API/model/schema/service, main, market repository/schema, 관리자 지역 지정 job | tracked 수정 |
| Phase 7 신규 backend | 0005 migration, regions API/repository/schema/service, test_property_regions.py | untracked |
| 기존 회귀 테스트 | test_imports.py/test_expenses.py의 과거 revision 검증 방식, test_market.py의 지역 계약 | tracked 수정; 과거 schema 상태에서 최신 API를 부르는 대신 과거 컬럼 확인 후 head 복원 |
| Phase 7 frontend | property detail, property-form, market-view, API client/types/market-types, market.test | tracked 수정 |
| Phase 7 신규 frontend | properties/[id]/edit/page.tsx, region-types.ts, property-regions.test.ts | untracked |
| Phase 7 문서 | README, AGENTS, api/architecture/database/product/public-accommodation-market | tracked 수정 |
| Phase 7 신규 문서 | property-region.md, phase7-verification.md | untracked |
| 개발 데이터 | tests/fixtures/__init__.py, development_dashboard.py, dashboard-demo의 README/CSV 4개/JSON 1개, test_development_dashboard.py | untracked 9개; 아래 11절 참조 |
| 이번 감사 | project-status-phase8-handoff.md | 새 문서 하나만 추가 |

다음 커밋은 **Phase 7 기능·권한 migration·회귀 테스트·관련 문서**를 하나의 경계로 권고한다. 예: `feat: add self-service Busan property regions`. 이후 개발 fixture 9개를 `test: add local dashboard development fixtures`로 분리하고, 기존 메모와 이 보고서는 명시적으로 검토해 별도 문서 커밋으로 정리한다. AGENTS.md에는 기존 메모와 Phase 7 변경이 섞여 있으므로 hunk 단위 확인이 필요하다. 무차별 `git add .`는 권고하지 않는다. 이번 감사에서는 실행하지 않았다.

## 3. Current technology stack

| 영역 | 확인한 현재 구현 | 계획과의 차이 |
| --- | --- | --- |
| Web | Next.js 16.3.5 App Router, React 19.3.0, TypeScript 5.9.3, Tailwind 4.3.3, Recharts 3.10.1 | shadcn/ui와 Kakao Maps 구현 없음 |
| Auth SDK | @supabase/ssr 0.12.7, @supabase/supabase-js 2.116.0 | hosted Supabase는 Auth만 사용 |
| API | Python 3.12 Docker, FastAPI 0.141.1, SQLAlchemy 2.0.54, Alembic 1.20.0, Pydantic 2.13.5 | 단일 모듈형 API |
| Runtime dependencies | psycopg 3.3.6, Uvicorn 0.53.0, PyJWT 2.14.0 | 실행 중 설치 버전 조회 |
| DB | 로컬 `postgis/postgis:17-3.5`, PostgreSQL app schema | Supabase 업무 DB 전환 미구현; 공간 분석 미구현 |
| Tooling | pnpm 11.19.0, uv 0.12.17, ESLint/Ruff, tsc/mypy, Node tests/pytest | lockfile 유지 |
| Storage/deploy | 개발 Docker Compose | Supabase Storage, Vercel/Render 운영 배포는 목표; 현재 코드/설정으로 완료 증거 없음 |

`frontend/`, `backend/`, `docs/` 모노레포다. `apps/web` 등 예전 구조 제안으로 변경하지 않는다. backend는 api → services → repositories → models, frontend는 중앙 lib/api transport를 이용한다.

## 4. Implemented Phase 1-7

| Phase | IMPLEMENTED — 실제 코드 근거 | PLANNED / DOCUMENTED ONLY 또는 한계 |
| --- | --- | --- |
| 1 | Compose 3서비스, health, App Router/FastAPI scaffolding, pnpm/uv와 검증 명령 | 운영 Dockerfile/CI/CD/배포 검증 없음; API health는 DB readiness가 아님 |
| 2 | signup/password login/signout, PKCE callback, proxy/SSR claims, 조직+OWNER 원자 온보딩, 숙소 create/list/detail/PATCH, tenant 검증/RLS | 비밀번호 복구 UI/API 호출 없음. 초대/멤버관리/조직 선택 UI 없음. UI는 첫 membership 사용 |
| 3 | GenericCsvAdapter, 미리보기/매핑/검증/확인/동기 import, 원자 upsert, checksum 중복 차단, 예약 목록/필터/가져오기 이력 | OTA별 전용 CSV adapter, 실시간 동기화, 원본 Storage 보관, 예약 변경값 전체 이력 없음 |
| 4 | 비용 create/read/update/delete, 항목·기간·FIXED/VARIABLE, 합계, 예약 fee 별도 읽기 | 삭제는 물리 삭제. void/복원/전체 수정 감사 이력 없음 |
| 5 | dashboard-v1, 8개 카드, 월별 매출/비용/이익·점유율 차트, 전월/전년 비교, 채널별 성과, 결측 경고 | 실제 투숙/일별 객실 재고/차단일/회계 순이익 아님 |
| 6 | MOIS REST provider, 전 페이지 검증/부산 정규화, 원자 sync, 성공/실패 이력, 구·군 집계, source/freshness | 관광 방문자/행사/지도/반경/벤치마크 없음 |
| 7 | 인증 regions API, 등록·수정 지역 선택/해제, 상세 표시/시장 연결, 좁은 UPDATE grant migration | 선택 지역은 주소 검증 결과가 아님. 레거시 주소 snapshot 유지하지만 연결 판단에 사용 안 함 |

근거: [Auth](authentication.md), [imports](imports.md), [expenses](expenses.md), [dashboard](dashboard.md), [metrics](metrics.md), [public market](public-accommodation-market.md), [property regions](property-region.md). 이들의 과거 개요 문장보다 현재 코드와 후속 명시 계약을 우선한다.

## 5. Current database and migrations

실제 `alembic history`와 파일을 대조했으며, 로컬 privileged 명령으로 `alembic current`를 조회했다. **현재 단일 head는 `0005_property_region_write`**다. API 역할 권한을 바꾸지 않았다.

| 순서 | 파일 | revision | 변경 |
| --- | --- | --- | --- |
| 1 | 0001_tenant_property_foundation.py | 0001_foundation | organizations, organization_members, properties, runtime role, grants, forced RLS |
| 2 | 0002_csv_imports.py | 0002_csv_imports | reservation_imports, reservations, composite FK, RLS/upsert 권한 |
| 3 | 0003_expenses.py | 0003_expenses | expenses, RLS, 제한된 수정/삭제 권한 |
| 4 | 0004_public_accommodation.py | 0004_public_accommodation | regions, public_accommodation_licenses, public_data_sync_runs, ingestion role, property 지역 연결 컬럼 |
| 5 | 0005_property_region_write.py | 0005_property_region_write | runtime에 properties.region_id UPDATE만 추가; 새 테이블/컬럼 없음 |

실제 app 테이블은 아래 9개 전부다. 제안된 reservation_nights, inventory history, market.events/visitor_observations, benchmark release 테이블은 없다.

| 테이블 | 로컬 행 수 | 역할 |
| --- | ---: | --- |
| organizations | 2 | 조직 |
| organization_members | 2 | 외부 Auth user UUID의 OWNER/MEMBER 연결 |
| properties | 3 | 숙소와 현재 inventory_units |
| reservation_imports | 5 | 원본 파일 자체가 아닌 가져오기 메타데이터 |
| reservations | 317 | 정규화 예약 |
| expenses | 81 | MANUAL 비용 |
| regions | 16 | 부산 구·군 참조 |
| public_accommodation_licenses | 4,714 | 공식 인허가 자료 |
| public_data_sync_runs | 4 | 수집 상태 이력 |

`properties.region_id`는 nullable FK → `app.regions.id`. 실제 FK 확인 완료. 내부 UUID는 공식 행정코드가 아니다. `region_address`, `region_road_address`는 레거시 컬럼으로 남는다. latitude/longitude 필드는 있어도 공공 업소 좌표 수집·PostGIS geometry 조회는 구현되지 않았다.

업무 테이블 6개는 ENABLE/FORCE RLS 모두 true. 공공 참조 3개는 RLS false이며 공유 정보라는 설계에 따라 PUBLIC 권한을 회수하고 runtime SELECT/ingestion 쓰기를 분리한다. 이 차이를 tenant isolation 누락과 혼동하지 않는다.

## 6. Authentication and tenant security

실제 검사한 코드: `core/auth/jwt.py`, `api/dependencies/tenant.py`, `db/context.py`, foundation/market/regions/imports/expenses/dashboard service/repository와 migrations/tests.

- JWT는 RS256/ES256 + kid를 요구하고 프로젝트 JWKS로 서명을 검증한다. issuer/audience/exp/iat/sub/role를 요구하며 UUID subject, authenticated role, 비익명 여부를 검사한다. HS256/unsigned/잘못된 서명·claims는 거부한다.
- JWKS 캐시 300초, 연결 timeout 5초. 검증 실패 401, provider 연결 실패/설정 부재 503. metadata로 권한을 부여하지 않는다.
- X-Organization-Id는 선택자다. 현재 user+org membership 조회 후에만 transaction-local app.organization_id를 설정한다. user context도 SET LOCAL 방식이며 pool 재사용 격리 테스트가 있다.
- membership에는 별도 active/status 컬럼이 없다. 현재 행의 존재가 권한이며 삭제 후 요청은 403이다. 초대/탈퇴 UI 구현과 혼동하지 않는다.
- 교차 조직 숙소/예약/비용/시장 접근은 scoped query+RLS로 거부한다. 허용된 org 안의 외부 객체는 404, 위조 org/탈퇴 membership은 403이다.
- 지역 참조 GET만 조직 헤더 없이 검증된 JWT로 접근 가능하다. 숙소 지역 PATCH는 기존 membership과 RLS를 모두 요구한다.
- 실제 API 실행 DB user는 stay_insight_app, NOSUPERUSER/NOBYPASSRLS이며 stay_insight_runtime 권한을 상속한다. API는 superuser/BYPASSRLS/app 테이블 owner 연결을 503으로 거부한다.
- 실제 권한 조회: UPDATE(region_id)=true, UPDATE(organization_id)=false, UPDATE(region_address)=false, public licenses INSERT=false.
- migrations는 일회성 관리자 연결로 수행. sync는 별도 MARKET_DATABASE_URL 연결 안에서 SET LOCAL ROLE stay_insight_ingestion. 이 역할은 NOLOGIN/NOSUPERUSER/NOBYPASSRLS이며 tenant 업무 테이블 접근을 허용하지 않는다. 로컬 관리자 연결을 운영 API 설정으로 쓰지 않는다.
- frontend getClaims/proxy는 보조 경계이고 FastAPI가 독립 검증한다. 업무 요청은 no-store. provider key는 backend 전용이다.

### 남은 보안 가정

서명된 access token은 로그아웃/계정 삭제만으로 즉시 무효가 되지 않는다. 매 요청 Supabase session_id 원격 검증은 없고 membership 철회와 token 만료에 의존한다. RLS의 app context는 신뢰된 API가 설정한다는 전제이며 DB 자격 탈취/임의 SQL 실행까지 방어하는 사용자별 DB 인증은 아니다. hosted Supabase dashboard의 현재 key/redirect/정책 설정 전체, 운영 secret manager, rate limiting, penetration test, dependency vulnerability audit는 이번에 검증하지 않았다. 테스트 성공을 운영 보안 인증으로 표현하지 않는다.

## 7. Reservation / expense / dashboard contract

### CSV / 비용

CSV는 5 MiB, 10,000행, 64열 등 제한과 UTF-8/BOM/엄격 CP949 fallback을 적용한다. 필수 stable ID/checkin/checkout/gross를 명시적으로 매핑한다. guest count는 room count가 아니다. Decimal/NUMERIC(18,0), 정수 KRW, 날짜 검증, fee 결측 null을 유지한다. 원본은 요청 한정으로 처리하며 Storage에 저장하지 않는다.

checksum+property/channel과 lock으로 동일 성공 파일 재수입을 no-op 처리한다. 다른 파일의 동일 property/channel/external ID는 해당 행 전체 값을 갱신하며 빠진 optional 값도 null/UNKNOWN으로 바뀐다. 파일에서 빠진 예약을 삭제하지 않는다. commit 때 다시 검증하고 reservation 변경은 savepoint로 전부 롤백한다. 이력은 메타데이터이며 모든 과거 값 복원 기능은 아니다.

비용은 MANUAL, FIXED/VARIABLE, 항목/날짜/금액을 입력하고 tenant-scoped CRUD를 수행한다. 수수료는 예약의 channel_fee만 사용하며 비용 행으로 복제하지 않는다. Phase 4 비용 요약은 **취소 포함 모든 예약 상태**의 체크인일 기준이다. Phase 5와 비교할 때 상태와 날짜 범위를 맞춰야 한다.

### 현재 권위: dashboard-v1

S=선택 월 첫날, E=유효 종료일(포함). 과거 월은 말일, 현재 월은 서울 오늘, 미래 월은 거부한다.

| 지표 | 실제 정의 |
| --- | --- |
| 포함 상태 | CONFIRMED + UNKNOWN; CANCELLED 제외. UNKNOWN은 경고하며 실제 투숙으로 바꾸지 않음 |
| 인식 매출 | S ≤ check_in ≤ E인 예약 gross 합계; 수수료 차감 전 |
| 예약건수/평균 숙박일수 | 같은 체크인 집단의 count / booked_nights 합계를 count로 나눔 |
| 예약 객실박(추정) | 겹친 예약별 min(check_out,E+1)-max(check_in,S) 합계; 예약 1건=객실 1개; checkout 제외 |
| 가능 객실박 | 현재 inventory_units × S~E 달력 일수 |
| 점유율(추정) | 객실박/가능 객실박×100. 100% 초과를 숨기거나 강제 제한하지 않고 경고 |
| 배분 매출 | 겹친 예약 gross×기간 겹친 박수/booked_nights. 분석 계산만 수행 |
| ADR(추정) | 배분 매출/예약 객실박 |
| RevPAR(추정) | 배분 매출/가능 객실박 |
| 직접 비용 | 기간 내 expense_date의 비용 합계; 고정/변동·항목별 집계 |
| 확인된 수수료 | 체크인 집단의 non-null channel_fee 합계. 결측 건수 별도 |
| 확인된 총비용 | 직접 비용+확인된 수수료, 한 번만 반영 |
| 확인된 영업이익 | 인식 매출-확인된 총비용. 음수 허용; 회계 순이익 아님 |
| 채널 지표 | 같은 체크인 집단을 channel로 그룹화. 매출 비중은 총 인식 매출 기준 |
| 비교 | 전월/전년 동월. 부분 월은 같은 경과 일수(해당 월 말일로 cap); 과거 전체 월은 전체 월 |
| 변화량 | 양수 baseline만 증감률. 0/음수는 절대 차이+비율 null. 점유율/이익률은 %p |
| 추이 | 기본 12개월, API 1~24개월. 현재 월만 오늘까지; 기록 없는 기간은 chart gap |

재무 총액은 정확한 Decimal, 배분은 PostgreSQL numeric, 비율은 HALF_UP 두 자리다. 프론트는 표시 형식만 담당한다. revenue 카드와 ADR 분자의 날짜 배분 기준이 다르다. 예: 8/31~9/3 30만원은 9월 객실박 2박/배분 매출 20만원에 기여하지만 9월 체크인 매출에는 없다.

현재 재고의 과거 소급 적용, 차단/정비일 미반영, 실제 투숙 확인 없음, 세금/환불/수입 완전성 미확인, 비용 누락 가능성이 남는다. 미래 service-night/dated inventory 계약을 현재 공식으로 바꾸지 않는다. 결측/기록 없음과 실제 영업 0을 구별한다.

## 8. Official public-market integration

**LIVE OFFICIAL DATA**: MOIS_LODGINGS, 행정안전부_문화_숙박업 조회서비스. [공식 출처](https://www.data.go.kr/data/15155124/openapi.do), 고정 HTTPS endpoint `https://apis.data.go.kr/1741000/lodgings/info`. 이번에는 외부 API를 다시 호출하지 않았으며 구현·기존 성공 이력·저장된 출처를 대조했다.

전국 전체 페이지를 크기 100으로 조회/검증한 뒤 부산 16개 구·군만 저장한다. 범위: 중구, 서구, 동구, 영도구, 부산진구, 동래구, 남구, 북구, 해운대구, 사하구, 금정구, 강서구, 연제구, 수영구, 사상구, 기장군. 주소 문자열은 공식 원본을 정규화하는 데 사용하며 사용자의 현재 위치/GPS를 수집하지 않는다.

실제 최신 성공:

- COMPLETED, 수집/완료 `2026-09-30T02:18:53.765182Z` = **2026-09-30 11:18:53 KST**.
- 4,714건, inserted 0 / updated 0 / unchanged 4,714 / failed 0.
- 저장된 전체 4,714행의 source는 MOIS_LODGINGS. 최신 run의 확인 지역 16개, closure_dates_supported=true, source_reference_date=null.
- 감사 시 수집시각 기준 7일 이내. stale 조건은 성공 수집시각이 7일 초과 또는 제공된 기준일이 7일 초과. 자료 기준일이 없다는 사실은 별도로 표시한다.
- 기존 source 문서는 원본 일 단위 갱신/2일 지연을 기록하지만 오늘-2일을 기준일로 만들어 저장하지 않는다. 실시간 영업 현황이 아니다.

provider는 코드/명칭 조합으로 상태를 판정하고 미확인 상태를 폐업으로 만들지 않는다. 일반호텔/숙박업(일반)→GENERAL, 숙박업(생활)→LIFESTYLE, 나머지 OTHER. TOURIST_HOTEL enum/표시명이 있다고 관광호텔 분류가 현재 live mapping에 구현된 것은 아니다. accommodation.py의 보수적 normalize helpers와 실제 lodgings_api.busan_record 매핑을 혼동하지 않는다.

완전 페이지 수/중복/총수 변화/첫 페이지 재검증, 제한된 재시도·timeout·응답크기 제한, 동기화 lock과 원자 반영이 있다. 실패하면 마지막 성공 자료를 유지한다. 누락된 기록을 자동 삭제/폐업으로 만들지 않아 오래된 상태가 남을 수 있다. offset pagination에 snapshot token이 없어 완벽한 동일시점 snapshot은 보장하지 못한다. 프로세스 강제 종료의 RUNNING 복구도 운영 고려사항이다.

license-market-v1은 현재 저장 OPEN 수, 최근 12개월 인허가/명시적 폐업, OPEN 업종 구성이다. reference_date는 신규/폐업 기간만 정하며 과거 영업 상태를 복원하지 않는다. 필요한 날짜가 누락되면 해당 지표 null. 현재 해운대구 화면은 영업 중 392개/신규 46개/폐업 데이터 없음(폐업일 누락 2개), 일반86/생활175/기타131로 확인했다. 이는 공식 등록 건수이며 더미 숙소의 예약/매출과 섞이지 않는다.

### 갱신 운영

로컬 개발 전용 수동 명령:

```powershell
docker compose exec -T -e MARKET_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run python -m app.jobs.sync_accommodation_licenses
```

API key는 기존 backend 환경변수 PUBLIC_ACCOMMODATION_API_KEY를 사용한다. 위 자격은 로컬 개발 기본값일 뿐 운영에 쓰지 않는다. 성공 기준은 종료 코드 0과 COMPLETED다.

현재 **저장소 외 Codex 로컬 heartbeat 자동화** `stay-insight`가 ACTIVE, 매일 오전 9시(Asia/Seoul)로 설정되어 있다. 저장된 설정과 앱의 automation view를 확인했다. 기존 sync 명령만 실행하며 backend/db가 꺼져 있으면 실패/사용자 조치만 알리도록 되어 있다. PC·Codex·Docker·서비스·네트워크가 필요하며 종료 중 정시 실행/누락분 보충은 보장하지 않는다. DB의 11:18 수집을 오전 9시 자동 작업의 실행 증거로 단정할 수 없다. 이번에는 다음 자동 실행을 기다리거나 트리거하지 않았다. Compose 안에 cron/worker/scheduler 서비스는 없다. 서버 예약 작업은 미구현이다.

## 9. Property region self-service

실제 흐름: 정상 Auth 사용자 → 조직 온보딩(없을 때) → 숙소 등록 → API의 부산 구·군 선택 → POST 저장 → 상세 region 표시 → market에서 해당 region_id의 공식 집계. 기존 숙소는 edit → PATCH → router.replace/refresh → 시장 범위 변경이다. 관리자 명령은 정상 제품 사용에 필요 없다.

GET /api/v1/regions?sido=부산광역시&level=SIGUNGU는 JWT 필수이고 지역은 DB에서 읽는다. POST 생략/null=미설정, PATCH 생략=보존/null=해제. 서비스가 존재/시도/level/지원 구·군을 검증한다. 로딩 중 저장 금지, 실패 재시도, 기존 지역 선택 유지와 빈 목록 상태가 있다.

지역은 분석 범위이며 실제 주소와 독립이다. 주소 편집이 지역을 바꾸지 않는다. 명시 선택은 EXPLICIT_SELECTION으로 표시하며 관리자 위치 검증/행위자 이력을 뜻하지 않는다. 지역 미설정은 숫자를 숨기고 설정 CTA를 제공한다. 아직 수집되지 않은 범위는 NOT_SYNCHRONIZED다.

이번 감사는 DB 불변 원칙으로 새 사용자 생성/숙소 저장/지역 변경을 브라우저에서 반복하지 않았다. 대신 기존 정상 로그인으로 등록·수정 화면/16옵션/현재 해운대 선택/시장 범위를 확인했고, 전체 실제 PostgreSQL 테스트가 create→market→edit→다른 범위→clear, 교차 tenant, 잘못된 지역, membership 철회를 검증했다. [이전 Phase 7 브라우저 보고서](phase7-verification.md)의 수영구→해운대→해제 여정은 과거 증거이며 이번 실행으로 표현하지 않는다.

남은 관리 작업은 DB 초기 migration/역할 provisioning, 공공 key 설정/수집 운영, 필요시 유지보수용 assign_property_region 명령이다. 사용자는 이를 직접 실행하지 않아도 이미 수집된 자료를 볼 수 있다.

## 10. Docker/local execution

| 경계 | 실제 주소/설정 |
| --- | --- |
| 공개 프론트 | http://localhost:3000 |
| host API | http://localhost:18000 |
| Swagger | http://localhost:18000/docs |
| container 내부 API | http://backend:8000 |
| DB | db:5432, 호스트 127.0.0.1:5432 |
| dev | next dev --webpack --hostname 0.0.0.0 |
| production build | next build (이번 출력: Turbopack), 변경 없음 |
| Watchpack | WATCHPACK_POLLING=false |
| frontend source | Docker image COPY; Windows 소스 bind mount 없음 |

0.0.0.0은 bind 주소만 사용한다. NEXT_PUBLIC_SITE_URL=http://localhost:3000이 signup/callback/proxy 공개 redirect 원점이며, 잘못된 bind 주소/credentials/path/query를 거부한다. API_PORT=18000으로 공개 API와 Compose port를 함께 정한다.

현재 일반 시작:

```powershell
cd "C:\Users\HDRBRND\Desktop\Web Workspace\accommodation"
docker compose up -d
docker compose ps
```

프론트 소스가 바뀌었으면:

```powershell
docker compose up -d --build frontend
```

기존 이미지 restart만으로 host 소스는 반영되지 않는다. 표준 Compose가 없는 현재 도구 환경에서는 모든 `docker compose`를 `.\.tools\docker-compose.exe`로 바꾸면 된다. `.tools`는 Git ignored이며 다른 PC에 존재한다고 가정하지 않는다.

권한을 보존하는 로컬 Alembic 조회:

```powershell
docker compose exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic current
```

새 migration 적용은 같은 일회성 로컬 관리자 연결로 `alembic upgrade head`; 이번 감사에서는 적용하지 않았다. API runtime URL을 관리자 값으로 바꾸지 않는다.

production build는 아래처럼 독립 컨테이너에서 실행한다. 실행 중 개발 .next를 공유하지 않는다.

```powershell
docker compose run --rm --no-deps frontend pnpm build
```

현재 db/backend/frontend 모두 running/healthy, 포트 loopback bind, DB named volume 유지. 기존 404 대책은 Webpack 전환뿐 아니라 **Windows frontend bind mount 제거 + polling=false + image source**다. [회귀 기록](dev-route-verification.md)은 검증된 구성 우회책이며 특정 upstream race나 Turbopack만의 원인으로 확정하지 않는다. 이번 감사에서 restart/recreate를 반복하지 않았다.

## 11. Current development data

별도 숙소 `[개발용 더미] 해운대 6객실 샘플`이 로컬 업무 DB에 존재한다. 가상 주소/숙소명/예약 DEMO ID/비용 메모로 표시하며 실제 소유자 운영 실적이 아니다. 2025-09~2026-09, 예약315/비용78/import4. 전체 DB317/81/5 중 나머지 예약2/비용3/import1은 기존 기록이며 이 감사에서 진위나 완전성을 인증하지 않는다.

| 분류 | 현재 상태 |
| --- | --- |
| A. DB-only | DB 행은 로컬이지만 **DB-only는 아님**. 재생성 코드/파일도 존재 |
| B. committed seed code | 없음. seed 스크립트는 아직 untracked |
| C. test fixture | tests/fixtures/development_dashboard.py + test_development_dashboard.py 있음, 현재 untracked |
| D. tracked SQL/file | 이 더미 묶음에 tracked SQL/dump는 없음. CSV4개/JSON/README는 현재 untracked이며 commit 가능 |

실제 파일 검사: AGODA78/AIRBNB80/BOOKING79/DIRECT78행, 모든 ID는 DEMO-로 시작. expense JSON78건 모두 개발용 메모다. 실제 고객명/연락처나 원본 운영 DB dump가 아니다.

명령은 APP_ENV=development, host=db, database=stay_insight, user=stay_insight_app를 요구하고 관리자 실행을 거부한다. membership/RLS와 서비스 계층을 거치며 동일 이름/가상 주소의 샘플 존재 시 중복 없이 반환한다. 기존 sample을 사용자가 수정해도 reset하지 않는다. 앱 시작 시 자동 seed/fallback은 없다. 환경 guard가 운영 데이터 분리의 대체 수단은 아니다.

9월 검증 기준: 인식 매출6,192,000원, 직접비용2,114,000원, 확인된 fee519,360원, 총비용2,633,360원, 확인된 영업이익3,558,640원, 객실박51/가능180, 점유율28.33%, ADR125,333.33원, RevPAR35,511.11원. 취소/월경계/수수료 누락 사례가 의도적으로 있다.

**주의:** 파일은 ignore되지 않아 `git add .`에 포함된다. 개발 fixture로 검토 후 별도 커밋할 수 있지만 실제 운영 데이터로 배포/시드하면 안 된다. 현재 backend Dockerfile의 COPY . .는 tests도 이미지에 포함한다. 운영 이미지의 fixture 제외가 필요하다. DB에 별도 is_demo/source_category=fixture 플래그는 없고 API는 owner_csv/MANUAL로 표시하므로 표식이 붙은 별도 숙소라는 운영 규칙에 의존한다. 향후 운영 이관/벤치마크에서 명시적으로 제외해야 한다. 공공 시장 데이터 4,714건은 이 fixture가 생성한 것이 아니다.

## 12. Verification results

2026-09-30 이번 감사에서 실제 실행한 결과:

| 검사 | 결과 |
| --- | --- |
| backend uv run ruff check . | PASS |
| backend uv run mypy app tests | PASS, 73 source files |
| backend 전체 pytest -q | **166 passed**, 36.38초, upstream deprecation 2건 |
| PostgreSQL integration | 전체 pytest에 포함. 실제 PostGIS의 임시 DB/random restricted login, migration 왕복/tenant/RLS/CSV/metrics/market/region 검사 |
| frontend pnpm lint | PASS |
| frontend pnpm typecheck | PASS; 실행 중 dev 환경에서 typegen 선행 없이 실행 |
| frontend pnpm test | **40 passed**, failed/skipped 0 |
| frontend pnpm build | PASS; 독립 compose run 컨테이너. protected nested routes가 build manifest에 포함 |
| docker compose config --quiet | PASS, secrets가 포함될 수 있는 확장 config는 출력하지 않음 |
| compose ps | 3서비스 healthy |
| Alembic current/history | PASS, 0005_property_region_write 단일 head |
| HTTP /, /api/v1/health, /docs | 각각 200 |
| Git diff whitespace / 보고서 구조·상대 링크 | 최종 파일 검증 수행 |

실행 명령은 README의 Compose 대체 절차를 사용했다. backend tests에만 `TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/postgres`를 일회성 전달했다. 테스트의 임시 DB 생성/삭제는 기존 테스트 절차이며 application DB 삭제/롤백과 다르다. root pnpm 통합 명령 대신 동일 workspace 검사들을 컨테이너에서 실행했다.

실제 **기존 Supabase 인증 세션**의 브라우저 확인:

- /properties, /properties/new, 샘플 숙소 detail, dashboard, imports/new, imports, reservations, expenses, edit, market가 정상 한국어 제목/본문으로 렌더링됐다.
- frontend 로그에서 숙소 중첩 경로 HTTP 200을 대조했다. 단순 로그인 redirect를 성공으로 세지 않았다.
- 등록/수정에서 부산16옵션, 기존 해운대 선택, 시장 해운대392/46/폐업 결측을 확인했다. 편집 저장/업로드/비용 삭제는 실행하지 않았다.
- 원래 샘플 시장 화면으로 복귀했다.

미실행/제한: 새 이메일 가입·확인·로그아웃/재로그인, 새 사용자 브라우저 온보딩, live 데이터 쓰기, 별도 계정 교차 접근, WCAG 전체·모바일·다중 브라우저, 재시작/재생성 반복, 외부 API 재수집, 실제 다음 예약 실행, 운영 배포/복원, 부하/취약점 검사는 수행하지 않았다. 권한과 쓰기 흐름은 자동 테스트로 검증했고 과거 live 쓰기 증거는 Phase7 보고서로 구분했다. Supabase changelog.md 조회는 도구 오류로 확인 못했으며 JWT 공식 문서는 열람했다; hosted 프로젝트 설정 감사의 대체가 아니다.

## 13. Known limitations

### 문서와 실제 상태 차이

1. product/architecture/repository-structure 일부 첫 문단과 과거 Phase 문구는 Phase2/3 또는 Phase6 미구현이라고 남아 있다. 실제 working tree는 Phase7까지 구현되어 있다.
2. public-accommodation-market 하단과 public-api-verification은 관리자 지역 지정/스케줄러 없음으로 남아 있다. 현재 사용자 지역 선택 가능, repo 내 scheduler는 없지만 **repo 밖 Codex 자동화는 ACTIVE**다.
3. authentication.md의 public redirect 설명 말미는 frontend mounted source라 rebuild 불필요라고 남아 있다. 현재 image source라 코드 변경 후 build가 필요하다.
4. dashboard.md의 localhost:8000 진단 URL과 checked-in .tools 표현은 현재 Docker18000/ignored .tools와 다르다. host 단독 개발8000은 별개다.
5. README의 runtime `alembic current` 예시는 관리자 역할 분리 원칙과 맞지 않는다. 현재 정확한 privileged 조회 명령은 10절을 따른다.
6. 목표 스택의 Supabase DB/Storage, shadcn/ui, Kakao Maps는 현재 구현으로 보아서는 안 된다. 실제는 local DB+hosted Auth, Tailwind/custom components다.
7. proposal의 password recovery, dated inventory, completed-stay/nightly revenue, refund revisions, void expense와 benchmark suppression은 현 구현이 아니다.
8. Phase7 보고서의 161 backend tests/숙소2개는 당시 수치. 더미 추가 후 현재166 tests/숙소3개다. 과거 기록을 오류로 덮어쓰지 않는다.
9. TypeScript transport types는 현재 수동 관리이며 자동 OpenAPI 생성 파이프라인은 없다.

이번 작업은 이 보고서만 수정할 수 있으므로 오래된 원문 문서들을 함께 고치지 않았다.

### 제품/운영 해석 주의

지역 시장의 등록 건수는 전체 숙박 공급 객실 수·직접 경쟁 숙소·수요·가격을 뜻하지 않는다. snapshot 과거 상태/일별 변화 이력 분석도 없다. 주소와 선택 구·군이 맞는지는 사용자 책임이다. 현재 오류 메시지는 안전하지만 일반적이고 초기 UI는 단순하다. 모든 테스트 통과가 실고객 운영 검증을 뜻하지 않는다.

## 14. Remaining MVP work

| 분류 | 미구현/남은 작업 |
| --- | --- |
| A. usability | 비밀번호 복구, 조직 선택/멤버 관리, import 실제 OTA 파일 샘플 검증, 지역 현황 설명 개선, 빈 상태·모바일·접근성·파일럿 사용성 검증 |
| B. data | 실제 투숙/객실 수량·dated inventory·차단일·환불/세금 계약, 데이터 완전성 확인, 공공 날짜/업종 누락과 역사 snapshot, 운영 이관에서 fixture 제외 |
| C. operations/deployment | 운영용 이미지/환경/CI, Supabase 업무 DB 계획 검증, Vercel/Render 배포, 서버 예약 sync, 실패 알림, 백업·복원 실습, 로그·모니터링 |
| D. security/hardening | 운영 runtime/migration/ingestion 로그인 분리와 RLS 검증, secret 관리, HTTPS/origin/redirect 설정, token revocation 정책, rate limit/abuse, dependency 취약점 점검, audit/retention·삭제 정책 |
| E. future product | 공식 관광 방문자 추이, 지역 행사, Kakao Maps와 위치 정규화/반경, 동의·최소규모·집중도·차분 노출 방지 조건의 익명 벤치마크 |

Supabase Storage는 현재 원본을 보관하지 않는 CSV 방식에 필수라고 단정하지 않는다. 벤치마크는 구현 자체가 없으므로 부족한 데이터 화면/억제 정책 테스트가 이미 구현됐다고 주장하지 않는다. Airbnb scraping/OTA live sync/가격 AI/booking engine/투자 분석/과금/모바일 앱/microservices는 여전히 범위 밖이다.

## 15. Recommended next phase

### 후보 비교

| 옵션 | 사용자 가치 | 의존성 | 기술 위험 | 데이터 출처 위험 | 지금/나중 판단 |
| --- | --- | --- | --- | --- | --- |
| A. 공식 관광 방문자 추이 | 계절·지역 방문 추세 맥락 | 이용 가능한 시계열/단위/지역 매핑/기간·방법론, 새 수집 계약 | 중~높음: 추정·중복방문·집계 단위 해석 | 높음: 공개 화면이 API/재배포 허용/원하는 구·군 시계열을 보장하지 않음 | 유용하지만 출처 검증이 먼저; 방문자를 예약 수요로 단정 금지 |
| B. 공식 부산 행사 | 향후 일정 확인, 인력/홍보 준비 참고 | 승인된 공식 provider, 일정/취소/장소/구·군 매핑 | 중간: 다일·중복·변경·취소 처리 | 중간: 누락·일정 변경·지역 세분화 한계 | 다음 제품 기능 후보로 좋음. 행사→매출 증가 예측은 제외 |
| C. Kakao Map/공간 표시 | 지역 분포를 직관적으로 이해 | 지도 key/domain, 검증된 좌표/CRS/정밀도, 위치 계약 | 높음: 현재 public 좌표 미저장, 공간 query 미구현 | 높음: 잘못된 지오코딩/범위·정밀도 오해 | 지금은 숫자를 지도에 옮길 원천 기반부터 부족; 후순위 |
| D. 기존 기능 배포·운영 강화 | PC가 꺼져도 접속/갱신, 파일럿 공유, 데이터 복구 가능 | 배포 계정/비공개 staging 환경/DB 역할·secret·운영 결정 | 중~높음: hosted DB 권한·연결·배포 env/rollbacks | 낮음~중간: 새 provider 없이 기존 데이터 운영; 누락/신선도 한계는 유지 | 로컬에서 검증된 기능을 실제 사용 가능한 형태로 만드는 선행 단계 |

2026-09-30 참고한 공식 후보 자료: [한국관광 데이터랩 지역 방문 현황](https://datalab.visitkorea.or.kr/datalab/portal/loc/getAreaVisitDataForm.do), [방문자 방법론](https://datalab.visitkorea.or.kr/datalab/portal/getMetaInfoList.do), [한국관광콘텐츠랩 OpenAPI 안내](https://api.visitkorea.or.kr/), [Kakao 지도 Web API 가이드](https://apis.map.kakao.com/web/guide/). 이는 후보 서비스/방법론 확인이며 신규 API 승인·인증 호출·전체 스키마/라이선스 검증은 하지 않았다. 방문자 방법론상 이동통신 추정 방문은 숙박객 실측과 다르다. 이 권고는 출처의 지시가 아닌 현재 프로젝트 의존성에 대한 개발 판단이다.

### 단일 권고: D — 기존 Phase 1–7의 비공개 스테이징 배포·운영 검증

범위를 기존 기능의 운영 경로 하나로 제한한다. 방문자/행사/지도/벤치마크 기능을 함께 넣지 않는다. 먼저 Phase7과 개발 fixture의 커밋 경계를 정리한 뒤 별도 승인된 다음 작업으로 진행한다.

권고 완료 조건:

1. 운영 목적 이미지와 환경 분리로 기존 Next.js/FastAPI를 비공개 staging에 배포한다. 개발 fixture/secret을 운영 이미지·DB에 옮기지 않는다.
2. 별도 staging 업무 DB에 Alembic과 runtime/migration/ingestion 역할 경계를 재현하고 tenant 음성 테스트를 실행한다. 로컬 DB 자체를 무조건 업로드하지 않는다.
3. 기존 공식 숙박업 sync를 서버 하루1회 작업으로 운영하고 실패/오래된 성공 상태를 알린다. 로컬 자동화와 중복 실행 정책을 정한다.
4. staging DB 백업 복원 한 번과 배포 rollback 절차를 실제 검증한다.
5. 정상 로그인→숙소→CSV→비용→대시보드→지역 시장을 staging에서 검증하고 비용/운영 주체를 문서화한다.

공개 출시·실고객 데이터 이관·새 제품 지표는 별도 범위다. 이번 감사에서는 배포 리소스 생성이나 과금 동의, scheduler 변경을 실행하지 않았다.

## 16. Important constraints for the next coding agent

- 정확한 저장소는 Desktop/Web Workspace/accommodation. Documents 아래 예전 동명 작업 폴더와 혼동하지 않는다.
- 작업 전 AGENTS/README/이 보고서/현재 기능 계약과 git status를 다시 읽는다. Phase7 미커밋 migration 누락에 특히 주의한다.
- 기존 작업을 reset/stash/checkout/clean/delete/revert하거나 무단 commit/push하지 않는다.
- FastAPI 권위, /api/v1, JWT 검증, 현재 membership, X-Organization-Id 재검증, explicit org SQL+forced RLS, 역할 분리를 유지한다.
- dashboard-v1을 future service-night 계약으로 몰래 변경하지 않는다. owner/public/benchmark를 합치거나 결측을 가짜 값으로 채우지 않는다.
- 사용자가 선택한 region_id와 주소를 분리하며 region 수정에 admin이 필요하도록 되돌리지 않는다.
- localhost 공개 origin, API18000/internal8000, Webpack dev/image source/polling=false를 유지한다. production build를 실행 중 dev .next 위에서 하지 않는다.
- API key/JWT/개인정보/환경 전체/raw public payload를 로그나 문서에 넣지 않는다. fixture는 개발 전용이며 운영 이관 금지다.
- 기존 데이터 볼륨 삭제·운영 권한 확대·미인가 새 provider/scraping·microservice 도입을 하지 않는다.
- 다음 Phase는 하나의 명시된 좁은 범위로 별도 요청받아 진행한다. lint/typecheck/full tests/build/실제 인증 경로 검증과 미검증 항목을 구분한다.

### 감사 종료 파일 목록

아래는 최종 Git 상태다. 이 보고서 외 변경은 감사 전부터 존재했다.

~~~text
 M AGENTS.md
 M README.md
 M backend/app/api/v1/foundation.py
 M backend/app/jobs/assign_property_region.py
 M backend/app/main.py
 M backend/app/models/foundation.py
 M backend/app/repositories/market.py
 M backend/app/schemas/foundation.py
 M backend/app/schemas/market.py
 M backend/app/services/foundation.py
 M backend/tests/test_expenses.py
 M backend/tests/test_imports.py
 M backend/tests/test_market.py
 M docs/api.md
 M docs/architecture.md
 M docs/database.md
 M docs/product.md
 M docs/public-accommodation-market.md
 M frontend/src/app/(protected)/properties/[id]/page.tsx
 M frontend/src/components/market-view.tsx
 M frontend/src/components/property-form.tsx
 M frontend/src/lib/api/client.ts
 M frontend/src/lib/api/market-types.ts
 M frontend/src/lib/api/types.ts
 M frontend/tests/market.test.ts
?? backend/alembic/versions/0005_property_region_write.py
?? backend/app/api/v1/regions.py
?? backend/app/repositories/regions.py
?? backend/app/schemas/regions.py
?? backend/app/services/regions.py
?? backend/tests/fixtures/__init__.py
?? backend/tests/fixtures/dashboard-demo/README.md
?? backend/tests/fixtures/dashboard-demo/development-AGODA.csv
?? backend/tests/fixtures/dashboard-demo/development-AIRBNB.csv
?? backend/tests/fixtures/dashboard-demo/development-BOOKING.csv
?? backend/tests/fixtures/dashboard-demo/development-DIRECT.csv
?? backend/tests/fixtures/dashboard-demo/development-expenses.json
?? backend/tests/fixtures/development_dashboard.py
?? backend/tests/test_development_dashboard.py
?? backend/tests/test_property_regions.py
?? docs/next-steps.md
?? docs/phase7-verification.md
?? docs/project-status-phase8-handoff.md
?? docs/property-region.md
?? frontend/src/app/(protected)/properties/[id]/edit/page.tsx
?? frontend/src/lib/api/region-types.ts
?? frontend/tests/property-regions.test.ts
~~~
