"use client";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DashboardTrend } from "@/lib/api/dashboard-types";
import { trendPoints } from "@/lib/dashboard";

export function DashboardCharts({ items }: { items: DashboardTrend[] }) {
  const data = trendPoints(items);
  return <div className="grid gap-6 xl:grid-cols-2">
    <section aria-label="월별 재무 추이" className="min-w-0 rounded-xl border border-slate-200 bg-white p-5">
      <h2 className="text-lg font-semibold">월별 재무 추이</h2><p className="mb-5 text-sm text-slate-600">매출 · 확인된 총 비용 · 확인된 영업이익 (원)</p>
      <div className="h-72 w-full"><ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <LineChart data={data} accessibilityLayer margin={{ top: 5, right: 12, bottom: 5, left: 16 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="month" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} width={80} /><Tooltip /><Legend />
          <Line name="매출" type="linear" dataKey="revenue" stroke="#2563eb" strokeWidth={2} connectNulls={false} isAnimationActive={false} />
          <Line name="확인된 총 비용" type="linear" dataKey="cost" stroke="#64748b" strokeWidth={2} connectNulls={false} isAnimationActive={false} />
          <Line name="확인된 영업이익" type="linear" dataKey="profit" stroke="#7c3aed" strokeWidth={2} connectNulls={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer></div>
    </section>
    <section aria-label="월별 점유율 추이" className="min-w-0 rounded-xl border border-slate-200 bg-white p-5">
      <h2 className="text-lg font-semibold">월별 점유율 추이 · 추정</h2><p className="mb-5 text-sm text-slate-600">등록 객실 수 기준 달력 점유율 (%)</p>
      <div className="h-72 w-full"><ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <LineChart data={data} accessibilityLayer margin={{ top: 5, right: 12, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="month" tick={{ fontSize: 11 }} />
          <YAxis domain={[0, "auto"]} tick={{ fontSize: 11 }} /><Tooltip /><Legend />
          <Line name="점유율 (%) · 추정" type="linear" dataKey="occupancy" stroke="#0891b2" strokeWidth={2} connectNulls={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer></div>
    </section>
  </div>;
}
