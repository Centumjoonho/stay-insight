export const channels = ["GENERIC", "AIRBNB", "BOOKING", "AGODA", "DIRECT"] as const;
export type Channel = typeof channels[number];
export type ReservationStatus = "CONFIRMED" | "CANCELLED" | "UNKNOWN";
export interface CsvPreview { encoding: string; headers: string[]; rows: string[][]; total_rows: number; warnings: string[] }
export interface RowError { row: number; field: string; message: string }
export interface ValidationResult {
  total_rows: number; valid_rows: number; invalid_rows: number;
  errors: RowError[]; errors_truncated: boolean; warnings: string[];
}
export interface ImportResult {
  id: string; property_id: string; channel: Channel; original_filename: string;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  total_rows: number; imported_rows: number; rejected_rows: number;
  inserted_rows: number; updated_rows: number; created_at: string;
  error_message: string | null; validation_errors: RowError[]; duplicate: boolean;
}
export interface Reservation {
  id: string; external_reservation_id: string; channel: Channel; import_id: string;
  check_in: string; check_out: string; booked_nights: number; guest_count: number | null;
  gross_revenue: string; channel_fee: string | null; net_revenue: string | null;
  reservation_status: ReservationStatus;
}
export interface Page<T> { items: T[]; total: number }
export type ColumnMapping = Record<string, string>;
