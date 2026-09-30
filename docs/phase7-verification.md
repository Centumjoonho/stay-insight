# Phase 7 완료·검증 보고서

검증일: 2026-09-30. 작업 저장소: C:/Users/HDRBRND/Desktop/Web Workspace/accommodation.
범위: SELF-SERVICE PROPERTY REGION ASSIGNMENT. 후속 Phase는 시작하지 않았다.

## A. 구현

- 등록 폼에 API 기반 부산 구·군 선택, 선택적 미설정, 오류/재시도/로딩/빈 목록 처리.
- 기존 등록 폼을 재사용하는 /properties/[id]/edit 추가. 기존 지역 선택을 불러오며 변경·해제 가능.
- 상세 화면 지역 표시·수정 링크, 미설정 시장 화면 수정 CTA.
- GET /api/v1/regions: 인증 필수 공유 참조 데이터. 부산/SIGUNGU 범위만 허용.
- POST/PATCH properties: region_id 검증·저장. 응답에 region_id 및 표시용 region 추가.
- 주소와 시장 지역 독립. 주소 변경이 지역을 바꾸지 않는다. 자동 주소 추론 없음.
- 기존 관리자 유지보수 명령은 동일 지원 지역 검증 서비스 사용. 사용자 등록에는 필요 없음.
- assignment_method는 EXPLICIT_SELECTION으로 변경. 실제 위치/관리자 검증·감사 이력을 주장하지 않음.
- app.regions 및 기존 region_id 재사용. 새 테이블·컬럼·dependency 없음.
- 마이그레이션 0005_property_region_write: runtime에 UPDATE(region_id)만 부여.
  기존 스키마의 영속 연결은 충분했지만 수정 권한이 부족했으므로 최소 권한 마이그레이션이 필요했다.
  이전 마이그레이션·RLS·JWT·조직 소유권 수정 금지·공공 테이블 쓰기 제한 유지.

## B. 자동 검사

- backend Ruff 전체 통과.
- backend mypy app tests: 70개 파일 통과.
- backend pytest: 161 passed, 기존 upstream deprecation 경고 2개.
- frontend pnpm lint 통과.
- frontend next typegen + pnpm typecheck 통과 (격리 컨테이너).
- frontend pnpm test: 40 passed, 0 failed.
- frontend pnpm build 통과. 기존 next build/Turbopack production 설정 그대로 유지.
- 실행 중 dev .next를 공유하지 않는 compose run --rm --no-deps 컨테이너에서 production 검증.
- 실행 중 Webpack dev의 pnpm typecheck는 typegen 선행 없이 초기·재시작·재생성 후 통과.
- git diff --check 통과. UTF-8 및 변경 문서 9개 상대 링크 60개 검증 통과.

처음 전체 백엔드 검사에서는 과거 스키마로 downgrade한 상태에서 최신 API를 호출하는
기존 migration 테스트가 실패했다. 테스트를 과거 컬럼/예약 금액 직접 비교로 수정하고
finally에서 head 복구를 보장한 뒤 전체 161개 통과를 확인했다. 제품 import/expense 로직은 변경하지 않았다.
프론트 테스트 작성 중 구문·lint 오류를 수정한 후 전체 lint/typecheck/40 tests/build를 재실행했다.

## C. PostgreSQL 통합 검증

실제 PostgreSQL/PostGIS의 격리 stay_insight_test_* DB와 제한 runtime 로그인으로 실행했다.
SQLite/관리자 연결만의 검증이 아니다. fixture 생성과 마이그레이션만 테스트 관리자 권한을 사용한다.

- 지역 조회 인증, 지원 범위 필터, 유효 지역 등록/변경/조회/목록/해제, 기존 미설정 숙소.
- 잘못된 UUID·없는 UUID·미지원 시도/구·군/level 거부 및 원자적 저장.
- 다른 조직 숙소 PATCH/GET/시장 GET은 404, 조직 위조/멤버십 해제는 403.
- MEMBER의 기존 수정 권한 유지. 컨텍스트 없는 UPDATE는 RLS로 0행.
- organization_id/legacy snapshot/public reference 수정 권한 확장 없음.
- 새 지역의 집계가 다르게 나오는 것과 source/freshness 유지, 저장 시 provider 호출 금지.
- 기존 tenant/JWT/CSV/expenses/dashboard/market/provider 회귀 테스트 포함.
- 기존 fixture는 migration base↔head 왕복도 실행한다.

미지원 시도/level은 실제 DB CHECK도 거부한다. API 자체의 방어까지 검사하기 위해 해당
테스트 DB에만 CHECK를 잠시 완화한 reference fixture를 넣고 finally로 복구했다.
실제 서비스 DB의 제약조건은 변경하지 않았다.

## D. Docker 검증

- Compose config --quiet 통과.
- frontend 이미지 rebuild 및 컨테이너 recreate 완료.
- backend/db/frontend 모두 running, healthy.
- 실제 Alembic head: 0005_property_region_write (로컬 적용 완료).
- frontend dev: next dev --webpack --hostname 0.0.0.0, source image copy, polling=false 유지.
- host frontend localhost:3000, API localhost:18000, container backend:8000 유지.
- restart 및 force-recreate 각각 이후 edit/dashboard/imports/new/imports/reservations/expenses/market
  인증 브라우저 렌더링과 dev 타입 검사 통과. 최종 frontend 로그에서 모든 경로 HTTP 200 확인.
- Compose/Dockerfile/package.json/lockfile 변경 없음. 볼륨 삭제 없음.

## E. 실제 브라우저 검증

기존 정상 Supabase 로그인 세션에서 실행했다. 인증 우회·토큰 조작·관리자 지역 연결 명령 없음.

1. /properties/new에서 임시 개발용 숙소 '개발 검증 전용 Phase7 20260930' 등록.
   주소는 '개발 테스트 주소 (실제 숙소 아님)'으로 개발 검증임을 표시했다.
2. UI에서 수영구 선택 → POST 성공 → 상세에서 부산광역시 수영구 표시.
3. 새 숙소 시장 페이지에 수영구 영업 중 252건, 신규 41건, 폐업 1건 표시.
4. 수정 페이지에서 수영구 초기 선택 확인 → 해운대구 선택 → PATCH 성공.
5. 상세에 해운대구 표시. 주소는 그대로. 링크로 다시 시장 진입해 해운대구
   영업 중 392건, 신규 46건, 폐업 데이터 없음(누락 안내) 확인. 오래된 수영구 캐시 없음.
6. 두 지역 모두 수집 시각 2026-09-30 11:18:53 KST 및 같은 공식 출처 유지.
7. UI로 지역 해제 → 상세 '미설정' → 시장 숫자 숨김·설정 안내 → 수정 CTA 이동 성공.
8. 기존 centumoffice 상세·수정·CSV 가져오기·가져오기 기록·예약·비용·대시보드·시장 렌더링 확인.
9. 프론트 재시작/재생성 후 기존 숙소의 위 중첩 경로 반복 확인.

임시 개발용 숙소 id: a437d56a-553a-4e3a-b85d-bf059de5b6b0.
검증 후 해당 id+org+name 및 예약/비용/import 없음 조건으로 한 행만 정리했다.
숙소 총수는 시작/종료 동일한 2건. 기존 숙소는 수정하지 않았다.
브라우저에서 지역 선택/변경만 했으며 SQL/관리자 명령은 이 임시 행 정리에만 사용했다.
실제 공공 시장 숫자는 기존 동기화 자료를 그대로 읽었으며 synthetic 시장 값은 없다.

## F. 미검증

- 신규 이메일 가입·확인·새 로그인·신규 조직 온보딩을 실제 브라우저에서 반복하지 않았다.
  기존 인증 세션을 사용했고 관련 자동 JWT/온보딩/조직 테스트는 통과했다.
- CSV 신규 업로드·비용 신규 작성은 실데이터 보존을 위해 브라우저에서 반복하지 않았다.
  화면/경로 회귀와 전체 자동 API/React/DB 테스트로 검사했다.
- 별도 사용자 계정 두 개의 브라우저 교차 접근은 반복하지 않았다. 실제 PostgreSQL
  서로 다른 사용자·조직·revoked membership 통합 검사로 검증했다.
- 전체 WCAG 심사·모바일/다중 브라우저 호환성·동시 편집 충돌 검사는 별도 미실시.
  폼 라벨/상태/키보드 제출·기존 선택 표시와 한국어 화면은 확인했다.
- 공공 API 재수집·배포·스케줄러 변경은 이번 범위가 아니어서 수행하지 않았다.

## G. 남은 제한과 보존 사항

- 지역은 사용자의 분석 범위 선택이며 주소와 일치하는지 자동 검증하지 않는다.
- 변경 행위자/이전 지역을 기록하는 별도 감사 이력은 없음. 기존 updated_at만 갱신.
- 성공한 공공자료 수집이 없는 지역은 기존 NOT_SYNCHRONIZED 상태를 유지한다.
- Phase 6 수집 시작/종료 비교: 최신 COMPLETED, collected_at=2026-09-30 02:18:53.765182+00,
  fetched_count=4714, public rows=4714로 유지. provider/sync 및 dashboard-v1 파일 diff 없음.
- 추가 환경변수·새 dependency 없음. 운영 API 권한 우회 없음.
- 커밋/원격 푸시는 이번 요청에 없어 실행하지 않았다.

## Git 시작 상태

~~~text
 M AGENTS.md
?? docs/next-steps.md
~~~

시작 HEAD: 82a2147 feat: connect Busan public accommodation market API.
기존 AGENTS.md의 next-session 추가분 및 docs/next-steps.md 내용은 보존했다.
AGENTS.md에는 Phase 7 현재 계약을 별도로 추가했다.

## 변경 파일 / 종료 상태

아래는 최종 작업 트리이며 docs/next-steps.md는 작업 전부터 있던 사용자 파일이다.
모든 Phase 7 변경은 커밋하지 않은 상태다.

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
?? backend/tests/test_property_regions.py
?? docs/next-steps.md
?? docs/phase7-verification.md
?? docs/property-region.md
?? frontend/src/app/(protected)/properties/[id]/edit/
?? frontend/src/lib/api/region-types.ts
?? frontend/tests/property-regions.test.ts
~~~
