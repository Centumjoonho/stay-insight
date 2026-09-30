"use client";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DailyVisitorPoint } from "@/lib/api/visitor-types";
export function VisitorChart({ history }: { history: DailyVisitorPoint[] }) {
 const points = history.map(p => ({ ...p, value: p.value === null ? null : Number(p.value) }));
 return <div role="img" aria-label="일별 추정 방문자 추이. 같은 자료를 아래 표에서 확인할 수 있습니다." className="h-72 min-w-0">
 <ResponsiveContainer width="100%" height="100%"><LineChart data={points}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="date" minTickGap={50} /><YAxis width={80} /><Tooltip />
 <Line dataKey="value" name="추정 방문자" stroke="#2563eb" dot={false} connectNulls={false} isAnimationActive={false} />
 </LineChart></ResponsiveContainer></div>;
}
