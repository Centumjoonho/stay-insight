# 공공 API 연동 검증

2026-09-28. 기존 Phase 6 기반 위에 공식 REST API 연결을 추가했다.
서버 전용 키는 Git 제외 루트 .env에 저장하고 Compose backend에만 전달한다.
API는 승인된 /lodgings/info의 JSON 응답을 사용한다. 전체 자료 기준일은 null 유지.

## 실행

```powershell
cd "C:\Users\HDRBRND\Desktop\Web Workspace\accommodation"
docker compose up -d --build backend
docker compose exec -T -e MARKET_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/stay_insight backend uv run python -m app.jobs.sync_accommodation_licenses
```

위 DB 자격은 이 저장소의 로컬 개발 DB에만 해당한다. 운영에서는 ingestion 전용 로그인 사용.
API 키를 명령줄 인자로 넣지 않는다. 현재 키는 backend 컨테이너 환경으로 전달된다.
새 dependency/migration 없음. 기존 데이터 볼륨을 삭제하지 않는다.
자동 스케줄러는 추가하지 않았으며 갱신은 위 명령으로 실행한다.
숙소 구·군 연결은 [기존 관리자 명령](public-accommodation-market.md)을 사용한다.

## 검사

- 실제 인증 성공 resultCode=0. 전국 totalCount=58,811. 페이지 크기 100.
- 마지막 페이지 11건과 실제 폐업 코드/명칭 확인. 원본 행/키 출력하지 않음.
- Backend pytest 153 passed, 기존 upstream deprecation 경고 2개.
- Backend Ruff/mypy app tests 통과 (65 files).
- 전체 수집 및 frontend 검사 결과는 아래 실행 결과로 보완한다.

- 첫 전체 수집 COMPLETED: 부산 4,714건 삽입, 실패 0. 원본 전국 총 58,811건 검증.
- Frontend lint/typecheck/tests 36 passed. 별도 컨테이너 production build 통과.
- Docker Compose config --quiet 통과.


## 브라우저 확인 및 최종 상태

- 기존 로그인 Chrome에서 대상 숙소의 지역 시장 페이지 정상 렌더링 확인.
- 기존 도로명 주소 Haeundae-gu를 근거로 해당 조직/숙소만 관리자 명령으로 해운대구에 연결.
  원래 주소/좌표는 변경하지 않았다.
- 화면: 해운대구 영업 중 392건, 최근 12개월 신규 인허가 46건.
- 폐업일 누락 2건 때문에 폐업 지표는 기존 계약에 따라 '데이터 없음'으로 표시.
- API 전체 응답에는 자료 기준일 필드가 없어 날짜를 임의 생성하지 않음.
- UI의 공식 API 출처 링크와 실제 수집 시각 확인. 전체 WCAG/다중 브라우저 검사는 미실시.
- 최종 수정 후 관련 테스트 39 passed, Ruff/mypy 재통과. 서비스 3개 healthy.
- 키는 Git 제외 .env에만 저장. 신규 dependency/migration/frontend 코드 변경 없음.
- 자동 갱신 스케줄은 구성하지 않음. 수집 명령을 실행할 때만 최신 공개 자료를 반영한다.
