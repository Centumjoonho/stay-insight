export interface CapacityValues { effective_from: string; effective_to: string | null; inventory_units: number }
export interface CapacityPeriod extends CapacityValues { id: string; created_at: string; updated_at: string }
export const unavailableReasons = { MAINTENANCE: "정비", OWNER_BLOCK: "소유자 사용", SALES_STOP: "판매 중지", OTHER: "기타" } as const;
export interface AvailabilityValues { unavailable_units: number; reason: keyof typeof unavailableReasons; memo: string | null }
export interface AvailabilityRecord extends AvailabilityValues { id: string; date: string }
export interface AvailabilityDay {
  date: string; base_capacity: number; unavailable_units: number; available_units: number;
  capacity_source: "history" | "estimated_property_default"; override: AvailabilityRecord | null;
}
