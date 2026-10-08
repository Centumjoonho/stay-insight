import type { CapacityPeriod, CapacityValues } from "./api/inventory-types.ts";

export function capacityError(values: CapacityValues, rows: CapacityPeriod[], editing?: string): string | null {
  if (!Number.isInteger(values.inventory_units) || values.inventory_units < 1 || values.inventory_units > 2147483647)
    return "객실 수는 양의 정수로 입력해 주세요.";
  if (!values.effective_from || (values.effective_to && values.effective_to < values.effective_from))
    return "종료일은 시작일 이후여야 합니다.";
  if (rows.some((r) => r.id !== editing && r.effective_from <= (values.effective_to || "9999-12-31") &&
      (!r.effective_to || r.effective_to >= values.effective_from)))
    return "객실 수 이력의 기간이 겹칩니다. 기존 기간을 먼저 수정해 주세요.";
  return null;
}
