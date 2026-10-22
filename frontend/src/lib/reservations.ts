import type { Reservation } from "./api/import-types";

export const reservationFields = {
  check_in: "체크인", check_out: "체크아웃", gross_revenue: "총 매출", channel_fee: "수수료",
  guest_count: "투숙인원", room_units: "객실 수", reservation_status: "상태",
} as const;
export type ReservationField = keyof typeof reservationFields;
export function reservationValues(form: FormData) {
  const text = (key: string) => String(form.get(key) ?? "").trim();
  const money = (key: string, optional = false) => {
    const value = text(key);
    if (!value && optional) return null;
    if (!/^\d{1,18}$/.test(value)) throw new Error("금액은 0 이상의 정수 원으로 입력해 주세요.");
    return BigInt(value).toString();
  };
  const count = (key: string) => {
    const value = text(key);
    if (!value) return null;
    if (!/^\d+$/.test(value) || Number(value) < 1 || Number(value) > 2147483647) throw new Error("인원·객실 수는 양의 정수여야 합니다.");
    return Number(value);
  };
  const check_in = text("check_in"), check_out = text("check_out");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(check_in) || !/^\d{4}-\d{2}-\d{2}$/.test(check_out) || check_out <= check_in) throw new Error("체크아웃은 체크인 이후여야 합니다.");
  const gross_revenue = money("gross_revenue")!, channel_fee = money("channel_fee", true);
  if (channel_fee !== null && BigInt(channel_fee) > BigInt(gross_revenue)) throw new Error("수수료는 총 매출을 초과할 수 없습니다.");
  const reservation_status = text("reservation_status");
  if (!["CONFIRMED", "CANCELLED", "UNKNOWN"].includes(reservation_status)) throw new Error("상태를 선택해 주세요.");
  return { check_in, check_out, gross_revenue, channel_fee, guest_count: count("guest_count"), room_units: count("room_units"), reservation_status: reservation_status as Reservation["reservation_status"] };
}
export function changedReservationValues(values: ReturnType<typeof reservationValues>, current: Reservation) {
  return Object.fromEntries(Object.entries(values).filter(([key, value]) => value !== current[key as ReservationField]));
}
export interface AuditEvent {
  id: string; event_type: string; change_source: "MANUAL" | "CSV_IMPORT"; actor_subject: string;
  reservation_import_id: string | null; reason: string | null; changed_fields: string[];
  before_values: Record<string, unknown>; after_values: Record<string, unknown>; created_at: string;
}
