export type EventMarket = {
  property_id: string; available: boolean; reason: string | null;
  scope: { level: "SIGUNGU"; name: string } | null;
  from_date: string; to_date: string; reference_date: string;
  events: { source_event_id: string; title: string; start_date: string; end_date: string;
    temporal_status: "ONGOING" | "UPCOMING" | "PAST"; address: string | null;
    source_status: string | null; last_seen_at: string }[];
  total_count: number | null; truncated: boolean;
  summary: { ongoing_count: number | null; next_30_days_count: number | null };
  source: { provider: string; dataset: string; url: string; collected_at: string | null;
    latest_sync_status: string | null; coverage_start: string | null; coverage_end: string | null };
  warnings: string[]; source_category: "public";
};
