import Link from "next/link";
import type { Reservation } from "@/lib/api/import-types";
const statusLabels = { CONFIRMED: "확정", CANCELLED: "취소", UNKNOWN: "미확인" };
const krw = (value: string | null) => value === null ? "미입력" : BigInt(value).toLocaleString("ko-KR") + "원";

export function ReservationTable({ items }: { items: Reservation[] }) {
  return <div className="overflow-auto"><table className="w-full text-left"><thead><tr>
    {["출처", "예약번호", "채널", "체크인", "체크아웃", "숙박일수", "투숙인원", "객실 수", "총 매출", "수수료", "순매출", "상태"]
      .map((label) => <th className="border p-2" key={label}>{label}</th>)}
  <th scope="col" className="border p-2">관리</th></tr></thead><tbody>{items.map((item) => <tr key={item.id}>
    {[item.origin === "MANUAL" ? "수동" : "CSV", item.external_reservation_id ?? "없음", item.channel, item.check_in, item.check_out, item.booked_nights,
      item.guest_count ?? "미입력", item.room_units ?? "미입력", krw(item.gross_revenue), krw(item.channel_fee), krw(item.net_revenue),
      statusLabels[item.reservation_status]].map((value, index) => <td className="border p-2" key={index}>{value}</td>)}
  <td className="border p-2"><Link href={`/properties/${item.property_id}/reservations/${item.id}`}>상세·수정</Link>{(item.manual_protected_fields?.length ?? 0) > 0 && <span> · 수동 보정</span>}</td></tr>)}</tbody></table>{items.length === 0 && <p>등록된 예약이 없습니다.</p>}</div>;
}
