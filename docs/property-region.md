# Phase 7: 숙소 지역 직접 설정

부산 구·군은 숙소의 **시장 분석 범위**다. 법적 주소나 실제 위치를 검증한 결과가 아니다.
주소·도로명주소·좌표는 지역 선택으로 바뀌지 않으며 주소를 수정해도 선택 지역은 유지한다.
자동 지오코딩, 문자열 주소 추론, 지도, 방문자·행사·벤치마크는 범위 밖이다.

## 사용 흐름

숙소 등록 → 부산 구·군 선택 → 저장 → 숙소 상세 → 지역 시장.
기존 숙소는 상세의 '숙소 정보 수정'에서 변경한다. '/properties/[id]/edit'는 기존
등록 폼을 재사용한다. 미설정도 허용하며 미설정으로 선택하면 기존 연결을 해제한다.
지역 시장의 미설정 안내에서 '숙소 정보 수정'으로 이동할 수 있다.
지역 옵션은 인증된 FastAPI 요청으로 DB의 지원 지역을 읽으며 프론트에 목록을 복제하지 않는다.
조회 중에는 저장을 막고 실패 시 재시도한다. 빈 목록에는 명확한 안내를 표시한다.

## API·보안

- GET /api/v1/regions?sido=부산광역시&level=SIGUNGU: JWT 인증 필수. 공유 참조 정보라
  조직 헤더/멤버십은 요구하지 않으며 온보딩 전에도 사용 가능하다. 다른 범위는 422.
- 응답은 id, sido_name, sigungu_name, region_level만 포함한 배열이다.
- POST/PATCH properties는 nullable region_id를 허용한다. POST 생략은 미설정,
  PATCH 생략은 유지, 명시적 null은 해제다. 응답은 region_id와 표시용 region 객체/null을 제공한다.
- 서비스가 실제 존재하는 부산광역시/SIGUNGU/현재 공공 출처 지원 구·군인지 검증한다.
  DB 참조 UUID는 공식 행정코드가 아니다. 잘못된 UUID/지역은 422이며 다른 필드도 저장되지 않는다.
- 숙소 변경은 기존 JWT·현재 조직 멤버십·조직 조건·강제 RLS를 거친다.
  다른 조직 객체는 404, 조직 위조/탈퇴 멤버십은 403이다. OWNER와 MEMBER 모두 기존 권한을 유지한다.
- API와 Next.js 요청은 no-store다. 저장 후 상세로 이동하고 router.refresh로 라우터 캐시를 갱신한다.
  시장 조회는 새 region_id에 연결된 기존 수집 자료를 읽는다. 저장 시 공공 API 호출은 없다.

## 기존 데이터와 관리자 명령

app.regions와 app.properties.region_id를 그대로 사용한다. 중복 테이블/컬럼은 만들지 않는다.
기존 nullable region_address/region_road_address는 레거시 스냅샷으로 보존하지만 더 이상
연결 유효성 판단이나 신규 쓰기에 사용하지 않는다. 기존 region_id는 그대로 유지되며,
과거 주소 불일치로 무효 처리됐던 연결도 이제 저장된 지원 지역을 시장 범위로 사용한다.
주소 정합성은 사용자가 확인한다. 자동 보정/추론/백필은 없다.

기존 유지보수 명령은 남긴다. 같은 지원 지역 서비스/검증을 사용하고 조직·숙소·확인 주소
일치 조건은 오조작 방지용으로 유지한다. 신규 사용자 온보딩에는 명령이 필요하지 않다.
시장 응답의 assignment_method는 EXPLICIT_SELECTION으로 변경한다. 사용자 또는 관리자에 의한
명시적 선택을 뜻하며 특정 행위자나 검증된 위치를 주장하지 않는다. 과거 변경 이력/행위자
감사 테이블은 추가하지 않았으며 기존 숙소 updated_at만 갱신한다.

## 마이그레이션과 실행

0004_public_accommodation에 연결 컬럼은 있었지만 runtime 역할에 해당 컬럼 UPDATE 권한이 없었다.
0005_property_region_write는 UPDATE(region_id) 권한만 추가한다. RLS, 조직 소유권 수정 금지,
공공 테이블 읽기 전용, legacy snapshot 수정 금지는 유지한다. 테이블/행/기존 마이그레이션은 변경하지 않는다.
다운그레이드는 해당 UPDATE 권한만 회수한다. 운영 API에 관리자 DB 연결을 넣지 않는다.

PowerShell, 저장소 루트에서 로컬 개발 DB에 한해서 실행:

~~~powershell
.\.tools\docker-compose.exe exec -T -e DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run alembic upgrade head
.\.tools\docker-compose.exe up -d --build frontend
~~~

현재 개발 프론트는 소스를 이미지에 복사하므로 변경 후 rebuild가 필요하다.
Webpack, 0.0.0.0 bind, localhost:3000 public origin, backend host 18000, polling=false를 유지한다.
환경변수·새 dependency는 필요 없다. 데이터 볼륨을 삭제하지 않는다.

## 검증 범위

[검증 보고서](phase7-verification.md)에 실제 실행 결과를 기록한다.
통합 테스트는 격리 PostgreSQL에서 runtime 권한, 조직 간 차단, 유효/무효 지역, 지역 해제,
주소 독립성, 지역별 다른 집계, 미수집 상태, 수집 이력 불변을 검사한다.
이전 스키마 보존 테스트는 과거 컬럼을 직접 비교한 뒤 head에서 최신 API를 검증한다.
프론트는 실제 React 폼과 API 클라이언트, 상세/수정 페이지, 미설정 CTA를 검사한다.

Phase 6의 count/date/source/freshness/sync와 dashboard-v1 계산은 변경하지 않는다.
