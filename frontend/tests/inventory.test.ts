import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import { runInNewContext } from "node:vm";
import { JSDOM } from "jsdom";
import { act, createElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";
import * as contracts from "../src/lib/api/inventory-types.ts";
import * as helpers from "../src/lib/inventory.ts";
import * as dashboard from "../src/lib/dashboard.ts";
import * as expenses from "../src/lib/api/expense-types.ts";
import type { Reservation } from "../src/lib/api/import-types.ts";
import type { DashboardSummary } from "../src/lib/api/dashboard-types.ts";

const require = createRequire(import.meta.url);
function load(path: string, dependencies: Record<string, unknown> = {}, extra: Record<string, unknown> = {}) {
  const exports = {};
  runInNewContext(ts.transpileModule(readFileSync(new URL(path, import.meta.url), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 },
  }).outputText, { exports, Error, ...extra, require: (name: string) => dependencies[name] ?? require(name) });
  return exports;
}
const period: contracts.CapacityPeriod = { id: "capacity", effective_from: "2026-09-01", effective_to: "2026-09-30", inventory_units: 6, created_at: "", updated_at: "" };
const day: contracts.AvailabilityDay = { date: "2026-09-01", base_capacity: 6, unavailable_units: 1, available_units: 5, capacity_source: "history",
  override: { id: "override", date: "2026-09-01", unavailable_units: 1, reason: "MAINTENANCE", memo: "테스트" } };

test("capacity ranges reject overlap and allow adjacent or own edited period", () => {
  assert.match(helpers.capacityError({ ...period, effective_from: "2026-09-30" }, [period])!, /겹칩니다/);
  assert.equal(helpers.capacityError(period, [period], period.id), null);
  assert.equal(helpers.capacityError({ ...period, effective_from: "2026-10-01", effective_to: null }, [period]), null);
  assert.match(helpers.capacityError({ ...period, inventory_units: 0 }, [])!, /양의 정수/);
});

test("reservation list displays reported room units and unknown without fabricating 1", () => {
  const { ReservationTable } = load("../src/components/reservation-table.tsx") as typeof import("../src/components/reservation-table.tsx");
  const base: Reservation = { property_id: "prop", origin: "CSV_IMPORT", version: 1, manual_protected_fields: [], id: "a", external_reservation_id: "R", channel: "GENERIC", import_id: "i", check_in: "2026-09-01", check_out: "2026-09-04", booked_nights: 3, guest_count: 2, room_units: 2, gross_revenue: "100", channel_fee: "0", net_revenue: "100", reservation_status: "CONFIRMED" };
  const html = renderToStaticMarkup(createElement(ReservationTable, { items: [base, { ...base, id: "b", room_units: null }] }));
  assert.ok(html.includes("객실 수"));
  const dom = new JSDOM(html);
  const rows = dom.window.document.querySelectorAll("tbody tr");
  assert.equal(rows[0].children[7].textContent, "2");
  assert.equal(rows[1].children[7].textContent, "미입력");
  dom.window.close();
});

test("inventory forms create/edit/delete with tenant scope, overlap feedback and refresh", async (t) => {
  const dom = new JSDOM("<!doctype html><div id='root'></div>", { url: "http://localhost:3000" });
  const previous = new Map<string, PropertyDescriptor | undefined>();
  for (const [name, value] of Object.entries({ window: dom.window, document: dom.window.document, HTMLElement: dom.window.HTMLElement, IS_REACT_ACT_ENVIRONMENT: true })) {
    previous.set(name, Object.getOwnPropertyDescriptor(globalThis, name));
    Object.defineProperty(globalThis, name, { configurable: true, writable: true, value });
  }
  const { createRoot } = await import("react-dom/client");
  const root = createRoot(dom.window.document.getElementById("root")!);
  t.after(async () => {
    await act(async () => root.unmount()); dom.window.close();
    for (const [name, descriptor] of previous) { if (descriptor) Object.defineProperty(globalThis, name, descriptor); else Reflect.deleteProperty(globalThis, name); }
  });
  const calls: string[] = [];
  let refresh = 0;
  const api = {
    saveCapacity: async (org: string, prop: string, body: contracts.CapacityValues, id?: string) => {
      assert.equal(org,"org"); assert.equal(prop,"prop"); assert.ok(body.inventory_units > 0); calls.push(id ? "editCapacity" : "createCapacity");
    },
    deleteCapacity: async () => { calls.push("deleteCapacity"); },
    saveAvailability: async (org: string, prop: string, date: string, body: contracts.AvailabilityValues) => {
      assert.equal(org,"org"); assert.equal(prop,"prop"); assert.equal(date,day.date); calls.push("availability:"+body.unavailable_units);
    },
    deleteAvailability: async () => { calls.push("deleteAvailability"); },
  };
  const { InventoryManager } = load("../src/components/inventory-manager.tsx", {
    "@/lib/api/inventory-types": contracts, "@/lib/inventory": helpers, "@/lib/api/client": { businessApi: api },
    "next/navigation": { useRouter: () => ({ refresh: () => { refresh++; } }) },
  }, { window: dom.window }) as typeof import("../src/components/inventory-manager.tsx");
  const doc = dom.window.document;
  const render = async (periods: contracts.CapacityPeriod[], key: string) => act(async () => root.render(createElement(InventoryManager, { key, organizationId:"org",propertyId:"prop",periods,days:[day],today:day.date })));
  const submit = async (label: string) => act(async () => { doc.querySelector(`form[aria-label="${label}"]`)!.dispatchEvent(new dom.window.Event("submit", {bubbles:true,cancelable:true})); });
  const click = async (prefix: string) => act(async () => { const button = [...doc.querySelectorAll("button")].find((b) => b.textContent?.startsWith(prefix)); assert.ok(button,prefix); button.click(); });
  await render([], "new");
  await submit("객실 수 이력 입력"); assert.ok(calls.includes("createCapacity"));
  await submit("판매 제외 입력"); assert.ok(calls.includes("availability:0"));
  await render([period],"existing");
  await submit("객실 수 이력 입력"); assert.match(doc.querySelector('[role="alert"]')!.textContent!, /겹칩니다/);
  await click("수정 2026-09-01 객실 이력");
  await submit("객실 수 이력 입력"); assert.ok(calls.includes("editCapacity"));
  await click("수정 2026-09-01 판매 제외");
  await submit("판매 제외 입력"); assert.ok(calls.includes("availability:1"));
  await click("삭제 2026-09-01 판매 제외"); assert.ok(!calls.includes("deleteAvailability"));
  await click("삭제 취소"); assert.ok(!calls.includes("deleteAvailability"));
  await click("삭제 2026-09-01 판매 제외"); await click("삭제 확인"); assert.ok(calls.includes("deleteAvailability"));
  await click("삭제 2026-09-01 객실 이력"); await click("삭제 확인"); assert.ok(calls.includes("deleteCapacity"));
  assert.equal(refresh,6);
  assert.ok(doc.querySelectorAll("label input").length >= 7);
  assert.ok(doc.querySelector('th[scope="col"]'));
});

test("dashboard-v2 renders calculated KPIs, fallback/overcapacity and null denominator without old claims", () => {
  const { DashboardView } = load("../src/components/dashboard-view.tsx", {
    "@/lib/dashboard": dashboard, "@/lib/api/expense-types": expenses,
    "./dashboard-charts": { DashboardCharts: () => null },
    "next/link": { default: ({href,children}:{href:string;children:ReactNode}) => createElement("a",{href},children) },
  }) as typeof import("../src/components/dashboard-view.tsx");
  const p={month:"2026-09",start_date:"2026-09-01",end_date:"2026-09-10",is_current_month:true,is_partial:true};
  const summary: DashboardSummary = {
    property:{id:"p",name:"test",inventory_units:10},period:p,
    financial:{recognized_gross_revenue:"100",manual_expense_total:"0",fixed_expense_total:"0",variable_expense_total:"0",known_channel_fee_total:"10",known_cost_total:"10",known_operating_profit:"90",known_operating_margin:"90"},
    operations:{reservation_count:1,occupied_room_nights:6,available_room_nights:98,occupancy_rate:"6.12",allocated_operational_revenue:"100",adr:"16.67",revpar:"1.02",average_length_of_stay:"3",overlapping_reservation_count:1},
    data_quality:{unknown_status_count:0,overlapping_unknown_status_count:0,cancelled_reservation_count:0,channel_fee_known_count:1,channel_fee_missing_count:0,expense_count:0,has_financial_reservations:true,has_operational_reservations:true,warnings:[{code:"CAPACITY_FALLBACK",message:"객실 수 이력이 없는 2일은 숙소 기본 객실 수로 추정했습니다."},{code:"OVERCAPACITY",message:"예약 객실 수가 가용 객실 수를 초과한 날짜가 1일입니다."}]},
    channels:[],category_breakdown:[],comparisons:{previous_month:{period:p,metrics:{}},previous_year:{period:p,metrics:{}}},
    metadata:{calculation_version:"dashboard-v2",source:"owner",revenue_source:"owner_csv",expense_source:"MANUAL",financial_date_basis:"check_in",operational_date_basis:"overlapping_nights",allocation_method:"gross_times_overlap_divided_by_booked_nights",estimated_metrics:["adr"],room_units_basis:"reported_or_estimated_one",inventory_basis:"effective_capacity_minus_unavailable",coverage:"recorded_data_only",generated_at:""}
  };
  const render=()=>renderToStaticMarkup(createElement(DashboardView,{summary,trends:{property:summary.property,metadata:summary.metadata,items:[]}}));
  const html=render();
  for(const label of ["dashboard-v2","6.1%","98박","객실 운영","기본 객실 수로 추정","초과한 날짜","예약 채널별 매출","확인된 비용 구성"]) assert.ok(html.includes(label),label);
  assert.ok(!html.includes("일정은 아직 반영되지 않습니다"));
  summary.operations.available_room_nights=0;summary.operations.occupancy_rate=null;summary.operations.revpar=null;
  assert.ok(render().includes("계산 불가"));
});
