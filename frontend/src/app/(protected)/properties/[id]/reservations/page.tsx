import Link from "next/link";
import { requireOrganization, serverApi } from "@/lib/api/server";
import { channels } from "@/lib/api/import-types";
import { ReservationTable } from "@/components/reservation-table";

export default async function Reservations({ params, searchParams }: {
  params: Promise<{ id: string }>; searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { id } = await params;
  const org = await requireOrganization();
  const property = await serverApi.property(org.organization_id, id);
  const search = await searchParams;
  const value = (key: string) => typeof search[key] === "string" ? search[key] as string : "";
  const offset = Math.max(0, Number(value("offset")) || 0);
  const filters = new URLSearchParams();
  for (const key of ["from", "to", "channel", "reservation_status"]) if (value(key)) filters.set(key, value(key));
  const query = new URLSearchParams(filters);
  query.set("property_id", id); query.set("limit", "50"); query.set("offset", String(offset));
  const result = await serverApi.reservations(org.organization_id, query.toString());
  const page = (next: number) => { const q = new URLSearchParams(filters); q.set("offset", String(next)); return "?" + q; };
  return <section><h1 className="text-2xl font-semibold">{property.name} · 예약 목록</h1>
    <p>출처: 소유자 CSV · 날짜 필터는 체크인일 기준(양 끝 포함)입니다. 순매출은 총 매출에서 입력한 수수료만 차감한 값입니다.</p>
    <form className="my-4 flex flex-wrap items-end gap-3">
      <label>시작일<input className="field" type="date" name="from" defaultValue={value("from")} /></label>
      <label>종료일<input className="field" type="date" name="to" defaultValue={value("to")} /></label>
      <label>채널<select className="field" name="channel" defaultValue={value("channel")}><option value="">전체</option>
        {channels.map((channel) => <option key={channel}>{channel}</option>)}</select></label>
      <label>상태<select className="field" name="reservation_status" defaultValue={value("reservation_status")}>
        <option value="">전체</option><option value="CONFIRMED">확정</option><option value="CANCELLED">취소</option>
        <option value="UNKNOWN">미확인</option></select></label><button className="action">조회</button>
    </form><p>총 {result.total}건</p><ReservationTable items={result.items} />
    <nav className="mt-4 flex gap-4">{offset > 0 && <Link href={page(Math.max(0, offset - 50))}>이전</Link>}
      {offset + 50 < result.total && <Link href={page(offset + 50)}>다음</Link>}
      <Link href={`/properties/${id}/imports/new`}>CSV 가져오기</Link>
      <Link href={`/properties/${id}/imports`}>가져오기 기록</Link></nav>
  </section>;
}
