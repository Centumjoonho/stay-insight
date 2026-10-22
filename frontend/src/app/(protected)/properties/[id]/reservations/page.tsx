import Link from "next/link";
import { requireOrganization, serverApi } from "@/lib/api/server";
import { channels } from "@/lib/api/import-types";
import { ReservationTable } from "@/components/reservation-table";
import { PropertyNav } from "@/components/property-nav";
import { FormField, PageHeader, Surface, buttonClass } from "@/components/ui";

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
  return <section className="page-stack"><PageHeader title="예약 목록" eyebrow={property.name} action={<Link className={buttonClass()} href={`/properties/${id}/reservations/new`}>예약 직접 등록</Link>} />
    <PropertyNav id={id} active="예약 목록" />
    <p className="text-sm text-slate-600">출처: 소유자 CSV / 직접 입력 · 날짜 필터는 체크인일 기준(양 끝 포함)입니다. 순매출은 총 매출에서 입력한 수수료만 차감한 값입니다.</p>
    <Surface><form className="filter-bar" aria-label="예약 목록 필터">
      <FormField label="시작일"><input className="field" type="date" name="from" defaultValue={value("from")} /></FormField>
      <FormField label="종료일"><input className="field" type="date" name="to" defaultValue={value("to")} /></FormField>
      <FormField label="채널"><select className="field" name="channel" defaultValue={value("channel")}><option value="">전체</option>
        {channels.map((channel) => <option key={channel}>{channel}</option>)}</select></FormField>
      <FormField label="상태"><select className="field" name="reservation_status" defaultValue={value("reservation_status")}>
        <option value="">전체</option><option value="CONFIRMED">확정</option><option value="CANCELLED">취소</option>
        <option value="UNKNOWN">미확인</option></select></FormField><button className={buttonClass("secondary")}>조회</button>
    </form></Surface><div className="form-actions"><p className="mr-auto">총 {result.total}건</p><Link className={buttonClass("secondary")} href={`/properties/${id}/imports/new`}>CSV 가져오기</Link><Link className={buttonClass("secondary")} href={`/properties/${id}/imports`}>가져오기 기록</Link></div><ReservationTable items={result.items} />
    <nav className="form-actions justify-end" aria-label="예약 페이지">{offset > 0 && <Link className={buttonClass("secondary")} href={page(Math.max(0, offset - 50))}>이전</Link>}
      {offset + 50 < result.total && <Link className={buttonClass("secondary")} href={page(offset + 50)}>다음</Link>}</nav>
  </section>;
}
