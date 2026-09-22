import type { Channel, ColumnMapping } from "./api/import-types.ts";

export const mappingFields = [
  ["external_reservation_id", "예약번호", true], ["check_in", "체크인", true],
  ["check_out", "체크아웃", true], ["gross_revenue", "총 매출", true],
  ["channel_fee", "플랫폼 수수료", false], ["guest_count", "투숙 인원", false],
  ["reservation_status", "상태", false],
] as const;

export function mappingErrors(mapping: ColumnMapping, headers: string[]): string[] {
  const errors: string[] = [];
  const chosen = new Set<string>();
  for (const [field, label, required] of mappingFields) {
    const value = mapping[field];
    if (!value) { if (required) errors.push(label + " 열을 연결해 주세요."); continue; }
    if (!headers.includes(value)) errors.push(label + " 열이 CSV에 없습니다.");
    if (chosen.has(value)) errors.push("각 항목에 서로 다른 CSV 열을 선택해 주세요.");
    chosen.add(value);
  }
  return errors;
}

export function importForm(file: File, propertyId: string, channel: Channel, mapping: ColumnMapping) {
  const form = new FormData();
  form.set("file", file);
  form.set("property_id", propertyId);
  form.set("channel", channel);
  form.set("column_mapping", JSON.stringify(Object.fromEntries(
    Object.entries(mapping).filter(([, value]) => value))));
  return form;
}
