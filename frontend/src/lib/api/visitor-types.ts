export type VisitorCategory = { code: string; name: string };
export type DailyVisitorPoint = { date: string; value: string | null };
export type VisitorMarket = {
 property_id: string; available: boolean; reason: string | null;
 scope: { level: "SIGUNGU"; name: string; source_region_code: string } | null;
 category: VisitorCategory; categories: VisitorCategory[]; latest: DailyVisitorPoint | null;
 rolling: { average_7d: string | null; average_28d: string | null; previous_7d_average: string | null; change_7d_percent: string | null };
 history: DailyVisitorPoint[];
 source: { source: string; provider: string; dataset: string; url: string; metric_label: string; is_estimated: true; methodology: string; methodology_version: string | null; last_collected_at: string | null; latest_reference_date: string | null; days_since_latest_reference: number | null; latest_sync_status: string | null };
 coverage: { requested_days: number; available_days: number; missing_days: number; complete_7d: boolean; complete_28d: boolean; completeness: "APPLICATION_COVERAGE_ONLY" };
 warnings: string[]; calculation_version: "visitor-daily-v1"; source_category: "public";
};
