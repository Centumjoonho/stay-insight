export interface AccommodationMarket {
  property_id: string;
  region: { scope_level: "SIGUNGU"; scope_name: string; assignment_method: "ADMIN_CONFIRMED" } | null;
  reference_date: string;
  window_start: string;
  window_end: string;
  market_context_available: boolean;
  reason: string | null;
  metrics: {
    open_businesses: number;
    new_licenses_12m: number | null;
    closures_12m: number | null;
    type_breakdown: Record<string, number>;
    unknown_status_count: number;
    missing_license_dates: number;
    missing_closure_dates: number;
  } | null;
  freshness: {
    source: string;
    source_dataset_name: string;
    source_url: string;
    collected_at: string | null;
    source_reference_date: string | null;
    latest_sync_status: string | null;
    stale: boolean;
    stale_after_days: number;
    live_provider_verified: boolean;
  };
  warnings: string[];
  source_category: "public";
  calculation_version: "license-market-v1";
}