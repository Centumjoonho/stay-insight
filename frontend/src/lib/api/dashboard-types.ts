export interface DashboardPeriod { month: string; start_date: string; end_date: string; is_current_month: boolean; is_partial: boolean }
export interface DashboardFinancial {
  recognized_gross_revenue: string; manual_expense_total: string; fixed_expense_total: string; variable_expense_total: string;
  known_channel_fee_total: string; known_cost_total: string; known_operating_profit: string; known_operating_margin: string | null;
}
export interface DashboardOperations {
  reservation_count: number; occupied_room_nights: number; available_room_nights: number;
  occupancy_rate: string | null; allocated_operational_revenue: string; adr: string | null; revpar: string | null;
  average_length_of_stay: string | null; overlapping_reservation_count: number;
}
export interface DashboardQuality {
  unknown_status_count: number; overlapping_unknown_status_count: number; cancelled_reservation_count: number;
  channel_fee_known_count: number; channel_fee_missing_count: number; expense_count: number;
  has_financial_reservations: boolean; has_operational_reservations: boolean;
  warnings: { code: string; message: string }[];
}
export interface DashboardChannel {
  channel: string; reservation_count: number; recognized_gross_revenue: string;
  known_channel_fee: string | null; channel_fee_known_count: number; channel_fee_missing_count: number;
  booked_nights: number; revenue_share_percent: string | null;
}
export interface MetricDelta {
  available: boolean; absolute_delta: string | null; percentage_change: string | null; percentage_points: string | null;
}
export interface DashboardMetadata {
  calculation_version: string; source: "owner"; revenue_source: "owner_csv"; expense_source: "MANUAL";
  financial_date_basis: "check_in"; operational_date_basis: "overlapping_nights"; allocation_method: string;
  estimated_metrics: string[]; room_units_per_reservation: 1; inventory_basis: string; coverage: string; generated_at: string;
}
export interface DashboardSummary {
  property: { id: string; name: string; inventory_units: number };
  period: DashboardPeriod; financial: DashboardFinancial; operations: DashboardOperations; data_quality: DashboardQuality;
  channels: DashboardChannel[]; category_breakdown: { category: string; amount: string }[];
  metadata: DashboardMetadata;
  comparisons: Record<"previous_month" | "previous_year", { period: DashboardPeriod; metrics: Record<string, MetricDelta> }>;
}
export interface DashboardTrend {
  month: string; end_date: string; is_partial: boolean;
  recognized_gross_revenue: string; manual_expense_total: string; known_channel_fee_total: string;
  known_cost_total: string; known_operating_profit: string; occupancy_rate: string | null;
  adr: string | null; revpar: string | null; reservation_count: number;
  has_financial_reservations: boolean; has_operational_reservations: boolean; expense_count: number;
}
export interface DashboardTrends { property: DashboardSummary["property"]; metadata: DashboardMetadata; items: DashboardTrend[] }
