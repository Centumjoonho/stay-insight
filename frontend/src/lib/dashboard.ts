import type { DashboardPeriod, DashboardTrend, MetricDelta } from "./api/dashboard-types.ts";

// Exact decimal formatting only; no financial/KPI calculations in the browser.
export function decimalText(value: string | number | null, digits = 0): string {
  if (value === null) return "계산 불가";
  const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(String(value));
  if (!match) return "계산 불가";
  const fraction = (match[3] ?? "").padEnd(digits + 1, "0");
  let scaled = BigInt(match[2] + fraction.slice(0, digits));
  if (fraction[digits] >= "5") scaled += BigInt(1);
  const raw = scaled.toString().padStart(digits + 1, "0");
  const whole = digits ? raw.slice(0, -digits) : raw;
  return (match[1] && scaled !== BigInt(0) ? "-" : "") + BigInt(whole).toLocaleString("ko-KR") +
    (digits ? "." + raw.slice(-digits) : "");
}
export const currency = (value: string | null) => value === null ? "계산 불가" : decimalText(value) + "원";
export const percentage = (value: string | null) => value === null ? "계산 불가" : decimalText(value, 1) + "%";
export function periodCaption(period: DashboardPeriod) {
  const caption = (value: string) => { const [, month, day] = value.split("-"); return `${Number(month)}월 ${Number(day)}일`; };
  return `${caption(period.start_date)} ~ ${caption(period.end_date)} 기준${period.is_current_month ? " · 오늘까지 집계" : ""}`;
}
function signed(value: string, digits: number) {
  const formatted = decimalText(value, digits);
  return /^-?0(?:\.0+)?$/.test(formatted.replaceAll(",", "")) || formatted.startsWith("-") ? formatted : "+" + formatted;
}
export function comparisonText(delta: MetricDelta | undefined, kind: "money" | "count" | "ratio") {
  if (!delta?.available) return "비교 데이터 없음";
  if (delta.percentage_points !== null) return signed(delta.percentage_points, 1) + "%p";
  if (delta.percentage_change !== null) return signed(delta.percentage_change, 1) + "%";
  if (delta.absolute_delta !== null) return signed(delta.absolute_delta, kind === "ratio" ? 1 : 0) +
    (kind === "money" ? "원" : "") + " · 증감률 계산 불가";
  return "비교 데이터 없음";
}
export function selectedMonth(search: Record<string, string | string[] | undefined>): string | undefined {
  if (search.month === undefined || search.month === "") return undefined;
  if (typeof search.month !== "string" || !/^[0-9]{4}-(0[1-9]|1[0-2])$/.test(search.month)) throw new Error("월을 YYYY-MM 형식으로 선택해 주세요.");
  return search.month;
}
// Recharts requires numbers for drawing; exact source strings remain in the accessible table.
export function chartNumber(value: string | null): number | null {
  if (value === null) return null;
  const number = Number(value);
  return Number.isFinite(number) && Math.abs(number) <= Number.MAX_SAFE_INTEGER ? number : null;
}
export function trendPoints(items: DashboardTrend[]) {
  return items.map((row) => ({
    month: row.month,
    revenue: row.has_financial_reservations ? chartNumber(row.recognized_gross_revenue) : null,
    cost: row.has_financial_reservations || row.expense_count > 0 ? chartNumber(row.known_cost_total) : null,
    profit: row.has_financial_reservations ? chartNumber(row.known_operating_profit) : null,
    occupancy: row.has_operational_reservations ? chartNumber(row.occupancy_rate) : null,
  }));
}
