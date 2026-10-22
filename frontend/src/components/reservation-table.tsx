import Link from "next/link";
import type { Reservation } from "@/lib/api/import-types";
import { StatusBadge, Surface, buttonClass } from "@/components/ui";

const statusLabels = { CONFIRMED: "확정", CANCELLED: "취소", UNKNOWN: "미확인" };
const krw = (value: string | null) => value === null ? "미입력" : BigInt(value).toLocaleString("ko-KR") + "원";
const origin = (item: Reservation) => item.origin === "MANUAL" ? "수동 등록" : "CSV";
function ReservationStatus({ item }: { item: Reservation }) {
  return <StatusBadge tone={item.reservation_status === "CONFIRMED" ? "success" : "neutral"}>{statusLabels[item.reservation_status]}</StatusBadge>;
}
const detailUrl = (item: Reservation) => `/properties/${item.property_id}/reservations/${item.id}`;

export function ReservationMobileCard({ item }: { item: Reservation }) {
  return <Surface className="reservation-mobile-card"><h2>{item.external_reservation_id ?? "예약번호 없음"}</h2>
    <div className="flex flex-wrap gap-2"><StatusBadge>{origin(item)}</StatusBadge><ReservationStatus item={item} />{!!item.manual_protected_fields?.length && <StatusBadge tone="info">수동 보정</StatusBadge>}</div>
    <p className="text-sm text-slate-600">채널 {item.channel}</p>
    <dl className="reservation-dates"><div><dt>체크인</dt><dd>{item.check_in}</dd></div><div><dt>체크아웃</dt><dd>{item.check_out}</dd></div></dl>
    <p className="meta-text">{item.booked_nights}박 · 객실 {item.room_units ?? "미입력"} · 투숙인원 {item.guest_count ?? "미입력"}</p>
    <div className="reservation-money"><span>총 매출</span><strong>{krw(item.gross_revenue)}</strong></div>
    <p className="meta-text">수수료 {krw(item.channel_fee)} · 순매출 {krw(item.net_revenue)}</p>
    <Link className={buttonClass("secondary")} href={detailUrl(item)} aria-label={`${item.external_reservation_id ?? "예약"} 상세·수정`}>상세·수정</Link>
  </Surface>;
}
export function ReservationTable({ items }: { items: Reservation[] }) {
  if (!items.length) return <Surface><p>등록된 예약이 없습니다.</p></Surface>;
  return <><div className="reservation-desktop surface !p-0"><div className="table-scroll"><table className="data-table">
    <caption className="sr-only">예약 목록 · 소유자 예약 자료</caption><thead><tr>{["예약번호 / 출처", "채널", "체크인 / 체크아웃", "숙박일수", "투숙인원", "객실 수", "총 매출", "수수료", "순매출", "상태", "관리"].map((label, index) => <th key={label} scope="col" className={index >= 3 && index <= 8 ? "numeric" : undefined}>{label}</th>)}</tr></thead>
    <tbody>{items.map((item) => <tr key={item.id}>
      <th scope="row" className="!bg-transparent !font-normal"><span className="block max-w-52 break-all text-[13px] text-slate-800">{item.external_reservation_id ?? "없음"}</span><span className="meta-text">{origin(item)}</span></th>
      <td>{item.channel}</td><td className="whitespace-nowrap">{item.check_in}<br />{item.check_out}</td>
      <td className="numeric">{item.booked_nights}</td><td className="numeric">{item.guest_count ?? "미입력"}</td><td className="numeric" data-label="객실 수">{item.room_units ?? "미입력"}</td>
      <td className="numeric">{krw(item.gross_revenue)}</td><td className="numeric">{krw(item.channel_fee)}</td><td className="numeric">{krw(item.net_revenue)}</td>
      <td><ReservationStatus item={item} /></td><td><Link href={detailUrl(item)}>상세·수정</Link>{!!item.manual_protected_fields?.length && <StatusBadge tone="info">수동 보정</StatusBadge>}</td>
    </tr>)}</tbody></table></div></div>
    <div className="reservation-mobile">{items.map((item) => <ReservationMobileCard key={item.id} item={item} />)}</div></>;
}
