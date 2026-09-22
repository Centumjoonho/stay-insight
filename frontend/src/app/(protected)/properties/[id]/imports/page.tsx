import Link from "next/link";
import { requireOrganization, serverApi } from "@/lib/api/server";
import { channels } from "@/lib/api/import-types";

export default async function ImportHistory({ params, searchParams }: {
  params: Promise<{ id: string }>; searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { id } = await params;
  const org = await requireOrganization();
  const property = await serverApi.property(org.organization_id, id);
  const search = await searchParams;
  const channel = typeof search.channel === "string" ? search.channel : "";
  const offset = Math.max(0, Number(search.offset) || 0);
  const query = new URLSearchParams({ property_id: id, limit: "50", offset: String(offset) });
  if (channel) query.set("channel", channel);
  const result = await serverApi.imports(org.organization_id, query.toString());
  const page = (next: number) => "?" + new URLSearchParams({ channel, offset: String(next) });
  return <section><h1 className="text-2xl font-semibold">{property.name} · 가져오기 기록</h1>
    <Link className="underline" href={`/properties/${id}/imports/new`}>CSV 가져오기</Link>
    <form className="my-4 flex gap-3"><label>채널<select name="channel" defaultValue={channel} className="field">
      <option value="">전체</option>{channels.map((value) => <option key={value}>{value}</option>)}</select></label>
      <button className="action">조회</button></form>
    <p>총 {result.total}건</p><div className="overflow-auto"><table className="w-full text-left">
      <thead><tr>{["파일명", "채널", "가져온 날짜", "총 행", "처리", "검증 오류", "상태"].map((label) =>
        <th className="border p-2" key={label}>{label}</th>)}</tr></thead>
      <tbody>{result.items.map((item) => <tr key={item.id}>
        {[item.original_filename, item.channel, new Date(item.created_at).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" }),
          item.total_rows, item.imported_rows, item.rejected_rows,
          item.status === "COMPLETED" ? "완료" : item.status === "FAILED" ? "실패" : "처리 중"].map((value, index) =>
          <td className="border p-2" key={index}>{value}</td>)}</tr>)}</tbody></table></div>
    {!result.items.length && <p>가져오기 기록이 없습니다.</p>}
    <nav className="mt-4 flex gap-4">{offset > 0 && <Link href={page(Math.max(0, offset - 50))}>이전</Link>}
      {offset + 50 < result.total && <Link href={page(offset + 50)}>다음</Link>}
      <Link href={`/properties/${id}/reservations`}>예약 목록</Link></nav>
  </section>;
}
