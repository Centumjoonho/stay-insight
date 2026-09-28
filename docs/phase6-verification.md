> Historical foundation report. The later REST API implementation supersedes the live blocker below; see [API verification](public-api-verification.md).

# Phase 6 검증 및 인수 보고서

기준일: 2026-09-28. 결론: Phase 6 내부 기반과 UI/API는 구현·검증했다.
**LIVE PROVIDER NOT VERIFIED** — 실데이터 제공까지 완료한 상태는 아니다.

## A. 실제 구현

- /properties/[id]/market, 기존 숙소 메뉴의 지역 시장 링크, 중앙 서버 API 클라이언트.
- GET /api/v1/market/accommodations, 조직/숙소 인증과 기존 오류 처리.
- 내부 제공자 Protocol/정규화 DTO, 기본 OTHER/UNKNOWN 함수. 검증된 upstream 매핑은 없음.
- 출처/지역 단위 집계, 기간 경계, 미수집·지역 없음·날짜 미확인·stale·최근 수집 실패 상태.
- 원자적/멱등 동기화 서비스, 기록 누락 시 유지, 실패 audit 및 command-only 쓰기 역할.
- 관리자 확인 지역 지정 명령. 원래 주소/좌표 보존, 주소 변경 후 연결 무효화.
- 0004_public_accommodation: regions, public_accommodation_licenses, public_data_sync_runs 및 properties의 nullable 지역 연결 필드.
- 신규 외부 라이브러리 없음. JWT/인증, dashboard-v1, Webpack 개발/production build 명령, Docker 포트와 mount 우회책 유지.
- MARKET_DATABASE_URL은 명령 전용 비공개 DB 연결 입력. 공급자 API 키는 필요 여부 미확인이라 만들지 않음.

## B. 실제 실행 검증

| 검사 | 실행 결과 |
| --- | --- |
| Backend Ruff | 통과 |
| Backend mypy app tests | 통과, 63 source files |
| Backend 전체 pytest | 133 passed, 기존 upstream deprecation 경고 2개 |
| 최종 SQL 경계 정리 후 관련 pytest | test_market.py 19 passed |
| Frontend ESLint | 통과 |
| Frontend next typegen + TypeScript | 독립 컨테이너 통과 |
| Frontend tests | 36 passed |
| Frontend next build | 독립 컨테이너 통과; market 경로 포함 |
| 실제 개발 서버 typecheck | 최초 실행/재시작/재생성 뒤 통과; typegen으로 덮어쓰지 않음 |
| Compose config | 통과 |
| Docker 상태 | frontend/backend/db healthy; host 3000/18000 유지 |
| Git whitespace | git diff --check 통과 |
| 실제 마이그레이션 | head 0003_expenses 확인 후 0004_public_accommodation 적용 |
| 기존 데이터 보존 | 적용 전후 properties=2, reservations=2, expenses=3; 기존 데이터를 수정/삭제하지 않음 |
| 공공 업소 데이터 | 실제 app DB 0행, fixture를 넣지 않음 |
| 수집 명령 | 종료 1, FAILED/LIVE_PROVIDER_NOT_VERIFIED, fetched=0/inserted=0, audit 저장 |

브라우저는 기존 로그인 세션으로 확인했다. 새 사용자 생성이나 실제 비용/예약 변경은 하지 않았다.
숙소 상세의 지역 시장 링크, 시장 화면 및 미지정 지역 안내, imports/new, imports, reservations,
expenses, dashboard 렌더링을 확인했다. frontend HTTP 로그에서 경로별 200을 확인했다.
숙소 목록, 기존 멤버의 onboarding→숙소 목록 이동도 확인했다.
frontend restart 및 force-recreate 후 market을 다시 열어 200을 확인했다.
단순히 page.tsx 존재나 로그인 redirect만으로 경로 검증을 대체하지 않았다.

## C. 자동/fixture로만 검증

- 수집 INSERT/UNCHANGED/UPDATE/명시적 폐업, 누락 기록 보존, 중복 ID/불완전 배치 실패.
- timeout 및 DB 쓰기 실패 시 마지막 자료 보존, 안전한 audit 오류, 과거 자료 기준일 거부.
- 내부 provider를 사용한 CLI 성공 종료 0과 실제 차단 provider의 실패 종료 1.
- 정규화 enum/미확인 fallback, 선택 필드/잘못된 DTO/허용 구·군 검증.
- OPEN/신규/폐업/업종 집계, 12개월·윤일 경계, 날짜 결측에 따른 null.
- 미수집과 확인된 0건 구별, 오래된 자료, 마지막 성공 자료 및 출처 메타데이터.
- 관리자 지역 지정의 정확한 주소/organization/property 조건, 잘못된 지정 거부.
- 다른 조직 404, 잘못된 멤버십 403, 멤버십 취소, 미인증 401, MEMBER 접근.
- 실제 제한 runtime 역할의 공공 데이터 mutation/region mutation 거부 및 ingestion 역할의 예약 접근 거부.
- 화면의 수치/범위/업종/폐업 없음/신선도/미수집/지역 없음/오래된 경고/권한 오류/메뉴 회귀.

Backend 테스트는 임의 이름의 폐기 가능한 PostgreSQL DB와 제한 로그인으로 수행했다.
기존 테스트는 전체 통과하며 초기 마이그레이션 downgrade/re-upgrade도 포함한다.
공공 fixture는 공식 upstream 파일이 아닌 DEVELOPMENT / TEST ONLY 내부 DTO다.
정확한 공식 파일 스키마가 없는데도 upstream fixture를 검증했다고 주장하지 않는다.

## D. 실제 외부 출처에서 확인한 범위

[공공데이터포털 공식 카탈로그](https://www.data.go.kr/data/15044968/fileData.do)에서
행정안전부_문화_숙박업의 존재, 제공기관, 파일 안내 위치, 이용허락범위 및 갱신 안내를 확인했다.
[현재 공식 파일 안내 주소](https://file.localdata.go.kr/file/lodgings/info)는 직접 HTTP 403.
이는 실데이터 다운로드/부산 수치 확인 성공이 아니다. 자세한 근거는
[출처 결정 문서](public-accommodation-source.md)에 있다.

## E. 검증하지 못한 것

- 실제 파일의 키/ID/상태/업태/날짜/지역 코드 및 부산 범위 완전성.
- 실제 성공한 정부 API/파일 요청, 실제 레코드 저장, 실제 시장 수치와 원본 대조.
- upstream mapping, timeout/retry/pagination 계약 구현 및 검증.
- 운영 스케줄링/배포, 장기 성능, 모든 브라우저/전체 WCAG 인증.
- 이번 작업에서 신규 가입·이메일 확인을 새로 수행하지 않음. 기존 인증 회귀 테스트와 로그인 세션 접근으로 확인.
- 실제 숙소의 지역을 추정해서 변경하지 않음. 지역 지정 명령 성공 경로는 격리 DB에서 확인.

## F. 남은 차단

공식 파일/명세에 접근해 실제 계약을 검증해야 한다. 확인된 계약을 토대로 provider를 구현하고
fixture를 공식 스키마로 추가한 후 제한된 실제 동기화를 수행해야 라이브 지역 수치를 제공할 수 있다.
다른 공급자를 임의 추가하거나 미확인 데이터를 실제 데이터로 대체하지 않는다.
관광/행사/지도/벤치마크/Phase 7은 진행하지 않았다.

## 수동 실행 문서

환경변수, 마이그레이션, sync 명령, 수집 이력/행 수 조회, 지역 지정, 페이지 확인 및
미수집/stale 테스트 절차는 [수동 확인 가이드](public-accommodation-market.md#실행과-수동-확인)에 있다.
현재 개발 API는 http://localhost:18000, 웹은 http://localhost:3000 이다.
기존 DB 볼륨과 로컬 환경 파일은 유지했다. 새 커밋은 만들지 않았다.

## Git 시작 상태

브랜치 main, HEAD f440ae9; 직전 5개 커밋을 조회했다.
기존 수정: .env.example, README.md, docker-compose.yml, docs/architecture.md.
기존 untracked: docs/dev-route-verification.md, docs/project-status-phase6-handoff.md.
이 작업에서 reset/stash/삭제 없이 보존했다. Docker Compose의 diff는 이전 수정 그대로다.

## Git 종료 상태 / 변경 파일 목록

아래에는 기존 변경도 포함된다. backend/app/jobs 및 providers의 __init__.py도 신규다.
```text
 M .env.example
 M AGENTS.md
 M README.md
 M backend/.env.example
 M backend/app/main.py
 M backend/app/models/__init__.py
 M backend/app/models/foundation.py
 M backend/tests/test_config.py
 M docker-compose.yml
 M docs/api.md
 M docs/architecture.md
 M docs/database.md
 M docs/product.md
 M frontend/src/app/(protected)/properties/[id]/page.tsx
 M frontend/src/lib/api/server.ts
?? backend/alembic/versions/0004_public_accommodation.py
?? backend/app/api/v1/market.py
?? backend/app/jobs/__init__.py
?? backend/app/jobs/assign_property_region.py
?? backend/app/jobs/sync_accommodation_licenses.py
?? backend/app/models/market.py
?? backend/app/providers/__init__.py
?? backend/app/providers/accommodation.py
?? backend/app/repositories/market.py
?? backend/app/schemas/market.py
?? backend/app/services/market.py
?? backend/app/services/public_sync.py
?? backend/tests/fixtures/development-public-licenses.json
?? backend/tests/test_market.py
?? docs/dev-route-verification.md
?? docs/phase6-verification.md
?? docs/project-status-phase6-handoff.md
?? docs/public-accommodation-market.md
?? docs/public-accommodation-source.md
?? frontend/src/app/(protected)/properties/[id]/market/page.tsx
?? frontend/src/components/market-view.tsx
?? frontend/src/lib/api/market-types.ts
?? frontend/tests/market.test.ts
```
