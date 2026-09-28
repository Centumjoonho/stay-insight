# Stay Insight 현재 프로젝트 진행 상태 — Phase 6 기획용 전달 문서

작성 기준: 2026-09-28. 아래 내용을 ChatGPT에 전달해 Phase 6 구현 지시 프롬프트를 설계한다.
이 문서는 현재 저장소와 구현 계약, 직전 검증 기록의 요약이다. Phase 6의 범위를 확정하거나 구현을 시작하는 지시가 아니다.

## 1. 프로젝트 목적과 현재 도달점

Stay Insight는 한국 숙박업 사업주를 위한 SaaS MVP다. 초기 외부 시장정보 범위는 부산이다.
사업주가 직접 보유한 예약·매출·비용을 관리하고 운영 성과를 확인하며, 추후 별도 출처로 제공되는 부산 공공 시장정보와 함께 참고할 수 있도록 한다.
한국어 UI, KRW, Asia/Seoul 영업일을 사용한다.

현재 Phase 1~5의 할당 기능이 구현돼 있다. 로그인 → 사업장 온보딩 → 숙소 등록/수정 → CSV 예약 가져오기 → 예약 조회 → 비용 관리 → 숙소별 대시보드까지 연결된다.
이는 전체 MVP 또는 프로덕션 출시가 완료됐다는 뜻이 아니다. 공공 시장정보, 관광 추이, 행사, 지도, 익명 벤치마크 등은 미구현이다.

작업 대상 저장소:

```text
C:\Users\HDRBRND\Desktop\Web Workspace\accommodation
```

다른 Documents 경로의 동명/유사 프로젝트와 혼동하지 않는다.
기준 커밋은 `f440ae9` (`feat: complete current Stay Insight MVP work`)다.
설명서 작성 시점에 직전 Docker 수정은 아직 미커밋 상태다: `.env.example`, `README.md`, `docker-compose.yml`, `docs/architecture.md`, 신규 `docs/dev-route-verification.md`.
이 설명서도 새 문서다. 다음 작업 전 실제 `git status`를 재확인하고 기존 변경을 보존한다.

## 2. 현재 기술 구성과 배포 목표의 차이

| 항목 | 현재 구현/설정 |
| --- | --- |
| 저장소 | frontend/ + backend/ 모노레포, pnpm workspace, uv |
| 프론트 | Next.js 16.3.5 App Router, React 19.3.0, TypeScript 5.9.3 |
| 스타일/차트 | Tailwind CSS 4.3.3, Recharts 3.10.1 |
| 개발 번들러 | `next dev --webpack --hostname 0.0.0.0` |
| 프로덕션 빌드 | `next build` 유지; 직전 빌드 로그는 Turbopack |
| 백엔드 | Python 3.12+, FastAPI, SQLAlchemy 2, Alembic, Pydantic, psycopg, PyJWT |
| 버전 고정 | 프론트 pnpm-lock.yaml, 백엔드 backend/uv.lock |
| 현재 업무 DB | 로컬 Docker PostgreSQL 17 + PostGIS 3.5 |
| 현재 인증 | 호스팅된 Supabase Auth, SSR 쿠키 연동 |
| 파일 저장 | CSV 원본 영구 보관 없음; Supabase Storage 미연동 |
| 지도/UI 라이브러리 | Kakao Maps 및 shadcn/ui는 목표 스택이나 현재 미도입 |
| 실행 | Docker Compose의 frontend, backend, db 세 서비스 |
| 배포 목표 | Frontend Vercel, Backend Docker + Render, 업무 DB PostgreSQL/PostGIS on Supabase |

배포 목표를 이미 완료된 상태로 서술하지 않는다. 현재 Dockerfile은 개발용이며 프로덕션 배포 설계의 완성본이 아니다.

## 3. 반드시 유지할 아키텍처와 보안

- FastAPI가 모든 업무 데이터와 지표 계산의 권위 있는 API다. 모든 애플리케이션 API는 `/api/v1`로 시작한다.
- 브라우저와 Next.js 모두 업무 테이블을 Supabase SDK/직접 SQL로 읽거나 쓰지 않는다. Supabase 직접 접근은 인증에 한정한다.
- 프론트 API 계층은 Bearer 토큰과 선택된 `X-Organization-Id`를 전송한다. 백엔드는 매 요청 실제 멤버십을 확인한다. 헤더 자체는 권한 증명이 아니다.
- 백엔드는 Supabase JWKS 기반 RS256/ES256 서명 및 issuer/audience/expiry/subject 등을 검증한다. JWT 검증을 약화하거나 단순 디코딩으로 대체하지 않는다.
- 업무 쿼리·집계·조인·수정에 명시적 organization 조건을 적용하며, 제한된 DB 실행 역할과 강제 RLS를 함께 사용한다. 트랜잭션 로컬 컨텍스트로 연결 풀 간 테넌트 누출을 방지한다.
- 라우트는 입력/인증/서비스 호출/출력만 담당한다. 비즈니스 규칙은 services, DB 조회는 repositories에 둔다.
- 금액은 Decimal/NUMERIC으로 정확하게 저장하고 API에서는 decimal 문자열로 전달한다. 프론트는 표시용 포맷만 담당한다.
- 소유자 데이터, 공공 관측값, 익명 벤치마크는 서로 다른 출처다. 섞어서 하나의 매출/점유율로 표시하지 않는다.
- 추정 지표에는 추정 표시와 산출 근거를 유지한다. 데이터 부재를 가짜 값으로 메우지 않는다.
- 서비스 역할 키/DB 비밀번호/JWT 비밀키를 브라우저나 NEXT_PUBLIC 변수에 넣지 않는다. 실제 토큰·키·원본 CSV를 문서/로그에 남기지 않는다.
- 마이그레이션은 Alembic 단일 이력이다. 별도 Supabase 마이그레이션 체인을 만들지 않는다.
- 단일 모듈형 백엔드를 유지한다. 필요가 입증되지 않은 마이크로서비스, 큐, 캐시, 범용 프레임워크를 추가하지 않는다.

## 4. Phase별 구현 상태

### Phase 1 — 기반 구성

프론트/백엔드 골격, 환경 설정, Docker Compose, 헬스 체크, 기본 테스트/린트/타입 검사, 문서 구축.
`GET /api/v1/health`와 프론트 `/health`로 연결 상태 확인.

### Phase 2 — 인증, 조직, 숙소

- 회원가입, 이메일 확인 콜백, 비밀번호 로그인, 로그아웃, 보호 페이지와 세션 갱신.
- 조직 온보딩 및 OWNER 멤버십 생성. 반복 온보딩의 멱등성과 동시성 처리.
- 숙소 생성·목록·상세·수정: 이름, 주소, 유형, 현재 객실/판매 단위 수, 선택 좌표 등.
- 조직별 접근 격리, JWT 음성 테스트, 실제 PostgreSQL/RLS 통합 테스트.
- 현재 UI는 첫 번째 멤버십을 사용한다. 조직 전환/초대/멤버 관리 UI는 없다.
- OWNER/MEMBER는 현재 숙소·비용 관리에 같은 권한을 가진다.
- 비밀번호 재설정 전용 사용자 흐름, 숙소 삭제, 객실 수 변경 이력/날짜별 재고 관리는 구현된 것으로 가정하지 않는다.

이메일 리다이렉트 문제는 공통 public origin 설정으로 수정됐다.
`NEXT_PUBLIC_SITE_URL=http://localhost:3000`을 회원가입 emailRedirectTo, 인증 콜백 및 보호 경로 리다이렉트에 사용한다.
`0.0.0.0`은 서버 바인딩 전용이며 브라우저 URL로 사용하지 않는다. 운영에서는 환경변수로 실제 도메인을 지정한다.

### Phase 3 — 일반 CSV 예약 가져오기

파일 선택 → 미리보기 → 명시적 컬럼 매핑 → 검증 → 교체 의미 확인 → 가져오기 → 기록/예약 조회.

- GenericCsvAdapter만 구현. AIRBNB/BOOKING/AGODA/DIRECT/GENERIC은 출처 라벨이며 OTA 연동이나 전용 파서가 아니다.
- CSV 5 MiB, 10,000행 제한. UTF-8/BOM 및 엄격한 CP949 fallback과 경고.
- 필수: 외부 예약 ID, 체크인, 체크아웃, 총매출. 선택: 수수료, 투숙 인원, 예약 상태.
- 체크아웃은 체크인보다 뒤여야 하며 숙박일수는 백엔드에서 계산한다.
- 상태 CONFIRMED/CANCELLED/UNKNOWN. 수수료 미입력은 null이며 0으로 추정하지 않는다.
- 전체 검증 및 원자적 반영, 실패 시 예약 변경 rollback. 원본 파일은 요청 동안만 처리하고 영구 저장하지 않는다.
- 파일 checksum + 숙소/채널로 완료 파일 중복 방지. 예약은 숙소/채널/외부 ID 기준 upsert.
- 변경 파일은 해당 ID의 전체 값 교체이며, 누락된 선택 값은 null/UNKNOWN으로 바뀔 수 있다. 파일에 없는 예약은 유지된다.
- 모든 예약 변경 버전과 원본 파일을 복원할 수 있는 완전한 감사 이력은 없다.
- 예약 목록 필터/페이지네이션과 가져오기 이력 제공. 예약 객실 수·실투숙 확인 데이터는 없다.

### Phase 4 — 운영비 관리

- 숙소별 수동 비용 생성/조회/수정/삭제. 날짜, 카테고리, FIXED/VARIABLE, 정수 KRW, 메모.
- 비용 유형은 사용자가 명시하며 카테고리로 자동 추론하지 않는다. source는 MANUAL만 지원.
- 기간/카테고리/유형 필터와 페이지네이션. 삭제는 UI 확인 후 물리 삭제다. 취소/복원/버전 이력은 없다.
- 월세, 관리비, 청소비, 세탁비, 전기/가스/수도, 소모품, 인건비, 마케팅, 수선, 구독료, 보험, 세금·공과금, 기타 카테고리.
- 예약 수수료는 reservations.channel_fee에서 읽는다. 동일 수수료의 가짜 비용 행을 만들지 않는다.
- 알려진 비용 합계와 수수료 누락 건수를 제공한다. 정기 비용 자동 생성·영수증 저장은 없다.

### Phase 5 — 숙소별 운영 대시보드

경로: `/properties/[id]/dashboard?month=YYYY-MM`.

- 8개 KPI: 매출, 확인된 영업이익, 추정 점유율, 추정 ADR, 추정 RevPAR, 확인된 운영비, 예약건수, 평균 숙박일수.
- 예약 채널별 매출/비중/알려진 수수료, 비용 카테고리 및 고정/변동 구성.
- 전월·전년 동월 비교, 월 선택, 기본 12개월 매출/비용/이익 및 점유율 차트.
- 차트의 정확한 값은 접근 가능한 표로도 제공. 데이터 없는 달은 차트 공백으로 처리.
- UNKNOWN 상태, 수수료 누락, 비용 미입력, 추정 근거 등 데이터 품질 안내.
- 서버 컴포넌트가 인증된 FastAPI 요청으로 초기 데이터를 가져온다. 차트는 클라이언트 컴포넌트다.
- 읽기 전용 집계이며 새 테이블/마이그레이션은 없다. 집계는 기간들을 묶은 세 번의 DB 집계 쿼리로 수행한다.

## 5. 가장 중요한 지표 계약: dashboard-v1

초기 product.md의 서비스 숙박일/실투숙 기반 계획을 현재 구현으로 오해하지 않는다.
현재 대시보드의 권위 있는 계약은 `docs/metrics.md`의 dashboard-v1이다.

| 항목 | 현재 계산 기준 |
| --- | --- |
| 대상 예약 | CONFIRMED + UNKNOWN 포함, CANCELLED 제외 |
| 매출/예약건수/채널 매출 | 선택 기간 안에 체크인한 대상 예약 |
| 평균 숙박일수 | 위 예약들의 전체 booked_nights 합 / 예약건수 |
| 예약 객실박 | 선택 기간과 겹친 숙박일수 합. 체크아웃일 제외. 예약 1건 = 객실 1개 가정 |
| 가능 객실박 | 현재 등록 inventory_units × 해당 기간 달력 일수 |
| 점유율(추정) | 예약 객실박 / 가능 객실박 × 100 |
| 배분 매출 | 겹친 숙박일수 / 전체 숙박일수 비례로 예약 매출 배분 |
| ADR(추정) | 배분 매출 / 예약 객실박 |
| RevPAR(추정) | 배분 매출 / 가능 객실박 |
| 확인된 비용 | 해당 기간 수동 비용 + 체크인 대상 예약의 알려진 수수료 |
| 확인된 영업이익 | 체크인 기준 매출 - 확인된 비용 |

현재 월은 오늘까지, 과거 월은 전체 월이다. 현재 부분 월 비교는 전월/전년의 동일 경과 일수로 맞춘다.
0/음수 비교 기준값의 증감률은 null, 점유율/이익률 변화는 %p다. 분모가 없으면 null이며 NaN/Infinity를 만들지 않는다.
점유율 100% 초과를 강제로 자르지 않고 품질 경고를 표시한다.

주의할 차이:

- 메인 매출은 체크인 기준이고 ADR/RevPAR는 겹친 숙박일 비례 배분 기준이다. 두 기준을 무단 통일하지 않는다.
- Phase 4 비용 요약의 예약 수수료는 취소 포함 모든 상태다. Phase 5는 취소를 제외한다. 동일 기간이라도 취소 수수료가 있으면 합계가 다를 수 있다.
- 현재 객실 수를 과거 기간에도 적용한다. 휴업/판매중지/객실차단/재고 이력은 반영하지 않는다.
- 실투숙, 세금 기준, 환불 정산, 모든 비용의 완전성은 검증되지 않는다. 확인된 영업이익은 회계상 순이익이 아니다.
- 지표 정의를 바꾸려면 문서, calculation version, 회귀 테스트를 함께 변경해야 한다.

## 6. 데이터베이스와 주요 API

현재 업무 테이블은 app 스키마의 organizations, organization_members, properties, reservation_imports, reservations, expenses다.
실제 마이그레이션은 다음 세 개이며 직전 검증의 head는 `0003_expenses`다.

1. `0001_tenant_property_foundation.py`
2. `0002_csv_imports.py`
3. `0003_expenses.py`

공공 데이터 및 benchmark 테이블 등 database.md의 나머지 설계는 제안일 수 있다. 모델/마이그레이션 존재 여부를 확인한다.

| 영역 | 주요 API (`/api/v1` 뒤 경로) |
| --- | --- |
| 계정/조직 | GET /me, POST /onboarding |
| 숙소 | GET/POST /properties, GET/PATCH /properties/{id} |
| CSV | POST /imports/preview, POST /imports/validate, POST /imports |
| 가져오기 조회 | GET /imports, GET /imports/{id} |
| 예약 조회 | GET /reservations, GET /reservations/{id} |
| 비용 | GET/POST /expenses, GET/PATCH/DELETE /expenses/{id}, GET /expenses/summary |
| 대시보드 | GET /dashboard/summary, GET /dashboard/trends |

대시보드는 property_id 필수, month 선택. trends의 months는 기본 12, 범위 1~24다.
인증 실패 401, 비멤버십 403, 다른 조직의 객체는 존재를 노출하지 않는 404다.

## 7. 주요 코드 위치

```text
frontend/src/
  app/(protected)/properties/[id]/
    page.tsx
    dashboard/page.tsx
    imports/page.tsx
    imports/new/page.tsx
    reservations/page.tsx
    expenses/page.tsx
    expenses/new/page.tsx
    expenses/[expenseId]/edit/page.tsx
  app/login/, app/signup/, app/auth/callback/
  proxy.ts
  lib/supabase/        # 인증 클라이언트/서버/public redirect
  lib/api/             # 중앙 API 통신 및 타입
  components/          # 인증/숙소/가져오기/비용/대시보드 UI
backend/app/
  api/v1/              # foundation, imports, expenses, dashboard, health
  api/dependencies/tenant.py
  core/auth/jwt.py
  services/            # 업무 규칙/기간/지표 계산
  repositories/        # 조직 범위를 명시한 조회와 집계
  schemas/, models/, db/, importers/generic.py
backend/alembic/versions/
frontend/tests/
backend/tests/
```

## 8. Docker 실행과 최근 404 수정

Docker Desktop의 Linux containers 환경에서 저장소 루트에서 실행한다.

```powershell
cd "C:\Users\HDRBRND\Desktop\Web Workspace\accommodation"
docker compose up -d --build
docker compose ps
```

| 접속 대상 | 현재 기본 주소 |
| --- | --- |
| 웹 | http://localhost:3000 |
| API 헬스 | http://localhost:18000/api/v1/health |
| Swagger | http://localhost:18000/docs |
| 컨테이너 내부 API | http://backend:8000 |

루트 `.env`는 기존 값을 보존하고 필요한 public 설정만 지정한다.

```dotenv
NEXT_PUBLIC_SITE_URL=http://localhost:3000
API_PORT=18000
SUPABASE_URL=<기존 프로젝트 URL>
SUPABASE_PUBLISHABLE_KEY=<기존 공개 키>
```

API_PORT 기본값은 18000이며 Compose가 외부 포트와 브라우저 API URL을 함께 맞춘다.
현재 Windows에서 8000이 예약 범위에 포함돼 발생한 바인딩 오류를 피하는 설정이다. 컨테이너 내부 8000은 유지한다.
Supabase Auth의 Site URL 및 허용 callback은 localhost:3000 기준을 유지한다.

404에 대해 확인된 사실:

- 페이지 소스가 있어도 Webpack 개발 서버의 생성 AppRoutes에서 하위 경로가 누락되고 dev 타입 파일에 잘못된 조각이 남았다.
- Windows 프론트 소스 bind mount + Watchpack polling 구성에서 발생했다.
- 프론트를 이미지 내부 소스로 실행하고 WATCHPACK_POLLING=false로 바꾸자 경로 등록과 타입 검사가 정상화됐다.
- Webpack만으로 해결된 문제가 아니다. 특정 Next.js 내부 race 또는 Turbopack만의 결함으로 확정하지 않는다.
- 현재 설정은 검증된 구성 우회책이며 모든 환경에서의 근본 원인 증명은 아니다.

현재 프론트는 소스 bind mount가 없다. 프론트 수정 후에는 `docker compose up -d --build frontend`가 필요하다.
단순 restart는 이미지 안의 코드를 갱신하지 않는다. 백엔드 개발 소스 mount는 유지된다.
개발 서버가 사용하는 .next에 프로덕션 빌드를 덮어쓰지 말고 별도 임시 컨테이너에서 build한다.
DB 볼륨을 지우는 `docker compose down -v`는 사용하지 않는다.
기존 문서의 localhost:8000 예제는 호스트 직접 실행/과거 구성일 수 있다. 최신 Docker 기준은 이 절과 README, ADR-034/035다.

## 9. 검증 상태와 한계

아래는 직전 2026-09-28 작업에서 실제 수행한 결과다. 이번 설명서 작성 작업에서 전체 테스트를 새로 실행했다는 의미는 아니다.

- 프론트 ESLint, TypeScript, 테스트 30개, 독립 컨테이너 프로덕션 빌드 통과.
- 같은 날 선행 리뷰에서 백엔드 Ruff, mypy, PostgreSQL 통합/단위 테스트 114개 통과. upstream deprecation 경고 2개가 있었다.
- Compose 설정 검증 및 frontend/backend/db healthy 확인.
- 수정된 개발 컨테이너 최초 실행/재시작/재생성 뒤 live typecheck 통과.
- 인증된 브라우저에서 대시보드, imports/new, imports, reservations 정상 렌더링 및 HTTP 200 확인.
- Phase 5 기존 검증에는 월 선택, 데이터 없는 기간, 추정/출처/품질 표시, 차트와 값 표 및 원자료 대조가 포함됐다.
- 모든 브라우저/장기간 재시작/운영 배포/전체 WCAG 준수까지 검증한 것은 아니다.
- 현재 로컬 데이터는 개발 검증 기록을 포함한다. 이를 실운영 데이터 또는 시장 통계로 재사용하지 않는다. 공유용으로 기존 레코드/토큰을 복사하지 않는다.

변경 후 기본 검증 계약은 루트의 `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build`다.
Docker에서 프론트 확인 예:

```sh
docker compose exec -T frontend pnpm typecheck
docker compose run --rm --no-deps frontend sh -c 'pnpm lint && pnpm exec next typegen && pnpm typecheck && pnpm test && pnpm build'
```

첫 명령은 실제 개발 서버 생성 타입을 검사한다. next typegen을 먼저 실행해 개발 서버의 타입 생성 실패를 숨기지 않는다.
백엔드 통합 테스트에는 별도 테스트 DB를 생성할 수 있는 TEST_DATABASE_URL이 필요하다. 자세한 절차는 authentication.md를 따른다.

## 10. 아직 구현되지 않은 범위와 Phase 6 결정 사항

현재 미구현:

- 부산 공공 숙박업소 목록/지도 및 공식 데이터 수집·갱신.
- 관광 방문자 추이, 지역 행사.
- Kakao Maps 연동.
- 익명 벤치마크 동의·집계·억제·승인·공개 흐름.
- Supabase 업무 DB/Storage 연결, 운영 배포 완성.
- 날짜별 판매 가능 재고, 실투숙 확인, 서비스 숙박일 기반 정산, 환불/세금 정합성.
- 위에서 명시한 조직 관리, 비밀번호 재설정, 완전한 변경 이력 등 잔여 기능.

Phase 6의 구체적인 기능 범위는 아직 이 문서에서 확정하지 않는다.
공공정보 영역은 남은 MVP 후보지만, 지도/관광/행사/벤치마크를 한 번에 구현하도록 추정하지 않는다.
공공정보를 선택한다면 먼저 실제 공식 소스의 제공 필드·라이선스·키·부산 범위·주기·호출 제한·품질을 확인해야 한다.
공급자/데이터셋이 검증되기 전에 가상의 API나 수치를 설계에 사실처럼 넣지 않는다.
외부 데이터 실패/미설정/오래된 데이터 상태를 명시하고, 정상 결과처럼 보이는 샘플 fallback을 금지한다.

익명 벤치마크는 공공정보와 다른 기능이다. 기존 제품 제안에는 동의한 조직 최소 10개, 기여도 제한, 고정 코호트, 차분 공격 방지/억제 조건이 있다.
이는 이미 구현된 보호장치도 익명성 보장도 아니다. 충분한 동의 데이터와 별도 검증 전에는 활성화하지 않는다.

명시적 MVP 제외 항목: Airbnb 스크래핑, 예약 엔진, OTA 실시간 동기화, AI 가격 추천, 부동산 투자 분석, 구독 결제, 모바일 앱, 마이크로서비스.

## 11. 다음 ChatGPT에게 요청할 작업

이 프로젝트 상태를 전제로, 개발 에이전트에게 줄 Phase 6 프롬프트를 작성해 달라.
먼저 Phase 6에서 다룰 단일 기능 또는 좁은 기능 묶음을 사용자와 확정하고, 미결정된 외부 소스/키/데이터 계약은 확인 항목으로 분리해 달라.
기존 구현을 다시 만들거나 Phase 1~5를 임의로 재설계하지 말아 달라.

최종 프롬프트에는 다음이 필요하다.

1. 정확한 저장소 경로, AGENTS.md 및 관련 docs 선독, 기존 미커밋 변경 보존.
2. 이번 Phase의 목표, 포함 기능, 제외 기능, 사용자 흐름과 완료 기준.
3. 실제 확인된 외부 소스가 필요한지, 키가 없을 때 무엇까지 검증 가능한지.
4. 필요한 API/스키마/마이그레이션/출처·신선도·추정 메타데이터 설계.
5. 조직 격리와 공개 데이터의 접근 정책 구분, JWT/RLS/비밀키 경계 유지.
6. dashboard-v1 및 기존 인증/숙소/가져오기/비용 동작의 회귀 방지.
7. 오류/빈 데이터/갱신 실패/오래된 데이터/설정 누락 상태의 정직한 UI.
8. 의미 있는 정상·실패·권한 테스트, lint/typecheck/tests/build 및 실제 브라우저 검증.
9. 현재 Docker 방식으로 재빌드·실행·재시작 검증, 새 환경변수와 문서 업데이트.
10. 실제 통과한 검사, 미실행 검사, 미해결 사항을 구분한 완료 보고.

## 12. 저장소 내 근거 문서

- [기여 규칙](../AGENTS.md)
- [제품 범위와 제안](product.md)
- [아키텍처 및 ADR](architecture.md)
- [DB 설계/구현 구분](database.md)
- [인증](authentication.md), [API](api.md)
- [CSV 가져오기](imports.md), [비용](expenses.md)
- [현재 지표 계약](metrics.md), [대시보드 및 기존 검증](dashboard.md)
- [최근 Docker 경로 검증](dev-route-verification.md)
- [실행 방법](../README.md)

문서의 오래된 상단 상태 문구/기준 트리와 후속 Phase 부록이 다를 수 있다.
현재 구현 계약과 코드, 후속 ADR을 함께 확인하며, 최초 제안을 구현 완료로 해석하지 않는다.