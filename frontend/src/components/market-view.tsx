import Link from "next/link";
import type { AccommodationMarket } from "@/lib/api/market-types";

const types: Record<string, string> = {
  GENERAL_ACCOMMODATION: "일반 숙박", TOURIST_HOTEL: "관광호텔",
  LIFESTYLE_ACCOMMODATION: "생활 숙박", OTHER: "기타 / 미분류",
};
const count = (value: number | null) => value === null ? "데이터 없음" : `${value.toLocaleString("ko-KR")}개`;

export function MarketView({ data }: { data: AccommodationMarket }) {
  const { metrics, freshness } = data;
  const base = `/properties/${encodeURIComponent(data.property_id)}`;
  return <section className="space-y-6">
    <header><p className="text-sm text-slate-600">공식 공공자료 · 소유자 운영 지표와 별도</p>
      <h1 className="text-2xl font-semibold">지역 시장</h1>
      {data.region && <p className="mt-2">{data.region.scope_name} · 구·군 단위</p>}
    </header>
    <nav aria-label="숙소 업무" className="flex flex-wrap gap-4 underline">
      <Link href={base}>숙소 정보</Link><Link href={`${base}/market`} aria-current="page">지역 시장</Link>
      <Link href={`${base}/dashboard`}>대시보드</Link><Link href={`${base}/imports/new`}>CSV 가져오기</Link>
      <Link href={`${base}/imports`}>가져오기 기록</Link><Link href={`${base}/reservations`}>예약 목록</Link>
      <Link href={`${base}/expenses`}>비용 관리</Link>
    </nav>
    {!data.market_context_available && <p role="status" className="rounded border bg-white p-5">
      {data.reason === "PROPERTY_REGION_UNAVAILABLE"
        ? "숙소 지역 정보가 없어 지역 시장 데이터를 연결할 수 없습니다."
        : "공식 숙박업 자료가 아직 수집되지 않았거나 해당 지역의 수집 범위를 확인할 수 없습니다."}
    </p>}
    {!freshness.live_provider_verified && <p className="text-sm text-amber-900">
      공식 데이터 파일의 연결·필드 검증이 완료되지 않아 실데이터 수집은 준비 중입니다.
    </p>}
    {freshness.stale && <p role="status" className="text-amber-900">데이터 갱신이 필요합니다.</p>}
    {data.market_context_available && metrics && <>
      <p>신규·폐업 집계 기간: {data.window_start} ~ {data.window_end} · 최근 12개월</p>
      <dl className="grid gap-4 sm:grid-cols-3">
        <div className="rounded border bg-white p-5"><dt>영업 중 숙박업소 · 수집 상태 기준</dt><dd className="text-2xl">{count(metrics.open_businesses)}</dd></div>
        <div className="rounded border bg-white p-5"><dt>최근 12개월 신규 인허가</dt><dd className="text-2xl">{count(metrics.new_licenses_12m)}</dd></div>
        <div className="rounded border bg-white p-5"><dt>최근 12개월 폐업</dt><dd className="text-2xl">{count(metrics.closures_12m)}</dd></div>
      </dl>
      {metrics.closures_12m === null && <p>폐업일 제공 여부 또는 누락으로 폐업 건수를 확인할 수 없습니다.</p>}
      {metrics.new_licenses_12m === null && <p>인허가일 누락으로 신규 인허가 건수를 확인할 수 없습니다.</p>}
      <table className="w-full border-collapse text-left"><caption className="text-left font-semibold">업종 구성 · 영업 중 기록만</caption>
        <thead><tr><th className="p-2">업종</th><th className="p-2">등록 건수</th></tr></thead>
        <tbody>{Object.entries(metrics.type_breakdown).map(([type, total]) => <tr key={type}><td className="p-2">{types[type] ?? "기타 / 미분류"}</td><td className="p-2">{count(total)}</td></tr>)}</tbody>
      </table>
      <p className="text-sm">상태 미확인 {metrics.unknown_status_count}건 · 인허가일 누락 {metrics.missing_license_dates}건 · 폐업일 누락 {metrics.missing_closure_dates}건</p>
    </>}
    {data.warnings.map((warning) => <p className="text-sm text-slate-700" key={warning}>{warning}</p>)}
    <footer className="space-y-2 border-t pt-4 text-sm text-slate-700">
      <p>출처: <a className="underline" href={freshness.source_url} target="_blank" rel="noreferrer">{freshness.source_dataset_name}</a></p>
      <p>최근 수집: {freshness.collected_at ? new Date(freshness.collected_at).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" }) + " (한국 시간)" : "수집 이력 없음"}</p>
      <p>자료 기준일: {freshness.source_reference_date ?? "제공 여부 미확인"} · 실시간 자료가 아닙니다.</p>
      <p>등록 건수는 경쟁 숙소의 매출·ADR·점유율이나 수요 전망을 의미하지 않습니다.</p>
    </footer>
  </section>;
}