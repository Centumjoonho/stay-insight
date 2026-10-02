import Link from "next/link";
import type { EventMarket } from "@/lib/api/event-types";

const dateLabel = (value: string) => value.replaceAll("-", ".");
const statuses = { ONGOING: "진행 중", UPCOMING: "예정", PAST: "기간 종료" };

export function EventView({ data }: { data: EventMarket | null }) {
  return <section aria-labelledby="events-heading" className="mt-10 space-y-4 border-t pt-6">
    <h2 id="events-heading" className="text-xl font-semibold">공식 행사·축제</h2>
    <p>한국관광공사에서 제공하는 행사 일정입니다. 부산의 모든 행사를 포함하지는 않습니다.</p>
    {!data ? <p role="alert">행사 정보를 불러오지 못했습니다. 잠시 후 새로고침해 주세요.</p> : <>
      <p>{data.scope?.name ?? "지역 미설정"} · {dateLabel(data.from_date)} ~ {dateLabel(data.to_date)}</p>
      {!data.available ? <p role="status">{data.reason === "PROPERTY_REGION_UNAVAILABLE"
        ? <>부산 구·군을 설정해 주세요. <Link className="underline" href={"/properties/" + encodeURIComponent(data.property_id) + "/edit"}>숙소 정보 수정</Link></>
        : data.reason === "OUTSIDE_COLLECTED_WINDOW" ? "선택한 기간의 행사 자료가 수집되지 않았습니다."
          : "행사 데이터가 아직 수집되지 않았습니다."}</p> : <>
        <p>저장된 공식 출처 자료 기준 · 현재 진행 중 {data.summary.ongoing_count ?? "-"}건 · 향후 30일 시작 예정 {data.summary.next_30_days_count ?? "-"}건</p>
        <p className="text-sm">진행 중·예정은 날짜 기준이며 개최·취소 확인 상태가 아닙니다.</p>
        {data.events.length === 0 ? <p role="status">선택한 기간에 확인된 공식 행사 정보가 없습니다.</p> :
          <ul className="space-y-3">{data.events.map(event => <li key={event.source_event_id} className="rounded border bg-white p-4">
            <h3 className="font-semibold">{event.title}</h3>
            <p>{statuses[event.temporal_status]} · <time dateTime={event.start_date}>{dateLabel(event.start_date)}</time> ~ <time dateTime={event.end_date}>{dateLabel(event.end_date)}</time></p>
            <p>{data.scope?.name}</p>
            {event.address && <p>{event.address}</p>}
            {event.source_status && event.source_status !== "선택안함" && <p>출처 제공 상태: {event.source_status}</p>}
          </li>)}</ul>}
        {data.truncated && <p>조회된 {data.total_count}건 중 {data.events.length}건을 표시합니다.</p>}
      </>}
      {data.warnings.map(w => <p key={w} className="text-sm">{w}</p>)}
      <footer className="text-sm"><p>출처: <a className="underline" href={data.source.url} target="_blank" rel="noreferrer">{data.source.provider} · {data.source.dataset}</a></p>
        <p>최근 수집: {data.source.collected_at ? new Date(data.source.collected_at).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" }) + " (한국 시간)" : "수집 이력 없음"}</p></footer>
    </>}
    <p className="text-sm">행사 정보는 공식 데이터 출처에서 제공하는 일정 정보이며, 숙박 수요나 매출 증가를 의미하지 않습니다.</p>
  </section>;
}
