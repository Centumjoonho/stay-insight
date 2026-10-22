"use client";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DashboardTrend } from "@/lib/api/dashboard-types";
import { trendPoints } from "@/lib/dashboard";
import { ChartContainer } from "@/components/ui";

export function DashboardCharts({ items }: { items: DashboardTrend[] }) {
  const data = trendPoints(items);
  return <div className="analysis-grid">
    <ChartContainer title="월별 재무 추이" subtitle="매출 · 확인된 총 비용 · 확인된 영업이익 (원)">
      {!data.some(p => p.revenue !== null || p.cost !== null || p.profit !== null) ? <div className="chart-empty"><p>해당 기간의 재무 자료가 없습니다.</p><p className="meta-text">자료 없음은 매출 0원을 의미하지 않습니다.</p></div> :
      <div className="h-72 w-full"><ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <LineChart data={data} accessibilityLayer margin={{ top: 5, right: 12, bottom: 5, left: 16 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="month" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} width={80} /><Tooltip wrapperClassName="chart-tooltip" contentStyle={{border:0,borderRadius:6,fontSize:12}} /><Legend wrapperStyle={{fontSize:12}} />
          <Line name="매출" type="linear" dataKey="revenue" stroke="#244d68" strokeWidth={2} connectNulls={false} isAnimationActive={false} />
          <Line name="확인된 총 비용" type="linear" dataKey="cost" stroke="#64748b" strokeDasharray="5 3" strokeWidth={2} connectNulls={false} isAnimationActive={false} />
          <Line name="확인된 영업이익" type="linear" dataKey="profit" stroke="#6b5b8d" strokeDasharray="2 3" strokeWidth={2} connectNulls={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer></div>}
    </ChartContainer>
    <ChartContainer title="월별 점유율 추이 · 추정" subtitle="예약 자료 기반 점유율 (%)">
      {!data.some(p => p.occupancy !== null) ? <div className="chart-empty"><p>해당 기간의 점유율 자료가 없습니다.</p><p className="meta-text">자료 없는 달은 선을 연결하지 않습니다.</p></div> :
      <div className="h-72 w-full"><ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <LineChart data={data} accessibilityLayer margin={{ top: 5, right: 12, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="month" tick={{ fontSize: 11 }} />
          <YAxis domain={[0, "auto"]} tick={{ fontSize: 11 }} /><Tooltip wrapperClassName="chart-tooltip" contentStyle={{border:0,borderRadius:6,fontSize:12}} /><Legend wrapperStyle={{fontSize:12}} />
          <Line name="점유율 (%) · 추정" type="linear" dataKey="occupancy" stroke="#275f8a" strokeWidth={2} connectNulls={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer></div>}
    </ChartContainer>
  </div>;
}
