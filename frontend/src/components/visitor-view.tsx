import Link from "next/link";
import type { VisitorMarket } from "@/lib/api/visitor-types";
import { VisitorChart } from "./visitor-chart";
// Format exact API strings; chart converts to Number only for presentation.
function number(value: string | null | undefined) {
 if (value == null) return "-";
 const [integer, fraction] = value.split(".");
 return integer.replace(/\B(?=(\d{3})+(?!\d))/g, ",") + (fraction === undefined ? "" : "." + fraction);
}
export function VisitorView({ data, error = false }: { data: VisitorMarket | null; error?: boolean }) {
 return <section aria-labelledby="visitor-heading" className="mt-10 space-y-5 border-t pt-6">
 <h2 id="visitor-heading" className="text-xl font-semibold">공식 지역 방문 추이</h2>
 <p>한국관광공사의 이동통신 기반 일별 추정 방문 지표입니다. 숙박객 수, 예약 수 또는 숙소 점유율을 의미하지 않습니다.</p>
 {error || !data ? <p role="alert">방문자 정보를 불러오지 못했습니다. 잠시 후 새로고침해 주세요.</p> : <>
 <form method="get" className="flex flex-wrap items-center gap-3"><label htmlFor="visitor-category">방문자 구분</label>
 <select id="visitor-category" name="category" defaultValue={data.category.code} className="rounded border bg-white p-2">{data.categories.map(c => <option key={c.code} value={c.code}>{c.name}</option>)}</select>
 <button className="rounded border px-3 py-2" type="submit">조회</button></form>
 <p>{data.scope?.name ?? "지역 미설정"} · {data.category.name} · 구분별 별도 집계</p>
 {!data.available && <p role="status">{data.reason === "PROPERTY_REGION_UNAVAILABLE" ? <>부산 구·군을 설정해 주세요. <Link className="underline" href={"/properties/" + encodeURIComponent(data.property_id) + "/edit"}>숙소 정보 수정</Link></> : "방문자 데이터가 아직 수집되지 않았습니다."}</p>}
 {data.available && <>
 <p>최근 제공일: {data.latest?.date} · 확인된 최신 관측일이며 공식 제공 완료 보장은 아닙니다.</p>
 <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{[["일별 추정 방문자", data.latest?.value, "명"], ["최근 7일 일평균", data.rolling.average_7d, "명"], ["최근 28일 일평균", data.rolling.average_28d, "명"], ["직전 7일 대비", data.rolling.change_7d_percent, "%"]].map(([label, value, unit]) => <div className="rounded border bg-white p-4" key={label}><dt>{label}</dt><dd className="text-2xl">{number(value)}{value == null ? "" : unit}</dd></div>)}</dl>
 <p className="text-sm">평균·증감률은 자체 계산한 일별 파생 지표입니다. 연속 7일·28일 자료가 없으면 평균은 표시하지 않습니다.</p>
 <h3 className="font-semibold">최근 {data.coverage.requested_days}일 일별 추정 방문자</h3><VisitorChart history={data.history} />
 <p>자료 있음 {data.coverage.available_days}일 / {data.coverage.requested_days}일 · 누락 {data.coverage.missing_days}일. 누락은 0이 아닙니다.</p>
 <details><summary className="cursor-pointer underline">일별 자료 표 보기</summary><div className="max-h-96 overflow-auto">
 <table className="w-full text-left"><caption>일별 추정 방문자 · {data.category.name}</caption><thead><tr><th scope="col">날짜</th><th scope="col">추정 방문자</th></tr></thead><tbody>{data.history.map(p => <tr key={p.date}><th scope="row" className="py-1 font-normal">{p.date}</th><td>{p.value === null ? "자료 없음" : number(p.value) + "명"}</td></tr>)}</tbody></table></div></details>
 </>}
 {data.warnings.map(w => <p className="text-sm text-slate-700" key={w}>{w}</p>)}
 <footer className="space-y-1 text-sm"><p>출처: <a className="underline" href={data.source.url} target="_blank" rel="noreferrer">{data.source.provider} · {data.source.dataset}</a></p>
 <p>최근 수집: {data.source.last_collected_at ? new Date(data.source.last_collected_at).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" }) + " (한국 시간)" : "수집 이력 없음"}</p>
 {data.source.days_since_latest_reference !== null && <p>최근 자료 기준일로부터 {data.source.days_since_latest_reference}일 경과 · 공식 데이터 제공 시차가 있을 수 있습니다.</p>}</footer>
 </>}
 </section>;
}
