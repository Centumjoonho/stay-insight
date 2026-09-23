import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import { runInNewContext } from "node:vm";
import { createElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";
import type { DashboardSummary, DashboardTrend } from "../src/lib/api/dashboard-types.ts";
import * as helpers from "../src/lib/dashboard.ts";
import * as expenses from "../src/lib/api/expense-types.ts";
import * as transport from "../src/lib/api/transport.ts";

const require = createRequire(import.meta.url);
function load(path: string, dependencies: Record<string, unknown>) {
  const exports = {};
  runInNewContext(ts.transpileModule(readFileSync(new URL(path, import.meta.url), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 },
  }).outputText, { exports, process, URLSearchParams, require: (name: string) => dependencies[name] ?? require(name) });
  return exports;
}
const period = { month: "2026-09", start_date: "2026-09-01", end_date: "2026-09-23", is_current_month: true, is_partial: true };
const point = { available: true, absolute_delta: "7.2", percentage_change: null, percentage_points: "7.2" };
function fixture(): DashboardSummary {
  return {
    property: { id: "property", name: "테스트 숙소", inventory_units: 3 }, period,
    financial: { recognized_gross_revenue: "800000", manual_expense_total: "150000", fixed_expense_total: "100000",
      variable_expense_total: "50000", known_channel_fee_total: "30000", known_cost_total: "180000",
      known_operating_profit: "620000", known_operating_margin: "77.50" },
    operations: { reservation_count: 3, occupied_room_nights: 9, available_room_nights: 69, occupancy_rate: "13.04",
      allocated_operational_revenue: "900000", adr: "100000", revpar: "13043.48", average_length_of_stay: "2.67", overlapping_reservation_count: 4 },
    data_quality: { unknown_status_count: 1, overlapping_unknown_status_count: 1, cancelled_reservation_count: 0,
      channel_fee_known_count: 2, channel_fee_missing_count: 1, expense_count: 2,
      has_financial_reservations: true, has_operational_reservations: true,
      warnings: [{ code: "MISSING_CHANNEL_FEE", message: "플랫폼 수수료 정보가 없는 예약 1건" }] },
    channels: [{ channel: "GENERIC", reservation_count: 3, recognized_gross_revenue: "800000", known_channel_fee: "30000",
      channel_fee_known_count: 2, channel_fee_missing_count: 1, booked_nights: 8, revenue_share_percent: "100" }],
    category_breakdown: [{ category: "RENT", amount: "100000" }],
    comparisons: { previous_month: { period, metrics: { occupancy_rate: point } }, previous_year: { period, metrics: {} } },
    metadata: { calculation_version: "dashboard-v1", source: "owner", revenue_source: "owner_csv", expense_source: "MANUAL",
      financial_date_basis: "check_in", operational_date_basis: "overlapping_nights", allocation_method: "even",
      estimated_metrics: ["adr"], room_units_per_reservation: 1, inventory_basis: "current", coverage: "recorded", generated_at: "" },
  };
}
const trend: DashboardTrend = {
  month: "2026-09", end_date: "2026-09-23", is_partial: true,
  recognized_gross_revenue: "800000", manual_expense_total: "150000", known_channel_fee_total: "30000",
  known_cost_total: "180000", known_operating_profit: "620000", occupancy_rate: "13.04",
  adr: "100000", revpar: "13043.48", reservation_count: 3,
  has_financial_reservations: true, has_operational_reservations: true, expense_count: 2,
};
const charts = load("../src/components/dashboard-charts.tsx", {
  "@/lib/dashboard": helpers,
}) as typeof import("../src/components/dashboard-charts.tsx");
const views = load("../src/components/dashboard-view.tsx", {
  "@/lib/dashboard": helpers, "@/lib/api/expense-types": expenses, "./dashboard-charts": charts,
  "next/link": { default: ({ href, children }: { href: string; children: ReactNode }) => createElement("a", { href }, children) },
}) as typeof import("../src/components/dashboard-view.tsx");
function render(summary = fixture()) {
  return renderToStaticMarkup(createElement(views.DashboardView, {
    summary, trends: { property: summary.property, metadata: summary.metadata, items: [trend] },
  }));
}

test("dashboard formats exact KRW, fractional percentages and unavailable ratios", () => {
  assert.equal(helpers.currency("9007199254740993"), "9,007,199,254,740,993원");
  assert.equal(helpers.currency("-1234.5"), "-1,235원");
  assert.equal(helpers.percentage("68.12"), "68.1%");
  assert.equal(helpers.percentage(null), "계산 불가");
  assert.equal(helpers.comparisonText(point, "ratio"), "+7.2%p");
  assert.equal(helpers.comparisonText(undefined, "money"), "비교 데이터 없음");
  assert.equal(helpers.comparisonText({ ...point, percentage_points: null, absolute_delta: "100" }, "money"), "+100원 · 증감률 계산 불가");
});

test("month selector preserves selected month and partial-period caption without client calculations", () => {
  assert.equal(helpers.selectedMonth({ month: "2026-09" }), "2026-09");
  assert.equal(helpers.selectedMonth({}), undefined);
  for (const month of ["2026-13", "2026-9", ["2026-09", "2026-08"]]) assert.throws(() => helpers.selectedMonth({ month }));
  assert.equal(helpers.periodCaption(period), "9월 1일 ~ 9월 23일 기준 · 오늘까지 집계");
  const html = render();
  assert.match(html, /name="month"/); assert.match(html, /value="2026-09"/);
  assert.match(html, /대시보드 월 선택/); assert.match(html, /오늘까지 집계/);
});

test("dashboard renders eight KPIs, source labels, neutral percentage points and property navigation", () => {
  const html = render();
  assert.equal((html.match(/<article/g) ?? []).length, 8);
  for (const label of ["매출", "확인된 영업이익", "점유율", "ADR", "RevPAR", "운영비", "예약건수", "평균 숙박일수", "추정", "dashboard-v1"]) assert.ok(html.includes(label));
  assert.ok(html.includes("620,000원")); assert.ok(html.includes("+7.2%p"));
  for (const suffix of ["", "/reservations", "/imports/new", "/expenses"]) assert.ok(html.includes('href="/properties/property' + suffix + '"'));
  const page = readFileSync(new URL("../src/app/(protected)/properties/[id]/page.tsx", import.meta.url), "utf8");
  assert.ok(page.includes("/dashboard"));
});

test("no-data and missing-expense states disclose unavailable coverage without fake KPI cards", () => {
  const summary = fixture();
  summary.data_quality.has_financial_reservations = false;
  summary.data_quality.has_operational_reservations = false;
  summary.data_quality.expense_count = 0;
  summary.channels = [];
  const html = render(summary);
  assert.ok(html.includes("아직 분석할 예약 데이터가 없습니다."));
  assert.ok(html.includes("등록된 운영비가 없습니다."));
  assert.ok(html.includes("CSV 가져오기"));
  assert.equal((html.match(/<article/g) ?? []).length, 0);
});

test("channel breakdown and missing fees remain explicit and read-only", () => {
  const summary = fixture();
  summary.channels[0].known_channel_fee = null;
  const html = render(summary);
  for (const value of ["GENERIC", "800,000원", "100.0%", "플랫폼 수수료 정보가 없는 예약 1건", "미입력 1건", "180,000원"]) assert.ok(html.includes(value));
  assert.match(html, /<td>-<span/);
  assert.ok(!html.includes("순이익"));
});

test("financial/occupancy charts render with accessible exact trend table and genuine gaps", () => {
  const html = render();
  for (const text of ["월별 재무 추이", "월별 점유율 추이", "월별 추이 원본 수치", "2026-09", "620,000원"]) assert.ok(html.includes(text));
  assert.equal(helpers.trendPoints([trend])[0].profit, 620000);
  const gap = helpers.trendPoints([{ ...trend, has_financial_reservations: false, has_operational_reservations: false, expense_count: 0 }])[0];
  assert.equal(gap.revenue, null); assert.equal(gap.cost, null); assert.equal(gap.occupancy, null);
  assert.equal(helpers.chartNumber("9007199254740993"), null);
  assert.equal(helpers.trendPoints([{ ...trend, occupancy_rate: "130.43" }])[0].occupancy, 130.43);
});

test("dashboard server client forwards verified token/tenant, redirects 401 and preserves safe 403", async (t) => {
  const api = load("../src/lib/api/server.ts", {
    "@/lib/supabase/server": { serverAuth: async () => ({ auth: {
      getClaims: async () => ({ data: { claims: { sub: "fixture" } }, error: null }),
      getSession: async () => ({ data: { session: { access_token: "fixture-token" } } }),
    } }) },
    "next/navigation": { redirect: (path: string) => { throw new Error("redirect:" + path); } },
    "./transport": transport,
  }) as typeof import("../src/lib/api/server.ts");
  const old = process.env.API_INTERNAL_BASE_URL;
  process.env.API_INTERNAL_BASE_URL = "http://backend:8000";
  t.after(() => { if (old === undefined) delete process.env.API_INTERNAL_BASE_URL; else process.env.API_INTERNAL_BASE_URL = old; });
  let status = 200;
  const paths: string[] = [];
  t.mock.method(globalThis, "fetch", async (url: string | URL | Request, options?: RequestInit) => {
    paths.push(String(url));
    const headers = new Headers(options?.headers);
    assert.equal(headers.get("Authorization"), "Bearer fixture-token");
    assert.equal(headers.get("X-Organization-Id"), "org");
    assert.equal(options?.cache, "no-store");
    return Response.json(status === 200 ? fixture() : { detail: "private database details" }, { status });
  });
  await api.serverApi.dashboardSummary("org", "property", "2026-09");
  await api.serverApi.dashboardTrends("org", "property", "2026-09");
  assert.ok(paths[0].includes("/api/v1/dashboard/summary?property_id=property&month=2026-09"));
  assert.ok(paths[1].includes("months=12&month=2026-09"));
  status = 401;
  await assert.rejects(api.serverApi.dashboardSummary("org", "property"), /redirect:\/login/);
  status = 403;
  await assert.rejects(api.serverApi.dashboardTrends("org", "property"), (e: unknown) =>
    e instanceof transport.ApiError && e.status === 403 && !e.message.includes("database"));
});
